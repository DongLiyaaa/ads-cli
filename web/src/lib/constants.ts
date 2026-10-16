import {
  SquaresFour,
  ChartBar,
  ClockCounterClockwise,
  Key,
  ShieldCheck,
  TerminalWindow,
  Buildings,
  Table,
  Funnel,
} from "@phosphor-icons/react";

export const PAGE_SIZE = 50;

export const navigation = [
  { path: "/", label: "工作概览", icon: SquaresFour },
  { path: "/accounts", label: "广告账户", icon: Buildings },
  { path: "/reports", label: "报表与数据", icon: ChartBar },
  { path: "/data", label: "数据表格", icon: Table },
  { path: "/amc", label: "AMC 洞察", icon: Funnel },
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
  "reports.create-sp-campaigns": "SP · 广告活动",
  "reports.create-sp-ad-groups": "SP · 广告组",
  "reports.create-sp-campaign-placement": "SP · 活动广告位",
  "reports.create-sp-targeting": "SP · 投放（关键词与商品定向）",
  "reports.create-sp-keywords": "SP · 关键词",
  "reports.create-search-terms": "SP · 搜索词",
  "reports.create-sp-impression-share": "SP · 搜索顶部展示份额（关键词）",
  "reports.create-sp-advertised-products": "SP · 推广的商品",
  "reports.create-sp-purchased-products": "SP · 已购买的商品",
  "reports.create-sp-gross-and-invalids": "SP · 总流量和无效流量",
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
export const AMC_OPERATION = "reports.create-amc-query";
/** Mirrors TEMPLATES in core/amc.py so task lists can name AMC runs offline. */
export const amcTemplateNames: Record<string, string> = {
  "ad-product-combo": "广告类型组合与转化",
  "time-to-conversion": "从点击/曝光到购买的时长",
  "new-to-brand-by-campaign": "品牌新客（按广告活动）",
  "frequency-vs-conversion": "曝光频次与购买率",
  "search-term-conversion": "搜索词：花费、购买与新客",
  "hour-of-day": "分时段表现",
};
export const AMC_MAX_DAYS = 366;
export const kindNames: Record<string, string> = {
  read: "查询",
  write: "变更计划",
  report: "报表",
};
export const scopeNames: Record<string, string> = {
  "ads:read": "查询广告数据",
  "reports:read": "读取已保存报表",
  "reports:create": "创建报表任务",
  "changes:plan": "提交变更计划",
  "changes:approve": "在对话中确认执行变更",
};
/** Scopes that change real ads; never pre-selected when creating a token. */
export const scopeWarnings: Record<string, string> = {
  "changes:plan": "生成待确认的变更计划，不会直接修改广告",
  "changes:approve":
    "用户在对话里回复“确认”后，AI 可直接提交执行，会修改真实广告；仅限该 Token 自己提交的计划",
};
export const MAX_REPORT_DAYS = 31;
