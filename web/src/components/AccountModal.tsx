import { useState } from "react";
import { LockKey } from "@phosphor-icons/react";
import { api } from "../api";
import { useWorkspace } from "../workspace";
import { Select } from "./Select";
import { Modal } from "./ui";

/** Marketplace → Amazon Ads API region; picking a site preselects its region. */
const marketplaces: [code: string, name: string, region: string][] = [
  ["US", "美国", "NA"],
  ["CA", "加拿大", "NA"],
  ["MX", "墨西哥", "NA"],
  ["UK", "英国", "EU"],
  ["DE", "德国", "EU"],
  ["FR", "法国", "EU"],
  ["IT", "意大利", "EU"],
  ["ES", "西班牙", "EU"],
  ["JP", "日本", "FE"],
  ["AU", "澳大利亚", "FE"],
];
const regions = [
  { value: "NA", label: "NA · 北美" },
  { value: "EU", label: "EU · 欧洲" },
  { value: "FE", label: "FE · 远东" },
];

export function AccountModal({ close }: { close: () => void }) {
  const { action, busy, setNotice } = useWorkspace();
  const [region, setRegion] = useState("NA");
  return (
    <Modal title="连接广告账户" close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const data = Object.fromEntries(new FormData(e.currentTarget));
          void action("account", async () => {
            await api("/accounts", "POST", data);
            close();
            setNotice("账户已保存，点击“验证连接”检查授权");
          });
        }}
      >
        <p className="hint">
          使用已有 Amazon Ads 授权；本页面不会重新申请或扩大 Amazon 权限。
        </p>
        <fieldset className="form-section">
          <legend>站点信息</legend>
          <div className="form-grid">
            <label className="span-2">
              账户名称
              <input
                name="label"
                placeholder="例如：品牌 · 美国站"
                maxLength={160}
                required
              />
            </label>
            <Select
              label="站点"
              name="marketplace"
              defaultValue="US"
              options={marketplaces.map(([code, name]) => ({
                value: code,
                label: `${code} · ${name}`,
              }))}
              onChange={(code) =>
                setRegion(marketplaces.find((m) => m[0] === code)![2])
              }
            />
            <Select
              label="API 区域"
              name="region"
              value={region}
              onChange={setRegion}
              options={regions}
            />
            <label className="span-2">
              Profile ID
              <input
                name="profile_id"
                inputMode="numeric"
                pattern="[0-9]+"
                placeholder="仅数字"
                required
              />
            </label>
          </div>
        </fieldset>
        <fieldset className="form-section">
          <legend>
            <LockKey size={15} />
            授权凭证 · 加密保存
          </legend>
          <label>
            Client ID
            <input name="client_id" autoComplete="off" required />
          </label>
          <label>
            Client Secret
            <input
              name="client_secret"
              type="password"
              autoComplete="new-password"
              required
            />
          </label>
          <label>
            Refresh Token
            <input
              name="refresh_token"
              type="password"
              autoComplete="new-password"
              required
            />
          </label>
        </fieldset>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>
            取消
          </button>
          <button className="primary" disabled={!!busy}>
            {busy === "account" ? "正在保存…" : "加密保存账户"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
