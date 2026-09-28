"""FP_SOURCE_MISSING / FP_HASH_MISMATCH / CONTRACT_UNDOCUMENTED.

Era-aware fingerprint verification: sources are hashed at their documented
anchor (birth commit or expected_head), never at the current epoch — a file
that legitimately changed or moved after the receipt was written is not a
finding (round-0 lesson 1).
"""

from __future__ import annotations

import hashlib

from ledgerwash.adapters.ec_ledger import CONTRACT_TABLE
from ledgerwash.models import Finding, short_json


def _anchor_commits(corpus):
    anchors = set()
    for receipt in corpus.receipts:
        if receipt.birth:
            anchors.add(receipt.birth)
        expected = receipt.data.get("expected_head")
        if isinstance(expected, str):
            anchors.add(expected)
    return corpus.epoch.has_objects(anchors)


def _verify_at(corpus, commit: str, src: str, want: str):
    """-> (status, got) where status in {"missing", "match", "mismatch"}."""
    blob = corpus.epoch.blob_at(commit, src)
    if blob is None:
        return "missing", None
    got = hashlib.sha256(blob).hexdigest()
    return ("match" if got == want else "mismatch"), got


def _undocumented(corpus, receipt, locator, hf, origin, src, want) -> Finding:
    message = f"undocumented fingerprint combo (hash_format={hf!r}, origin={origin!r})"
    if not isinstance(src, str) or not isinstance(want, str) or not src or not want:
        return Finding(
            rule="CONTRACT_UNDOCUMENTED",
            severity="warn",
            message=message + "; entry missing source or sha256",
            path=receipt.path,
            locator=locator,
            before=short_json(src),
            after=short_json(want),
        )
    anchors = []
    if receipt.birth:
        anchors.append(receipt.birth)
        parent = corpus.epoch.parent(receipt.birth)
        if parent:
            anchors.append(parent)
    trail = []
    matched = None
    for commit in anchors:
        status, _got = _verify_at(corpus, commit, src, want)
        if status == "match":
            matched = commit
            trail.append(f"{commit[:12]}:match")
            break
        trail.append(f"{commit[:12]}:{status}")
    if matched:
        message += (
            f"; bytes match birth-side anchor {matched[:12]}"
            " (evidence validates, contract undeclared)"
        )
    elif anchors:
        message += "; no birth-side anchor matched (" + "; ".join(trail) + ")"
    else:
        message += "; no birth-side anchor available"
    return Finding(
        rule="CONTRACT_UNDOCUMENTED",
        severity="warn",
        message=message,
        path=receipt.path,
        locator=locator,
        before=src,
        after=want,
    )


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []
    epoch = corpus.epoch
    resolved = _anchor_commits(corpus)
    for receipt in corpus.receipts:
        entries = receipt.data.get("source_fingerprints")
        if entries is None:
            continue
        if not isinstance(entries, list):
            corpus.residuals.append(
                {"path": receipt.path, "reason": "source_fingerprints is not a list"}
            )
            continue
        for index, entry in enumerate(entries):
            locator = f"{receipt.name}#source_fingerprints[{index}]"
            if not isinstance(entry, dict):
                findings.append(
                    Finding(
                        rule="CONTRACT_UNDOCUMENTED",
                        severity="warn",
                        message="fingerprint entry is not an object",
                        path=receipt.path,
                        locator=locator,
                    )
                )
                continue
            hf = entry.get("hash_format")
            origin = entry.get("origin")
            src = entry.get("source")
            want = entry.get("sha256")
            anchor_kind = (
                CONTRACT_TABLE.get((hf, origin))
                if isinstance(hf, str) and isinstance(origin, str)
                else None
            )
            if anchor_kind is None or not isinstance(src, str) or not isinstance(want, str):
                findings.append(
                    _undocumented(corpus, receipt, locator, hf, origin, src, want)
                )
                continue
            if anchor_kind == "birth":
                anchor = receipt.birth
            else:
                anchor = receipt.data.get("expected_head")
                anchor = anchor if isinstance(anchor, str) else None
            if not anchor or anchor not in resolved:
                corpus.residuals.append(
                    {
                        "path": receipt.path,
                        "reason": (
                            f"{locator}: {anchor_kind} anchor unresolvable in target repo;"
                            " fingerprint unverified"
                        ),
                    }
                )
                continue
            status, got = _verify_at(corpus, anchor, src, want)
            if status == "missing":
                findings.append(
                    Finding(
                        rule="FP_SOURCE_MISSING",
                        severity="high",
                        message=(
                            f"source {src!r} does not exist at {anchor_kind} anchor {anchor[:12]}"
                        ),
                        path=receipt.path,
                        locator=locator,
                        before=src,
                    )
                )
            elif status == "mismatch":
                findings.append(
                    Finding(
                        rule="FP_HASH_MISMATCH",
                        severity="high",
                        message=(
                            f"sha256 mismatch at {anchor_kind} anchor {anchor[:12]}: "
                            f"receipt {want[:12]}… vs actual {got[:12]}…"
                        ),
                        path=receipt.path,
                        locator=locator,
                        before=want,
                        after=got,
                    )
                )
    return findings
