import { useEffect, useState } from "react";
import { Plus } from "@phosphor-icons/react";
import { api } from "../api";
import { MAX_REPORT_DAYS, PAGE_SIZE, reportNames, statuses } from "../lib/constants";
import { shiftDays, todayIn } from "../lib/dates";
import { daySpan } from "../lib/format";
import type { Task } from "../lib/types";
import { TaskTable } from "../components/TaskTable";
import { DateRangePicker } from "../components/DateRangePicker";
import { Select } from "../components/Select";
import { PageHeader, Pagination, PanelHeading } from "../components/ui";
import { useWorkspace } from "../workspace";

const productNames: Record<string, string> = {
  SP: "Sponsored Products",
  SB: "Sponsored Brands",
  SD: "Sponsored Display",
};
const reportOptions = Object.entries(reportNames).map(([value, label]) => ({
  value,
  label,
  group: productNames[label.slice(0, 2)],
}));
const statusOptions = [
  { value: "", label: "全部状态", prefix: <i className="dot all" aria-hidden="true" /> },
  ...Object.entries(statuses).map(([value, label]) => ({
    value,
    label,
    prefix: <i className={`dot ${value.toLowerCase()}`} aria-hidden="true" />,
  })),
];

export function Reports() {
  const {
    selected,
    accountId,
    busy,
    action,
    setNotice,
    openTask,
    tasks,
    filter,
    setFilter,
    offset,
    setOffset,
    navigate,
  } = useWorkspace();
  const [reportKind, setReportKind] = useState(
    "reports.create-sp-campaign-placement",
  );
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const today = todayIn(selected?.timezone || "America/Los_Angeles");
  useEffect(() => {
    if (!selected) return;
    const yesterday = shiftDays(today, -1);
    setEndDate(yesterday);
    setStartDate(shiftDays(yesterday, -6));
  }, [selected?.id, selected?.timezone]);
  const span = daySpan(startDate, endDate);
  const rangeError =
    span === null
      ? ""
      : span < 1
        ? "结束日期不能早于开始日期"
        : span > MAX_REPORT_DAYS
          ? `单个任务最多 ${MAX_REPORT_DAYS} 天，当前 ${span} 天，请拆分任务`
          : "";
  return (
    <>
      <PageHeader
        title="报表与数据"
        description="后台持续查询 Amazon 报表状态，完成后自动保存原始数据，可以离开页面等待。"
      />
      <section className="panel">
        <PanelHeading
          title="创建报表任务"
          description={`单个任务最多 ${MAX_REPORT_DAYS} 天；日期按账户时区${
            selected?.timezone ? `（${selected.timezone}）` : ""
          }计算，可查询的历史范围以 Amazon 返回为准。`}
        />
        <form
          className="report-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (rangeError) return;
            void action("report", async () => {
              const t = await api<Task>("/reports", "POST", {
                account_id: accountId,
                operation: reportKind,
                arguments: {
                  start_date: startDate,
                  end_date: endDate,
                  time_unit: "DAILY",
                },
                idempotency_key: crypto.randomUUID(),
              });
              setNotice("报表已入队，后台将自动等待并保存结果");
              await openTask(t.id);
            });
          }}
        >
          <Select
            label="报表类型"
            value={reportKind}
            onChange={setReportKind}
            options={reportOptions}
          />
          <DateRangePicker
            label="日期范围"
            start={startDate}
            end={endDate}
            today={today}
            maxDays={MAX_REPORT_DAYS}
            onChange={(start, end) => {
              setStartDate(start);
              setEndDate(end);
            }}
          />
          <button
            className="primary"
            disabled={!!busy || !accountId || !span || !!rangeError}
          >
            <Plus size={17} />
            {busy === "report" ? "正在创建…" : "创建任务"}
          </button>
          <p className={rangeError ? "field-note error" : "field-note"}>
            {!accountId ? (
              <>
                先在
                <button
                  type="button"
                  className="text-button inline"
                  onClick={() => navigate("/accounts")}
                >
                  广告账户
                </button>
                连接并选择一个账户。
              </>
            ) : (
              rangeError || "按日汇总；报表生成后自动保存，无需停留在此页面。"
            )}
          </p>
        </form>
      </section>
      <section className="panel">
        <PanelHeading
          title="任务记录"
          description="报表、查询与操作任务统一留存，空报表和失败任务会明确区分。"
        >
          <Select
            ariaLabel="按状态筛选"
            size="sm"
            className="filter-select"
            value={filter}
            onChange={(v) => {
              setFilter(v);
              setOffset(0);
            }}
            options={statusOptions}
          />
        </PanelHeading>
        <TaskTable
          items={tasks}
          emptyTitle={filter ? "没有符合条件的任务" : undefined}
          emptyDetail={filter ? "换一个状态筛选，或清除筛选查看全部任务。" : undefined}
        />
        <Pagination
          label={`第 ${offset / PAGE_SIZE + 1} 页`}
          canPrev={offset > 0}
          canNext={tasks.length >= PAGE_SIZE}
          onPrev={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          onNext={() => setOffset(offset + PAGE_SIZE)}
        />
      </section>
    </>
  );
}
