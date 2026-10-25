import { useState } from "react";
import {
  ArrowRight,
  PencilSimple,
  Plus,
  ShieldCheck,
} from "@phosphor-icons/react";
import { api } from "../api";
import { stamp } from "../lib/format";
import { Select } from "../components/Select";
import { Empty, PageHeader, Status } from "../components/ui";
import { useWorkspace } from "../workspace";

export function Accounts() {
  const {
    accounts,
    accountId,
    servers,
    busy,
    action,
    setNotice,
    navigate,
    openAccountModal,
  } = useWorkspace();
  const usable = servers.filter((s) => s.installed);
  function setEgress(id: string, relayId: string) {
    void action("egress:" + id, async () => {
      await api(`/accounts/${id}/relay`, "PUT", { relay_id: relayId || null });
      const server = servers.find((s) => s.id === relayId);
      setNotice(
        server
          ? `已切换为经 ${server.name} 转发`
          : "已切换为本地直连",
      );
    });
  }
  const [editing, setEditing] = useState<{ id: string; label: string } | null>(
    null,
  );
  function save(id: string, label: string) {
    const value = label.trim();
    if (!value) return;
    void action("rename:" + id, async () => {
      await api(`/accounts/${id}`, "PATCH", { label: value });
      setEditing(null);
      setNotice("店铺名称已更新");
    });
  }
  return (
    <>
      <PageHeader
        title="广告账户"
        description="每个站点独立保存授权信息，敏感凭证加密存储。"
        actions={
          <button className="primary" onClick={openAccountModal}>
            <Plus size={17} />
            连接账户
          </button>
        }
      />
      {!accounts.length ? (
        <section className="panel">
          <Empty
            title="连接你的第一个广告账户"
            detail="准备 Client ID、Client Secret、Refresh Token 和站点 Profile ID。"
            action={
              <button className="primary" onClick={openAccountModal}>
                连接账户
                <ArrowRight size={16} />
              </button>
            }
          />
        </section>
      ) : (
        <div className="account-grid">
          {accounts.map((a) => {
            const verifying = busy === "verify:" + a.id;
            return (
              <section
                className={
                  a.id === accountId
                    ? "panel account-card current"
                    : "panel account-card"
                }
                key={a.id}
              >
                <div className="account-card-head">
                  <span className="market">{a.marketplace}</span>
                  {editing?.id === a.id ? (
                    <form
                      className="account-rename"
                      onSubmit={(e) => {
                        e.preventDefault();
                        save(a.id, editing.label);
                      }}
                    >
                      <input
                        aria-label="店铺名称"
                        value={editing.label}
                        maxLength={160}
                        autoFocus
                        onChange={(e) =>
                          setEditing({ id: a.id, label: e.target.value })
                        }
                        onKeyDown={(e) =>
                          e.key === "Escape" && setEditing(null)
                        }
                      />
                      <div className="account-rename-actions">
                        <button
                          className="primary"
                          disabled={
                            !editing.label.trim() || busy === "rename:" + a.id
                          }
                        >
                          {busy === "rename:" + a.id ? "保存中…" : "保存"}
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setEditing(null)}
                        >
                          取消
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="account-name">
                      <div className="account-name-row">
                        <h2>{a.label}</h2>
                        <button
                          type="button"
                          className="icon-button"
                          aria-label={`编辑店铺名称：${a.label}`}
                          data-tip="编辑名称"
                          disabled={!!busy}
                          onClick={() =>
                            setEditing({ id: a.id, label: a.label })
                          }
                        >
                          <PencilSimple size={16} />
                        </button>
                      </div>
                      {a.id === accountId && <small>当前账户</small>}
                    </div>
                  )}
                  <Status
                    value={a.verified_at ? "SUCCEEDED" : "WAITING"}
                    label={a.verified_at ? "授权已验证" : "待验证"}
                  />
                </div>
                <dl>
                  <dt>Profile ID</dt>
                  <dd className="mono">{a.profile_id}</dd>
                  <dt>区域 / 币种</dt>
                  <dd>
                    {a.region} / {a.currency || "待验证"}
                  </dd>
                  <dt>时区</dt>
                  <dd>{a.timezone || "待验证"}</dd>
                  <dt>最近验证</dt>
                  <dd>{stamp(a.verified_at)}</dd>
                  <dt>网络出口</dt>
                  <dd className="egress">
                    {usable.length || a.relay_id ? (
                      <Select
                        size="sm"
                        ariaLabel={`${a.label} 的网络出口`}
                        value={a.relay_id || ""}
                        disabled={!!busy}
                        onChange={(v) => v !== (a.relay_id || "") && setEgress(a.id, v)}
                        options={[
                          { value: "", label: "本地直连" },
                          ...servers
                            .filter((s) => s.installed || s.id === a.relay_id)
                            .map((s) => ({
                              value: s.id,
                              label: `经 ${s.name} 转发`,
                              description: `${s.host}${s.status === "INSTALLED" ? "" : " · 通道未连通"}`,
                            })),
                        ]}
                      />
                    ) : (
                      <>
                        本地直连
                        <button
                          type="button"
                          className="text-button inline"
                          onClick={() => navigate("/servers")}
                        >
                          添加转发服务器
                        </button>
                      </>
                    )}
                  </dd>
                </dl>
                <button
                  className="secondary"
                  disabled={!!busy}
                  onClick={() =>
                    action("verify:" + a.id, async () => {
                      await api(`/accounts/${a.id}/verify`, "POST", {});
                      setNotice("授权与站点 Profile 验证成功");
                    })
                  }
                >
                  <ShieldCheck size={17} />
                  {verifying ? "正在验证…" : "验证连接"}
                </button>
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
