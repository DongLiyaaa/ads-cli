"""SSH management of relay servers: probe, install and remove ads-relay."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import secrets
import shlex
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import paramiko
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from ..core import relay_agent

SERVICE = "ads-relay"
MIN_PYTHON = (3, 6)


class SSHFailure(Exception):
    """Message is safe to show: never contains credentials."""


def openssh_fingerprint(key: paramiko.PKey) -> str:
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def load_private_key(text: str, passphrase: str | None) -> paramiko.PKey:
    last = None
    for kind in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
        try:
            return kind.from_private_key(io.StringIO(text), password=passphrase or None)
        except paramiko.PasswordRequiredException:
            raise SSHFailure("私钥已加密，请填写私钥口令") from None
        except (paramiko.SSHException, ValueError) as exc:
            last = exc
    if last and "password" in str(last).lower():
        raise SSHFailure("私钥口令不正确")
    raise SSHFailure("无法解析私钥，请粘贴 OpenSSH / PEM 格式的完整私钥")


class PinnedHostKey(paramiko.MissingHostKeyPolicy):
    """Trust on first use; afterwards the stored key must match exactly."""

    def __init__(self, expected: str | None):
        self.expected, self.seen = expected, None

    def missing_host_key(self, client, hostname, key):
        self.seen = f"{key.get_name()} {key.get_base64()}"
        if self.expected and not secrets.compare_digest(self.expected, self.seen):
            raise SSHFailure(
                "服务器 SSH 指纹与首次连接时记录的不一致（服务器重装或存在中间人）；"
                "确认无误后在编辑服务器时勾选“重置指纹”"
            )
        self.fingerprint = openssh_fingerprint(key)


class Remote:
    """One SSH session; use as a context manager."""

    def __init__(self, host, port, username, auth_type, credentials, host_key=None):
        self.host, self.port, self.username = host, port, username
        self.auth_type, self.credentials = auth_type, credentials
        self.policy = PinnedHostKey(host_key)
        self.client = None

    def __enter__(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(self.policy)
        auth = (
            {"password": self.credentials["password"]}
            if self.auth_type == "password"
            else {"pkey": load_private_key(self.credentials["private_key"], self.credentials.get("passphrase"))}
        )
        try:
            client.connect(
                self.host,
                self.port,
                self.username,
                timeout=10,
                banner_timeout=15,
                auth_timeout=15,
                allow_agent=False,
                look_for_keys=False,
                **auth,
            )
        except SSHFailure:
            client.close()
            raise
        except paramiko.AuthenticationException:
            client.close()
            raise SSHFailure("SSH 认证失败：用户名、密码或私钥不正确") from None
        except (socket.timeout, TimeoutError):
            client.close()
            raise SSHFailure(f"连接 {self.host}:{self.port} 超时，请检查地址、端口和安全组") from None
        except (OSError, paramiko.SSHException) as exc:
            client.close()
            raise SSHFailure(f"无法连接 {self.host}:{self.port}：{exc}") from None
        self.client = client
        return self

    def __exit__(self, *exc):
        self.client.close()

    @property
    def host_key(self):
        return self.policy.seen

    @property
    def fingerprint(self):
        return getattr(self.policy, "fingerprint", "")

    def run(self, command: str, stdin: bytes = b"", timeout: int = 120):
        try:
            channel = self.client.get_transport().open_session(timeout=15)
            channel.settimeout(timeout)
            channel.exec_command(command)
            if stdin:
                channel.sendall(stdin)
            channel.shutdown_write()
            out, err = bytearray(), bytearray()
            while True:
                if channel.recv_ready():
                    out += channel.recv(65536)
                elif channel.recv_stderr_ready():
                    err += channel.recv_stderr(65536)
                elif channel.exit_status_ready():
                    break
                else:
                    channel.status_event.wait(0.05)
            while channel.recv_ready():
                out += channel.recv(65536)
            while channel.recv_stderr_ready():
                err += channel.recv_stderr(65536)
            code = channel.recv_exit_status()
            channel.close()
        except (socket.timeout, TimeoutError):
            raise SSHFailure("远端命令执行超时") from None
        except (OSError, paramiko.SSHException) as exc:
            raise SSHFailure(f"远端命令执行失败：{exc}") from None
        return code, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def probe_script(port: int, root: str) -> str:
    q = shlex.quote
    return f"""
echo "uname=$(uname -sm 2>/dev/null)"
echo "os=$( (. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME") || uname -s)"
if [ "$(id -u)" = 0 ]; then echo "sudo=root"
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then echo "sudo=nopasswd"
elif command -v sudo >/dev/null 2>&1; then echo "sudo=password"
else echo "sudo=none"; fi
PY=$(command -v python3 2>/dev/null)
echo "python=$PY"
if [ -n "$PY" ]; then
  echo "python_version=$("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
  echo "port_free=$("$PY" -c 'import socket, sys
