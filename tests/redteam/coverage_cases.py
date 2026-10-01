"""Paired complete-profile controls; executed only by remote verification."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from tests.redteam.harness import SRC_BYTES, SRC_REL, commit, fp_entry, git, sha_of, task, w

IDS = [f"00000000-0000-4000-8000-{index:012d}" for index in (1, 2, 3)]


def record_digest(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def modern_receipt(repo, before, after, index, operation):
    path = f"evidence/task-operations/{IDS[index - 1]}.json"
    anchor = git(repo, "rev-parse", "HEAD").decode().strip()
    after["history"] = (before["history"] if before else []) + [
        {"kind": "operation", "hash_format": "git-commit-bound", "source": path}]
    return path, {"schema_version": 2, "kind": "ec-task-operation",
                  "operation_id": IDS[index - 1], "task_id": "T-100", "expected_head": anchor,
                  "recorded_at": f"2026-09-28T{9 + index:02d}:00:00Z",
                  "request": {"at": "2026-09-28T09:00:00Z", "actor": "agent-7",
                              "operation": operation, "sources": [SRC_REL]},
                  "before_record": before,
                  "before_record_sha256": record_digest(before) if before is not None else None,
                  "after_record": after, "after_record_sha256": record_digest(after),
                  "source_fingerprints": [fp_entry(digest=sha_of(SRC_BYTES), origin="expected-head-blob")]}


def complete_ledger(repo, *, two=True, final_state="DONE"):
    w(repo, ".gitattributes", b"* -text\n")
    w(repo, SRC_REL, SRC_BYTES)
    commit(repo, "sources")
    first = task("T-100", state="CLAIMED", status="CLAIMED", id="T-100", history=[], description="中文驗收")
    path, receipt = modern_receipt(repo, None, first, 1, "claim")
    w(repo, "governance/tasks/T-100.json", first)
    w(repo, path, receipt)
    commit(repo, "claim")
    if two:
        second = deepcopy(first)
        second.update(state=final_state, status=final_state, title="legitimate changed title")
        path, receipt = modern_receipt(repo, first, second, 2, "finish" if final_state == "DONE" else "progress")
        w(repo, "governance/tasks/T-100.json", second)
        w(repo, path, receipt)
        commit(repo, "record transition")


def mutate_receipt(repo, field, value=None, *, remove=False):
    path = f"evidence/task-operations/{IDS[1]}.json"
    data = json.loads((repo / path).read_text(encoding="utf-8"))
    if remove:
        data.pop(field)
    else:
        data[field] = value
    w(repo, path, data)
    commit(repo, "receipt field mutation")


def controls():
    entries = [{"id": "COMPLETE-LIFECYCLE", "plan": complete_ledger, "expected_strict": 0},
               {"id": "COMPLETE-CLAIMED", "plan": lambda repo: complete_ledger(repo, final_state="CLAIMED"), "expected_strict": 0}]
    for field in ("source_fingerprints", "before_record_sha256", "after_record", "recorded_at"):
        def plan(repo, field=field):
            complete_ledger(repo)
            mutate_receipt(repo, field, remove=True)
        entries.append({"id": "MISSING-" + field.upper(), "plan": plan, "expected_strict": 1})
    def digest_mismatch(repo):
        complete_ledger(repo)
        mutate_receipt(repo, "after_record_sha256", "f" * 64)
    entries.append({"id": "RECORD-DIGEST-MISMATCH", "plan": digest_mismatch, "expected_strict": 1})
    def true_drift(repo):
        complete_ledger(repo)
        data = json.loads((repo / "governance/tasks/T-100.json").read_text(encoding="utf-8"))
        data["title"] = "unrecorded rewrite"
        w(repo, "governance/tasks/T-100.json", data)
        commit(repo, "unrecorded rewrite")
    entries.append({"id": "TRUE-DRIFT", "plan": true_drift, "expected_strict": 1, "expected_rule": "POST_HOC_DRIFT"})
    def missing_after_drift(repo):
        true_drift(repo)
        mutate_receipt(repo, "after_record", remove=True)
    entries.append({"id": "PAIRED-NO-AFTER-DRIFT", "plan": missing_after_drift, "expected_strict": 1})
    def swamp(repo):
        complete_ledger(repo)
        current = json.loads((repo / "governance/tasks/T-100.json").read_text(encoding="utf-8"))
        before = deepcopy(current)
        current["title"] = "new unrecorded scope"
        path, receipt = modern_receipt(repo, before, current, 3, "progress")
        # This matches current yet fails to attach the new receipt to its history.
        current["history"] = before["history"]
        receipt["after_record_sha256"] = record_digest(current)
        w(repo, "governance/tasks/T-100.json", current)
        w(repo, path, receipt)
        commit(repo, "unattached matching anchor")
    entries.append({"id": "UNATTACHED-ANCHOR", "plan": swamp, "expected_strict": 1})
    def hidden(repo):
        complete_ledger(repo, final_state="CLAIMED")
        destination = repo / "evidence/task-operations/hidden"
        destination.mkdir()
        for path in (repo / "evidence/task-operations").glob("*.json"):
            path.rename(destination / path.name)
        commit(repo, "hidden operations")
    entries.append({"id": "PAIRED-HIDDEN-CLAIMED", "plan": hidden, "expected_strict": 1})
    def unexpected_task(repo):
        complete_ledger(repo)
        w(repo, "governance/tasks/DONE-800.json", task("DONE-800"))
        commit(repo, "unexpected task filename")
    entries.append({"id": "UNEXPECTED-TASK", "plan": unexpected_task, "expected_strict": 1})
    def duplicate_sources(repo):
        complete_ledger(repo)
        mutate_receipt(repo, "source_fingerprints", [fp_entry(digest=sha_of(SRC_BYTES)), fp_entry(digest=sha_of(SRC_BYTES))])
    entries.append({"id": "DUPLICATE-SOURCE-CONTRACT", "plan": duplicate_sources, "expected_strict": 1})
    return entries
