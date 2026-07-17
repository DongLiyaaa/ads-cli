# Test Plan

## Planned test files

- `test_core.py`: 35 unit tests planned
- `test_full_e2e.py`: 17 E2E / subprocess tests planned

## Unit test plan

### `core.env`

- verify environment parsing from process variables
- verify missing credential detection
- verify region normalization fallback

### `core.snapshot`

- verify marketplace profile selection
- verify campaign record extraction from `campaigns`, `results`, and `items`
- verify missing-credential snapshot metadata
- verify live summary aggregation for campaign counts

### `core.keywords`

- verify keyword list filter payload construction
- verify ad group list filter payload construction
- verify negative keyword list filter payload construction
- verify keyword row normalization
- verify ad group row normalization
- verify portfolio row normalization
- verify negative keyword row normalization
- verify ad group negative creation payload construction
- verify campaign negative creation payload construction
- verify keyword bid edit payload construction
- verify keyword state payload construction
- verify negative keyword state payload construction

### `core.campaigns`

- verify campaign state payload construction
- verify campaign budget payload construction

### `core.reports`

- verify Sponsored Products keyword report request body construction
- verify Sponsored Products search term report request body construction
- verify report download target path construction
- verify local report row loading
- verify search term report row normalization
- verify SP keyword report row normalization
- verify parsed report summary generation

### `core.client`

- verify request headers contain OAuth token and Amazon Ads client id
- verify campaign list pagination stops when `nextToken` is empty
- verify campaign update payload wraps into `campaigns`
- verify keyword update payload wraps into `keywords`
- verify ad group negative payload wraps into `negativeKeywords`
- verify campaign negative payload wraps into `campaignNegativeKeywords`

## E2E test plan

- `--help` returns usage for the installed CLI
- `--json auth health` returns machine-readable status
- `--json snapshot` returns a structured response even when credentials are incomplete
- `--json profiles resolve --marketplace US` resolves or reports fallback cleanly
- `--json portfolios list` returns a stable fallback envelope without credentials
- `--json ad-groups list --campaign-id 123` returns a stable fallback envelope without credentials
- `--json campaigns set-state ...` returns a stable fallback envelope without credentials
- `--json campaigns edit-budget ...` returns a stable fallback envelope without credentials
- `--json keywords list --campaign-id 123` returns a stable fallback envelope without credentials
- `--json keywords edit-bid ...` returns a stable fallback envelope without credentials
- `--json keywords set-state ...` returns a stable fallback envelope without credentials
- `--json negatives add-ad-group ...` returns a stable fallback envelope without credentials
- `--json negatives add-campaign ...` returns a stable fallback envelope without credentials
- `--json negatives set-state ...` returns a stable fallback envelope without credentials
- `--json reports create-sp-keywords ...` returns a stable fallback envelope without credentials
- `--json reports create-search-terms ...` returns a stable fallback envelope without credentials
- `--json reports download --report-id ...` returns a stable fallback envelope without credentials
- `--json reports parse-search-terms --input-file ...` parses a local file without credentials
- `--json reports parse-sp-keywords --input-file ...` parses a local file without credentials

## Workflow scenarios

### Scenario 1: Cold-start credential audit

- Simulates: an agent validating whether live Amazon Ads credentials are configured
- Operations chained: run `auth health`, inspect missing credentials, run `snapshot`
- Verified: JSON contains `missingCredentials`, mode/status, and a stable top-level shape

### Scenario 2: Marketplace profile resolution

- Simulates: an agent preparing to query one marketplace without hardcoding a profile id
- Operations chained: load env, fetch or simulate profiles, resolve marketplace
- Verified: preferred direct marketplace match wins, fallback to first profile otherwise

## Test Results

Validated on 2026-07-08 with the local virtual environment at `agent-harness/.venv`.

### `python3 -m unittest discover -s cli_anything/amazon_ads_ops_workbench/tests -p 'test_*.py'`

```text
........................
----------------------------------------------------------------------
Ran 24 tests in 0.39s

OK
```

## Summary Statistics

- Total tests: 24
- Pass rate: 100%
- Runtime: 0.39s

## Validation Notes

- `cli-anything-amazon-ads-ops-workbench --help` returned the expected command tree.
- `cli-anything-amazon-ads-ops-workbench --json auth health` returned the expected credential-fallback structure.
- `cli-anything-amazon-ads-ops-workbench --json snapshot` returned the normalized mock snapshot when credentials were absent.
- `cli-anything-amazon-ads-ops-workbench --json keywords list --campaign-id 123` returned the expected mock envelope when credentials were absent.
- `cli-anything-amazon-ads-ops-workbench --json negatives add-ad-group ...` returned the expected mock envelope when credentials were absent.
- `cli-anything-amazon-ads-ops-workbench --json reports create-sp-keywords ...` returned the expected mock envelope when credentials were absent.
- `cli-anything-amazon-ads-ops-workbench --json reports create-search-terms ...` returned the expected mock envelope when credentials were absent.
- `cli-anything-amazon-ads-ops-workbench --json reports download --report-id ...` returned the expected mock envelope when credentials were absent.
- `cli-anything-amazon-ads-ops-workbench --json keywords edit-bid ...` returned the expected mock envelope when credentials were absent.
- Live profile and campaign calls are implemented but were not exercised in this test run because no credentials were injected into the local validation shell.

