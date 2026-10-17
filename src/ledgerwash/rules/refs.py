"""DANGLING_REF / RECEIPT_ORPHAN: reference and identity bindings.

DANGLING_REF covers task→path references. RECEIPT_ORPHAN (spec 5, red-team
R9) is the receipt→task mirror: a receipt bound to a task_id that names no
loaded task used to vanish silently, so deleting a task record left its
receipts mechanically untraceable.
"""

from __future__ import annotations

import re

from ledgerwash.adapters.ec_ledger import REFERENCE_RE
from ledgerwash.models import Finding

from .common import iter_strings


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []

    for receipt in corpus.receipts:
        task_id = receipt.data.get("task_id")
        if isinstance(task_id, str) and task_id and task_id not in corpus.tasks:
            findings.append(
                Finding(
                    rule="RECEIPT_ORPHAN",
                    severity="warn",
                    message=(
                        f"receipt is bound to task_id {task_id} but no task record with "
                        "that id is loaded; the operation is not attached to any task record"
                    ),
                    path=receipt.path,
                    locator=receipt.name,
                )
            )

    refs: dict[str, set[str]] = {}
    for task in corpus.tasks.values():
        for text in iter_strings(task.data):
            for match in re.findall(REFERENCE_RE, text):
                refs.setdefault(match, set()).add(task.id)

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
                severity="warn",
                message=(
                    f"referenced path does not exist in the epoch tree "
                    f"(referenced by {len(ids)} task record(s): {shown})"
                ),
                path=path,
                locator=" ".join(ids),
            )
        )
    return findings
