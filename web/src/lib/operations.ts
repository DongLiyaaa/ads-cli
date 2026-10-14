import type { Capability } from "./types";

const resources: Record<string, string> = {
  campaigns: "广告活动",
  "ad-groups": "广告组",
  keywords: "关键词",
  negatives: "否定关键词",
  "negative-targets": "否定投放",
  targets: "投放目标",
  portfolios: "广告组合",
  "product-ads": "商品广告",
  audiences: "受众",
  "budget-rules": "预算规则",
  locations: "地理位置",
  snapshots: "快照",
  snapshot: "快照",
  raw: "原始接口",
};
const verbs: Record<string, string> = {
  list: "列表查询",
  show: "查看详情",
  create: "创建",
  add: "添加",
  archive: "归档",
  update: "更新",
  request: "发起请求",
  status: "查询状态",
  download: "下载",
  usage: "使用情况",
  taxonomy: "分类目录",
  associate: "关联广告活动",
  disassociate: "取消关联",
  campaigns: "关联的广告活动",
  "campaign-rules": "广告活动规则",
  "set-state": "修改状态",
  "edit-bid": "修改竞价",
  "edit-budget": "修改预算",
  "edit-name": "修改名称",
  "edit-bidding": "修改竞价设置",
  "edit-bidding-strategy": "修改竞价策略",
  "edit-placement-bids": "修改广告位竞价",
  "add-ad-group": "添加到广告组",
  "add-campaign": "添加到广告活动",
  "add-asin": "添加 ASIN 投放",
  "add-category": "添加品类投放",
  "add-expression": "添加表达式投放",
  "add-audience": "添加受众投放",
};

export type OperationInfo = {
  product: "SP" | "SB" | "SD";
  resource: string;
  title: string;
};

export function describeOperation(operation: string): OperationInfo {
  const [group, verb = group] = operation.split(".");
  const product = group.startsWith("sb-")
    ? "SB"
    : group.startsWith("sd-")
      ? "SD"
      : "SP";
  const bare = group.replace(/^(sp|sb|sd)-/, "");
  const resource = resources[bare] || bare;
  return {
    product,
    resource,
    title:
      verb === group ? resource : `${resource} · ${verbs[verb] || verb}`,
  };
}

export function argumentDefaults(c?: Capability) {
  return JSON.stringify(
    Object.fromEntries(
      Object.entries(c?.inputSchema.properties || {})
        .filter(([, v]) => v.default !== undefined)
        .map(([k, v]) => [k, v.default]),
    ),
    null,
    2,
  );
}

export function placeholderFor(schema: {
  type: string;
  default?: unknown;
  enum?: string[];
}) {
  if (schema.default !== undefined) return schema.default;
  if (schema.enum?.length) return schema.enum[0];
  return schema.type === "integer" || schema.type === "number"
    ? 0
    : schema.type === "boolean"
      ? false
      : schema.type === "array"
        ? []
        : "";
}
