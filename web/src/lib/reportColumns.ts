/** Display metadata for Amazon Ads report columns (see core/reports.py). */
type Format = "int" | "money" | "share";
type Column = { label: string; format?: Format };

const COLUMNS: [string, Column][] = [
  ["date", { label: "日期" }],
  ["campaignName", { label: "广告活动" }],
  ["campaignId", { label: "活动 ID" }],
  ["campaignStatus", { label: "活动状态" }],
  ["campaignBudgetType", { label: "预算类型" }],
  ["campaignBudgetAmount", { label: "预算", format: "money" }],
  ["campaignBudgetCurrencyCode", { label: "币种" }],
  ["adGroupName", { label: "广告组" }],
  ["adGroupId", { label: "广告组 ID" }],
  ["adId", { label: "广告 ID" }],
  ["asin", { label: "ASIN" }],
  ["sku", { label: "SKU" }],
  ["placementClassification", { label: "广告位" }],
  ["keyword", { label: "关键词" }],
  ["keywordText", { label: "关键词" }],
  ["keywordId", { label: "关键词 ID" }],
  ["matchType", { label: "匹配类型" }],
  ["targetingText", { label: "投放目标" }],
  ["targetingType", { label: "投放类型" }],
  ["targetingId", { label: "投放 ID" }],
  ["targetId", { label: "投放 ID" }],
  ["searchTerm", { label: "搜索词" }],
  ["impressions", { label: "曝光", format: "int" }],
  ["clicks", { label: "点击", format: "int" }],
  ["cost", { label: "花费", format: "money" }],
  ["purchases", { label: "订单", format: "int" }],
  ["purchases30d", { label: "订单（30 天）", format: "int" }],
  ["sales", { label: "销售额", format: "money" }],
  ["sales30d", { label: "销售额（30 天）", format: "money" }],
  ["topOfSearchImpressionShare", { label: "搜索顶部曝光份额", format: "share" }],
];
const known = new Map(COLUMNS.map(([key, c], i) => [key, { ...c, order: i }]));

export function columnLabel(key: string) {
  return known.get(key)?.label ?? key;
}

export function isNumericColumn(key: string) {
  return !!known.get(key)?.format;
}

/** Known columns in a fixed business order, unknown ones after in first-seen order. */
export function orderColumns(rows: Record<string, unknown>[]) {
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r ?? {}))));
  const rank = (k: string) => known.get(k)?.order ?? COLUMNS.length;
  return keys
    .map((k, i) => ({ k, i }))
    .sort((a, b) => rank(a.k) - rank(b.k) || a.i - b.i)
    .map(({ k }) => k);
}

const money = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const integer = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 });
const share = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 });

export function formatCell(key: string, value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  const format = known.get(key)?.format;
  // IDs stay verbatim: grouping separators would corrupt them.
  if (format && typeof value === "number") {
    if (format === "money") return money.format(value);
    if (format === "int") return integer.format(value);
    return share.format(value);
  }
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
