import { useState } from "react";
import {
  ArrowRight,
  CheckCircle,
  DownloadSimple,
  Heartbeat,
  PencilSimple,
  Plugs,
  Plus,
  ShieldCheck,
  WarningCircle,
  XCircle,
} from "@phosphor-icons/react";
import { api } from "../api";
import { stamp } from "../lib/format";
import type { RelayServer } from "../lib/types";
import { ServerModal } from "../components/ServerModal";
import { ConfirmDialog, Empty, Modal, PageHeader, Status } from "../components/ui";
import { useWorkspace } from "../workspace";

/** Server status → existing pill tone and label. */
const serverStatus: Record<string, [tone: string, label: string]> = {
  NEW: ["new", "未检测"],
  READY: ["queued", "可安装"],
  BLOCKED: ["partial", "条件不足"],
  INSTALLED: ["succeeded", "转发运行中"],
  UNREACHABLE: ["partial", "通道未连通"],
  ERROR: ["failed", "连接失败"],
};

function ServerChecks({ server }: { server: RelayServer }) {
  if (!server.checks.length) return null;
  return (
    <ul className="server-checks">
      {server.checks.map((c) => (
        <li key={c.key} className={c.ok ? "ok" : c.required ? "bad" : "warn"}>
          {c.ok ? (
            <CheckCircle size={16} weight="fill" />
          ) : c.required ? (
            <XCircle size={16} weight="fill" />
          ) : (
            <WarningCircle size={16} weight="fill" />
          )}
          <strong>{c.label}</strong>
          <span>{c.detail}</span>
        </li>
      ))}
    </ul>
  );
}

