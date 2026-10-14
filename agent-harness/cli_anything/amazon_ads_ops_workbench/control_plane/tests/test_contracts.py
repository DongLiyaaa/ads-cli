from concurrent.futures import ThreadPoolExecutor
import json
from unittest.mock import patch
import pytest
from cli_anything.amazon_ads_ops_workbench.control_plane.contracts import (
    public_catalog,
    invoke_contract,
    validate_arguments,
)
from cli_anything.amazon_ads_ops_workbench.control_plane.security import (
    password_hash,
    password_matches,
    redact,
    bound_hash,
    encrypt_config,
    decrypt_config,
    Problem,
)
from cli_anything.amazon_ads_ops_workbench.control_plane.worker import (
    mutation_outcome,
    validate_download_url,
)
from cli_anything.amazon_ads_ops_workbench.core.env import (
    AdsEnvironment,
    load_ads_environment,
)
from cli_anything.amazon_ads_ops_workbench.core.runtime import (
    OperationRuntime,
    operation_runtime,
    current_runtime,
)
from cli_anything.amazon_ads_ops_workbench.core.snapshot import normalize_campaign_row
from cryptography.fernet import Fernet

ENV = AdsEnvironment(
    "test-client-id", "test-client-secret", "test-refresh-token", "123", "NA", "US"
)


def test_catalog_does_not_expose_local_files_or_approval_execution():
    catalog = public_catalog()
    json.dumps(catalog, allow_nan=False)
    assert len(catalog) >= 120
    assert not any(
        r["operation"].startswith(("approvals.", "profiles.", "auth.")) for r in catalog
    )
    assert not any(
        set(r["inputSchema"]["properties"])
        & {"input_file", "output_dir", "marketplace", "confirm_submit", "dry_run"}
        for r in catalog
    )
    assert sum(r["kind"] == "report" for r in catalog) == 12


def test_plan_never_calls_upstream_or_writes_local_approval():
    with patch(
        "cli_anything.amazon_ads_ops_workbench.core.client.AmazonAdsClient.create_campaign",
        side_effect=AssertionError("network write"),
    ):
        plan = invoke_contract(
            "campaigns.create",
            {
                "name": "test",
                "budget": 10,
                "targeting_type": "MANUAL",
                "start_date": "2026-10-14",
                "state": "PAUSED",
            },
            ENV,
            "plan",
        )
    assert plan["payload"]["campaigns"][0]["state"] == "PAUSED"
    assert current_runtime.get() is None


@pytest.mark.parametrize(
    "operation", [r["operation"] for r in public_catalog() if r["kind"] == "report"]
)
def test_all_report_builders_prepare_without_network(operation):
    with patch(
        "cli_anything.amazon_ads_ops_workbench.core.client.AmazonAdsClient.exchange_refresh_token",
        side_effect=AssertionError("network"),
    ):
        body = invoke_contract(
            operation,
            {
                "start_date": "2026-10-01",
                "end_date": "2026-10-07",
                "time_unit": "DAILY",
            },
            ENV,
            "report_plan",
        )
    assert (
        body["startDate"] == "2026-10-01"
        and body["configuration"]["timeUnit"] == "DAILY"
    )


def test_thread_local_context_and_outputs():
    def run(number):
        env = AdsEnvironment(str(number), "s", "r", str(number), "NA", "US")
        with operation_runtime(OperationRuntime(env, "plan")):
            assert load_ads_environment().profile_id == str(number)
        return current_runtime.get()

    with ThreadPoolExecutor(max_workers=5) as pool:
        assert all(v is None for v in pool.map(run, range(30)))


@pytest.mark.parametrize("budget", [-1, 0, float("inf"), float("nan"), True, "10"])
def test_invalid_money_rejected(budget):
    with pytest.raises(Problem):
        validate_arguments("campaigns.create", {"budget": budget})


