---
name: "cli-anything-amazon-ads-ops-workbench"
description: "Use when the user wants a CLI for the current Amazon Ads workbench, or needs command-line access to Amazon Ads OAuth health, profiles, portfolios, ad groups, Sponsored Products campaign metadata, keywords, negatives, report tasks, local report parsing, or snapshot inspection. Trigger whenever the task is about operating this repo's Amazon Ads backend without opening the web UI."
---

# cli-anything-amazon-ads-ops-workbench

Command-line interface for the Amazon Ads Ops Workbench in this repository.

## Purpose

This CLI exposes the same backend contract already present in the local workbench:

- OAuth credential health inspection
- profile discovery and marketplace resolution
- portfolio listing
- Sponsored Products ad group listing
- Sponsored Products campaign metadata listing
- Sponsored Products campaign state editing
- Sponsored Products campaign budget editing
- Sponsored Products keyword listing
- Sponsored Products keyword bid editing
- Sponsored Products keyword state editing
- negative keyword listing, ad group/campaign negative creation, and negative state editing
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
- `campaigns set-state --campaign-id 123 --state PAUSED`
  - Update one Sponsored Products campaign state.
- `campaigns edit-budget --campaign-id 123 --budget 5.0 --budget-type DAILY`
  - Update one Sponsored Products campaign daily budget.

### `portfolios`

- `portfolios list --marketplace US`
  - Fetch and normalize portfolio rows for the selected marketplace.

### `ad-groups`

- `ad-groups list --campaign-id 123`
  - Fetch and normalize Sponsored Products ad groups.

### `keywords`

- `keywords list --campaign-id 123 --ad-group-id 456`
  - Fetch and normalize Sponsored Products keywords.
- `keywords edit-bid --campaign-id 123 --ad-group-id 456 --keyword-id 789 --bid 0.92`
  - Update one keyword bid.
- `keywords set-state --campaign-id 123 --ad-group-id 456 --keyword-id 789 --state PAUSED`
  - Update one keyword state without changing its bid.

### `negatives`

- `negatives list --campaign-id 123 --scope both`
  - Fetch and normalize negative keywords at ad group and/or campaign scope.
- `negatives add-ad-group --campaign-id 123 --ad-group-id 456 --keyword-text "carplay wireless adapter" --match-type NEGATIVE_EXACT`
  - Create one ad group negative keyword payload and submit it to Amazon Ads.
- `negatives add-campaign --campaign-id 123 --keyword-text "usb c camera" --match-type NEGATIVE_EXACT`
  - Create one campaign negative keyword payload and submit it to Amazon Ads.
- `negatives set-state --negative-keyword-id 789 --scope adGroup --state PAUSED`
  - Update one negative keyword state at ad group or campaign scope.

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

# pause one campaign
cli-anything-amazon-ads-ops-workbench --json campaigns set-state --campaign-id 123 --state PAUSED

# update one campaign daily budget
cli-anything-amazon-ads-ops-workbench --json campaigns edit-budget --campaign-id 123 --budget 5.0

# inspect portfolios
cli-anything-amazon-ads-ops-workbench --json portfolios list --marketplace US

# inspect ad groups
cli-anything-amazon-ads-ops-workbench --json ad-groups list --campaign-id 123

# inspect keyword rows
cli-anything-amazon-ads-ops-workbench --json keywords list --campaign-id 123

# update one keyword bid
cli-anything-amazon-ads-ops-workbench --json keywords edit-bid --campaign-id 123 --ad-group-id 456 --keyword-id 789 --bid 0.92

# pause one keyword
cli-anything-amazon-ads-ops-workbench --json keywords set-state --campaign-id 123 --ad-group-id 456 --keyword-id 789 --state PAUSED

# inspect negatives
cli-anything-amazon-ads-ops-workbench --json negatives list --campaign-id 123 --scope both

# create one ad group negative
cli-anything-amazon-ads-ops-workbench --json negatives add-ad-group --campaign-id 123 --ad-group-id 456 --keyword-text "carplay wireless adapter" --match-type NEGATIVE_EXACT

# create one campaign negative
cli-anything-amazon-ads-ops-workbench --json negatives add-campaign --campaign-id 123 --keyword-text "usb c camera" --match-type NEGATIVE_EXACT

# pause one ad group negative keyword
cli-anything-amazon-ads-ops-workbench --json negatives set-state --negative-keyword-id 789 --scope adGroup --state PAUSED

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
- `portfolios list`, `ad-groups list`, `keywords list`, `negatives list`, and `reports ...` all return a stable `meta + data` envelope.
- `negatives set-state` accepts the live Amazon Ads negative keyword states, which are narrower than campaign states.
- `reports download` defaults to `~/Downloads` unless `--output-dir` is supplied.
- `reports parse-search-terms`, `reports parse-sp-keywords`, and `reports parse-sp-campaign-placement` are local-only commands and do not require live credentials.
