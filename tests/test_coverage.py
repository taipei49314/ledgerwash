"""Remote acceptance of the new mechanical coverage contract and consumer gate."""
from __future__ import annotations

import json
import pytest

from ledgerwash.cli import main
from ledgerwash.engine import run_scan
from tests.redteam.coverage_cases import controls
from tests.redteam.harness import build_repo, original_cases


@pytest.mark.parametrize("case", controls(), ids=lambda case: case["id"])
def test_paired_coverage_controls(tmp_path, case):
    repo = tmp_path / "ledger"
    epoch = build_repo(repo, case["plan"])
    default = run_scan(repo, epoch)
    strict = run_scan(repo, epoch, require_complete=True)
    assert strict["run"]["epoch"] == epoch
    assert default["verdict"] == default["finding_verdict"]
    assert default["findings"] == strict["findings"]
    assert default["finding_verdict"] == strict["finding_verdict"]
    assert default["coverage"] == strict["coverage"]
    assert (strict["verdict"] == "block") == bool(case["expected_strict"])
    assert strict["coverage"]["complete"] == (case["expected_strict"] == 0)
    counts = {status: sum(item["status"] == status for item in strict["coverage"]["checks"])
              for status in ("verified", "unverified", "mismatch")}
    assert strict["coverage"]["counts"] == counts
    assert strict["coverage"]["complete"] == (counts["unverified"] == counts["mismatch"] == 0)
    if case["expected_strict"] == 0:
        assert strict["coverage"]["complete"]
        assert default["findings"] == []
        assert default["residuals"] == []
    if case.get("expected_check"):
        assert any(item["check"] == case["expected_check"] and item["status"] != "verified"
                   for item in strict["coverage"]["checks"])
    if case.get("expected_rule"):
        assert any(item["rule"] == case["expected_rule"] for item in default["findings"])


def test_vacuous_receipt_default_compatible_strict_blocks(tmp_path, capsys):
    case = next(case for case in original_cases() if case["id"] == "A12-VACUOUS-LEDGER")
    repo = tmp_path / "ledger"
    epoch = build_repo(repo, case["plan"])
    assert main(["scan", str(repo), "--at", epoch]) == 0
    default = json.loads(capsys.readouterr().out)
    assert default["finding_verdict"] == "pass"
    assert default["findings"] == []
    assert not default["coverage"]["complete"]
    assert main(["scan", str(repo), "--at", epoch, "--fail-on", "critical", "--require-complete"]) == 1
    strict = json.loads(capsys.readouterr().out)
    assert strict["finding_verdict"] == "pass"
    assert strict["coverage"] == default["coverage"]


def test_empty_ledger_strict_never_passes(tmp_path, capsys):
    def plan(repo):
        from tests.redteam.harness import commit, w
        w(repo, "README.md", b"empty\n")
        commit(repo, "empty")
    repo = tmp_path / "empty"
    epoch = build_repo(repo, plan)
    assert main(["scan", str(repo), "--at", epoch, "--require-complete"]) == 1
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["findings"] == []
    assert envelope["finding_verdict"] == "pass"
    assert not envelope["coverage"]["complete"]
