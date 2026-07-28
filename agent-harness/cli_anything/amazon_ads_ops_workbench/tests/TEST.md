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

- Installed command path resolved to `/Users/dongli/Documents/广告自动化/agent-harness/.venv/bin/cli-anything-amazon-ads-ops-workbench`.
- New mock-path coverage now includes `portfolios list`, `ad-groups list`, `keywords set-state`, `negatives add-campaign`, and `reports parse-search-terms`.
- Live validation on 2026-07-17 confirmed these command paths:
  - `portfolios list --marketplace US`
  - `ad-groups list --marketplace US --campaign-id 205964387637073`
  - `keywords set-state ... --keyword-id 999999999999999` reaches business validation and returns `ENTITY_NOT_FOUND`
  - `negatives add-campaign ... --campaign-id 0` reaches business validation and returns `ENTITY_NOT_FOUND`
- `reports parse-search-terms --input-file /Users/dongli/Downloads/spSearchTerm-160f042f-c1b8-4192-938b-6970860a4438.json` parsed 58 rows successfully

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

- Installed command path remained `/Users/dongli/Documents/广告自动化/agent-harness/.venv/bin/cli-anything-amazon-ads-ops-workbench`.
- Mock-path coverage now includes `campaigns set-state`, `campaigns edit-budget`, `negatives set-state`, and `reports parse-sp-keywords`.
- Live validation on 2026-07-17 confirmed these list/read paths:
  - `profiles resolve --marketplace US`
  - `campaigns list --marketplace US`
  - `portfolios list --marketplace US`
  - `ad-groups list --marketplace US --campaign-id 205964387637073`
  - `keywords list --marketplace US --campaign-id 205964387637073`
  - `negatives list --marketplace US --campaign-id 205964387637073 --scope both`
- Live validation on 2026-07-17 confirmed these mutation shapes via safe invalid-id probes:
  - `campaigns set-state --campaign-id 999999999999999 --state PAUSED` reached business validation and returned `ENTITY_NOT_FOUND`
  - `campaigns edit-budget --campaign-id 999999999999999 --budget 5.0` reached business validation and returned `ENTITY_NOT_FOUND`
  - `keywords set-state --keyword-id 999999999999999 ...` reached business validation and returned `ENTITY_NOT_FOUND`
  - `keywords edit-bid --keyword-id 999999999999999 ...` reached business validation and returned `ENTITY_NOT_FOUND`
  - `negatives set-state --scope adGroup --negative-keyword-id 999999999999999` reached business validation and returned `ENTITY_NOT_FOUND`
  - `negatives set-state --scope campaign --negative-keyword-id 999999999999999` reached business validation and returned `ENTITY_NOT_FOUND`
  - `negatives add-ad-group --campaign-id 999999999999999 --ad-group-id 999999999999999 ...` reached business validation and returned `adGroupId cannot be found`
  - `negatives add-campaign --campaign-id 999999999999999 ...` reached business validation and returned `ENTITY_NOT_FOUND`
- A live shape bug was found and fixed during this validation round:
  - `keywords list` and `negatives list` originally sent bare arrays for `campaignIdFilter` and `adGroupIdFilter`
  - Amazon Ads expected the v3 `{\"include\": [..]}` shape, and the fixed commands now return live data correctly
- Live report orchestration on 2026-07-17 created `spKeywords` report id `8e054314-bb48-4d0e-ba8c-8cc77e716921`, but the task was still `PENDING` as of `2026-07-17T12:10:12.918Z`; download and real-file parse were therefore not completed in this run.

## Test Results

Validated on 2026-07-22 after adding the Sponsored Products campaign placement bid adjustment interface.

### `PYTHONPATH=/Users/dongli/Documents/ads-cli-publish-20260717/agent-harness python3 -m unittest cli_anything.amazon_ads_ops_workbench.tests.test_core cli_anything.amazon_ads_ops_workbench.tests.test_full_e2e -v`

```text
----------------------------------------------------------------------
Ran 64 tests in 1.573s

OK
```

### `PYTHONPATH=/Users/dongli/Documents/广告自动化/agent-harness python3 -m compileall -q cli_anything/amazon_ads_ops_workbench`

```text
OK
```

## Summary Statistics

- Total tests: 64
- Pass rate: 100%
- New coverage includes `campaigns edit-placement-bids` dry-run, missing-credential fallback, user-value requirement, placement payload shape, optional strategy, and 0-900 range validation.

