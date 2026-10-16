import { useEffect, useMemo, useState } from "react";
import { ArrowRight, DownloadSimple } from "@phosphor-icons/react";
import { api } from "../api";
import { stamp } from "../lib/format";
import {
  columnLabel,
  formatCell,
  isNumericColumn,
  orderColumns,
} from "../lib/reportColumns";
import type { RowsPage, Task } from "../lib/types";
import { Select } from "../components/Select";
import { reportLabel } from "../components/TaskTable";
import {
  Empty,
  PageHeader,
  Pagination,
  PanelHeading,
  Segmented,
} from "../components/ui";
import { useWorkspace } from "../workspace";

const PAGE_SIZES = ["50", "100", "200"] as const;
type PageSize = (typeof PAGE_SIZES)[number];

function reportParam() {
  return new URLSearchParams(location.search).get("report") || "";
}

function range(task: Task) {
  const { start_date, end_date } = task.arguments || {};
  return start_date ? `${start_date} ~ ${end_date}` : "";
}

export function ReportData() {
  const { accountId, selected, navigate, setError } = useWorkspace();
  const [reports, setReports] = useState<Task[] | null>(null);
  const [taskId, setTaskId] = useState(reportParam);
  const [size, setSize] = useState<PageSize>("200");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<RowsPage | null>(null);
  const [loading, setLoading] = useState(false);
  const limit = Number(size);

  useEffect(() => {
    if (!accountId) return setReports([]);
    let live = true;
    setReports(null);
    api<Task[]>(
      `/tasks?kind=report&status=SUCCEEDED&account_id=${accountId}&limit=100`,
    )
      .then((list) => {
        if (!live) return;
        setReports(list);
        // Keep a linked report if it belongs to this account, else the newest.
        setTaskId((id) => (list.some((t) => t.id === id) ? id : list[0]?.id || ""));
      })
      .catch((e) => live && setError((e as Error).message));
    return () => {
      live = false;
    };
  }, [accountId]);

  // Switching reports clears the table; paging keeps the old page (dimmed) until the next arrives.
  useEffect(() => setPage(null), [taskId]);
  useEffect(() => {
    if (!taskId) return;
    history.replaceState({}, "", `/data?report=${taskId}`);
    let live = true;
    setLoading(true);
    api<RowsPage>(`/tasks/${taskId}/rows?offset=${offset}&limit=${limit}`)
      .then((p) => live && setPage(p))
      .catch((e) => live && setError((e as Error).message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [taskId, offset, limit]);

  const task = reports?.find((t) => t.id === taskId);
  const columns = useMemo(() => orderColumns(page?.rows || []), [page]);
  const total = page?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / limit));

  return (
    <>
      <PageHeader
        title="数据表格"
        description="按报表查看已保存的数据，每页最多 200 条；完整数据可导出 JSON。"
      />
      <section className="panel">
        <PanelHeading
          title={task ? reportLabel(task.operation, task.arguments) : "报表数据"}
          description={
            task
              ? `${range(task)} · ${task.row_count.toLocaleString()} 行 · 完成于 ${stamp(task.updated_at)}`
              : selected
                ? `${selected.label} · ${selected.marketplace} 已完成的报表`
                : "先选择一个广告账户"
          }
        >
          {!!reports?.length && (
            <>
              <Select
                ariaLabel="选择报表"
                size="sm"
                className="report-picker"
                menuWidth={360}
                value={taskId}
                onChange={(id) => {
                  setTaskId(id);
                  setOffset(0);
                }}
                options={reports.map((t) => ({
                  value: t.id,
                  label: `${reportLabel(t.operation, t.arguments)} · ${range(t)}`,
                  description: `${t.row_count.toLocaleString()} 行 · 完成于 ${stamp(t.updated_at)}`,
                }))}
              />
              <Segmented
                label="每页条数"
                value={size}
                options={PAGE_SIZES.map((v) => ({ value: v, label: `${v} 条` }))}
                onChange={(v) => {
                  setSize(v);
                  setOffset(0);
                }}
              />
              {task && (
                <a className="secondary" href={`/api/tasks/${task.id}/export`}>
                  <DownloadSimple size={16} />
                  导出 JSON
                </a>
              )}
            </>
          )}
        </PanelHeading>
        {reports === null ? (
          <p className="table-status">正在读取报表列表…</p>
        ) : !reports.length ? (
          <Empty
            title="还没有已完成的报表"
            detail="在“报表与数据”创建报表任务，完成后会自动出现在这里。"
            action={
              <button className="primary" onClick={() => navigate("/reports")}>
                去创建报表
                <ArrowRight size={16} />
              </button>
            }
          />
        ) : !page ? (
          <p className="table-status">{loading ? "正在加载数据…" : ""}</p>
        ) : !page.rows.length ? (
          <Empty
            title="这份报表没有数据"
            detail="Amazon 已完成生成，但该日期范围内没有记录；这不是仍在等待。"
          />
        ) : (
          <>
            <div
              className="table-scroll data-table"
              aria-busy={loading}
              tabIndex={0}
              aria-label="报表数据"
            >
              <table>
                <thead>
                  <tr>
                    <th className="row-no" scope="col">
                      #
                    </th>
                    {columns.map((k) => (
                      <th
                        key={k}
                        scope="col"
                        title={k}
                        className={isNumericColumn(k) ? "numeric" : undefined}
                      >
                        {columnLabel(k)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {page.rows.map((r: Record<string, unknown>, i: number) => (
                    <tr key={offset + i}>
                      <td className="row-no">{offset + i + 1}</td>
                      {columns.map((k) => (
                        <td
                          key={k}
                          className={isNumericColumn(k) ? "numeric" : undefined}
                        >
                          {formatCell(k, r?.[k])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              label={`第 ${offset / limit + 1} / ${pages} 页 · ${offset + 1}–${Math.min(
                offset + limit,
                total,
              )} / ${total.toLocaleString()} 条`}
              canPrev={offset > 0 && !loading}
              canNext={offset + limit < total && !loading}
              onPrev={() => setOffset(Math.max(0, offset - limit))}
              onNext={() => setOffset(offset + limit)}
            />
          </>
        )}
      </section>
    </>
  );
}
