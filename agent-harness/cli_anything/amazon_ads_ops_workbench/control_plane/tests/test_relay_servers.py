"""SSH server management end to end against an in-process mock SSH server.

The mock runs commands in a local shell whose PATH has test doubles for sudo,
systemctl, useradd, chown and userdel, and every installed file lands under a
temporary root, so nothing outside the temp directory is touched.

ADS_TEST_EMPTY_DATABASE=1 python -m unittest \
 cli_anything.amazon_ads_ops_workbench.control_plane.tests.test_relay_servers -v
"""

import io
import json
import os
import secrets
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import paramiko
from sqlalchemy import delete, select, func

from ...core.client import AmazonAdsClient
from ..database import Database
from ..models import Account, Audit, RelayServer, Session, Task, User
from ..security import Actor, Problem, password_hash
from ..service import Service
from ..settings import Settings
from .test_relay import free_port

FAKES = {
    "sudo": r"""#!/bin/sh
# sudo [-n] [-S -k -p PROMPT] cmd...
while [ $# -gt 0 ]; do
  case "$1" in
    -n) [ "$MOCK_SUDO" = nopasswd ] || exit 1; shift;;
    -k) shift;;
    -p) shift 2;;
    -S) IFS= read -r pw; [ "$MOCK_SUDO" = password ] && [ "$pw" = "$MOCK_SUDO_PASSWORD" ] || exit 1; shift;;
    *) break;;
  esac
done
[ "$MOCK_SUDO" = none ] && exit 1
exec "$@"
""",
    "systemctl": r"""#!/bin/sh
quiet=0; now=0; args=""
for a in "$@"; do case "$a" in --quiet) quiet=1;; --now) now=1;; *) args="$args $a";; esac; done
set -- $args
unit="$MOCK_ROOT/etc/systemd/system/ads-relay.service"
alive() { [ -f "$MOCK_STATE/pid" ] && kill -0 "$(cat "$MOCK_STATE/pid")" 2>/dev/null; }
case "$1" in
  --version) echo "systemd 252 (mock)";;
  daemon-reload|enable) ;;
  disable) if [ $now = 1 ] && alive; then kill "$(cat "$MOCK_STATE/pid")"; rm -f "$MOCK_STATE/pid"; fi;;
  restart)
    if alive; then kill "$(cat "$MOCK_STATE/pid")"; sleep 0.3; fi
    cmd=$(sed -n 's/^ExecStart=//p' "$unit")
    nohup $cmd </dev/null >"$MOCK_STATE/log" 2>&1 &
    echo $! > "$MOCK_STATE/pid"; sleep 0.5;;
  is-active) if alive; then [ $quiet = 1 ] || echo active; exit 0; else [ $quiet = 1 ] || echo inactive; exit 3; fi;;
esac
""",
    "useradd": "#!/bin/sh\nexit 0\n",
    "userdel": "#!/bin/sh\nexit 0\n",
    "chown": "#!/bin/sh\nexit 0\n",
    "journalctl": "#!/bin/sh\ncat \"$MOCK_STATE/log\" 2>/dev/null\n",
}


class MockSSH(paramiko.ServerInterface):
    def __init__(self, user, password, client_key, env):
        self.user, self.password, self.client_key, self.env = user, password, client_key, env

    def get_allowed_auths(self, username):
        return "password,publickey"

    def check_auth_password(self, username, password):
        ok = username == self.user and password == self.password
        return paramiko.AUTH_SUCCESSFUL if ok else paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        ok = username == self.user and key.asbytes() == self.client_key.asbytes()
        return paramiko.AUTH_SUCCESSFUL if ok else paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        threading.Thread(target=self.execute, args=(channel, command.decode()), daemon=True).start()
        return True

    def execute(self, channel, command):
        proc = subprocess.Popen(
            ["/bin/sh", "-c", command], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=self.env, cwd=self.env["HOME"],
        )

        def feed():
            try:
                while True:
                    data = channel.recv(65536)
                    if not data:
                        break
                    proc.stdin.write(data)
                    proc.stdin.flush()
            except (OSError, BrokenPipeError):
                pass
            finally:
                try:
                    proc.stdin.close()
                except OSError:
                    pass

        def drain(stream, send):
            for chunk in iter(lambda: stream.read1(65536), b""):
                send(chunk)

        threads = [
            threading.Thread(target=feed, daemon=True),
            threading.Thread(target=drain, args=(proc.stdout, channel.sendall), daemon=True),
            threading.Thread(target=drain, args=(proc.stderr, channel.sendall_stderr), daemon=True),
        ]
        for t in threads:
            t.start()
        threads[1].join()
        threads[2].join()
        proc.stdout.close()
        proc.stderr.close()
        channel.send_exit_status(proc.wait())
        channel.close()


