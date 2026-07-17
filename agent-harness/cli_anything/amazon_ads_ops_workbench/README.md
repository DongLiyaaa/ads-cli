# Amazon Ads Ops Workbench CLI

This CLI gives agents a direct command-line interface to the Amazon Ads workbench backend capabilities already present in this repository.

## Covered now

- OAuth health inspection
- Profile listing and marketplace resolution
- Portfolio listing
- Sponsored Products ad group listing
- Sponsored Products campaign metadata listing
- Sponsored Products campaign state editing
- Sponsored Products campaign budget editing
- Sponsored Products keyword listing
- Sponsored Products keyword bid editing
- Sponsored Products keyword state editing
- Negative keyword listing, ad group/campaign negative creation, and negative state editing
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
cli-anything-amazon-ads-ops-workbench --json campaigns list --marketplace US
cli-anything-amazon-ads-ops-workbench --json campaigns set-state --campaign-id 123 --state PAUSED
cli-anything-amazon-ads-ops-workbench --json campaigns edit-budget --campaign-id 123 --budget 5.0
cli-anything-amazon-ads-ops-workbench --json portfolios list --marketplace US
cli-anything-amazon-ads-ops-workbench --json ad-groups list --campaign-id 123
cli-anything-amazon-ads-ops-workbench --json keywords list --campaign-id 123
cli-anything-amazon-ads-ops-workbench --json keywords edit-bid --campaign-id 123 --ad-group-id 456 --keyword-id 789 --bid 0.92
cli-anything-amazon-ads-ops-workbench --json keywords set-state --campaign-id 123 --ad-group-id 456 --keyword-id 789 --state PAUSED
cli-anything-amazon-ads-ops-workbench --json negatives list --campaign-id 123 --scope both
cli-anything-amazon-ads-ops-workbench --json negatives add-ad-group --campaign-id 123 --ad-group-id 456 --keyword-text "carplay wireless adapter" --match-type NEGATIVE_EXACT
cli-anything-amazon-ads-ops-workbench --json negatives add-campaign --campaign-id 123 --keyword-text "usb c camera" --match-type NEGATIVE_EXACT
cli-anything-amazon-ads-ops-workbench --json negatives set-state --negative-keyword-id 789 --scope adGroup --state PAUSED
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
