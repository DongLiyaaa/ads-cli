# Amazon Ads Ops Workbench CLI SOP

This harness exposes the current Amazon Ads workbench as an agent-usable CLI.

## Scope

- Amazon Ads OAuth health inspection
- Profile discovery and marketplace resolution
- Portfolio listing, creation, and state editing
- Sponsored Products campaign metadata listing, creation, state editing, budget editing, bidding strategy editing, and placement bid adjustment interfaces
- Sponsored Products ad group listing, creation, default bid editing, and state editing
- Sponsored Products keyword listing, creation, bid editing, and state editing
- Sponsored Products product ad listing, creation, and state editing
- Sponsored Products ASIN/category/expression target listing, creation, bid editing, and state editing
- Negative keyword listing and mutation
- Negative product targeting listing and mutation
- Restricted raw `/sp/` request escape hatch for official SP endpoints not yet wrapped by typed commands
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

| SP object | Create/Add command | Bid/Budget command | State command |
|---|---|---|---|
| Portfolio | `portfolios create` | budget on create | `portfolios set-state` |
| Campaign | `campaigns create` | `campaigns edit-budget`, `campaigns edit-bidding-strategy`, `campaigns edit-placement-bids` | `campaigns set-state` |
| Ad group | `ad-groups create` | `ad-groups edit-bid` | `ad-groups set-state` |
| Keyword | `keywords add` | `keywords edit-bid` | `keywords set-state` |
| Product ad | `product-ads add` | not applicable | `product-ads set-state` |
| Product/category target | `targets add-asin`, `targets add-category`, `targets add-expression` | `targets edit-bid` | `targets set-state` |
| Negative keyword | `negatives add-ad-group`, `negatives add-campaign` | not applicable | `negatives set-state` |
| Negative product/category target | `negative-targets add-ad-group`, `negative-targets add-campaign` | not applicable | `negative-targets set-state` |

All write commands support `--dry-run` so agents can inspect the exact request payload before submitting to Amazon Ads.

`sp-raw request` is restricted to `/sp/` paths and requires `--confirm-submit` for live calls. It exists as an escape hatch for official SP endpoints not yet covered by typed commands, not as the default operation path.