class MockSSHServer:
    def __init__(self, base, user, password, client_key):
        self.base = Path(base)
        self.host_key = paramiko.RSAKey.generate(2048)
        self.user, self.password, self.client_key = user, password, client_key
        fakebin = self.base / "bin"
        fakebin.mkdir(parents=True, exist_ok=True)
        for name, body in FAKES.items():
            (fakebin / name).write_text(body)
            (fakebin / name).chmod(0o755)
        (fakebin / "python3").symlink_to(sys.executable)
        (self.base / "root").mkdir(exist_ok=True)
        (self.base / "state").mkdir(exist_ok=True)
        (self.base / "home").mkdir(exist_ok=True)
        self.env = {
            "PATH": f"{fakebin}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(self.base / "home"),
            "TMPDIR": str(self.base / "home"),
            "MOCK_ROOT": str(self.base / "root"),
            "MOCK_STATE": str(self.base / "state"),
            "MOCK_SUDO": "password",
            "MOCK_SUDO_PASSWORD": password,
        }
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(20)
        self.port = self.sock.getsockname()[1]
        self.transports = []
        threading.Thread(target=self.accept, daemon=True).start()

    def accept(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            t = paramiko.Transport(conn)
            t.add_server_key(self.host_key)
            self.transports.append(t)
            try:
                t.start_server(server=MockSSH(self.user, self.password, self.client_key, self.env))
            except (paramiko.SSHException, EOFError):
                continue

    def stop_relay(self):
        pid = self.base / "state" / "pid"
        if pid.exists():
            try:
                os.kill(int(pid.read_text()), signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass

    def close(self):
        self.stop_relay()
        self.sock.close()
        for t in self.transports:
            t.close()


class RelayServers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("ADS_TEST_EMPTY_DATABASE") != "1":
            raise RuntimeError("Explicit empty NEW database test flag required")
        cls.settings = Settings.load()
        cls.db = Database(cls.settings)
        if "ads_control" not in cls.settings.database_url:
            raise RuntimeError("Unexpected database name")
        with cls.db.sessions() as s:
            if s.scalar(select(func.count()).select_from(Account)):
                raise RuntimeError("Database is not empty; do not run fixtures against user data")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.client_key = paramiko.ECDSAKey.generate()
        self.password = "ssh-pass-" + secrets.token_hex(4)
        self.ssh = MockSSHServer(self.tmp.name, "deploy", self.password, self.client_key)
        self.service = Service(self.db, self.settings)
        self.service.relay_root = self.ssh.env["MOCK_ROOT"]
        self.service.relay_listen = "127.0.0.1"
        with self.db.sessions.begin() as s:
            user = User(username="relay-" + secrets.token_hex(6), password_hash=password_hash("fixture-password-123"))
            s.add(user)
            s.flush()
            self.user_id = user.id
        self.actor = Actor(self.user_id, "session")
        self.account = self.service.add_account(
            self.actor,
            {
                "label": "relay fixture", "region": "NA", "marketplace": "US", "profile_id": "123",
                "client_id": "fixture-client-id", "client_secret": "fixture-client-secret",
                "refresh_token": "fixture-refresh-token",
            },
        )

    def tearDown(self):
        self.ssh.close()
        with self.db.sessions.begin() as s:
            for model in (Audit, Task, Account, RelayServer):
                s.execute(delete(model).where(model.owner_id == self.user_id))
            s.execute(delete(Session).where(Session.user_id == self.user_id))
            s.execute(delete(User).where(User.id == self.user_id))
        self.tmp.cleanup()

    def add(self, **extra):
        data = {
            "name": "mock-" + secrets.token_hex(3), "host": "127.0.0.1", "ssh_port": self.ssh.port,
            "username": "deploy", "auth_type": "password", "password": self.password,
            "relay_port": free_port(),
        }
        data.update(extra)
        return self.service.add_server(self.actor, data)

    def checks(self, result):
        return {c["key"]: c for c in result["checks"]}

    def test_password_server_install_bind_and_uninstall(self):
        server = self.add()
        self.assertNotIn(self.password, json.dumps(server))
        with self.db.sessions() as s:
            row = s.get(RelayServer, server["id"])
            self.assertNotIn(self.password, row.credentials_ciphertext)

        tested = self.service.test_server(self.actor, server["id"])
        self.assertEqual(tested["status"], "READY", tested)
        self.assertTrue(tested["host_fingerprint"].startswith("SHA256:"))
        self.assertIn("sudo（使用 SSH 密码）", self.checks(tested)["privilege"]["detail"])
        self.assertTrue(any("安全组" in line for line in tested["plan"]))

        installed = self.service.install_server(self.actor, server["id"])
        self.assertEqual(installed["status"], "INSTALLED", installed)
        self.assertTrue(installed["installed"])
        self.assertTrue(self.checks(installed)["tls"]["ok"], installed)
        root = Path(self.ssh.env["MOCK_ROOT"])
        config = json.loads((root / "etc/ads-relay/config.json").read_text())
        self.assertEqual(stat.S_IMODE((root / "etc/ads-relay/key.pem").stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE((root / "etc/ads-relay/config.json").stat().st_mode), 0o640)
        unit = (root / "etc/systemd/system/ads-relay.service").read_text()
        self.assertIn("User=ads-relay", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertEqual(list(Path(self.ssh.env["HOME"]).glob("tmp.*")), [])  # staged script removed
        with self.db.sessions() as s:
            row = s.get(RelayServer, server["id"])
            self.assertNotIn(config["secret"], row.relay_secret_ciphertext)

        retested = self.service.test_server(self.actor, server["id"])
        self.assertEqual(retested["status"], "INSTALLED")
        self.assertTrue(self.checks(retested)["relay"]["ok"])

        # Bound account: every Amazon call leaves from the relay.
        self.service.set_account_relay(self.actor, self.account["id"], server["id"])
        with self.db.sessions() as s:
            env = self.service.environment(s.get(Account, self.account["id"]))
        self.assertEqual(env.relay.id, server["id"])
        self.assertEqual(env.relay.port, config["port"])
        with self.assertRaises(Problem) as ctx:
            self.service.uninstall_server(self.actor, server["id"])
        self.assertEqual(ctx.exception.status, 409)
        with self.assertRaises(Problem):
            self.service.delete_server(self.actor, server["id"])
        with self.assertRaises(Problem) as ctx:
            self.service.update_server(self.actor, server["id"], {"relay_port": free_port()})
        self.assertEqual(ctx.exception.status, 409)

        self.service.set_account_relay(self.actor, self.account["id"], None)
        removed = self.service.uninstall_server(self.actor, server["id"])
        self.assertEqual(removed["status"], "NEW", removed)
        self.assertFalse(removed["installed"])
        self.assertFalse((root / "etc/ads-relay").exists())
        self.assertFalse((root / "etc/systemd/system/ads-relay.service").exists())
        with self.assertRaises(Problem) as ctx:
            self.service.set_account_relay(self.actor, self.account["id"], server["id"])
        self.assertEqual(ctx.exception.status, 409)
        self.service.delete_server(self.actor, server["id"])
        self.assertEqual(self.service.servers(self.actor), [])

    def test_bound_relay_that_disappears_never_falls_back_to_direct(self):
        server = self.add()
        self.service.install_server(self.actor, server["id"])
        self.service.set_account_relay(self.actor, self.account["id"], server["id"])
        with self.db.sessions.begin() as s:
            s.get(RelayServer, server["id"]).relay_secret_ciphertext = None
        with self.db.sessions() as s:
            a = s.get(Account, self.account["id"])
        with self.assertRaises(Problem) as ctx:
            self.service.environment(a)
        self.assertEqual(ctx.exception.status, 409)

    def test_installed_relay_carries_real_client_calls(self):
        server = self.add()
        self.assertEqual(self.service.install_server(self.actor, server["id"])["status"], "INSTALLED")
        self.service.set_account_relay(self.actor, self.account["id"], server["id"])
        with self.db.sessions() as s:
            env = self.service.environment(s.get(Account, self.account["id"]))
        # Fake credentials: Amazon (reached from the relay process) must reject them.
        with self.assertRaises(RuntimeError) as ctx:
            AmazonAdsClient(env).exchange_refresh_token()
        self.assertRegex(str(ctx.exception), r"OAuth token exchange failed: (4\d\d|转发服务器)")
        self.service.set_account_relay(self.actor, self.account["id"], None)

    def test_key_auth_with_passphrase_and_privilege_rules(self):
        buf = io.StringIO()
        self.client_key.write_private_key(buf, password="pp-secret")
        with self.assertRaises(Problem) as ctx:
            self.add(auth_type="key", private_key=buf.getvalue(), password=None)
        self.assertIn("口令", ctx.exception.message if hasattr(ctx.exception, "message") else str(ctx.exception))
        with self.assertRaises(Problem):
            self.add(auth_type="key", private_key=buf.getvalue(), passphrase="wrong", password=None)
        server = self.add(auth_type="key", private_key=buf.getvalue(), passphrase="pp-secret", password=None)
        # Key login cannot answer a sudo password prompt.
        tested = self.service.test_server(self.actor, server["id"])
        self.assertEqual(tested["status"], "BLOCKED", tested)
        self.assertFalse(self.checks(tested)["privilege"]["ok"])
        self.ssh.env["MOCK_SUDO"] = "nopasswd"
        tested = self.service.test_server(self.actor, server["id"])
        self.assertEqual(tested["status"], "READY", tested)
        self.assertEqual(self.service.install_server(self.actor, server["id"])["status"], "INSTALLED")

    def test_wrong_password_and_host_key_change(self):
        bad = self.add(password="nope")
        failed = self.service.test_server(self.actor, bad["id"])
        self.assertEqual(failed["status"], "ERROR")
        self.assertIn("认证失败", failed["message"])

        server = self.add()
        first = self.service.test_server(self.actor, server["id"])["host_fingerprint"]
        self.ssh.host_key = paramiko.RSAKey.generate(2048)  # "server reinstalled / MITM"
        changed = self.service.test_server(self.actor, server["id"])
        self.assertEqual(changed["status"], "ERROR")
        self.assertIn("指纹", changed["message"])
        self.assertEqual(changed["host_fingerprint"], first)
        self.service.update_server(self.actor, server["id"], {"reset_host_key": True})
        again = self.service.test_server(self.actor, server["id"])
        self.assertEqual(again["status"], "READY")
        self.assertNotEqual(again["host_fingerprint"], first)

    def test_validation(self):
        for bad in ({"host": "a b"}, {"username": "-oProxy"}, {"relay_port": 80}, {"auth_type": "password", "password": ""}):
            with self.assertRaises(Problem):
                self.add(**bad)
        with self.assertRaises(Problem) as ctx:
            self.service.servers(Actor(self.user_id, "token", frozenset({"ads:read"}), (), "t"))
        self.assertEqual(ctx.exception.status, 403)


if __name__ == "__main__":
    unittest.main()
