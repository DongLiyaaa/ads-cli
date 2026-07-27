---
name: "cli-anything-amazon-ads-ops-workbench"
description: "Use when the user wants a CLI for the current Amazon Ads workbench, or needs command-line access to Amazon Ads OAuth health, profiles, portfolios, ad groups, Sponsored Products campaign metadata, keywords, product/category targets, negative targets, report tasks, local report parsing, or snapshot inspection. Trigger whenever the task is about operating this repo's Amazon Ads backend without opening the web UI."
---

# cli-anything-amazon-ads-ops-workbench

Command-line interface for the Amazon Ads Ops Workbench in this repository.

## Purpose

This CLI exposes the same backend contract already present in the local workbench:

- OAuth credential health inspection
- profile discovery and marketplace resolution
- portfolio listing, creation, and state editing
- Sponsored Products ad group listing, creation, default bid editing, and state editing
- Sponsored Products campaign creation
- Sponsored Products campaign metadata listing
- Sponsored Products campaign state editing
- Sponsored Products campaign budget editing
- Sponsored Products campaign bidding strategy and placement bid adjustment interfaces with user-supplied values
- Sponsored Products keyword listing
- Sponsored Products keyword creation
- Sponsored Products keyword bid editing
- Sponsored Products keyword state editing
- Sponsored Products product ad listing, creation, and state editing
- Sponsored Products ASIN/category/expression target listing, creation, bid editing, and state editing
- negative keyword listing, ad group/campaign negative creation, and negative state editing
- negative product targeting listing, ad group/campaign negative creation, and negative state editing
- restricted raw `/sp/` request escape hatch for official SP endpoints not yet wrapped by typed commands
- Sponsored Products keyword, search term, and campaign placement report task creation
- report status inspection, file download, and local report parsing
- snapshot output aligned with the existing proxy semantics

## Install

From the harness directory:

```bash
cd agent-harness
python -m pip install -e .
```

## Environment

The CLI reads the same environment variables as the existing web proxy:

```bash
AMAZON_ADS_CLIENT_ID=
AMAZON_ADS_CLIENT_SECRET=
AMAZON_ADS_REFRESH_TOKEN=
AMAZON_ADS_PROFILE_ID=
AMAZON_ADS_REGION=NA
AMAZON_ADS_MARKETPLACE=US
```

## Command Surface

### `auth`

- `auth health`
  - Check whether the required Amazon Ads credentials are present.

### `profiles`

- `profiles list`
  - Fetch raw profile rows from Amazon Ads.
- `profiles resolve --marketplace US`
  - Resolve the preferred profile for a marketplace.

### `campaigns`

- `campaigns list --marketplace US`
  - Fetch and normalize Sponsored Products campaign metadata.
- `campaigns create --name "T11 Manual" --targeting-type MANUAL --budget 10 --start-date 2026-07-22 --strategy MANUAL --dry-run`
  - Build or submit one Sponsored Products campaign creation payload.
- `campaigns set-state --campaign-id 123 --state PAUSED --dry-run`
  - Update one Sponsored Products campaign state.
- `campaigns edit-budget --campaign-id 123 --budget 5.0 --budget-type DAILY --dry-run`
  - Update one Sponsored Products campaign daily budget.
- `campaigns edit-bidding-strategy --campaign-id 123 --strategy AUTO_FOR_SALES --dry-run`
  - Build or submit one campaign dynamic bidding strategy update payload.
- `campaigns edit-placement-bids --campaign-id 123 --top-of-search 100 --product-pages 25 --rest-of-search 0 --dry-run`
  - Build or submit one Sponsored Products campaign placement bid adjustment payload.
  - Percentages are explicit user inputs only. Do not recommend, infer, or auto-calculate placement values inside this CLI.
  - Supported placement percentage flags are `--top-of-search`, `--product-pages`, and `--rest-of-search`, each in the 0-900 range.
  - Use `--dry-run` first to inspect the exact request payload without submitting it.

