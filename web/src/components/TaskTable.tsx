import { CaretRight } from "@phosphor-icons/react";
import { kindNames, reportNames } from "../lib/constants";
import { accountName, stamp } from "../lib/format";
import { describeOperation } from "../lib/operations";
import type { Task } from "../lib/types";
import { useWorkspace } from "../workspace";
import { Empty, Status } from "./ui";

/** Report tasks use their report label; other operations get "SP · 资源 · 动作". */
export function taskTitle(operation: string) {
  if (reportNames[operation]) return `${reportNames[operation]}报表`;
  const info = describeOperation(operation);
  return `${info.product} · ${info.title}`;
}

export function TaskTable({
  items,
  emptyTitle = "这里还没有任务",
  emptyDetail = "创建报表或查询广告后，任务状态与结果会保存在这里。",
}: {
  items: Task[];
  emptyTitle?: string;
  emptyDetail?: string;
}) {
  const { accounts, openTask } = useWorkspace();
  if (!items.length) return <Empty title={emptyTitle} detail={emptyDetail} />;
  return (
    <div className="table-scroll">
      <table className="task-table">
        <thead>
          <tr>
            <th>任务 / 操作</th>
            <th>账户</th>
            <th>状态</th>
            <th className="numeric">数据行</th>
            <th>创建时间</th>
            <th>
              <span className="visually-hidden">操作</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.id}>
              <td>
                <strong>{taskTitle(t.operation)}</strong>
                <small>
                  <span className="kind">{kindNames[t.kind] || t.kind}</span>
                  <span className="mono">{t.operation}</span>
                </small>
              </td>
              <td>{accountName(accounts, t.account_id)}</td>
              <td>
                <Status value={t.status} />
              </td>
              <td className="numeric">
                {t.kind === "report" && t.status === "SUCCEEDED"
                  ? t.row_count.toLocaleString()
                  : "—"}
              </td>
              <td>{stamp(t.created_at)}</td>
              <td className="row-action">
                <button className="text-button" onClick={() => openTask(t.id)}>
                  {t.status === "AWAITING_CONFIRMATION" ? "核对" : "查看"}
                  <CaretRight size={14} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
