import {
  SquaresFour,
  ChartBar,
  ClockCounterClockwise,
  Key,
  ShieldCheck,
  TerminalWindow,
  Buildings,
} from "@phosphor-icons/react";

export const PAGE_SIZE = 50;

export const navigation = [
  { path: "/", label: "工作概览", icon: SquaresFour },
  { path: "/accounts", label: "广告账户", icon: Buildings },
  { path: "/reports", label: "报表与数据", icon: ChartBar },
  { path: "/operations", label: "广告操作", icon: TerminalWindow },
  { path: "/approvals", label: "待确认操作", icon: ShieldCheck },
  { path: "/tokens", label: "MCP Token", icon: Key },
  { path: "/logs", label: "执行日志", icon: ClockCounterClockwise },
];
export const statuses: Record<string, string> = {
  AWAITING_CONFIRMATION: "待用户确认",
  QUEUED: "已排队",
  PROCESSING: "处理中",
  EXECUTING: "正在执行",
  SUBMITTING: "提交报表中",
  WAITING: "等待 Amazon",
  SUCCEEDED: "已完成",
  FAILED: "失败",
  PARTIAL: "部分成功",
  UNKNOWN: "结果待核实",
  CANCELLED: "已取消",
};
export const ACTIVE_STATUSES = [
  "QUEUED",
  "PROCESSING",
  "EXECUTING",
  "SUBMITTING",
  "WAITING",
];
export const CANCELLABLE_STATUSES = ["AWAITING_CONFIRMATION", "QUEUED", "WAITING"];
export const reportNames: Record<string, string> = {
  "reports.create-sp-campaign-placement": "SP · 活动广告位",
  "reports.create-sp-keywords": "SP · 关键词",
  "reports.create-search-terms": "SP · 搜索词",
  "reports.create-sb-campaigns": "SB · 广告活动",
  "reports.create-sb-ad-groups": "SB · 广告组",
  "reports.create-sb-targeting": "SB · 投放目标",
  "reports.create-sb-search-terms": "SB · 搜索词",
  "reports.create-sb-campaign-placement": "SB · 活动广告位",
  "reports.create-sd-campaigns": "SD · 广告活动",
  "reports.create-sd-ad-groups": "SD · 广告组",
  "reports.create-sd-product-ads": "SD · 商品广告",
  "reports.create-sd-targeting": "SD · 投放目标",
};
export const kindNames: Record<string, string> = {
  read: "查询",
  write: "变更计划",
  report: "报表",
};
export const scopeNames: Record<string, string> = {
  "ads:read": "查询广告数据",
  "reports:read": "读取已保存报表",
  "reports:create": "创建报表任务",
  "changes:plan": "提交变更计划（不能自行批准）",
};
export const MAX_REPORT_DAYS = 31;
