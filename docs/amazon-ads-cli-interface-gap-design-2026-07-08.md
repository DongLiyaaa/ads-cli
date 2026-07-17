# Amazon Ads CLI Interface Gap Design

日期：2026-07-08

## 1. 当前 CLI 已覆盖

当前 CLI 已经有这些命令：

- `auth health`
- `profiles list`
- `profiles resolve`
- `campaigns list`
- `campaigns set-state`
- `campaigns edit-budget`
- `portfolios list`
- `ad-groups list`
- `keywords list`
- `keywords edit-bid`
- `keywords set-state`
- `negatives list`
- `negatives add-ad-group`
- `negatives add-campaign`
- `negatives set-state`
- `reports create-sp-keywords`
- `reports create-sp-campaign-placement`
- `reports create-search-terms`
- `reports download`
- `reports parse-search-terms`
- `reports parse-sp-keywords`
- `reports parse-sp-campaign-placement`
- `reports status`
- `snapshot`

它已经覆盖了：

- OAuth 健康检查
- profile 发现
- portfolio 拉取
- ad group 拉取
- campaign metadata 拉取
- campaign 状态与预算写操作
- keyword 拉取与 bid/state 变更
- negative keyword 拉取、广告组/活动级否词新增、否词状态变更
- SP keyword/search term/campaign placement report 任务创建、状态查询、下载、解析

## 2. 仍未设计的接口总览

| 模块 | 当前状态 | 建议接口 | 优势 | 劣势 |
|---|---|---|---|---|
| Campaigns 扩展写操作 | 部分已设计 | `campaigns create` `campaigns clone` `campaigns placements` | 补齐活动搭建与投放位控制 | 写操作风险更高，需要审计 |
| Keywords 扩展写操作 | 部分已设计 | `keywords create` `keywords archive` `keywords bulk-edit` | 直接支持收词扩量和批量调价 | 需要参数校验与批量保护 |
| Negatives 扩展操作 | 部分已设计 | `negatives bulk-add` `negatives bulk-enable-pause` | 否词闭环更接近企业级作业 | Amazon negative keyword 状态枚举受限，不能照搬 archive |
| Display share reports | 未设计 | `reports create-sp-targeting-views` `reports create-search-impression-share` | 直接补展示份额和排名指标 | 报表异步且字段兼容复杂 |
| Targets / Product targets | 未设计 | `targets list` `targets create` `targets edit-bid` | 打通商品投放和类目投放 | 结构复杂，字段多 |
| Search term analysis | 未设计 | `search-terms analyze` `search-terms suggest-negatives` | 是广告优化最核心入口 | 依赖报表规则和阈值体系 |
| Recommendations | 未设计 | `recommendations ranked-keywords` | 直接接推荐词与展示份额指标 | 易受限流影响 |
| Bulk | 未设计 | `bulk preview` `bulk apply-bids` `bulk add-negatives` | 企业级执行效率高 | 需要模板与回滚设计 |
| Logs / Audit | 未设计 | `logs list` `logs export` `logs append` | 满足留痕和审计 | 需要本地/数据库日志策略 |
| Rules | 未设计 | `rules list` `rules simulate` `rules apply` | 把广告优化策略工程化 | 依赖规则 DSL 或配置格式 |

## 3. 高优先级设计顺序

### P1：展示份额与搜索词层

| 接口 | 作用 | 优势 | 劣势 |
|---|---|---|---|
| `reports create-search-impression-share` | 创建 SP 搜索展示份额报表任务 | 直接补你最关注的展示份额数据入口 | 报表异步且字段兼容性要先探明 |
| `reports create-search-terms` | 创建 SP 搜索词报表任务 | 直接打通最核心分析入口 | 依赖报表异步任务 |
| `reports download --report-id` | 下载报表结果文件 | 形成报表闭环 | 需要处理 url 过期、gzip 解压 |
| `search-terms analyze --file <path>` | 从已下载报表产出迁移/否词建议 | 可以直接服务广告优化动作 | 需要先定义分析规则 |

建议响应结构：

```json
{
  "meta": {
    "mode": "live",
    "status": "connected",
    "profileId": "<PROFILE_ID>",
    "marketplace": "US"
  },
  "data": {
    "report": {
      "reportId": "xxx",
      "status": "COMPLETED",
      "url": "https://...",
      "localPath": "/absolute/path.json"
    }
  }
}
```

### P1：关键词写操作

| 接口 | 作用 | 优势 | 劣势 |
|---|---|---|---|
| `keywords create` | 新增关键词 | 支持收词迁移 | 要求 campaign/adgroup 上下文完整 |
| `keywords edit-bid` | 调整竞价 | 最贴近实战优化 | 误改会直接影响投放 |
| `keywords set-state` | 暂停/启用/归档 | 支持风险词管理 | 需要严格状态校验 |
| `keywords bulk-edit` | 批量提价/降价/暂停 | 更接近企业级日常运营 | 需要 dry-run 和回滚 |

建议最小请求参数：

```json
{
  "campaignId": "123",
  "adGroupId": "456",
  "keywordId": "789",
  "bid": 0.92
}
```

### P1：否词闭环