## Test Results

Validated on 2026-07-17 with the local virtual environment at `agent-harness/.venv`.

### `CLI_ANYTHING_FORCE_INSTALLED=1 python -m unittest discover -s cli_anything/amazon_ads_ops_workbench/tests -p 'test_*.py'`

```text
...........................................
----------------------------------------------------------------------
Ran 43 tests in 0.587s

OK
```

## Summary Statistics

- Total tests: 43
- `test_core.py`: 30
- `test_full_e2e.py`: 13
- Pass rate: 100%
- Runtime: 0.587s

## Validation Notes

- Installed command path resolved to `<venv>/bin/cli-anything-amazon-ads-ops-workbench`.
- New mock-path coverage now includes `portfolios list`, `ad-groups list`, `keywords set-state`, `negatives add-campaign`, and `reports parse-search-terms`.
- Live validation on 2026-07-17 confirmed these command paths:
  - `portfolios list --marketplace US`
  - `ad-groups list --marketplace US --campaign-id <CAMPAIGN_ID>`
  - `keywords set-state ... --keyword-id <INVALID_KEYWORD_ID>` reaches business validation and returns `ENTITY_NOT_FOUND`
  - `negatives add-campaign ... --campaign-id 0` reaches business validation and returns `ENTITY_NOT_FOUND`
- `reports parse-search-terms --input-file ~/Downloads/spSearchTerm-example.json` parsed 58 rows successfully

## Test Results

Validated on 2026-07-17 after the campaign mutation and negative list expansion work.

### `CLI_ANYTHING_FORCE_INSTALLED=1 python -m unittest discover -s cli_anything/amazon_ads_ops_workbench/tests -p 'test_*.py'`

```text
....................................................
----------------------------------------------------------------------
Ran 52 tests in 0.857s

OK
```

## Summary Statistics

- Total tests: 52
- `test_core.py`: 35
- `test_full_e2e.py`: 17
- Pass rate: 100%
- Runtime: 0.857s

## Validation Notes

- Installed command path remained `<venv>/bin/cli-anything-amazon-ads-ops-workbench`.
- Mock-path coverage now includes `campaigns set-state`, `campaigns edit-budget`, `negatives set-state`, and `reports parse-sp-keywords`.
- Live validation on 2026-07-17 confirmed these list/read paths:
  - `profiles resolve --marketplace US`
  - `campaigns list --marketplace US`
  - `portfolios list --marketplace US`
  - `ad-groups list --marketplace US --campaign-id <CAMPAIGN_ID>`
  - `keywords list --marketplace US --campaign-id <CAMPAIGN_ID>`
  - `negatives list --marketplace US --campaign-id <CAMPAIGN_ID> --scope both`
- Live validation on 2026-07-17 confirmed these mutation shapes via safe invalid-id probes:
  - `campaigns set-state --campaign-id <INVALID_CAMPAIGN_ID> --state PAUSED` reached business validation and returned `ENTITY_NOT_FOUND`
  - `campaigns edit-budget --campaign-id <INVALID_CAMPAIGN_ID> --budget 5.0` reached business validation and returned `ENTITY_NOT_FOUND`
  - `keywords set-state --keyword-id <INVALID_KEYWORD_ID> ...` reached business validation and returned `ENTITY_NOT_FOUND`
  - `keywords edit-bid --keyword-id <INVALID_KEYWORD_ID> ...` reached business validation and returned `ENTITY_NOT_FOUND`
  - `negatives set-state --scope adGroup --negative-keyword-id <INVALID_NEGATIVE_ID>` reached business validation and returned `ENTITY_NOT_FOUND`
  - `negatives set-state --scope campaign --negative-keyword-id <INVALID_NEGATIVE_ID>` reached business validation and returned `ENTITY_NOT_FOUND`
  - `negatives add-ad-group --campaign-id <INVALID_CAMPAIGN_ID> --ad-group-id <INVALID_AD_GROUP_ID> ...` reached business validation and returned `adGroupId cannot be found`
  - `negatives add-campaign --campaign-id <INVALID_CAMPAIGN_ID> ...` reached business validation and returned `ENTITY_NOT_FOUND`
- A live shape bug was found and fixed during this validation round:
  - `keywords list` and `negatives list` originally sent bare arrays for `campaignIdFilter` and `adGroupIdFilter`
  - Amazon Ads expected the v3 `{\"include\": [..]}` shape, and the fixed commands now return live data correctly
- Live report orchestration on 2026-07-17 created an `spKeywords` report task, but the task was still `PENDING` during the validation window; download and real-file parse were therefore not completed in that run.
