# ads-cli

Private GitHub mirror for the Amazon Ads CLI extracted from a larger local workbench.

This repository intentionally contains only the CLI harness, package code, tests, and lightweight design notes needed to operate the command-line surface. It does not include local credential files, generated reports, or unrelated application code.

## Layout

- `agent-harness/`: installable Python package and CLI source
- `skills/`: Codex skill entry for routing this CLI in agent flows
- `docs/`: design notes for interface gaps and next-step expansion

## Install

```bash
cd agent-harness
python -m pip install -e .
```

## Environment

Copy `.env.example` into your local environment management flow and populate real values outside git:

```bash
export AMAZON_ADS_CLIENT_ID=...
export AMAZON_ADS_CLIENT_SECRET=...
export AMAZON_ADS_REFRESH_TOKEN=...
export AMAZON_ADS_PROFILE_ID=
export AMAZON_ADS_REGION=NA
export AMAZON_ADS_MARKETPLACE=US
```

## Core commands

```bash
cli-anything-amazon-ads-ops-workbench --json auth health
cli-anything-amazon-ads-ops-workbench --json campaigns list --marketplace US
cli-anything-amazon-ads-ops-workbench --json keywords list --campaign-id 123
cli-anything-amazon-ads-ops-workbench --json negatives list --campaign-id 123 --scope both
cli-anything-amazon-ads-ops-workbench --json reports create-sp-keywords --start-date 2026-07-01 --end-date 2026-07-07
cli-anything-amazon-ads-ops-workbench --json reports create-sp-campaign-placement --start-date 2026-07-01 --end-date 2026-07-07 --time-unit DAILY
cli-anything-amazon-ads-ops-workbench --json reports create-search-terms --start-date 2026-07-01 --end-date 2026-07-07
cli-anything-amazon-ads-ops-workbench --json reports parse-sp-keywords --input-file ~/Downloads/spKeywords.json
cli-anything-amazon-ads-ops-workbench --json reports parse-sp-campaign-placement --input-file ~/Downloads/spCampaignPlacement.json
cli-anything-amazon-ads-ops-workbench --json snapshot --marketplace US
```

## Privacy

- Do not commit `.env`, refresh tokens, or generated report files.
- Keep real campaign, profile, and report identifiers out of public documentation.
- Use `.env.example` only for variable names, never for live values.
