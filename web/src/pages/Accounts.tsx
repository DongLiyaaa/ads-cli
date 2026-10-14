import { ArrowRight, Plus, ShieldCheck } from "@phosphor-icons/react";
import { api } from "../api";
import { stamp } from "../lib/format";
import { Empty, PageHeader, Status } from "../components/ui";
import { useWorkspace } from "../workspace";

export function Accounts() {
  const { accounts, accountId, busy, action, setNotice, openAccountModal } =
    useWorkspace();
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
                  a.id === accountId ? "panel account-card current" : "panel account-card"
                }
                key={a.id}
              >
                <div className="account-card-head">
                  <span className="market">{a.marketplace}</span>
                  <div>
                    <h2>{a.label}</h2>
                    {a.id === accountId && <small>当前账户</small>}
                  </div>
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
