"""Each rule fires on its planted case; clean controls stay silent."""

from __future__ import annotations

from tests.conftest import by_rule


def test_dangling_ref(mini_envelope):
    (finding,) = by_rule(mini_envelope)["DANGLING_REF"]
    assert finding["path"] == "docs/gone-path.md"
    assert finding["locator"] == "T-901"
    # T-900 references the existing directory `evidence/notes/` (trailing slash):
    # directories count as existing, worktree `exists()` parity.
    assert not [f for f in by_rule(mini_envelope)["DANGLING_REF"] if "T-900" in f["locator"]]


def test_fp_hash_mismatch(mini_envelope):
    (finding,) = by_rule(mini_envelope)["FP_HASH_MISMATCH"]
    assert finding["path"].endswith("r902b.json")
    assert finding["before"] == "0" * 64
    assert "expected_head anchor" in finding["message"]


def test_fp_source_missing(mini_envelope):
    (finding,) = by_rule(mini_envelope)["FP_SOURCE_MISSING"]
    assert finding["path"].endswith("r902e.json")
    assert "never-created.md" in finding["message"]
    assert "birth anchor" in finding["message"]


def test_contract_undocumented(mini_envelope):
    findings = by_rule(mini_envelope)["CONTRACT_UNDOCUMENTED"]
    assert len(findings) == 2
    by_locator = {f["locator"].split("#")[0]: f for f in findings}
    pre_image = by_locator["r902c.json"]
    assert "match birth-side anchor" in pre_image["message"]
    assert "contract undeclared" in pre_image["message"]
    nothing = by_locator["r902d.json"]
    assert "no birth-side anchor matched" in nothing["message"]


def test_era_aware_receipt_stays_silent(mini_envelope):
    """r900a fingerprints a file that existed at its birth commit and was deleted
    later; only a worktree scanner (round-0 style) would flag it."""
    touched = [f for f in mini_envelope["findings"] if "r900a.json" in f["locator"]]
    assert touched == []


def test_pin_local_missing_wording(mini_envelope):
    (finding,) = by_rule(mini_envelope)["PIN_LOCAL_MISSING"]
    assert finding["path"].endswith("r906a.json")
    assert "unverified locally" in finding["message"]
    assert "not failed" in finding["message"]


def test_pin_unroutable(mini_envelope):
    (finding,) = by_rule(mini_envelope)["PIN_UNROUTABLE"]
    assert finding["locator"] == "T-906"
    assert "cannot be routed" in finding["message"]


def test_timeline_inversion(mini_envelope):
    (finding,) = by_rule(mini_envelope)["TIMELINE_INVERSION"]
    assert finding["path"].endswith("r903a.json")
    assert finding["before"] == "2026-01-02T12:00:00Z"
    assert finding["after"] == "2026-01-02T08:00:00Z"


def test_chain_break(mini_envelope):
    (finding,) = by_rule(mini_envelope)["CHAIN_BREAK"]
    assert finding["locator"] == "T-903:r903b.json"
    assert finding["before"] == "d" * 16
    assert finding["after"] == "e" * 16


def test_post_hoc_drift(mini_envelope):
    (finding,) = by_rule(mini_envelope)["POST_HOC_DRIFT"]
    assert finding["locator"] == "T-905:anchor=r905a.json"
    assert "state" in finding["message"]
    assert "status" in finding["message"]


def test_timestamp_malformed(mini_envelope):
    (finding,) = by_rule(mini_envelope)["TIMESTAMP_MALFORMED"]
    assert finding["locator"] == "r904a.json#recorded_at"
    assert finding["severity"] == "warn"
    assert "not-a-timestamp" in finding["after"]


def test_timestamp_redacted(mini_envelope):
    """EC legacy digit masking is a convention, not weakening: info, not warn."""
    (finding,) = by_rule(mini_envelope)["TIMESTAMP_REDACTED"]
    assert finding["locator"] == "T-910#time"
    assert finding["severity"] == "info"
    assert "15:2xZ" in finding["after"]


def test_record_unparseable(mini_envelope):
    (finding,) = by_rule(mini_envelope)["RECORD_UNPARSEABLE"]
    assert finding["path"].endswith("T-907.json")
    assert "json:" in finding["message"]


def test_status_state_mismatch_and_cjk_silence(mini_envelope):
    findings = by_rule(mini_envelope)["STATUS_STATE_MISMATCH"]
    assert [f["locator"] for f in findings] == ["T-909#status"]
    (finding,) = findings
    assert finding["after"] == "**DONE**"
    # T-908's `DONE（兩台）` must normalize to DONE and stay silent (round-0 FP class)
    assert not [f for f in findings if f["locator"] == "T-908#status"]


def test_clean_control_passes(mini_envelope, clean_envelope):
    assert mini_envelope["verdict"] == "block"
    assert clean_envelope["verdict"] == "pass"
    assert clean_envelope["findings"] == []
    assert clean_envelope["residuals"] == []
