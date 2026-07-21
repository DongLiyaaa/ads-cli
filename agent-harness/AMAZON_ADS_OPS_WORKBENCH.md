# Amazon Ads Ops Workbench CLI SOP

This harness exposes the current Amazon Ads workbench as an agent-usable CLI.

## Scope

- Amazon Ads OAuth health inspection
- Profile discovery and marketplace resolution
- Portfolio listing, creation, and state editing
- Sponsored Products campaign metadata listing, creation, state editing, budget editing, and placement bid adjustment interfaces
- Sponsored Products ad group listing, creation, and state editing
- Sponsored Products keyword listing, creation, bid editing, and state editing
- Sponsored Products product ad listing, creation, and state editing
- Sponsored Products ASIN target listing, creation, and state editing
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

## Placement bid adjustment

`campaigns edit-placement-bids` only exposes the Amazon Ads placement bid adjustment request surface. The caller must provide exact percentages; the CLI does not calculate or recommend top of search, product pages, or rest of search values.

## SP mutation coverage

| SP object | Create/Add command | State command |
|---|---|---|
| Portfolio | `portfolios create` | `portfolios set-state` |
| Campaign | `campaigns create` | `campaigns set-state` |
| Ad group | `ad-groups create` | `ad-groups set-state` |
| Keyword | `keywords add` | `keywords set-state` |
| Product ad | `product-ads add` | `product-ads set-state` |
| ASIN target | `targets add-asin` | `targets set-state` |

All newly added write commands support `--dry-run` so agents can inspect the exact request payload before submitting to Amazon Ads.
