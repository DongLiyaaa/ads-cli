import { api } from "../api";
import { scopeNames, scopeWarnings } from "../lib/constants";
import { useWorkspace } from "../workspace";
import { Select } from "./Select";
import { Modal } from "./ui";

export function TokenModal({ close }: { close: () => void }) {
  const { action, busy, accounts, accountId, setNotice, setOneTime } =
    useWorkspace();
  return (
    <Modal title="生成 MCP Token" close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          void action("token", async () => {
            const result = await api("/tokens", "POST", {
              name: f.get("name"),
              scopes: f.getAll("scope"),
              account_ids: f.getAll("account"),
              expires_in_days: Number(f.get("days")),
            });
            setOneTime(result.token);
            close();
            setNotice("Token 已生成，请立即保存");
          });
        }}
      >
        <div className="form-grid">
          <label>
            令牌名称
            <input
              name="name"
              placeholder="例如：运营助手 / 测试客户端"
              required
            />
          </label>
          <Select
            label="有效期"
            name="days"
            defaultValue="7"
            options={[
              { value: "7", label: "7 天", description: "适合测试与临时接入" },
              { value: "30", label: "30 天", description: "适合日常使用" },
              { value: "90", label: "90 天", description: "适合长期运行的自动化" },
            ]}
          />
        </div>
        <fieldset className="form-section">
          <legend>可访问账户</legend>
          <div className="check-list">
            {accounts.map((a) => (
              <label className="check" key={a.id}>
                <input
                  type="checkbox"
                  name="account"
                  value={a.id}
                  defaultChecked={a.id === accountId}
                />
                <span>
                  {a.label}
                  <small>
                    {a.marketplace} · {a.profile_id}
                  </small>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset className="form-section">
          <legend>操作权限</legend>
          <div className="check-list">
            {Object.entries(scopeNames).map(([s, label]) => (
              <label className="check" key={s}>
                <input
                  type="checkbox"
                  name="scope"
                  value={s}
                  defaultChecked={!scopeWarnings[s]}
                />
                <span>
                  {label}
                  <small className="mono">{s}</small>
                  {scopeWarnings[s] && <small>{scopeWarnings[s]}</small>}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="modal-actions">
          <button className="secondary" type="button" onClick={close}>
            取消
          </button>
          <button className="primary" disabled={!!busy}>
            {busy === "token" ? "正在生成…" : "生成令牌"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