s = socket.socket()
try:
    s.bind(("0.0.0.0", int(sys.argv[1]))); print("yes")
except OSError:
    print("no")' {int(port)})"
fi
echo "systemd=$(systemctl --version 2>/dev/null | head -n1)"
echo "tools=$(for t in base64 useradd chown; do command -v $t >/dev/null 2>&1 || printf '%s ' $t; done)"
echo "relay_active=$(systemctl is-active {SERVICE} 2>/dev/null)"
echo "relay_installed=$([ -f {q(root + '/etc/systemd/system/' + SERVICE + '.service')} ] && echo yes || echo no)"
echo "relay_version=$(cat {q(root + '/opt/ads-relay/VERSION')} 2>/dev/null)"
"""


def parse_facts(output: str) -> dict:
    facts = {}
    for line in output.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            facts[key.strip()] = value.strip()
    return facts


def version_tuple(text):
    try:
        return tuple(int(x) for x in text.split(".")[:2])
    except ValueError:
        return (0, 0)


def evaluate(facts: dict, auth_type: str, fingerprint: str) -> list[dict]:
    def check(key, label, ok, detail, required=True):
        return {"key": key, "label": label, "ok": ok, "detail": detail, "required": required}

    sudo = facts.get("sudo", "none")
    privilege_ok = sudo in {"root", "nopasswd"} or (sudo == "password" and auth_type == "password")
    privilege = {
        "root": "root 用户",
        "nopasswd": "免密 sudo",
        "password": "sudo（使用 SSH 密码）" if auth_type == "password" else "sudo 需要密码，私钥登录无法提供；请用 root 或配置免密 sudo",
        "none": "非 root 且没有 sudo",
    }[sudo if sudo in {"root", "nopasswd", "password"} else "none"]
    py = facts.get("python_version", "")
    active = facts.get("relay_active") == "active"
    missing = facts.get("tools", "").split()
    port_ok = facts.get("port_free") == "yes" or active
    return [
        check("ssh", "SSH 连接", True, f"已登录，主机指纹 {fingerprint}"),
        check("os", "操作系统", True, f"{facts.get('os', '')} · {facts.get('uname', '')}".strip(" ·"), False),
        check("privilege", "安装权限", privilege_ok, privilege),
        check(
            "python",
            "Python 3",
            version_tuple(py) >= MIN_PYTHON,
            f"{facts.get('python')} ({py})" if py else "未找到 python3（需要 3.6 以上）",
        ),
        check("systemd", "systemd", bool(facts.get("systemd")), facts.get("systemd") or "未找到 systemctl"),
        check("tools", "系统工具", not missing, "base64 / useradd / chown 齐全" if not missing else "缺少：" + " ".join(missing)),
        check(
            "port",
            "转发端口",
            port_ok,
            "端口空闲" if facts.get("port_free") == "yes" else ("由 ads-relay 自身占用" if active else "端口已被其他程序占用，请换一个端口"),
        ),
        check(
            "relay",
            "转发服务",
            active,
            f"运行中（版本 {facts.get('relay_version') or '?'}）"
            if active
            else ("已安装但未运行" if facts.get("relay_installed") == "yes" else "未安装"),
            False,
        ),
    ]


def privilege(facts: dict, auth_type: str, credentials: dict):
    """(command prefix, stdin prefix) to run the install script as root."""
    sudo = facts.get("sudo")
    if sudo == "root":
        return "", b""
    if sudo == "nopasswd":
        return "sudo -n ", b""
    if sudo == "password" and auth_type == "password":
        # -k forces the prompt, so the password line can never reach the script.
        return "sudo -S -k -p '' ", credentials["password"].encode() + b"\n"
    raise SSHFailure("需要 root 用户或免密 sudo 才能安装 systemd 服务")


def make_certificate():
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, SERVICE)])
    start = datetime.now(timezone.utc) - timedelta(days=1)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(start + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    der = cert.public_bytes(serialization.Encoding.DER)
    return (
        cert.public_bytes(serialization.Encoding.PEM),
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        hashlib.sha256(der).hexdigest(),
    )


def install_script(root: str, port: int, secret: str, cert_pem: bytes, key_pem: bytes, listen: str = "0.0.0.0") -> str:
    q = shlex.quote
    config = json.dumps(
        {
            "listen": listen,
            "port": int(port),
            "secret": secret,
            "cert": f"{root}/etc/ads-relay/cert.pem",
            "key": f"{root}/etc/ads-relay/key.pem",
        }
    ).encode()
    agent = Path(relay_agent.__file__).read_bytes()

    def put(path, data):
        encoded = base64.encodebytes(data).decode()
        return f'base64 -d > {q(root + path)} <<\'ADS_RELAY_EOF\'\n{encoded}ADS_RELAY_EOF\n'

    unit = root + f"/etc/systemd/system/{SERVICE}.service"
    return f"""set -eu