## Validation Notes

- `pytest` was not installed in the active Python 3.14 environment, so validation used the existing `unittest` suite.
- Dry-run output confirmed the payload includes only user-supplied placement percentages and does not submit to Amazon Ads.

## Test Results

Validated on 2026-07-29 after adding the Sponsored Brands non-creative operation surface.

### `python3 -m py_compile agent-harness/cli_anything/amazon_ads_ops_workbench/amazon_ads_ops_workbench_cli.py agent-harness/cli_anything/amazon_ads_ops_workbench/core/*.py`

```text
OK
```

### `python3 -m unittest discover -s agent-harness/cli_anything/amazon_ads_ops_workbench/tests -v`

```text
----------------------------------------------------------------------
Ran 157 tests in 3.411s

OK
```

## Summary Statistics

- Total tests: 157
- Pass rate: 100%
- Runtime: 3.411s
- Validation runner: Python 3.14 `unittest`; `pytest` was not installed in the active environment.

## Validation Notes

- New SB dry-run and approval coverage includes campaigns, ad groups, keywords, negative keywords, product targets, negative targets, raw requests, and SB report creation/parsing.
- All SP and SB write commands are approval-gated when not run with `--dry-run`.
- `sb-raw` blocks media, creative, image, video, logo, and asset paths or payload keys before network execution.
- No live Amazon Ads mutation was submitted during this validation run.

## Test Results

Validated on 2026-07-29 after adding the machine-readable capability contract for agents.

### `python3 -m py_compile agent-harness/cli_anything/amazon_ads_ops_workbench/amazon_ads_ops_workbench_cli.py agent-harness/cli_anything/amazon_ads_ops_workbench/core/*.py agent-harness/cli_anything/amazon_ads_ops_workbench/tests/*.py`

```text
OK
```

### `python3 -m unittest discover -s agent-harness/cli_anything/amazon_ads_ops_workbench/tests -v`

```text
----------------------------------------------------------------------
Ran 159 tests in 3.499s

OK
```

## Summary Statistics

- Total tests: 159
- Pass rate: 100%
- Runtime: 3.499s

## Validation Notes

- Added `capabilities --ad-product SP --writes-only` so agents can inspect executable SP write operations before claiming an operation is unsupported.
- Verified `campaigns.edit-budget` returns `canExecute: true`, `approvalRequired: true`, and `executionMode: approval-gated`.
- The capability contract explicitly tells agents not to treat the approval gate as lack of execution capability.

## Test Results

Validated on 2026-07-29 after adding SB-specific capability contract assertions.

### `python3 -m py_compile agent-harness/cli_anything/amazon_ads_ops_workbench/amazon_ads_ops_workbench_cli.py agent-harness/cli_anything/amazon_ads_ops_workbench/core/*.py agent-harness/cli_anything/amazon_ads_ops_workbench/tests/*.py`

```text
OK
```

### `python3 -m unittest discover -s agent-harness/cli_anything/amazon_ads_ops_workbench/tests -v`

```text
----------------------------------------------------------------------
Ran 162 tests in 3.822s

OK
```

## Summary Statistics

- Total tests: 162
- Pass rate: 100%
- Runtime: 3.822s

## Validation Notes

- Added SB capability checks for `sb-keywords.edit-bid` so agents can inspect executable SB write operations before claiming SB is unsupported.
- Verified `sb-keywords.edit-bid` returns `canExecute: true`, `approvalRequired: true`, and `executionMode: approval-gated`.
- Verified `sb-raw.request` remains executable through the approval gate while documenting that media, creative, image, video, logo, and asset paths or payload keys are blocked.

## Test Results

Validated on 2026-07-22 after completing the Sponsored Products create/add/state mutation surface.

### `PATH=/Users/dongli/Documents/广告自动化/agent-harness/.venv/bin:$PATH CLI_ANYTHING_FORCE_INSTALLED=1 PYTHONPATH=/Users/dongli/Documents/广告自动化/agent-harness python3 -m unittest cli_anything.amazon_ads_ops_workbench.tests.test_core cli_anything.amazon_ads_ops_workbench.tests.test_full_e2e -v`

```text
----------------------------------------------------------------------
Ran 91 tests in 2.072s

OK
```

