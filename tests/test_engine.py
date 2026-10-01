"""Envelope shape, determinism, observations."""

from __future__ import annotations

import json
import re

from ledgerwash.qualify import cmd_qualify
from ledgerwash.qualify_corpus import build_corpus

from ledgerwash.engine import run_scan

_FINGERPRINT_RE = re.compile(r"^[A-Z_]+/.*/v1:[0-9a-f]{64}$")


def test_envelope_shape(mini_envelope):
    assert set(mini_envelope) == {
        "ledgerwash_findings_version",
        "run",
        "verdict",
        "finding_verdict",
        "coverage",
        "findings",
        "observations",
        "residuals",
        "summary",
    }
    run = mini_envelope["run"]
    assert set(run) == {
        "adapter",
        "epoch",
        "ledgerwash_version",
        "ref",
        "spec_version",
        "target",
        "require_complete",
    }
    assert run["adapter"] == "ec-ledger"
    assert run["ledgerwash_version"] == "0.4.0"
    assert run["spec_version"] == 4
    assert len(run["epoch"]) == 40
    assert mini_envelope["ledgerwash_findings_version"] == 2
    assert mini_envelope["verdict"] == mini_envelope["finding_verdict"]
    assert run["require_complete"] is False
    assert set(mini_envelope["coverage"]) == {"version", "complete", "counts", "checks", "scope", "limitations"}
    assert mini_envelope["coverage"]["version"] == 1


def test_summary_matches_findings(mini_envelope):
    counts = {"info": 0, "warn": 0, "high": 0, "critical": 0}
    for finding in mini_envelope["findings"]:
        counts[finding["severity"]] += 1
    assert mini_envelope["summary"] == counts


def test_findings_sorted(mini_envelope):
    keys = [(f["rule"], f["path"], f["locator"]) for f in mini_envelope["findings"]]
    assert keys == sorted(keys)


def test_fingerprints_well_formed(mini_envelope):
    for finding in mini_envelope["findings"]:
        assert _FINGERPRINT_RE.match(finding["fingerprint"]), finding["fingerprint"]
    assert len({f["fingerprint"] for f in mini_envelope["findings"]}) == len(
        mini_envelope["findings"]
    )


def test_determinism_across_builds(tmp_path):
    envelopes = []
    for i in range(2):
        repo = build_corpus(tmp_path / f"repo{i}")
        envelope = run_scan(repo)
        envelope["run"]["target"] = "<normalized>"
        envelopes.append(json.dumps(envelope, sort_keys=True, ensure_ascii=False))
    assert envelopes[0] == envelopes[1]


def test_observations(mini_envelope):
    kinds = {o["kind"] for o in mini_envelope["observations"]}
    assert {"self_signing", "schema_versions", "snapshot_expires_at"} <= kinds
    self_signing = next(o for o in mini_envelope["observations"] if o["kind"] == "self_signing")
    assert self_signing["actor_equals_owner"]["same"] == 2  # r900a + r900b
    versions = next(o for o in mini_envelope["observations"] if o["kind"] == "schema_versions")
    assert versions["counts"] == {"1": 11}  # T-907 is unparseable, not counted


def test_qualify_subcommand(capsys):
    assert cmd_qualify() == 0
    assert "qualify ok" in capsys.readouterr().out