@pytest.mark.parametrize(
    "path",
    [
        "/sp/../sb/campaigns",
        "/sp/%2e%2e/a",
        "/sp//campaigns",
        "https://evil.example/sp",
        "/sp/campaigns?scope=other",
    ],
)
def test_raw_paths_cannot_escape_scope(path):
    with pytest.raises(Problem):
        validate_arguments("sp-raw.request", {"path": path})


@pytest.mark.parametrize(
    "url",
    [
        "http://a.s3.amazonaws.com/a",
        "https://127.0.0.1/a",
        "https://s3.amazonaws.com.evil.test/a",
        "https://u:p@a.s3.amazonaws.com/a",
        "https://a.s3.amazonaws.com:123/a",
    ],
)
def test_download_url_rejects_ssrf(url):
    with pytest.raises(ValueError):
        validate_download_url(url)


def test_download_url_accepts_amazon_s3():
    assert validate_download_url(
        "https://bucket.s3.amazonaws.com/report?signature=example"
    )


def test_result_does_not_equate_partial_or_unknown_with_success():
    assert (
        mutation_outcome({"campaigns": {"success": [{"campaignId": "1"}], "error": []}})
        == "SUCCEEDED"
    )
    assert (
        mutation_outcome(
            {
                "campaigns": {
                    "success": [{"campaignId": "1"}],
                    "error": [{"message": "bad"}],
                }
            }
        )
        == "PARTIAL"
    )
    assert mutation_outcome([{"code": "INVALID_ARGUMENT"}]) == "FAILED"
    assert mutation_outcome({}) == "UNKNOWN"


def test_secrets_and_signed_urls_redacted():
    output = json.dumps(
        redact(
            {
                "refresh_token": "secret",
                "credentials_ciphertext": "cipher",
                "msg": "Atza|secret amcp_secret https://bucket.s3.amazonaws.com/a?secret=yes",
            }
        )
    )
    assert (
        "secret" not in output
        and json.loads(output)["credentials_ciphertext"] == "[REDACTED]"
    )


def test_password_and_encryption_roundtrip():
    encoded = password_hash("strong-test-password")
    assert password_matches("strong-test-password", encoded)
    assert not password_matches("wrong", encoded)
    key = Fernet.generate_key().decode()
    encrypted = encrypt_config({"refresh_token": "private"}, key)
    assert (
        "private" not in encrypted
        and decrypt_config(encrypted, key)["refresh_token"] == "private"
    )


def test_plan_binding_covers_owner_account_profile():
    base = bound_hash("u", "a", "p", "op", {"bid": 1})
    assert (
        len(
            {
                base,
                bound_hash("v", "a", "p", "op", {"bid": 1}),
                bound_hash("u", "b", "p", "op", {"bid": 1}),
                bound_hash("u", "a", "q", "op", {"bid": 1}),
            }
        )
        == 4
    )


def test_v3_budget_display_fixed():
    row = normalize_campaign_row(
        {
            "campaignId": "1",
            "name": "x",
            "state": "PAUSED",
            "budget": {"budget": 10, "budgetType": "DAILY"},
        },
        "US",
    )
    assert row["budget"] == "DAILY $10.00"


def test_post_lists_follow_all_pages_and_detect_repeated_tokens():
    from cli_anything.amazon_ads_ops_workbench.core.client import AmazonAdsClient

    client = AmazonAdsClient(ENV)
    with patch.object(
        client,
        "_send_json",
        side_effect=[
            {"campaigns": [{"campaignId": "1"}], "nextToken": "next"},
            {"campaigns": [{"campaignId": "2"}]},
        ],
    ):
        assert len(client.list_campaigns("token", "123")) == 2
    with patch.object(
        client, "_send_json", return_value={"keywords": [], "nextToken": "repeated"}
    ):
        with pytest.raises(RuntimeError, match="Repeated pagination"):
            client._post_list("/sp/keywords/list", "token", "123", {})