### `portfolios`

- `portfolios list --marketplace US`
  - Fetch and normalize portfolio rows for the selected marketplace.
- `portfolios create --name "T11" --budget 100 --currency-code USD --dry-run`
  - Build or submit one portfolio creation payload.
- `portfolios set-state --portfolio-id 123 --state ARCHIVED --dry-run`
  - Build or submit one portfolio state update payload.

### `ad-groups`

- `ad-groups list --campaign-id 123`
  - Fetch and normalize Sponsored Products ad groups.
- `ad-groups create --campaign-id 123 --name "Exact Core" --default-bid 0.72 --dry-run`
  - Build or submit one Sponsored Products ad group creation payload.
- `ad-groups set-state --campaign-id 123 --ad-group-id 456 --state PAUSED --dry-run`
  - Build or submit one Sponsored Products ad group state update payload.
- `ad-groups edit-bid --campaign-id 123 --ad-group-id 456 --default-bid 0.81 --dry-run`
  - Build or submit one Sponsored Products ad group default bid update payload.

### `keywords`

- `keywords list --campaign-id 123 --ad-group-id 456`
  - Fetch and normalize Sponsored Products keywords.
- `keywords add --campaign-id 123 --ad-group-id 456 --keyword-text "ai recorder" --match-type EXACT --bid 0.91 --dry-run`
  - Build or submit one Sponsored Products keyword creation payload.
- `keywords edit-bid --campaign-id 123 --ad-group-id 456 --keyword-id 789 --bid 0.92 --dry-run`
  - Build or submit one keyword bid update payload. The CLI does not include `state` unless explicitly supplied.
- `keywords set-state --campaign-id 123 --ad-group-id 456 --keyword-id 789 --state PAUSED --dry-run`
  - Update one keyword state without changing its bid.

### `product-ads`

- `product-ads list --campaign-id 123`
  - Fetch and normalize Sponsored Products advertised product rows.
- `product-ads add --campaign-id 123 --ad-group-id 456 --sku SKU-1 --dry-run`
  - Build or submit one Sponsored Products advertised product payload. Use exactly one of `--sku` or `--asin`.
- `product-ads set-state --product-ad-id 789 --state PAUSED --dry-run`
  - Build or submit one Sponsored Products advertised product state update payload.

### `targets`

- `targets list --campaign-id 123`
  - Fetch and normalize Sponsored Products targeting clauses.
- `targets add-asin --campaign-id 123 --ad-group-id 456 --asin B000000001 --bid 0.88 --dry-run`
  - Build or submit one ASIN product targeting payload.
- `targets add-category --campaign-id 123 --ad-group-id 456 --category-id 123456 --bid 0.67 --dry-run`
  - Build or submit one category product targeting payload.
- `targets add-expression --campaign-id 123 --ad-group-id 456 --category-id 123456 --predicate BRAND_SAME_AS=Brand --expression-type AUTO --dry-run`
  - Build or submit one generic product targeting expression payload. Repeat `--predicate TYPE=VALUE` for user-supplied refinements.
- `targets edit-bid --target-id 789 --bid 0.79 --dry-run`
  - Build or submit one product targeting bid update payload.
- `targets set-state --target-id 789 --state ARCHIVED --dry-run`
  - Build or submit one targeting clause state update payload.

### `negatives`

- `negatives list --campaign-id 123 --scope both`
  - Fetch and normalize negative keywords at ad group and/or campaign scope.
- `negatives add-ad-group --campaign-id 123 --ad-group-id 456 --keyword-text "carplay wireless adapter" --match-type NEGATIVE_EXACT --dry-run`
  - Build or submit one ad group negative keyword payload.
- `negatives add-campaign --campaign-id 123 --keyword-text "usb c camera" --match-type NEGATIVE_EXACT --dry-run`
  - Build or submit one campaign negative keyword payload.
