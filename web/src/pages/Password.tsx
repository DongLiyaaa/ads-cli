import { useState } from "react";
import { api } from "../api";
import { PageHeader } from "../components/ui";
import {
  NewPasswordFields,
  passwordsMatch,
} from "../components/PasswordFields";
import { useWorkspace } from "../workspace";

export function Password() {
  const { busy, action, setNotice } = useWorkspace();
  const [mismatch, setMismatch] = useState(false);
  return (
    <>
      <PageHeader
        title="修改密码"
        description="修改后其他设备上的登录会退出，当前页面保持登录。"
      />
      <section className="panel">
        <form
          className="password-form"
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const f = new FormData(form);
            if (!passwordsMatch(f)) {
              setMismatch(true);
              return;
            }
            void action("password", async () => {
              await api("/password", "POST", { password: f.get("password") });
              form.reset();
              setNotice("密码已修改");
            });
          }}
        >
          <NewPasswordFields
            id="change"
            label="新密码"
            mismatch={mismatch}
            onEdit={() => setMismatch(false)}
          />
          <button className="primary" disabled={busy === "password"}>
            {busy === "password" ? "正在保存…" : "保存新密码"}
          </button>
        </form>
      </section>
    </>
  );
}
