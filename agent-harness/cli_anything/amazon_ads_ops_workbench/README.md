# Amazon Ads Ops Workbench CLI

This CLI gives agents a direct command-line interface to the Amazon Ads workbench backend capabilities already present in this repository.

## Covered now

- OAuth health inspection
- Profile listing and marketplace resolution
- Portfolio listing, creation, and state editing
- Sponsored Products ad group listing
- Sponsored Products ad group creation, default bid editing, and state editing
- Sponsored Products campaign metadata listing
- Sponsored Products campaign creation
- Sponsored Products campaign state editing
- Sponsored Products campaign budget editing
- Sponsored Products campaign bidding strategy and placement bid adjustment interfaces with user-supplied values
- Sponsored Products keyword listing
- Sponsored Products keyword creation
- Sponsored Products keyword bid editing
- Sponsored Products keyword state editing
- Sponsored Products product ad listing, creation, and state editing
- Sponsored Products ASIN/category/expression target listing, creation, bid editing, and state editing
- Negative keyword listing, ad group/campaign negative creation, and negative state editing
- Negative product targeting listing, ad group/campaign negative creation, and negative state editing
- Restricted raw `/sp/` request escape hatch for SP endpoints not yet wrapped by typed commands
- Sponsored Products keyword, search term, and campaign placement report task creation
- Report status inspection, file download, and local report parsing
- Snapshot output aligned with the web proxy

## Environment variables

Set the same variables used by the web proxy:

```bash
export AMAZON_ADS_CLIENT_ID=...
export AMAZON_ADS_CLIENT_SECRET=...
export AMAZON_ADS_REFRESH_TOKEN=...
export AMAZON_ADS_PROFILE_ID=
export AMAZON_ADS_REGION=NA
export AMAZON_ADS_MARKETPLACE=US
```

## Install

```bash
cd agent-harness
pip install -e .
```

## Command examples

```bash
cli-anything-amazon-ads-ops-workbench --json auth health
cli-anything-amazon-ads-ops-workbench --json profiles list
cli-anything-amazon-ads-ops-workbench --json profiles resolve --marketplace US
cli-anything-amazon-ads-ops-workbench --json portfolios create --name "T11" --budget 100 --currency-code USD --dry-run
cli-anything-amazon-ads-ops-workbench --json portfolios set-state --portfolio-id 123 --state ARCHIVED --dry-run
cli-anything-amazon-ads-ops-workbench --json campaigns list --marketplace US
cli-anything-amazon-ads-ops-workbench --json campaigns create --name "T11 Manual" --targeting-type MANUAL --budget 10 --start-date 2026-07-22 --strategy MANUAL --dry-run
cli-anything-amazon-ads-ops-workbench --json campaigns set-state --campaign-id 123 --state PAUSED --dry-run
cli-anything-amazon-ads-ops-workbench --json campaigns edit-budget --campaign-id 123 --budget 5.0 --dry-run
cli-anything-amazon-ads-ops-workbench --json campaigns edit-bidding-strategy --campaign-id 123 --strategy AUTO_FOR_SALES --dry-run
cli-anything-amazon-ads-ops-workbench --json campaigns edit-placement-bids --campaign-id 123 --top-of-search 100 --product-pages 25 --rest-of-search 0 --dry-run
cli-anything-amazon-ads-ops-workbench --json portfolios list --marketplace US
cli-anything-amazon-ads-ops-workbench --json ad-groups list --campaign-id 123
cli-anything-amazon-ads-ops-workbench --json ad-groups create --campaign-id 123 --name "Exact Core" --default-bid 0.72 --dry-run
cli-anything-amazon-ads-ops-workbench --json ad-groups set-state --campaign-id 123 --ad-group-id 456 --state PAUSED --dry-run
cli-anything-amazon-ads-ops-workbench --json ad-groups edit-bid --campaign-id 123 --ad-group-id 456 --default-bid 0.81 --dry-run
cli-anything-amazon-ads-ops-workbench --json keywords list --campaign-id 123
cli-anything-amazon-ads-ops-workbench --json keywords add --campaign-id 123 --ad-group-id 456 --keyword-text "ai recorder" --match-type EXACT --bid 0.91 --dry-run
cli-anything-amazon-ads-ops-workbench --json keywords edit-bid --campaign-id 123 --ad-group-id 456 --keyword-id 789 --bid 0.92 --dry-run
cli-anything-amazon-ads-ops-workbench --json keywords set-state --campaign-id 123 --ad-group-id 456 --keyword-id 789 --state PAUSED --dry-run
cli-anything-amazon-ads-ops-workbench --json product-ads list --campaign-id 123
cli-anything-amazon-ads-ops-workbench --json product-ads add --campaign-id 123 --ad-group-id 456 --sku SKU-1 --dry-run
cli-anything-amazon-ads-ops-workbench --json product-ads set-state --product-ad-id 789 --state PAUSED --dry-run
cli-anything-amazon-ads-ops-workbench --json targets list --campaign-id 123
cli-anything-amazon-ads-ops-workbench --json targets add-asin --campaign-id 123 --ad-group-id 456 --asin B000000001 --bid 0.88 --dry-run
cli-anything-amazon-ads-ops-workbench --json targets add-category --campaign-id 123 --ad-group-id 456 --category-id 123456 --bid 0.67 --dry-run
cli-anything-amazon-ads-ops-workbench --json targets add-expression --campaign-id 123 --ad-group-id 456 --category-id 123456 --predicate BRAND_SAME_AS=Brand --expression-type AUTO --dry-run
cli-anything-amazon-ads-ops-workbench --json targets edit-bid --target-id 789 --bid 0.79 --dry-run
cli-anything-amazon-ads-ops-workbench --json targets set-state --target-id 789 --state ARCHIVED --dry-run
cli-anything-amazon-ads-ops-workbench --json negatives list --campaign-id 123 --scope both
cli-anything-amazon-ads-ops-workbench --json negatives add-ad-group --campaign-id 123 --ad-group-id 456 --keyword-text "carplay wireless adapter" --match-type NEGATIVE_EXACT --dry-run
cli-anything-amazon-ads-ops-workbench --json negatives add-campaign --campaign-id 123 --keyword-text "usb c camera" --match-type NEGATIVE_EXACT --dry-run
cli-anything-amazon-ads-ops-workbench --json negatives set-state --negative-keyword-id 789 --scope adGroup --state PAUSED --dry-run
cli-anything-amazon-ads-ops-workbench --json negative-targets list --campaign-id 123 --scope both
cli-anything-amazon-ads-ops-workbench --json negative-targets add-ad-group --campaign-id 123 --ad-group-id 456 --asin B000000001 --expression-type AUTO --dry-run
cli-anything-amazon-ads-ops-workbench --json negative-targets add-campaign --campaign-id 123 --category-id 123456 --dry-run
cli-anything-amazon-ads-ops-workbench --json negative-targets set-state --negative-target-id 789 --scope campaign --state PAUSED --dry-run
cli-anything-amazon-ads-ops-workbench --json sp-raw request --method POST --path /sp/targets/list --payload-json '{"maxResults":10}' --dry-run
cli-anything-amazon-ads-ops-workbench --json reports create-sp-keywords --start-date 2026-07-01 --end-date 2026-07-07
cli-anything-amazon-ads-ops-workbench --json reports create-sp-campaign-placement --start-date 2026-07-01 --end-date 2026-07-07 --time-unit DAILY
cli-anything-amazon-ads-ops-workbench --json reports create-search-terms --start-date 2026-07-01 --end-date 2026-07-07
cli-anything-amazon-ads-ops-workbench --json reports status --report-id <REPORT_ID>
cli-anything-amazon-ads-ops-workbench --json reports download --report-id <REPORT_ID>
cli-anything-amazon-ads-ops-workbench --json reports parse-search-terms --input-file ~/Downloads/spSearchTerm.json
cli-anything-amazon-ads-ops-workbench --json reports parse-sp-keywords --input-file ~/Downloads/spKeywords.json
cli-anything-amazon-ads-ops-workbench --json reports parse-sp-campaign-placement --input-file ~/Downloads/spCampaignPlacement.json
cli-anything-amazon-ads-ops-workbench --json snapshot --marketplace US
```