- `negatives set-state --negative-keyword-id 789 --scope adGroup --state PAUSED --dry-run`
  - Build or submit one negative keyword state update payload at ad group or campaign scope.

### `negative-targets`

- `negative-targets list --campaign-id 123 --scope both`
  - Fetch and normalize negative product/category targets at ad group and/or campaign scope.
- `negative-targets add-ad-group --campaign-id 123 --ad-group-id 456 --asin B000000001 --expression-type AUTO --dry-run`
  - Build or submit one ad group negative product target payload.
- `negative-targets add-campaign --campaign-id 123 --category-id 123456 --dry-run`
  - Build or submit one campaign negative category target payload.
- `negative-targets set-state --negative-target-id 789 --scope campaign --state PAUSED --dry-run`
  - Build or submit one negative target state update payload.

### `sp-raw`

- `sp-raw request --method POST --path /sp/targets/list --payload-json '{"maxResults":10}' --dry-run`
  - Inspect or submit one raw Sponsored Products request for official SP endpoints not yet wrapped by typed commands.
  - The path must start with `/sp/`.
  - Live raw requests require `--confirm-submit` because raw requests bypass typed validation.

### `reports`

- `reports create-sp-keywords --start-date 2026-07-01 --end-date 2026-07-07`
  - Create a Sponsored Products keyword report task.
- `reports create-sp-campaign-placement --start-date 2026-07-01 --end-date 2026-07-07 --time-unit DAILY`
  - Create a Sponsored Products campaign placement report task.
- `reports create-search-terms --start-date 2026-07-01 --end-date 2026-07-07`
  - Create a Sponsored Products search term report task.
- `reports status --report-id <REPORT_ID>`
  - Inspect one report task status.
- `reports download --report-id <REPORT_ID>`
  - Download one completed report to a local JSON file.
- `reports parse-search-terms --input-file <PATH>`
  - Parse a downloaded SP search term report into normalized JSON rows.
- `reports parse-sp-keywords --input-file <PATH>`
  - Parse a downloaded SP keyword report into normalized JSON rows.
- `reports parse-sp-campaign-placement --input-file <PATH>`
  - Parse a downloaded SP campaign placement report into normalized JSON rows.

### root commands

- `snapshot --marketplace US`
  - Return the normalized snapshot structure used by the workbench.

## Examples