PY=$(command -v python3)
if ! id -u {SERVICE} >/dev/null 2>&1; then
  useradd --system --no-create-home --home-dir /nonexistent --shell "$(command -v nologin || echo /bin/false)" {SERVICE}
fi
mkdir -p {q(root + '/opt/ads-relay')} {q(root + '/etc/ads-relay')} {q(root + '/etc/systemd/system')}
umask 027
{put('/opt/ads-relay/ads_relay.py', agent)}{put('/opt/ads-relay/VERSION', relay_agent.VERSION.encode())}{put('/etc/ads-relay/config.json', config)}{put('/etc/ads-relay/cert.pem', cert_pem)}{put('/etc/ads-relay/key.pem', key_pem)}chmod 755 {q(root + '/opt/ads-relay')}
chmod 644 {q(root + '/opt/ads-relay/ads_relay.py')} {q(root + '/opt/ads-relay/VERSION')} {q(root + '/etc/ads-relay/cert.pem')}
chown root:{SERVICE} {q(root + '/etc/ads-relay')} {q(root + '/etc/ads-relay/config.json')} {q(root + '/etc/ads-relay/key.pem')}
chmod 750 {q(root + '/etc/ads-relay')}
chmod 640 {q(root + '/etc/ads-relay/config.json')} {q(root + '/etc/ads-relay/key.pem')}
cat > {q(unit)} <<ADS_RELAY_UNIT
[Unit]
Description=ADS MCP relay (forwards Amazon Ads API calls for the hub)
After=network-online.target
Wants=network-online.target

[Service]
User={SERVICE}
Group={SERVICE}
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=$PY {root}/opt/ads-relay/ads_relay.py --config {root}/etc/ads-relay/config.json
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true

[Install]
WantedBy=multi-user.target
ADS_RELAY_UNIT
chmod 644 {q(unit)}
systemctl daemon-reload
systemctl enable {SERVICE} >/dev/null 2>&1
systemctl restart {SERVICE}
i=0
while [ $i -lt 10 ]; do
  systemctl is-active --quiet {SERVICE} && break
  sleep 1; i=$((i+1))
done
if ! systemctl is-active --quiet {SERVICE}; then
  journalctl -u {SERVICE} -n 20 --no-pager 2>/dev/null || true
  exit 1
fi
echo installed
"""


def uninstall_script(root: str) -> str:
    q = shlex.quote
    return f"""set -u
systemctl disable --now {SERVICE} >/dev/null 2>&1 || true
rm -f {q(root + '/etc/systemd/system/' + SERVICE + '.service')}
systemctl daemon-reload >/dev/null 2>&1 || true
rm -rf {q(root + '/opt/ads-relay')} {q(root + '/etc/ads-relay')}
if id -u {SERVICE} >/dev/null 2>&1; then userdel {SERVICE} >/dev/null 2>&1 || true; fi
echo removed
"""


def run_as_root(remote: Remote, script: str, prefix: str, stdin_prefix: bytes, timeout=180):
    # Stage the script privately, then run it as root and always delete it.
    code, out, err = remote.run(
        'umask 077 && d=$(mktemp -d) && cat > "$d/run.sh" && echo "$d"', script.encode()
    )
    staged = out.strip()
    if code or not staged.startswith("/"):
        raise SSHFailure(f"无法在服务器上创建临时目录：{err.strip()[:300]}")
    d = shlex.quote(staged)
    return remote.run(f'{prefix}sh {d}/run.sh; rc=$?; rm -rf {d}; exit $rc', stdin_prefix, timeout)


def install_plan(facts: dict, port: int, root: str = "") -> list[str]:
    reinstall = facts.get("relay_installed") == "yes"
    return [
        "新建系统用户 ads-relay（无登录 shell、无家目录）" if facts.get("relay_installed") != "yes" else "复用已有系统用户 ads-relay",
        f"写入 {root}/opt/ads-relay/ads_relay.py 和 VERSION（只用 Python 标准库，不装任何包）",
        f"写入 {root}/etc/ads-relay/config.json、cert.pem、key.pem（新生成的通信密钥和自签证书，仅 ads-relay 可读）",
        f"写入 {root}/etc/systemd/system/ads-relay.service，执行 systemctl enable 并重启 ads-relay",
        f"ads-relay 监听 0.0.0.0:{port}（TLS，签名校验，只转发到 Amazon Ads / S3）",
        "覆盖旧版本并更换密钥；本机会同步保存新密钥" if reinstall else "首次安装",
        "不会修改：防火墙 / 安全组、其他 systemd 服务、Docker 容器、Nginx / 反向代理、系统软件包",
        f"需要你在云服务器安全组放行 TCP {port}（入站来源建议只填本机出口 IP）",
    ]
