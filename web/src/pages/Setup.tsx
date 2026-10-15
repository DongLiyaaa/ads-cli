import { useState } from "react";
import { ArrowRight, WarningCircle } from "@phosphor-icons/react";
import { api, ApiError, setCsrf } from "../api";
import type { SetupState } from "../lib/types";
import {
  NewPasswordFields,
  passwordsMatch,
  SetupTokenField,
} from "../components/PasswordFields";
import { AuthIntro } from "./Login";

/** First-run screen: shown only while the database has no users. */
export function Setup({
  state,
  onDone,
  onAlreadySetup,
}: {
  state: SetupState;
  onDone: (user: string) => void;
  onAlreadySetup: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mismatch, setMismatch] = useState(false);
  return (
    <main className="login">
      <AuthIntro />
      <form
        className="login-form"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          if (!passwordsMatch(f)) {
            setMismatch(true);
            return;
          }
          setBusy(true);
          setError("");
          try {
            const s = await api("/setup", "POST", {
              username: String(f.get("username")).trim(),
              password: f.get("password"),
              setup_token: state.token_required
                ? String(f.get("setup_token")).trim()
                : "",
            });
            setCsrf(s.csrf_token);
            onDone(s.username);
          } catch (err) {
            if (err instanceof ApiError && err.status === 409)
              onAlreadySetup(err.message);
            else setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>创建管理员账号</h2>
        <p>首次使用，请设置登录控制台的用户名和密码。</p>
        {!state.available && (
          <p role="alert" className="callout warning">
            <WarningCircle size={18} />
            远程部署需先在 .env 设置 ADS_SETUP_TOKEN
            并重启服务，才能在此创建账号。
          </p>
        )}
        <label>
          用户名
          <input
            name="username"
            autoComplete="username"
            placeholder="例如 admin"
            pattern="[A-Za-z0-9._@\-]{3,64}"
            title="3–64 位字母、数字或 . _ @ -"
            required
          />
        </label>
        <NewPasswordFields
          id="setup"
          mismatch={mismatch}
          onEdit={() => setMismatch(false)}
        />
        {state.token_required && <SetupTokenField id="setup" />}
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <button className="primary large" disabled={busy || !state.available}>
          {busy ? "正在创建…" : "创建并进入工作台"}
          <ArrowRight size={18} />
        </button>
        <small>
          此账号用于登录和确认广告变更，只能创建一次；之后请直接登录。
        </small>
      </form>
    </main>
  );
}