```bash
# machine-readable auth check
cli-anything-amazon-ads-ops-workbench --json auth health

# list profiles
cli-anything-amazon-ads-ops-workbench --json profiles list

# resolve one marketplace
cli-anything-amazon-ads-ops-workbench --json profiles resolve --marketplace US

# inspect SP campaign metadata
cli-anything-amazon-ads-ops-workbench --json campaigns list --marketplace US

# create one SP campaign payload without submitting
cli-anything-amazon-ads-ops-workbench --json campaigns create --name "T11 Manual" --targeting-type MANUAL --budget 10 --start-date 2026-07-22 --strategy MANUAL --dry-run

# pause one campaign payload without submitting
cli-anything-amazon-ads-ops-workbench --json campaigns set-state --campaign-id 123 --state PAUSED --dry-run

# update one campaign daily budget payload without submitting
cli-anything-amazon-ads-ops-workbench --json campaigns edit-budget --campaign-id 123 --budget 5.0 --dry-run

# update one campaign bidding strategy payload without submitting
cli-anything-amazon-ads-ops-workbench --json campaigns edit-bidding-strategy --campaign-id 123 --strategy AUTO_FOR_SALES --dry-run

# inspect one campaign placement bid adjustment payload without submitting
cli-anything-amazon-ads-ops-workbench --json campaigns edit-placement-bids --campaign-id 123 --top-of-search 100 --product-pages 25 --rest-of-search 0 --dry-run

# inspect portfolios
cli-anything-amazon-ads-ops-workbench --json portfolios list --marketplace US

# create one portfolio payload without submitting
cli-anything-amazon-ads-ops-workbench --json portfolios create --name "T11" --budget 100 --currency-code USD --dry-run

# archive one portfolio payload without submitting
cli-anything-amazon-ads-ops-workbench --json portfolios set-state --portfolio-id 123 --state ARCHIVED --dry-run

# inspect ad groups
cli-anything-amazon-ads-ops-workbench --json ad-groups list --campaign-id 123

# create one ad group payload without submitting
cli-anything-amazon-ads-ops-workbench --json ad-groups create --campaign-id 123 --name "Exact Core" --default-bid 0.72 --dry-run

# pause one ad group payload without submitting
cli-anything-amazon-ads-ops-workbench --json ad-groups set-state --campaign-id 123 --ad-group-id 456 --state PAUSED --dry-run

# update one ad group default bid payload without submitting
cli-anything-amazon-ads-ops-workbench --json ad-groups edit-bid --campaign-id 123 --ad-group-id 456 --default-bid 0.81 --dry-run

# inspect keyword rows
cli-anything-amazon-ads-ops-workbench --json keywords list --campaign-id 123

# create one keyword payload without submitting
cli-anything-amazon-ads-ops-workbench --json keywords add --campaign-id 123 --ad-group-id 456 --keyword-text "ai recorder" --match-type EXACT --bid 0.91 --dry-run

# update one keyword bid payload without submitting
cli-anything-amazon-ads-ops-workbench --json keywords edit-bid --campaign-id 123 --ad-group-id 456 --keyword-id 789 --bid 0.92 --dry-run

# pause one keyword payload without submitting
cli-anything-amazon-ads-ops-workbench --json keywords set-state --campaign-id 123 --ad-group-id 456 --keyword-id 789 --state PAUSED --dry-run

# create one advertised product payload without submitting
cli-anything-amazon-ads-ops-workbench --json product-ads add --campaign-id 123 --ad-group-id 456 --sku SKU-1 --dry-run

# pause one advertised product payload without submitting
cli-anything-amazon-ads-ops-workbench --json product-ads set-state --product-ad-id 789 --state PAUSED --dry-run

# create one ASIN target payload without submitting
cli-anything-amazon-ads-ops-workbench --json targets add-asin --campaign-id 123 --ad-group-id 456 --asin B000000001 --bid 0.88 --dry-run

# create one category target payload without submitting
cli-anything-amazon-ads-ops-workbench --json targets add-category --campaign-id 123 --ad-group-id 456 --category-id 123456 --bid 0.67 --dry-run

# create one generic product targeting expression payload without submitting
cli-anything-amazon-ads-ops-workbench --json targets add-expression --campaign-id 123 --ad-group-id 456 --category-id 123456 --predicate BRAND_SAME_AS=Brand --expression-type AUTO --dry-run

# update one product target bid payload without submitting
cli-anything-amazon-ads-ops-workbench --json targets edit-bid --target-id 789 --bid 0.79 --dry-run

# archive one ASIN target payload without submitting
cli-anything-amazon-ads-ops-workbench --json targets set-state --target-id 789 --state ARCHIVED --dry-run

# inspect negatives
cli-anything-amazon-ads-ops-workbench --json negatives list --campaign-id 123 --scope both

# create one ad group negative payload without submitting
cli-anything-amazon-ads-ops-workbench --json negatives add-ad-group --campaign-id 123 --ad-group-id 456 --keyword-text "carplay wireless adapter" --match-type NEGATIVE_EXACT --dry-run

# create one campaign negative payload without submitting
cli-anything-amazon-ads-ops-workbench --json negatives add-campaign --campaign-id 123 --keyword-text "usb c camera" --match-type NEGATIVE_EXACT --dry-run

# pause one ad group negative keyword payload without submitting
cli-anything-amazon-ads-ops-workbench --json negatives set-state --negative-keyword-id 789 --scope adGroup --state PAUSED --dry-run

# inspect negative product/category targets
cli-anything-amazon-ads-ops-workbench --json negative-targets list --campaign-id 123 --scope both

# create one ad group negative ASIN target payload without submitting
cli-anything-amazon-ads-ops-workbench --json negative-targets add-ad-group --campaign-id 123 --ad-group-id 456 --asin B000000001 --expression-type AUTO --dry-run

# create one campaign negative category target payload without submitting
cli-anything-amazon-ads-ops-workbench --json negative-targets add-campaign --campaign-id 123 --category-id 123456 --dry-run

# pause one negative target payload without submitting
cli-anything-amazon-ads-ops-workbench --json negative-targets set-state --negative-target-id 789 --scope campaign --state PAUSED --dry-run

# inspect one raw SP request payload without submitting
cli-anything-amazon-ads-ops-workbench --json sp-raw request --method POST --path /sp/targets/list --payload-json '{"maxResults":10}' --dry-run

# create an SP keyword report
cli-anything-amazon-ads-ops-workbench --json reports create-sp-keywords --start-date 2026-07-01 --end-date 2026-07-07

# create an SP campaign placement report
cli-anything-amazon-ads-ops-workbench --json reports create-sp-campaign-placement --start-date 2026-07-01 --end-date 2026-07-07 --time-unit DAILY

# create an SP search term report
cli-anything-amazon-ads-ops-workbench --json reports create-search-terms --start-date 2026-07-01 --end-date 2026-07-07

# inspect report status
cli-anything-amazon-ads-ops-workbench --json reports status --report-id <REPORT_ID>

# download one completed report
cli-anything-amazon-ads-ops-workbench --json reports download --report-id <REPORT_ID>

# parse one downloaded search term report
cli-anything-amazon-ads-ops-workbench --json reports parse-search-terms --input-file ~/Downloads/spSearchTerm.json

# parse one downloaded SP keyword report
cli-anything-amazon-ads-ops-workbench --json reports parse-sp-keywords --input-file ~/Downloads/spKeywords.json

# parse one downloaded SP campaign placement report
cli-anything-amazon-ads-ops-workbench --json reports parse-sp-campaign-placement --input-file ~/Downloads/spCampaignPlacement.json

# inspect the full normalized snapshot
cli-anything-amazon-ads-ops-workbench --json snapshot --marketplace US
```