| 接口 | 作用 | 优势 | 劣势 |
|---|---|---|---|
| `negatives add-campaign` | 新增活动级否词 | 补齐 ad group 之外的主要场景 | 一旦否错影响更大 |
| `negatives set-state` | 启用/暂停否词 | 能撤销或恢复错误否词 | Amazon negative keyword 不支持普通 archive 语义 |
| `negatives bulk-add` | 批量新增否词 | 适合企业级作业 | 需要批量预检查 |

建议最小请求参数：

```json
{
  "campaignId": "123",
  "keywordText": "usb c camera",
  "matchType": "NEGATIVE_EXACT"
}
```

## 4. 中优先级设计顺序

### P2：广告组层

| 接口 | 作用 | 优势 | 劣势 |
|---|---|---|---|
| `ad-groups list` | 拉取 ad group 列表 | 让 campaign/keyword/negative 关系完整 | 只是结构补齐，不直接产出优化动作 |

建议响应字段：

- `adGroupId`
- `campaignId`
- `name`
- `defaultBid`
- `state`

### P2：推荐词与投放对象层

| 接口 | 作用 | 优势 | 劣势 |
|---|---|---|---|
| `recommendations ranked-keywords` | 拉推荐词和展示份额指标 | 直接补 AI 优化输入 | 接口限流明显 |
| `targets list` | 拉自动投放/商品投放 target | 把 campaign 优化粒度继续下钻 | 字段面较大 |
| `targets edit-bid` | 调 target 竞价 | 能覆盖商品投放调价 | 误操作影响真实流量 |

建议响应字段：

- `keyword`
- `translation`
- `searchTermImpressionShare`
- `searchTermImpressionRank`
- `suggestedBid`
- `bidInfo`

### P2：报表解析层

| 接口 | 作用 | 优势 | 劣势 |
|---|---|---|---|
| `reports parse-sp-keywords` | 把报表转为结构化 JSON | 为后续分析和 Excel 导出打底 | 要处理多列兼容 |
| `reports parse-search-terms` | 把搜索词报表转为结构化 JSON | 直接服务优化策略 | 需要定义稳定 schema |

## 5. 企业级必须补的横切设计

### 5.1 Bulk 接口

建议设计：

- `bulk preview-bid-changes --input file.json`
- `bulk apply-bid-changes --input file.json`
- `bulk preview-negatives --input file.json`
- `bulk apply-negatives --input file.json`

推荐输入格式：

```json
{
  "operator": "codex",
  "reason": "harvest and waste cleanup",
  "items": [
    {
      "type": "keyword_bid",
      "campaignId": "123",
      "adGroupId": "456",
      "keywordId": "789",
      "bid": 0.88
    }
  ]
}
```

优势：

- 批量执行效率高
- 适合 SOP 化
- 便于接审批流

劣势：

- 一次影响面大
- 更依赖 dry-run、审计和回滚

### 5.2 审计日志接口

建议设计：

- `logs list`
- `logs export --format json`
- `logs append` 仅内部调用，不对人工暴露

建议日志字段：

- `logId`
- `time`
- `operator`
- `action`
- `targetType`
- `targetId`
- `before`
- `after`
- `request`
- `response`
- `status`
- `reason`

### 5.3 规则引擎接口

建议设计：

- `rules list`
- `rules simulate --rule-file rule.json`
- `rules apply --rule-file rule.json`

建议规则文件格式：

```json
{
  "ruleId": "low-acos-raise-bid",
  "scope": "keyword",
  "filters": {
    "matchType": ["EXACT", "PHRASE"],
    "minClicks": 8,
    "maxAcos": 0.2
  },
  "action": {
    "type": "increase_bid_pct",
    "value": 0.1,
    "cap": 1.2
  }
}
```

## 6. 推荐的下一阶段接口实施顺序

| 顺序 | 接口 | 原因 |
|---|---|---|
| 1 | `reports create-search-impression-share` | 先补展示份额这个高价值数据入口 |
| 2 | `reports create-search-terms` | 搜索词仍然是优化分析主入口 |
| 3 | `search-terms analyze` | 让 CLI 开始具备优化判断能力 |
| 4 | `targets list` + `targets edit-bid` | 把优化粒度从 keyword 扩展到 target |
| 5 | `bulk apply-bids` + `bulk add-negatives` | 补企业级批量执行闭环 |
| 6 | `ad-groups list` | 把对象层级补完整 |
| 7 | `recommendations ranked-keywords` | 补推荐和展示份额输入 |
| 8 | `bulk preview/apply` | 进入企业级执行模式 |
| 9 | `logs list/export` | 补留痕和追责能力 |
| 10 | `rules simulate/apply` | 完成规则化自动运营基础设施 |

## 7. 建议的统一响应约定

所有新接口继续统一为：

```json
{
  "meta": {
    "mode": "live",
    "status": "connected",
    "profileId": "<PROFILE_ID>",
    "marketplace": "US"
  },
  "data": {},
  "domain": "keywords"
}
```

无凭证或无法调用 live 时：

```json
{
  "meta": {
    "mode": "mock",
    "status": "attention",
    "missingCredentials": ["CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"]
  },
  "data": {},
  "domain": "reports"
}
```

## 8. 最值得优先做的 3 个设计结论

1. 先补 `reports download`，因为现在报表链路还没闭环。
2. 先补 `search-terms`，因为前端已经有搜索词域，但 CLI 还没接到最关键的数据。
3. 先补 `keywords edit-bid` 和 `negatives archive`，因为它们是最常用的真实优化动作。
