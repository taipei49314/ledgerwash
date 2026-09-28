"""DANGLING_REF: referenced paths that do not exist in the epoch tree."""

from __future__ import annotations

import re

from ledgerwash.adapters.ec_ledger import REFERENCE_RE
from ledgerwash.models import Finding

from .common import iter_strings


def run(corpus) -> list[Finding]:
    refs: dict[str, set[str]] = {}
    for task in corpus.tasks.values():
        for text in iter_strings(task.data):
            for match in re.findall(REFERENCE_RE, text):
                refs.setdefault(match, set()).add(task.id)

    findings = []
    for path in sorted(refs):
        if corpus.epoch.path_exists(path):
            continue
        ids = sorted(refs[path])
        shown = ", ".join(ids[:4])
        if len(ids) > 4:
            shown += f" (+{len(ids) - 4} more)"
        findings.append(
            Finding(
                rule="DANGLING_REF",
                severity="medium",
                message=(
                    f"referenced path does not exist in the epoch tree "
                    f"(referenced by {len(ids)} task record(s): {shown})"
                ),
                path=path,
                locator=" ".join(ids),
            )
        )
    return findings
