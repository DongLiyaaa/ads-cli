import { useState } from "react";
import {
  ArrowRight,
  ClockCounterClockwise,
  Database,
  Info,
  PlugsConnected,
  ShieldCheck,
} from "@phosphor-icons/react";
import { api, setCsrf } from "../api";

/** Brand column shared by the login and first-run setup screens. */
export function AuthIntro() {
  return (
    <div className="login-intro">
      <div className="brand">
        <span className="brand-icon">
          <PlugsConnected size={24} weight="bold" />
        </span>
        Ads Console
      </div>
      <h1>
        让广告操作
        <br />
        有据可查。
      </h1>
      <p>
        连接账户、等待报表、确认变更。
        <br />
        把每一步交给一个可追踪的工作台。
      </p>
      <ul className="login-features">
        <li>
          <ShieldCheck weight="duotone" />
          <span>
            <strong>人工确认</strong>
            变更只生成计划，由你确认后执行
          </span>
        </li>
        <li>
          <Database weight="duotone" />
          <span>
            <strong>数据留存</strong>
            报表结果保存在 PostgreSQL
          </span>
        </li>
        <li>
          <ClockCounterClockwise weight="duotone" />
          <span>
            <strong>执行记录</strong>
            请求、审批与 Amazon 响应全程留痕
          </span>
        </li>
      </ul>
    </div>
  );
}

export function Login({
  onLogin,
  onForgot,
  notice,
}: {
  onLogin: (user: string) => void;
  onForgot: () => void;
  notice?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <main className="login">
      <AuthIntro />
      <form
        className="login-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          const f = new FormData(e.currentTarget);
          try {
            const s = await api("/login", "POST", {
              username: f.get("username"),
              password: f.get("password"),
            });
            setCsrf(s.csrf_token);
            onLogin(s.username);
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>登录控制台</h2>
        <p>使用初始化时创建的管理员账号。</p>
        {notice && !error && (
          <p role="status" className="callout info">
            <Info size={18} />
            {notice}
          </p>
        )}
        <label>
          用户名
          <input name="username" autoComplete="username" required />
        </label>
        <label>
          密码
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <div className="form-links">
          <button type="button" className="text-button" onClick={onForgot}>
            忘记密码？
          </button>
        </div>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <button className="primary large" disabled={busy}>
          {busy ? "正在登录…" : "进入工作台"}
          <ArrowRight size={18} />
        </button>
        <small>管理账户与 MCP Token 独立；Token 无法批准广告变更。</small>
      </form>
    </main>
  );
}
