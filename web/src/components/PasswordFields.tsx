/** New password + confirmation, shared by setup, reset and change password. */
export function NewPasswordFields({
  id,
  label = "密码",
  mismatch,
  onEdit,
}: {
  id: string;
  label?: string;
  mismatch: boolean;
  onEdit: () => void;
}) {
  return (
    <>
      <label>
        {label}
        <input
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={1024}
          aria-describedby={`${id}-password-note`}
          required
        />
      </label>
      <span id={`${id}-password-note`} className="field-note">
        至少 12 位，且不能与用户名相同
      </span>
      <label>
        确认{label}
        <input
          name="confirm"
          type="password"
          autoComplete="new-password"
          aria-invalid={mismatch || undefined}
          aria-describedby={mismatch ? `${id}-confirm-note` : undefined}
          onChange={onEdit}
          required
        />
      </label>
      {mismatch && (
        <span id={`${id}-confirm-note`} className="field-note error">
          两次输入的密码不一致
        </span>
      )}
    </>
  );
}

/** Server-side ADS_SETUP_TOKEN, required for setup/reset on remote deployments. */
export function SetupTokenField({ id }: { id: string }) {
  return (
    <>
      <label>
        初始化口令
        <input
          name="setup_token"
          type="password"
          autoComplete="off"
          aria-describedby={`${id}-token-note`}
          required
        />
      </label>
      <span id={`${id}-token-note`} className="field-note">
        在服务器 .env 的 ADS_SETUP_TOKEN 中查看
      </span>
    </>
  );
}

export function passwordsMatch(form: FormData) {
  return form.get("password") === form.get("confirm");
}