## REPL

Running the command without a subcommand enters the interactive REPL:

```bash
cli-anything-amazon-ads-ops-workbench
```

Type `help` to see the short command list and `exit` to leave.

## For Agents

- Prefer `--json` for all programmatic use.
- Treat missing credentials as a valid fallback response, not a transport failure.
- `snapshot` is the best high-level command when you want one stable response envelope.
- `campaigns list` is the narrower command when you only need campaign rows.
- `campaigns edit-budget` currently validates against the Amazon Ads v3 daily budget shape.
- `campaigns edit-placement-bids` is an interface only. Agents must not infer placement percentages; pass only values supplied by the user and prefer `--dry-run` before live submission.
- All write commands support `--dry-run`; prefer dry-run before live submission.
- `targets add-expression` and `negative-targets add-*` accept user-supplied predicates as `TYPE=VALUE`; positive targets and ad group negative targets also accept explicit `--expression-type MANUAL|AUTO`.
- Use typed commands first. Use `sp-raw request` only for official SP endpoints not yet wrapped here; it is restricted to `/sp/` paths and requires `--confirm-submit` for live submission.
- `portfolios list`, `ad-groups list`, `keywords list`, `product-ads list`, `targets list`, `negatives list`, `negative-targets list`, and `reports ...` all return a stable `meta + data` envelope.
- `negatives set-state` accepts the live Amazon Ads negative keyword states, which are narrower than campaign states.
- `reports download` defaults to `~/Downloads` unless `--output-dir` is supplied.
- `reports parse-search-terms`, `reports parse-sp-keywords`, and `reports parse-sp-campaign-placement` are local-only commands and do not require live credentials.
