import { useMemo, useState } from "react";
import {
  ArrowClockwise,
  DownloadSimple,
  Eye,
  ShieldCheck,
  WarningCircle,
} from "@phosphor-icons/react";
import { api } from "../api";
import {
  CANCELLABLE_STATUSES,
  PAGE_SIZE,
  kindNames,
} from "../lib/constants";
import { stamp } from "../lib/format";
import type { RowsPage, Task } from "../lib/types";
import { useWorkspace } from "../workspace";
import { Modal, Pagination, Status } from "./ui";
import { taskTitle } from "./TaskTable";

export function TaskDetail({
  task,
  setTask,
  close,
}: {
  task: Task;
  setTask: (task: Task) => void;
  close: () => void;
}) {
  const { accounts, busy, action, setNotice, setError } = useWorkspace();
  const [rows, setRows] = useState<RowsPage | null>(null);
  const [rowOffset, setRowOffset] = useState(0);
  const [confirmation, setConfirmation] = useState("");
  const account = accounts.find((a) => a.id === task.account_id);
  const columns = useMemo(
    () =>
      Array.from(
        new Set<string>(
          (rows?.rows || []).flatMap((r: any) => Object.keys(r || {})),
        ),
      ),
    [rows],
  );

  async function reload() {
    try {
      setTask(await api<Task>(`/tasks/${task.id}`));
      setRows(null);
      setRowOffset(0);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function loadRows(offset = 0) {
    try {
      setRows(
        await api<RowsPage>(
          `/tasks/${task.id}/rows?offset=${offset}&limit=${PAGE_SIZE}`,
        ),
      );
      setRowOffset(offset);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <Modal title={taskTitle(task.operation)} close={close} wide>
      <div className="task-meta">
        <Status value={task.status} />
        <code>{task.id}</code>
        <button className="text-button" onClick={reload}>
          <ArrowClockwise size={15} />
          刷新状态
        </button>
      </div>
      <dl className="summary-grid">
        <div>
          <dt>账户</dt>
          <dd>
            {account ? `${account.label} · ${account.marketplace}` : "—"}
          </dd>
        </div>
        <div>
          <dt>Profile ID</dt>
          <dd className="mono">{account?.profile_id || "—"}</dd>
        </div>
        <div>
          <dt>操作</dt>
          <dd className="mono">{task.operation}</dd>
        </div>
        <div>
          <dt>类型</dt>
          <dd>{kindNames[task.kind] || task.kind}</dd>
        </div>
        <div>
          <dt>创建时间</dt>
          <dd>{stamp(task.created_at)}</dd>
        </div>
        <div>
          <dt>最近更新</dt>
          <dd>{stamp(task.updated_at)}</dd>
        </div>
        {task.remote_status && (
          <div>
            <dt>Amazon 状态</dt>
            <dd className="mono">{task.remote_status}</dd>
          </div>
        )}
        {task.kind === "report" && task.status === "SUCCEEDED" && (
          <div>
            <dt>数据行</dt>
            <dd>{task.row_count.toLocaleString()}</dd>
          </div>
        )}
      </dl>
      {task.error && <p className="form-error">{task.error}</p>}
      {task.status === "UNKNOWN" && (
        <p className="callout warning">
          <WarningCircle size={18} />
          Amazon 未返回明确结果。请先在 Amazon 广告后台核对实际状态，不要重复提交同一变更。
        </p>
      )}
      <details className="payload" open={!rows}>
        <summary>请求内容与执行结果</summary>
        <pre>
          {JSON.stringify(
            {
              arguments: task.arguments,
              payload: task.payload,
              result: task.result,
            },
            null,
            2,
          )}
        </pre>
        {task.result_truncated && (
          <p className="hint">
            此处仅预览前 50 条；点击“数据预览”或导出读取完整数据。
          </p>
        )}
      </details>
      {task.status === "AWAITING_CONFIRMATION" && (
        <div className="approval-box">
          <h3>
            <ShieldCheck size={20} weight="fill" />
            核对清单后确认执行
          </h3>
          <p>
            本操作会修改真实广告。确认只对当前账户和上方请求内容生效，提交后不能撤回。
          </p>
          <form
            className="approval-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (confirmation !== "确认" || busy) return;
              void action("approve", async () => {
                const t = await api<Task>(`/tasks/${task.id}/approve`, "POST", {
                  confirm_text: confirmation,
                  payload_hash: task.payload_hash,
                });
                setTask(t);
                setConfirmation("");
                setNotice("已确认，后台正在排队执行");
              });
            }}
          >
            <label>
              是否执行？执行请输入“确认”，不执行则无需操作。
              <input
                value={confirmation}
                onChange={(e) => setConfirmation(e.target.value)}
                placeholder="确认"
                autoComplete="off"
              />
            </label>
            <button
              className="primary"
              disabled={confirmation !== "确认" || !!busy}
            >
              {busy === "approve" ? "正在提交…" : "确认并提交执行"}
            </button>
          </form>
        </div>
      )}
      <div className="button-row">
        {task.status === "SUCCEEDED" && (
          <>
            <button className="secondary" onClick={() => loadRows(0)}>
              <Eye size={17} />
              数据预览
            </button>
            <a className="secondary" href={`/api/tasks/${task.id}/export`}>
              <DownloadSimple size={17} />
              导出 JSON
            </a>
          </>
        )}
        {CANCELLABLE_STATUSES.includes(task.status) && (
          <button
            className="text-button danger"
            disabled={!!busy}
            onClick={() =>
              action("cancel", async () =>
                setTask(await api<Task>(`/tasks/${task.id}/cancel`, "POST", {})),
              )
            }
          >
            取消本地任务
          </button>
        )}
      </div>
      {rows && (
        <section className="row-preview">
          <h3>已保存数据 · {rows.total.toLocaleString()} 条</h3>
          {rows.rows.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {columns.map((k) => (
                      <th key={k}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.rows.map((r: any, i: number) => (
                    <tr key={i}>
                      {columns.map((k) => (
                        <td key={k}>
                          {typeof r?.[k] === "object" && r?.[k] !== null
                            ? JSON.stringify(r[k])
                            : String(r?.[k] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="hint">
              任务已完成，但接口未返回数据记录。这不是仍在等待。
            </p>
          )}
          {rows.total > 0 && (
            <Pagination
              label={`${rowOffset + 1}–${Math.min(rowOffset + PAGE_SIZE, rows.total)} / ${rows.total}`}
              canPrev={rowOffset > 0}
              canNext={rowOffset + PAGE_SIZE < rows.total}
              onPrev={() => loadRows(Math.max(0, rowOffset - PAGE_SIZE))}
              onNext={() => loadRows(rowOffset + PAGE_SIZE)}
            />
          )}
        </section>
      )}
    </Modal>
  );
}
