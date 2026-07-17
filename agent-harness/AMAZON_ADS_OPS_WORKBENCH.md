# Amazon Ads Ops Workbench CLI SOP

This harness exposes the current Amazon Ads workbench as an agent-usable CLI.

## Scope

- Amazon Ads OAuth health inspection
- Profile discovery and marketplace resolution
- Sponsored Products campaign metadata listing
- Sponsored Products campaign state and budget editing
- Portfolio listing
- Sponsored Products ad group listing
- Sponsored Products keyword listing and mutation
- Negative keyword listing and mutation
- Sponsored Products report task creation, download, and local parsing
- Snapshot output aligned with the current workbench proxy semantics

## Environment

The CLI uses the same environment variables as the existing Vite proxy:

- `AMAZON_ADS_CLIENT_ID`
- `AMAZON_ADS_CLIENT_SECRET`
- `AMAZON_ADS_REFRESH_TOKEN`
- `AMAZON_ADS_PROFILE_ID`
- `AMAZON_ADS_REGION`
- `AMAZON_ADS_MARKETPLACE`

## Output contract

- Human-readable output by default
- Machine-readable output with `--json`
- Snapshot JSON stays close to the current `server/amazonAdsProxy.ts` structure:
  - `meta.mode`
  - `meta.status`
  - `meta.profileId`
  - `meta.missingCredentials`
  - `data.campaignSummary`
  - `data.campaigns`