## Approval gate for live mutations

Read commands and report commands run normally. SP write commands do not submit directly by default. When a write command is run without `--dry-run`, the CLI writes an approval plan and returns `meta.mode = "approval-plan"` with a `planId`, payload hash, risk level, and this required prompt:

```text
是否执行？执行请回复“确认”，不执行则无需回复！
```

After the user replies exactly `确认`, execute the saved plan:

```bash
cli-anything-amazon-ads-ops-workbench --json approvals show --plan-id <PLAN_ID>
cli-anything-amazon-ads-ops-workbench --json approvals execute --plan-id <PLAN_ID> --confirm-text 确认
```

If the user does not reply exactly `确认`, do not call `approvals execute`.

## Placement bid adjustment

`campaigns edit-placement-bids` is an interface only. Pass only placement percentages explicitly supplied by the user; the CLI does not recommend or auto-calculate bid adjustments.

Supported flags are `--top-of-search`, `--product-pages`, and `--rest-of-search`, each in the 0-900 range. Use `--dry-run` to inspect the request payload without creating an approval plan.

## SP mutation coverage

| SP object | Create/Add | Bid/Budget edit | Pause | Archive |
|---|---|---|---|---|
| Portfolio | `portfolios create` | portfolio budget on create | `portfolios set-state --state PAUSED` | `portfolios set-state --state ARCHIVED` |
| Campaign | `campaigns create` | `campaigns edit-budget`, `campaigns edit-bidding-strategy`, `campaigns edit-placement-bids` | `campaigns set-state --state PAUSED` | `campaigns set-state --state ARCHIVED` |
| Ad group | `ad-groups create` | `ad-groups edit-bid` | `ad-groups set-state --state PAUSED` | `ad-groups set-state --state ARCHIVED` |
| Keyword | `keywords add` | `keywords edit-bid` | `keywords set-state --state PAUSED` | `keywords set-state --state ARCHIVED` |
| Product ad | `product-ads add` | not applicable | `product-ads set-state --state PAUSED` | `product-ads set-state --state ARCHIVED` |
| Product/category target | `targets add-asin`, `targets add-category`, `targets add-expression` | `targets edit-bid` | `targets set-state --state PAUSED` | `targets set-state --state ARCHIVED` |
| Negative keyword | `negatives add-ad-group`, `negatives add-campaign` | not applicable | `negatives set-state --state PAUSED` | state support follows Amazon Ads negative keyword API |
| Negative product/category target | `negative-targets add-ad-group`, `negative-targets add-campaign` | not applicable | `negative-targets set-state --state PAUSED` | `negative-targets set-state --state ARCHIVED` |

All commands in this table support `--dry-run`. Without `--dry-run`, they create approval plans instead of directly submitting to Amazon Ads.

## Raw SP escape hatch

`sp-raw request` is intentionally restricted to paths beginning with `/sp/`. Use it only when an official SP endpoint is not yet wrapped by a typed command. Raw SP requests are also approval-gated; run `--dry-run` to inspect the exact method, path, payload, and optional media types, or run without `--dry-run` to create an approval plan for `approvals execute`.
