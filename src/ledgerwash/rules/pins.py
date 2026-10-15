"""PIN_UNROUTABLE / PIN_LOCAL_MISSING / PIN_NOT_COMMIT.

Round-0 lesson 3: "not found in the local clone" is not "pin failure". Pins on
the target repo itself (receipt expected_head) are verified locally; bare
40-hex references that cannot be routed to a source repo are reported as
unroutable. Wording never claims a pin is dead — remote checks are out of
scope (SPEC §9). PIN_NOT_COMMIT (spec 5, red-team R1): an expected_head that
resolves to a non-commit object used to silence both the pin check
(any-object lookup) and fingerprint verification (commit-only anchors) at
zero findings; the type disagreement between the two checks is itself the
signal.
"""

from __future__ import annotations

import re

from ledgerwash.models import Finding

from .common import iter_strings

# Bounded: a 40-hex run embedded in a longer hex string (e.g. a 64-char sha256
# digest) is not a pin and must not be sliced out of it.
_HEX40 = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")
_HEX40_FULL = re.compile(r"[0-9a-f]{40}")
_QUALIFIED = re.compile(r"([A-Za-z0-9_.\-]+)@([0-9a-f]{40})(?![0-9a-f])")


def qualified_pins(corpus) -> list[dict]:
    """repo@sha qualified references seen (observation input; not verified, SPEC §9)."""
    seen: dict[tuple[str, str], set[str]] = {}
    for task in corpus.tasks.values():
        for text in iter_strings(task.data):
            for repo_name, sha in _QUALIFIED.findall(text):
                seen.setdefault((repo_name, sha.lower()), set()).add(task.id)
    return [
        {"repo": repo_name, "sha": sha, "referenced_by": sorted(ids)}
        for (repo_name, sha), ids in sorted(seen.items())
    ]


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []
    prose: dict[str, set[str]] = {}
    task_path = {}
    for task in corpus.tasks.values():
        task_path[task.id] = task.path
        for text in iter_strings(task.data):
            for sha in _HEX40.findall(text):
                prose.setdefault(sha, set()).add(task.id)

    expected: dict[str, list] = {}
    for receipt in corpus.receipts:
        eh = receipt.data.get("expected_head")
        if isinstance(eh, str) and _HEX40_FULL.fullmatch(eh.lower()):
            expected.setdefault(eh.lower(), []).append(receipt)

    types = corpus.epoch.object_types(set(prose) | set(expected))
    have = set(types)
    commit_set = {sha for sha, kind in types.items() if kind == "commit"}

    for sha in sorted(expected):
        receipts = expected[sha]
        names = ", ".join(r.name for r in receipts[:4])
        if len(receipts) > 4:
            names += f" (+{len(receipts) - 4} more)"
        if sha not in have:
            findings.append(
                Finding(
                    rule="PIN_LOCAL_MISSING",
                    severity="warn",
                    message=(
                        f"expected_head {sha} is not an object in the target repo; "
                        f"pin unverified locally, not failed (referenced by {names})"
                    ),
                    path=receipts[0].path,
                    locator=" ".join(r.name for r in receipts),
                )
            )
        elif sha not in commit_set:
            findings.append(
                Finding(
                    rule="PIN_NOT_COMMIT",
                    severity="warn",
                    message=(
                        f"expected_head {sha} resolves to a {types[sha]} object, not a "
                        "commit; fingerprint anchoring requires a commit, so the receipt's "
                        f"claimed source digests are not verified locally (referenced by {names})"
                    ),
                    path=receipts[0].path,
                    locator=" ".join(r.name for r in receipts),
                )
            )

    for sha in sorted(prose):
        if sha in have or sha in expected:
            continue
        ids = sorted(prose[sha])
        shown = ", ".join(ids[:4])
        if len(ids) > 4:
            shown += f" (+{len(ids) - 4} more)"
        findings.append(
            Finding(
                rule="PIN_UNROUTABLE",
                severity="warn",
                message=(
                    f"sha {sha} referenced in task record(s) ({shown}) is not an object in the "
                    "target repo; bare reference cannot be routed to a source repo; unverified"
                ),
                path=task_path[ids[0]],
                locator=" ".join(ids),
            )
        )
    return findings
