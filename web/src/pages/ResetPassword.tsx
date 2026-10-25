import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, WarningCircle } from "@phosphor-icons/react";
import { AuthorCredit } from "../components/ui";
import { api } from "../api";
import type { SetupState } from "../lib/types";
import {
  NewPasswordFields,
  passwordsMatch,
  SetupTokenField,
} from "../components/PasswordFields";
import { AuthIntro } from "./Login";

/** Forgotten password: no email or captcha; remote deployments need ADS_SETUP_TOKEN. */
export function ResetPassword({
  onDone,
  onBack,
}: {
  onDone: (message: string) => void;
  onBack: () => void;
}) {
  const [state, setState] = useState<SetupState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mismatch, setMismatch] = useState(false);
  useEffect(() => {
    api<SetupState>("/setup")
      .then(setState)
      .catch((e) => setError((e as Error).message));
  }, []);
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
            await api("/password/reset", "POST", {
              username: String(f.get("username")).trim(),
              password: f.get("password"),
              setup_token: state?.token_required
                ? String(f.get("setup_token")).trim()
                : "",
            });
            onDone("密码已重置，请使用新密码登录");
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>重置密码</h2>
        <p>输入管理员用户名并设置新密码，所有设备上的登录都会退出。</p>
        {state && !state.available && (
          <p role="alert" className="callout warning">
            <WarningCircle size={18} />
            远程部署需先在 .env 设置 ADS_SETUP_TOKEN
            并重启服务，才能在此重置密码。
          </p>
        )}
        <label>
          用户名
          <input name="username" autoComplete="username" required />
        </label>
        <NewPasswordFields
          id="reset"
          label="新密码"
          mismatch={mismatch}
          onEdit={() => setMismatch(false)}
        />
        {state?.token_required && <SetupTokenField id="reset" />}
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <button className="primary large" disabled={busy || !state?.available}>
          {busy ? "正在重置…" : "重置密码"}
          <ArrowRight size={18} />
        </button>
        <button type="button" className="text-button" onClick={onBack}>
          <ArrowLeft size={16} />
          返回登录
        </button>
      </form>
      <AuthorCredit className="login-credit" />
    </main>
  );
}
