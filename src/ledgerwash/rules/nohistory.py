"""NO_OPERATION_HISTORY and its negative space (spec 5).

Taxonomy 8 (post-hoc rewrite) in its pure form: the record claims completion
with zero operation history backing it. The S4 escape sample
(attack-nemotron-3-ultra-free) demonstrated the blind spot — POST_HOC_DRIFT
needs a receipt anchor, so a receipt-less record could be rewritten freely.

Era-awareness (round-0 lesson 1): NO_OPERATION_HISTORY fires only when the
receipt system demonstrably existed at the task's close time — state is DONE,
the task has zero receipts, and its `time` parses to a moment on/after the
earliest receipt `recorded_at` in the ledger. Pre-receipt-system tasks and
tasks with unparseable time stay silent (on the round-0 corpus: 275
receipt-less DONE tasks closed before the first receipt stay silent; 3 closed
after it fire — T-291, T-293, T-297).

The 2026-10-01 red-team round showed that the era gate's keys sit in audited
hands: erasing or backdating the `time` field (R2), emptying every
`recorded_at` (R3), or wearing the legacy redaction shape (R5) silenced the
rule ledger-wide at zero findings. Spec 5 promotes those states to findings:

- DONE_TIME_UNESTABLISHED (high): DONE, zero receipts, unusable closure time
  (missing/empty/unparseable/redacted), receipts exist. No birth carve-out —
  a redacted or empty time is mechanically indistinguishable from an erased
  one, and honest pre-system tasks carry usable times.
- DONE_TIME_BACKDATED (high): the closure time claims the pre-receipt-system
  carve-out, but the task file's birth commit is dated inside the receipt
  era. This compares claimed dates, not ancestry order or trusted execution
  time (SPEC §3.1). A new child commit can carry an old committer date and
  avoid this finding without rewriting any existing history. Strict coverage
  still blocks the missing operation history.
- ERA_UNDETERMINABLE (warn): receipts exist but none yields a parseable
  recorded_at, so the era check is unenforceable ledger-wide.

Ledgers with zero loaded receipts keep residual semantics (SPEC §3): the DONE
rules fire only when the receipt system is demonstrably present at the epoch.
"""

from __future__ import annotations

from ledgerwash.adapters.ec_ledger import RECEIPTS_DIR, TASKS_DIR
from ledgerwash.models import Finding

from .common import parse_ts


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []
    system_start = None
    for receipt in corpus.receipts:
        ts = parse_ts(receipt.data.get("recorded_at"))
        if ts is not None and (system_start is None or ts < system_start):
            system_start = ts
    if system_start is None:
        if corpus.receipts:
            findings.append(
                Finding(
                    rule="ERA_UNDETERMINABLE",
                    severity="warn",
                    message=(
                        f"{len(corpus.receipts)} receipt(s) exist but none has a parseable "
                        "recorded_at; era-aware verification (NO_OPERATION_HISTORY) cannot "
                        "run for this ledger"
                    ),
                    path=RECEIPTS_DIR,
                    locator="ledger",
                )
            )
        findings.extend(_negspace(corpus, system_start))
        return findings
    ops = corpus.ops_by_task()
    for task in corpus.tasks.values():
        if task.data.get("state") != "DONE":
            continue
        if task.id in ops:
            continue
        closed_at = parse_ts(task.data.get("time"))
        if closed_at is None or closed_at < system_start:
            continue
        findings.append(
            Finding(
                rule="NO_OPERATION_HISTORY",
                severity="high",
                message=(
                    f"task {task.id} is DONE but has no operation receipts; "
                    "completion is not backed by any recorded operation chain"
                ),
                path=task.path,
                locator=f"{task.id}:state=DONE",
            )
        )
    findings.extend(_negspace(corpus, system_start))
    return findings


def _negspace(corpus, system_start) -> list[Finding]:
    """DONE claims with zero receipts whose closure time cannot support the
    era check: unusable, or backdated and contradicted by the file's birth."""
    if not corpus.receipts:
        return []
    findings: list[Finding] = []
    ops = corpus.ops_by_task()
    births = corpus.epoch.birth_map(TASKS_DIR)
    birth_shas = {
        births[task.path] for task in corpus.tasks.values() if task.path in births
    }
    dates = corpus.epoch.commit_dates(birth_shas)
    for task in corpus.tasks.values():
        if task.data.get("state") != "DONE" or task.id in ops:
            continue
        closed_at = parse_ts(task.data.get("time"))
        if closed_at is None:
            findings.append(
                Finding(
                    rule="DONE_TIME_UNESTABLISHED",
                    severity="high",
                    message=(
                        f"task {task.id} is DONE with no operation receipts and its closure "
                        "time is missing, empty, unparseable or redacted; the receipt-era "
                        "check for this task cannot run"
                    ),
                    path=task.path,
                    locator=f"{task.id}:state=DONE",
                )
            )
            continue
        if system_start is None or closed_at >= system_start:
            continue  # NOH territory, or era dead: ERA_UNDETERMINABLE carries the ledger
        birth = births.get(task.path)
        birth_date = parse_ts(dates.get(birth)) if birth else None
        if birth_date is not None and birth_date >= system_start:
            findings.append(
                Finding(
                    rule="DONE_TIME_BACKDATED",
                    severity="high",
                    message=(
                        f"task {task.id} claims completion {task.data.get('time')} before the "
                        f"earliest receipt, but the task file first appears in history at "
                        f"{dates.get(birth)}; the pre-receipt-system carve-out is contradicted "
                        "by the file's own history"
                    ),
                    path=task.path,
                    locator=f"{task.id}:state=DONE",
                )
            )
    return findings
