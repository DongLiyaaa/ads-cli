import { useState } from "react";
import {
  ArrowsClockwise,
  Copy,
  Eye,
  Key,
  LinkSimple,
  Plus,
} from "@phosphor-icons/react";
import { api } from "../api";
import { scopeNames } from "../lib/constants";
import { accountName, stamp, tokenState } from "../lib/format";
import type { MCPToken } from "../lib/types";
import {
  ConfirmDialog,
  Empty,
  Modal,
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
  const [deleting, setDeleting] = useState<MCPToken | null>(null);
  const [rotating, setRotating] = useState<MCPToken | null>(null);
  const [revealed, setRevealed] = useState<{
    token: MCPToken;
    value: string;
  } | null>(null);
  async function reveal(t: MCPToken) {
    const r = await api<{ token: string }>(
      `/tokens/${t.id}/reveal`,
      "POST",
      {},
    );
    return r.token;
  }
  const endpoint = (overview.mcp_endpoint || location.origin + "/mcp").replace(
    /\/?$/,
    "/",
  );
  function copyToken(t: MCPToken, withEndpoint = false) {
    void action((withEndpoint ? "connect:" : "copy:") + t.id, async () => {
      const token = await reveal(t);
      // MCP address + Authorization header, ready to paste into a client.
      const value = withEndpoint
        ? `${endpoint}\nAuthorization: Bearer ${token}`
        : token;
      try {
        await navigator.clipboard.writeText(value);
        setNotice(
          withEndpoint ? `已复制接入地址和 Token：${t.name}` : `已复制 Token：${t.name}`,
        );
      } catch {
        // Some browsers drop clipboard access after the request; copy from the dialog instead.
        setRevealed({ token: t, value });
      }
    });
  }
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
            Token 已生成
          </h3>
          <p>
            请保存到客户端的 Authorization
            请求头；之后也可以在下方列表点“复制”再次复制。
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
          使用支持自定义 Authorization 请求头的 MCP
          客户端。工具提供账户、能力查询、报表任务、变更计划和结果读取；真实广告变更需要到“待确认操作”完成用户确认。
        </p>
      </section>
      <section className="panel">
        <PanelHeading
          title="访问令牌"
          description="Token 加密保存，可随时复制或查看；撤销后立即拒绝新请求，删除后从列表移除。"
        />
        {tokens.length ? (
          <div className="table-scroll token-table">
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
                  // Issued before plaintext was stored: copying needs a new value.
                  const legacy = state.tone === "succeeded" && !t.can_reveal;
                  return (
                    <tr key={t.id}>
                      <td>
                        <strong>{t.name}</strong>
                        <small className="mono">{t.prefix}…</small>
                        {legacy && (
                          <small className="token-note">
                            旧版本 Token 未保存明文，重新生成后即可复制
                          </small>
                        )}
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
                      <td>{t.permanent ? "永久有效" : stamp(t.expires_at)}</td>
                      <td>{stamp(t.last_used_at)}</td>
                      <td>
                        <Status value={state.tone} label={state.label} />
                      </td>
                      <td className="row-action token-actions">
                        <div>
                          {t.can_reveal && (
                            <>
                              <button
                                className="text-button"
                                disabled={!!busy}
                                onClick={() => copyToken(t)}
                              >
                                <Copy size={15} />
                                {busy === "copy:" + t.id ? "正在复制…" : "复制"}
                              </button>
                              <button
                                className="text-button"
                                disabled={!!busy}
                                onClick={() => copyToken(t, true)}
                              >
                                <LinkSimple size={15} />
                                {busy === "connect:" + t.id
                                  ? "正在复制…"
                                  : "复制地址+Token"}
                              </button>
                              <button
                                className="text-button"
                                disabled={!!busy}
                                onClick={() =>
                                  void action("reveal:" + t.id, async () =>
                                    setRevealed({
                                      token: t,
                                      value: await reveal(t),
                                    }),
                                  )
                                }
                              >
                                <Eye size={15} />
                                查看
                              </button>
                            </>
                          )}
                          {legacy && (
                            <button
                              className="text-button"
                              disabled={!!busy}
                              onClick={() => setRotating(t)}
                            >
                              <ArrowsClockwise size={15} />
                              重新生成
                            </button>
                          )}
                          <button
                            className="text-button danger"
                            disabled={t.revoked || !!busy}
                            onClick={() => setRevoking(t)}
                          >
                            撤销
                          </button>
                          <button
                            className="text-button danger"
                            disabled={!!busy}
                            onClick={() => setDeleting(t)}
                          >
                            删除
                          </button>
                        </div>
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
      {revealed && (
        <Modal
          title={`查看 Token：${revealed.token.name}`}
          close={() => setRevealed(null)}
        >
          <div className="token-reveal">
            <p>
              复制到 MCP 客户端的 Authorization
              请求头。请勿发给他人，每次查看和复制都会写入执行日志。
            </p>
            <pre>{revealed.value}</pre>
            <div className="modal-actions">
              <button className="secondary" onClick={() => setRevealed(null)}>
                完成
              </button>
              <button className="primary" onClick={() => copy(revealed.value)}>
                <Copy size={16} />
                复制 Token
              </button>
            </div>
          </div>
        </Modal>
      )}
      {rotating && (
        <ConfirmDialog
          title="重新生成 MCP Token"
          confirmLabel={busy === "rotate" ? "正在生成…" : "确认重新生成"}
          busy={!!busy}
          close={() => setRotating(null)}
          onConfirm={() =>
            void action("rotate", async () => {
              const r = await api<{ token: string }>(
                `/tokens/${rotating.id}/rotate`,
                "POST",
                {},
              );
              setRevealed({ token: rotating, value: r.token });
            }).finally(() => setRotating(null))
          }
        >
          <p>
            为 <strong>{rotating.name}</strong>
            <span className="mono">（{rotating.prefix}…）</span>
            生成新的 Token
            值。名称、可访问账户、权限和有效期都不变，之后可随时查看和复制。
          </p>
          <p className="confirm-warning">
            旧的 Token 值会立即失效，请把新值更新到正在使用它的 MCP 客户端。
          </p>
        </ConfirmDialog>
      )}
      {deleting && (
        <ConfirmDialog
          title="删除 MCP Token"
          confirmLabel={busy === "delete" ? "正在删除…" : "确认删除"}
          busy={!!busy}
          close={() => setDeleting(null)}
          onConfirm={() =>
            void action("delete", async () => {
              await api(`/tokens/${deleting.id}`, "DELETE");
              setNotice("Token 已删除");
            }).finally(() => setDeleting(null))
          }
        >
          <p>
            删除 <strong>{deleting.name}</strong>
            <span className="mono">（{deleting.prefix}…）</span>
            后，它会从列表中移除{deleting.revoked ? "" : "，并立即失效"}。
          </p>
          <p className="confirm-warning">
            此操作不能恢复；执行日志和它提交过的任务记录会保留。
          </p>
        </ConfirmDialog>
      )}
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
          <p className="confirm-warning">
            此操作不能恢复，需要时请重新生成 Token。
          </p>
        </ConfirmDialog>
      )}
    </>
  );
}
