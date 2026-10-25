import { useState } from "react";
import { LockKey } from "@phosphor-icons/react";
import { api } from "../api";
import type { RelayServer } from "../lib/types";
import { useWorkspace } from "../workspace";
import { Modal, Segmented } from "./ui";

type Auth = "key" | "password";

/** Add or edit an SSH-managed relay server; credentials are write-only. */
export function ServerModal({
  server,
  close,
}: {
  server?: RelayServer;
  close: () => void;
}) {
  const { action, busy, setNotice } = useWorkspace();
  const [auth, setAuth] = useState<Auth>(server?.auth_type || "key");
  const editing = !!server;
  // Editing keeps the stored credential unless a new one is typed in.
  const credentialRequired = !editing || auth !== server.auth_type;
  return (
    <Modal title={editing ? `编辑服务器：${server.name}` : "添加转发服务器"} close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const text = (k: string) => String(f.get(k) ?? "").trim();
          const data: Record<string, unknown> = {
            name: text("name"),
            host: text("host"),
            username: text("username"),
            ssh_port: Number(text("ssh_port")),
          };
          if (!server?.installed) data.relay_port = Number(text("relay_port"));
          const secret =
            auth === "key" ? String(f.get("private_key") ?? "") : String(f.get("password") ?? "");
          if (secret.trim()) {
            data.auth_type = auth;
            if (auth === "key") {
              data.private_key = secret;
              data.passphrase = String(f.get("passphrase") ?? "");
            } else data.password = secret;
          }
          if (f.get("reset_host_key")) data.reset_host_key = true;
          void action("server-save", async () => {
            if (editing) await api(`/servers/${server.id}`, "PATCH", data);
            else await api("/servers", "POST", data);
            close();
            setNotice(editing ? "服务器信息已更新" : "服务器已保存，点击“测试连接”检查环境");
          });
        }}
      >
        <p className="hint">
          Hub 通过 SSH 登录服务器安装 ads-relay 转发服务；之后 Amazon API
          请求从该服务器发出，数据回传到本机。
        </p>
        <fieldset className="form-section">
          <legend>服务器</legend>
          <div className="form-grid">
            <label className="span-2">
              名称
              <input
                name="name"
                defaultValue={server?.name}
                placeholder="例如：美西出口"
                maxLength={120}
                required
              />
            </label>
            <label>
              地址
              <input
                name="host"
                defaultValue={server?.host}
                placeholder="IP 或域名"
                autoComplete="off"
                spellCheck={false}
                required
              />
            </label>
            <label>
              SSH 端口
              <input
                name="ssh_port"
                type="number"
                min={1}
                max={65535}
                defaultValue={server?.ssh_port ?? 22}
                required
              />
            </label>
            <label>
              SSH 用户名
              <input
                name="username"
                defaultValue={server?.username ?? "root"}
                autoComplete="off"
                spellCheck={false}
                required
              />
            </label>
            <label>
              转发端口
              <input
                name="relay_port"
                type="number"
                min={1024}
                max={65535}
                defaultValue={server?.relay_port ?? 8787}
                disabled={server?.installed}
                title={server?.installed ? "已安装，修改端口需先卸载" : undefined}
                required
              />
            </label>
          </div>
        </fieldset>
        <fieldset className="form-section">
          <legend>
            <LockKey size={15} />
            SSH 认证 · 加密保存
          </legend>
          <div className="server-auth">
            <Segmented<Auth>
              label="认证方式"
              value={auth}
              onChange={setAuth}
              options={[
                { value: "key", label: "私钥" },
                { value: "password", label: "密码" },
              ]}
            />
          </div>
          {auth === "key" ? (
            <>
              <label>
                私钥
                <textarea
                  name="private_key"
                  className="mono server-key"
                  rows={5}
                  spellCheck={false}
                  autoComplete="off"
                  placeholder={
                    credentialRequired
                      ? "-----BEGIN OPENSSH PRIVATE KEY-----"
                      : "已保存，留空则不修改"
                  }
                  required={credentialRequired}
                />
              </label>
              <label>
                私钥口令（可选）
                <input
                  name="passphrase"
                  type="password"
                  autoComplete="new-password"
                  placeholder="私钥未加密可留空"
                />
              </label>
            </>
          ) : (
            <label>
              SSH 密码
              <input
                name="password"
                type="password"
                autoComplete="new-password"
                placeholder={credentialRequired ? "" : "已保存，留空则不修改"}
                required={credentialRequired}
              />
            </label>
          )}
          {auth === "password" && (
            <p className="field-note">
              非 root 用户需要 sudo 权限；密码同时用于 sudo 提权。
            </p>
          )}
          {editing && server.host_fingerprint && (
            <label className="check">
              <input type="checkbox" name="reset_host_key" />
              <span>
                重置 SSH 指纹
                <small>服务器重装系统后指纹会变化，确认是同一台机器再勾选</small>
              </span>
            </label>
          )}
        </fieldset>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>
            取消
          </button>
          <button className="primary" disabled={!!busy}>
            {busy === "server-save" ? "正在保存…" : "加密保存"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
