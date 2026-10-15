import { ShieldCheck } from "@phosphor-icons/react";
import { PAGE_SIZE } from "../lib/constants";
import { TaskTable } from "../components/TaskTable";
import {
  PageHeader,
  Pagination,
  PanelHeading,
  Segmented,
} from "../components/ui";
import { useWorkspace } from "../workspace";

export function Approvals() {
  const { tasks, filter, setFilter, offset, setOffset, overview } =
    useWorkspace();
  const pendingOnly = filter === "AWAITING_CONFIRMATION";
  const pending = overview.tasks_by_status?.AWAITING_CONFIRMATION || 0;
  return (
    <>
      <PageHeader
        title="待确认操作"
        description="核对账户、对象和具体数值后输入“确认”。每个计划只能提交一次。"
      />
      <div className="callout info">
        <ShieldCheck size={20} weight="fill" />
        <p>
          可在此页面核对后确认；拥有“在对话中确认执行变更”权限的 MCP Token，也可在用户于对话中回复“确认”后直接执行它自己提交的计划。计划 24 小时后过期；结果待核实的任务不会自动重试。
        </p>
      </div>
      <section className="panel">
        <PanelHeading
          title={pendingOnly ? "待确认清单" : "全部变更计划"}
          description={
            pendingOnly
              ? "点击“核对”查看请求内容并确认执行。"
              : "包括已确认、已执行、失败和已取消的变更计划。"
          }
        >
          <Segmented
            label="显示范围"
            value={pendingOnly ? "pending" : "all"}
            options={[
              { value: "pending", label: `待确认 · ${pending}` },
              { value: "all", label: "全部变更" },
            ]}
            onChange={(v) => {
              setFilter(v === "pending" ? "AWAITING_CONFIRMATION" : "");
              setOffset(0);
            }}
          />
        </PanelHeading>
        <TaskTable
          items={tasks.filter((t) => t.kind === "write")}
          emptyTitle={pendingOnly ? "没有等待确认的变更" : "还没有变更计划"}
          emptyDetail={
            pendingOnly
              ? "AI 助手或“广告操作”页提交的变更计划会出现在这里，等待你核对。"
              : "在“广告操作”中选择变更类操作，即可生成待确认计划。"
          }
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