### `PYTHONPATH=/Users/dongli/Documents/广告自动化/agent-harness python3 -m compileall -q cli_anything/amazon_ads_ops_workbench`

```text
OK
```

## Summary Statistics

- Total tests: 91
- Pass rate: 100%
- New coverage includes portfolio create/state, campaign create, ad group create/state, keyword add, product ad list/add/state, ASIN target list/add/state, new media types, new wrappers, and dry-run payload contracts.

## Validation Notes

- All newly added write commands support `--dry-run`.
- This run validated request construction and CLI command routing without submitting live account mutations.

## Test Results

Validated on 2026-07-28 after expanding the Sponsored Products operation surface for conversation-driven CLI use.

### `PYTHONPATH=/Users/dongli/Documents/广告自动化/agent-harness python3 -m unittest cli_anything.amazon_ads_ops_workbench.tests.test_core cli_anything.amazon_ads_ops_workbench.tests.test_full_e2e -v`

```text
----------------------------------------------------------------------
Ran 123 tests in 2.395s

OK
```

## Summary Statistics

- Total tests: 123
- Pass rate: 100%
- Runtime: 2.395s

## Validation Notes

- Unit coverage now includes campaign bidding strategy payloads, ad group default bid edits, generic product targeting expressions, target bid edits, negative product targeting payloads, negative target normalization, and raw `/sp/` path restriction.
- E2E subprocess coverage now includes dry-run payload checks for campaign state/budget/strategy, ad group bid, keyword bid/state, category/expression targets, target bid, negative keywords, negative product targets, and restricted `sp-raw request`.
- Installed command path `/Users/dongli/Documents/广告自动化/agent-harness/.venv/bin/cli-anything-amazon-ads-ops-workbench` was smoke-tested for `--help`, `targets add-expression --dry-run`, `negative-targets add-ad-group --dry-run`, `campaigns edit-bidding-strategy --dry-run`, and `sp-raw request --dry-run`.

## Test Results

Validated on 2026-07-28 after adding the live mutation approval gate.

### `PYTHONPATH=/Users/dongli/Documents/ads-cli-publish-20260717/agent-harness python3 -m unittest cli_anything.amazon_ads_ops_workbench.tests.test_core cli_anything.amazon_ads_ops_workbench.tests.test_full_e2e -v`

```text
----------------------------------------------------------------------
Ran 128 tests in 2.625s

OK
```

### `python3 -m compileall -q agent-harness/cli_anything/amazon_ads_ops_workbench`

```text
OK
```

## Summary Statistics

- Total tests: 128
- Pass rate: 100%
- Runtime: 2.625s

## Validation Notes

- SP write commands now return `meta.mode = "approval-plan"` by default instead of submitting live mutations.
- `approvals show`, `approvals list`, and `approvals execute` are covered in E2E subprocess tests.
- `approvals execute` rejects non-exact confirmation text and does not submit when credentials are missing.
- Read commands and report task/data commands remain outside the approval gate.

## Test Results

Validated on 2026-07-29 after adding the Sponsored Display non-media operation surface and SBV capability alias.

### `python3 -m py_compile agent-harness/cli_anything/amazon_ads_ops_workbench/amazon_ads_ops_workbench_cli.py agent-harness/cli_anything/amazon_ads_ops_workbench/core/*.py agent-harness/cli_anything/amazon_ads_ops_workbench/tests/test_core.py agent-harness/cli_anything/amazon_ads_ops_workbench/tests/test_full_e2e.py`

```text
OK
```

### `PYTHONPATH=agent-harness python3 -m unittest discover -s agent-harness/cli_anything/amazon_ads_ops_workbench/tests -v`

```text
----------------------------------------------------------------------
Ran 180 tests in 5.172s

OK
```

## Summary Statistics

- Total tests: 180
- Pass rate: 100%
- Runtime: 5.172s

## Validation Notes

- Added SD dry-run and approval-plan coverage for campaigns, ad groups, product ads, product/audience targets, location targets, budget rules, raw requests, and SD report creation/parsing.
- Added `capabilities --ad-product SD --writes-only` and `capabilities --ad-product SBV --writes-only`; SBV is documented as the SB non-creative command alias.
- Verified `sd-raw` blocks creative, image, video, logo, media, and asset paths or payload keys before network execution.
- No live Amazon Ads mutation was submitted during this validation run.
