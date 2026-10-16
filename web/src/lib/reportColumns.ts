/** Display metadata for Amazon Ads report columns (see core/reports.py). */
type Format = "int" | "money" | "share";
type Column = { label: string; format?: Format };

/** Amazon suffixes attributed metrics with their window, e.g. sales7d. */
function attribution(key: string, label: string, format: Format): [string, Column][] {
  return [1, 7, 14, 30].map((d) => [`${key}${d}d`, { label: `${label}（${d} 天）`, format }]);
}

const COLUMNS: [string, Column][] = [
  ["date", { label: "日期" }],
  ["campaignName", { label: "广告活动" }],
  ["campaignId", { label: "活动 ID" }],
  ["campaignStatus", { label: "活动状态" }],
  ["campaignBiddingStrategy", { label: "竞价策略" }],
  ["campaignBudgetType", { label: "预算类型" }],
  ["campaignBudgetAmount", { label: "预算", format: "money" }],
  ["adGroupName", { label: "广告组" }],
  ["adGroupId", { label: "广告组 ID" }],
  ["adStatus", { label: "广告组状态" }],
  ["adId", { label: "广告 ID" }],
  ["asin", { label: "ASIN" }],
  ["sku", { label: "SKU" }],
  ["advertisedAsin", { label: "推广 ASIN" }],
  ["advertisedSku", { label: "推广 SKU" }],
  ["purchasedAsin", { label: "购买的 ASIN" }],
  ["placementClassification", { label: "广告位" }],
  ["keyword", { label: "关键词" }],
  ["keywordText", { label: "关键词" }],
  ["keywordId", { label: "关键词 ID" }],
  ["keywordType", { label: "关键词类型" }],
  ["matchType", { label: "匹配类型" }],
  ["targeting", { label: "投放表达式" }],
  ["adKeywordStatus", { label: "投放状态" }],
  ["keywordBid", { label: "竞价", format: "money" }],
  ["targetingText", { label: "投放目标" }],
  ["targetingType", { label: "投放类型" }],
  ["targetingId", { label: "投放 ID" }],
  ["targetId", { label: "投放 ID" }],
  ["searchTerm", { label: "搜索词" }],
  ["campaignBudgetCurrencyCode", { label: "币种" }],
  ["ad_product_type", { label: "广告类型" }],
  ["ad_product_combo", { label: "广告类型组合" }],
  ["campaign", { label: "广告活动" }],
  ["customer_search_term", { label: "搜索词" }],
  ["frequency_bucket", { label: "曝光频次" }],
  ["time_to_purchase", { label: "购买时长" }],
  ["hour_of_day", { label: "小时" }],
  ["reached_users", { label: "触达人数", format: "int" }],
  ["purchasing_users", { label: "购买人数", format: "int" }],
  ["impressions", { label: "曝光", format: "int" }],
  ["clicks", { label: "点击", format: "int" }],
  ["clickThroughRate", { label: "点击率", format: "share" }],
  ["costPerClick", { label: "单次点击花费", format: "money" }],
  ["cost", { label: "花费", format: "money" }],
  ["purchases", { label: "订单", format: "int" }],
  ["sales", { label: "销售额", format: "money" }],
  ["spend", { label: "花费", format: "money" }],
  ["product_sales", { label: "销售额", format: "money" }],
  ["units_sold", { label: "销量", format: "int" }],
  ["ntb_purchases", { label: "新客订单", format: "int" }],
  ["ntb_product_sales", { label: "新客销售额", format: "money" }],
  ...attribution("purchases", "订单", "int"),
  ...attribution("sales", "销售额", "money"),
  ...attribution("unitsSoldClicks", "销量", "int"),
  ...attribution("purchasesSameSku", "同 SKU 订单", "int"),
  ...attribution("attributedSalesSameSku", "同 SKU 销售额", "money"),
  ...attribution("unitsSoldSameSku", "同 SKU 销量", "int"),
  ...attribution("purchasesOtherSku", "其他 SKU 订单", "int"),
  ...attribution("salesOtherSku", "其他 SKU 销售额", "money"),
  ...attribution("unitsSoldOtherSku", "其他 SKU 销量", "int"),
  ["topOfSearchImpressionShare", { label: "搜索顶部曝光份额", format: "share" }],
  ["grossImpressions", { label: "总曝光", format: "int" }],
  ["grossClickThroughs", { label: "总点击", format: "int" }],
  ["invalidImpressions", { label: "无效曝光", format: "int" }],
  ["invalidClickThroughs", { label: "无效点击", format: "int" }],
  ["invalidImpressionRate", { label: "无效曝光率", format: "share" }],
  ["invalidClickThroughRate", { label: "无效点击率", format: "share" }],
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
