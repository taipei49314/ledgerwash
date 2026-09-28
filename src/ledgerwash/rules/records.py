"""RECORD_UNPARSEABLE / STATUS_STATE_MISMATCH."""

from __future__ import annotations

import re

from ledgerwash.models import Finding

_ASCII_HEAD = re.compile(r"[A-Za-z0-9_-]+")


def normalized_head(status: str) -> str:
    """Leading ASCII run of the status head.

    `DONE（兩台）` normalizes to `DONE` — round 0's C3 produced 60/60 false
    positives from CJK-annotated statuses because it compared the raw token.
    """
    tokens = status.strip().strip("*").split()
    if not tokens:
        return ""
    match = _ASCII_HEAD.match(tokens[0])
    return match.group(0) if match else ""


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []
    for unparseable in sorted(corpus.unparsed, key=lambda item: item["path"]):
        findings.append(
            Finding(
                rule="RECORD_UNPARSEABLE",
                severity="high",
                message=f"record unparseable: {unparseable['reason']}",
                path=unparseable["path"],
            )
        )
    for task in corpus.tasks.values():
        status = task.data.get("status")
        state = task.data.get("state")
        if not isinstance(status, str) or not isinstance(state, str):
            continue  # adapter residual covers the shape violation
        head = normalized_head(status)
        if head and head != state:
            findings.append(
                Finding(
                    rule="STATUS_STATE_MISMATCH",
                    severity="warn",
                    message=f"normalized status head {head!r} != state {state!r}",
                    path=task.path,
                    locator=f"{task.id}#status",
                    before=state,
                    after=status,
                )
            )
    return findings
