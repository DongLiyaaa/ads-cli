import { useState } from "react";
import { Copy, Key, Plus } from "@phosphor-icons/react";
import { api } from "../api";
import { scopeNames } from "../lib/constants";
import { accountName, stamp, tokenState } from "../lib/format";
import type { MCPToken } from "../lib/types";
import {
  ConfirmDialog,
  Empty,
  PageHeader,
  PanelHeading,
  Status,
} from "../components/ui";
import { useWorkspace } from "../workspace";

const AUTH_HEADER = "Authorization: Bearer <你的 MCP Token>";

export function Tokens() {
  const {
    accounts,
    tokens,
    overview,
    busy,
    action,
    setNotice,
    copy,
    oneTime,
    setOneTime,
    openTokenModal,
  } = useWorkspace();
  const [revoking, setRevoking] = useState<MCPToken | null>(null);
  const endpoint = (overview.mcp_endpoint || location.origin + "/mcp").replace(
    /\/?$/,
    "/",
  );
  return (
    <>
      <PageHeader
        title="MCP Token"
        description="为 AI 客户端生成独立令牌，限定账户、权限和有效期。"
        actions={
          <button
            className="primary"
            disabled={!accounts.length}
            onClick={openTokenModal}
          >
            <Plus size={17} />
            生成 Token
          </button>
        }
      />
      {oneTime && (
        <section className="panel token-secret" aria-live="polite">
          <h3>
            <Key size={20} weight="fill" />
            Token 已生成，仅此一次展示
          </h3>
          <p>
            请保存到客户端的 Authorization 请求头；离开此页后不能再次查看明文。
          </p>
          <pre>{oneTime}</pre>
          <div className="button-row">
            <button className="primary" onClick={() => copy(oneTime)}>
              <Copy size={16} />
              复制 Token
            </button>
            <button className="secondary" onClick={() => setOneTime("")}>
              已保存，隐藏
            </button>
          </div>
        </section>
      )}
      <section className="panel connect-panel">
        <div className="connect-row">
          <div>
            <h2>
              MCP 接入地址
              <span className="tag">Streamable HTTP</span>
            </h2>
            <code>{endpoint}</code>
          </div>
          <button className="secondary" onClick={() => copy(endpoint)}>
            <Copy size={16} />
            复制地址
          </button>
        </div>
        <div className="connect-row">
          <div>
            <h2>请求头</h2>
            <code>{AUTH_HEADER}</code>
          </div>
          <button className="secondary" onClick={() => copy(AUTH_HEADER)}>
            <Copy size={16} />
            复制请求头
          </button>
        </div>
        <p className="hint">
          使用支持自定义 Authorization 请求头的 MCP 客户端。工具提供账户、能力查询、报表任务、变更计划和结果读取；真实广告变更需要到“待确认操作”完成用户确认。
        </p>
      </section>
      <section className="panel">
        <PanelHeading
          title="访问令牌"
          description="数据库仅保存 Token 摘要，撤销后立即拒绝新的请求。"
        />
        {tokens.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>名称 / 前缀</th>
                  <th>可访问账户</th>
                  <th>权限</th>
                  <th>有效期至</th>
                  <th>最近使用</th>
                  <th>状态</th>
                  <th>
                    <span className="visually-hidden">操作</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {tokens.map((t) => {
                  const state = tokenState(t);
                  return (
                    <tr key={t.id}>
                      <td>
                        <strong>{t.name}</strong>
                        <small className="mono">{t.prefix}…</small>
                      </td>
                      <td className="wrap">
                        {t.account_ids
                          .map((id) => accountName(accounts, id))
                          .join("、")}
                      </td>
                      <td className="tags">
                        {t.scopes.map((s) => (
                          <span className="tag" key={s}>
                            {scopeNames[s] || s}
                          </span>
                        ))}
                      </td>
                      <td>{stamp(t.expires_at)}</td>
                      <td>{stamp(t.last_used_at)}</td>
                      <td>
                        <Status value={state.tone} label={state.label} />
                      </td>
                      <td className="row-action">
                        <button
                          className="text-button danger"
                          disabled={t.revoked || !!busy}
                          onClick={() => setRevoking(t)}
                        >
                          撤销
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="还没有 MCP Token"
            detail={
              accounts.length
                ? "为你的 AI 客户端生成一个独立令牌。"
                : "先连接一个广告账户，再为它分配 Token。"
            }
          />
        )}
      </section>
      {revoking && (
        <ConfirmDialog
          title="撤销 MCP Token"
          confirmLabel={busy === "revoke" ? "正在撤销…" : "确认撤销"}
          busy={!!busy}
          close={() => setRevoking(null)}
          onConfirm={() =>
            void action("revoke", async () => {
              await api(`/tokens/${revoking.id}/revoke`, "POST", {});
              setNotice("Token 已撤销");
            }).finally(() => setRevoking(null))
          }
        >
          <p>
            撤销 <strong>{revoking.name}</strong>
            <span className="mono">（{revoking.prefix}…）</span>
            后，使用它的客户端会立即失效。
          </p>
          <p className="confirm-warning">此操作不能恢复，需要时请重新生成 Token。</p>
        </ConfirmDialog>
      )}
    </>
  );
}