export function Servers() {
  const { servers, busy, action, setNotice, setError } = useWorkspace();
  const [form, setForm] = useState<{ server?: RelayServer } | null>(null);
  const [plan, setPlan] = useState<RelayServer | null>(null);
  const [uninstalling, setUninstalling] = useState<RelayServer | null>(null);
  const [deleting, setDeleting] = useState<RelayServer | null>(null);

  function test(s: RelayServer) {
    void action("server-test:" + s.id, async () => {
      const r = await api<RelayServer>(`/servers/${s.id}/test`, "POST", {});
      if (r.status === "ERROR" || r.status === "BLOCKED") setError(r.message || "检测未通过");
      else setNotice(r.status === "READY" ? "环境检测通过，可以安装转发服务" : "连接正常");
    });
  }
  // Installing always re-probes first, so the plan shown matches the server now.
  function prepareInstall(s: RelayServer) {
    void action("server-test:" + s.id, async () => {
      const r = await api<RelayServer>(`/servers/${s.id}/test`, "POST", {});
      if (r.status === "ERROR" || r.status === "BLOCKED")
        setError(r.message || "环境检测未通过，无法安装");
      else setPlan(r);
    });
  }
  function install(s: RelayServer) {
    void action("server-install:" + s.id, async () => {
      const r = await api<RelayServer>(`/servers/${s.id}/install`, "POST", {});
      setPlan(null);
      if (r.status === "INSTALLED") setNotice(`ads-relay 已安装到 ${s.name}，加密通道已连通`);
      else setError(r.message || "安装未完成");
    });
  }
  function check(s: RelayServer) {
    void action("server-check:" + s.id, async () => {
      const r = await api<RelayServer>(`/servers/${s.id}/check`, "POST", {});
      if (r.status === "INSTALLED") setNotice("转发通道与 Amazon 出口检查通过");
      else setError(r.message || "转发服务检查未通过");
    });
  }

  return (
    <>
      <PageHeader
        title="转发服务器"
        description="Amazon API 请求可以从这里的服务器发出，数据回传到本机；未绑定服务器的店铺继续本地直连。"
        actions={
          <button className="primary" onClick={() => setForm({})}>
            <Plus size={17} />
            添加服务器
          </button>
        }
      />
      <div className="callout info">
        <ShieldCheck size={20} weight="fill" />
        <p>
          为防止 API 关联，建议采用服务器隔离：每个店铺绑定一台独立的转发服务器，不同店铺不要共用同一台服务器（同一出口 IP）。
        </p>
      </div>
      {!servers.length ? (
        <section className="panel">
          <Empty
            title="还没有转发服务器"
            detail="准备一台能 SSH 登录的 Linux 服务器（systemd + Python 3.6 以上），Hub 会自动安装转发服务。"
            action={
              <button className="primary" onClick={() => setForm({})}>
                添加服务器
                <ArrowRight size={16} />
              </button>
            }
          />
        </section>
      ) : (
        <div className="server-list">
          {servers.map((s) => {
            const [tone, label] = serverStatus[s.status] || ["new", s.status];
            const running = (name: string) => busy === `server-${name}:${s.id}`;
            return (
              <section className="panel server-card" key={s.id}>
                <div className="server-head">
                  <div className="server-title">
                    <h2>{s.name}</h2>
                    <span className="mono">
                      {s.username}@{s.host}:{s.ssh_port}
                    </span>
                  </div>
                  <Status value={tone} label={label} />
                </div>
                <dl className="server-facts">
                  <div>
                    <dt>SSH 认证</dt>
                    <dd>{s.auth_type === "key" ? "私钥" : "密码"}</dd>
                  </div>
                  <div>
                    <dt>转发端口</dt>
                    <dd className="mono">TCP {s.relay_port}</dd>
                  </div>
                  <div>
                    <dt>转发服务</dt>
                    <dd>
                      {s.installed
                        ? `ads-relay ${s.relay_version || ""} · ${stamp(s.installed_at)}`
                        : "未安装"}
                    </dd>
                  </div>
                  <div>
                    <dt>最近检测</dt>
                    <dd>{stamp(s.checked_at)}</dd>
                  </div>
                  <div className="wide">
                    <dt>SSH 指纹</dt>
                    <dd className="mono">{s.host_fingerprint || "首次连接时记录"}</dd>
                  </div>
                  <div className="wide">
                    <dt>使用中的店铺</dt>
                    <dd>
                      {s.accounts.length
                        ? s.accounts.map((a) => (
                            <span className="tag" key={a.id}>
                              {a.label}
                            </span>
                          ))
                        : "无（在“广告账户”里为店铺选择网络出口）"}
                    </dd>
                  </div>
                </dl>
                {s.message && (
                  <div className={`callout ${tone === "succeeded" ? "info" : "warning"} server-message`}>
                    <WarningCircle size={16} />
                    <p>{s.message}</p>
                  </div>
                )}
                <ServerChecks server={s} />
                <div className="server-actions">
                  <button className="secondary" disabled={!!busy} onClick={() => test(s)}>
                    <Plugs size={17} />
                    {running("test") ? "正在检测…" : "测试连接"}
                  </button>
                  <button
                    className={s.installed ? "secondary" : "primary"}
                    disabled={!!busy}
                    onClick={() => prepareInstall(s)}
                  >
                    <DownloadSimple size={17} />
                    {running("install") ? "正在安装…" : s.installed ? "重新安装" : "安装服务"}
                  </button>
                  {s.installed && (
                    <button className="secondary" disabled={!!busy} onClick={() => check(s)}>
                      <Heartbeat size={17} />
                      {running("check") ? "正在检查…" : "检查服务"}
                    </button>
                  )}
                  <span className="server-actions-end">
                    <button
                      className="text-button"
                      disabled={!!busy}
                      onClick={() => setForm({ server: s })}
                    >
                      <PencilSimple size={15} />
                      编辑
                    </button>
                    {s.installed && (
                      <button
                        className="text-button danger"
                        disabled={!!busy || !!s.accounts.length}
                        title={s.accounts.length ? "先把使用它的店铺切回本地直连" : undefined}
                        onClick={() => setUninstalling(s)}
                      >
                        卸载
                      </button>
                    )}
                    <button
                      className="text-button danger"
                      disabled={!!busy || !!s.accounts.length}
                      title={s.accounts.length ? "先把使用它的店铺切回本地直连" : undefined}
                      onClick={() => setDeleting(s)}
                    >
                      删除
                    </button>
                  </span>
                </div>
              </section>
            );
          })}
        </div>
      )}
      {form && <ServerModal server={form.server} close={() => setForm(null)} />}
      {plan && (
        <Modal title={`安装到 ${plan.name}`} close={() => !busy && setPlan(null)}>
          <ServerChecks server={plan} />
          <h3 className="server-plan-title">将在服务器上执行</h3>
          <ul className="server-plan">
            {(plan.plan || []).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="hint">
            安装以 root 权限运行，可随时在本页卸载。服务器 SSH 指纹：
            <span className="mono">{plan.host_fingerprint}</span>
          </p>
          <div className="modal-actions">
            <button type="button" className="secondary" disabled={!!busy} onClick={() => setPlan(null)}>
              取消
            </button>
            <button type="button" className="primary" disabled={!!busy} onClick={() => install(plan)}>
              {busy === "server-install:" + plan.id ? "正在安装…" : "确认安装"}
            </button>
          </div>
        </Modal>
      )}
      {uninstalling && (
        <ConfirmDialog
          title="卸载转发服务"
          confirmLabel="卸载"
          busy={!!busy}
          close={() => setUninstalling(null)}
          onConfirm={() =>
            void action("server-uninstall:" + uninstalling.id, async () => {
              const r = await api<RelayServer>(`/servers/${uninstalling.id}/uninstall`, "POST", {});
              setUninstalling(null);
              if (r.status === "NEW") setNotice(`已从 ${uninstalling.name} 卸载 ads-relay`);
              else setError(r.message || "卸载失败");
            })
          }
        >
          <p>
            将停止并删除 <strong>{uninstalling.name}</strong> 上的 ads-relay
            服务、文件和系统用户，不影响服务器上的其他服务。
          </p>
        </ConfirmDialog>
      )}
      {deleting && (
        <ConfirmDialog
          title="删除服务器"
          confirmLabel="删除"
          busy={!!busy}
          close={() => setDeleting(null)}
          onConfirm={() =>
            void action("server-delete:" + deleting.id, async () => {
              await api(`/servers/${deleting.id}`, "DELETE");
              setDeleting(null);
              setNotice("服务器已删除");
            })
          }
        >
          <p>
            删除 <strong>{deleting.name}</strong> 的连接信息和加密凭证。
          </p>
          {deleting.installed && (
            <p className="confirm-warning">
              服务器上的 ads-relay 不会被卸载；如需清理请先点“卸载”。
            </p>
          )}
        </ConfirmDialog>
      )}
    </>
  );
}
