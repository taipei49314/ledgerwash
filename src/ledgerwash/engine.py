"""Engine: load corpus, run rules in fixed order, sort, fingerprint, envelope, verdict."""

from __future__ import annotations

from ledgerwash import SPEC_VERSION, __version__
from ledgerwash.adapters import ec_ledger
from ledgerwash.epoch import Epoch
from ledgerwash.models import SEVERITY_ORDER, SEVERITY_RANK, Finding, finding_fingerprint
from ledgerwash.rules import drift, fingerprints, nohistory, pins, records, refs, timeline

ADAPTERS = {"ec-ledger": ec_ledger}

# SPEC §4 closed rule set; gate A8 checks this list against SPEC.md.
RULE_IDS = [
    "CHAIN_BREAK",
    "CONTRACT_UNDOCUMENTED",
    "DANGLING_REF",
    "FP_HASH_MISMATCH",
    "FP_SOURCE_MISSING",
    "NO_OPERATION_HISTORY",
    "PIN_LOCAL_MISSING",
    "PIN_UNROUTABLE",
    "POST_HOC_DRIFT",
    "RECORD_UNPARSEABLE",
    "STATUS_STATE_MISMATCH",
    "TIMELINE_INVERSION",
    "TIMESTAMP_MALFORMED",
    "TIMESTAMP_REDACTED",
]

_RULES = (refs.run, fingerprints.run, pins.run, timeline.run, drift.run,
          nohistory.run, records.run)


def build_observations(corpus):
    """Structural stats with no verdict (SPEC §5): self-signing, snapshot expiry as
    recorded, cross-repo qualified pins, schema_version distribution."""
    observations = []
    same = differ = 0
    for receipt in corpus.receipts:
        request = receipt.data.get("request")
        actor = request.get("actor") if isinstance(request, dict) else None
        task_id = receipt.data.get("task_id")
        owner = (
            corpus.tasks[task_id].data.get("owner")
            if isinstance(task_id, str) and task_id in corpus.tasks else None
        )
        if isinstance(actor, str) and isinstance(owner, str):
            if actor == owner:
                same += 1
            else:
                differ += 1
    observations.append(
        {"kind": "self_signing", "actor_equals_owner": {"same": same, "differ": differ}}
    )
    snapshot = corpus.snapshot or {}
    expires = snapshot.get("expires_at")
    if expires:
        observations.append(
            {
                "kind": "snapshot_expires_at",
                "expires_at": expires,
                "note": "recorded as found; no freshness judgment (no clock in this tool)",
            }
        )
    qualified = pins.qualified_pins(corpus)
    if qualified:
        observations.append({"kind": "cross_repo_qualified_pins", "pins": qualified})
    versions: dict[str, int] = {}
    for task in corpus.tasks.values():
        key = str(task.data.get("schema_version"))
        versions[key] = versions.get(key, 0) + 1
    observations.append({"kind": "schema_versions", "counts": versions})
    return observations


def run_scan(repo, ref: str | None = None, adapter: str = "ec-ledger", fail_on: str = "high") -> dict:
    adapter_mod = ADAPTERS[adapter]
    epoch = Epoch(repo, ref)
    corpus = adapter_mod.load(epoch)

    findings: list[Finding] = []
    for rule in _RULES:
        findings.extend(rule(corpus))
    findings.sort(key=lambda f: f.sort_key())

    summary = {name: 0 for name in SEVERITY_ORDER}
    for finding in findings:
        finding.fingerprint = finding_fingerprint(finding)
        summary[finding.severity] += 1
    verdict = (
        "block"
        if any(SEVERITY_RANK[f.severity] >= SEVERITY_RANK[fail_on] for f in findings)
        else "pass"
    )

    return {
        "ledgerwash_findings_version": 1,
        "run": {
            "adapter": adapter,
            "epoch": epoch.sha,
            "ledgerwash_version": __version__,
            "ref": epoch.ref,
            "spec_version": SPEC_VERSION,
            "target": str(epoch.repo),
        },
        "verdict": verdict,
        "findings": [
            {
                "rule": f.rule,
                "severity": f.severity,
                "message": f.message,
                "path": f.path,
                "locator": f.locator,
                "before": f.before,
                "after": f.after,
                "fingerprint": f.fingerprint,
            }
            for f in findings
        ],
        "observations": build_observations(corpus),
        "residuals": sorted(corpus.residuals, key=lambda item: (item["path"], item["reason"])),
        "summary": summary,
    }
