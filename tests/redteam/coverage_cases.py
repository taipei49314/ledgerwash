"""Paired complete-profile controls; executed only by remote verification."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from tests.redteam.harness import SRC_BYTES, SRC_REL, commit, fp_entry, git, sha_of, task, w

IDS = [f"00000000-0000-4000-8000-{index:012d}" for index in (1, 2, 3)]
EXPECTED_IDS = {
    "COMPLETE-LIFECYCLE", "COMPLETE-CLAIMED", "MISSING-SOURCE_FINGERPRINTS",
    "MISSING-BEFORE_RECORD_SHA256", "MISSING-AFTER_RECORD", "MISSING-RECORDED_AT",
    "RECORD-DIGEST-MISMATCH", "TRUE-DRIFT", "PAIRED-NO-AFTER-DRIFT", "UNATTACHED-ANCHOR",
    "PAIRED-HIDDEN-CLAIMED", "UNEXPECTED-TASK", "DUPLICATE-SOURCE-CONTRACT",
    "MISSING-REQUEST-ID", "MISSING-INTENT", "MISSING-BEFORE", "NULL-PROGRESS-BEFORE",
    "NONOBJECT-REQUEST", "DUPLICATE-REQUEST-SOURCES", "NONSTRING-REQUEST-SOURCES",
    "HISTORY-DUPLICATE", "HISTORY-MISSING", "HISTORY-CROSS-TASK", "COMPLETE-REPAIR",
    "PAIRED-EMPTY-RECEIPT", "DUPLICATE-JSON-KEY", "NONFINITE-JSON", "NONFINITE-EXPONENT",
    "LONE-SURROGATE-RECEIPT", "UNSUPPORTED-MIGRATION", "LONE-SURROGATE-TASK", "LONE-SURROGATE-SNAPSHOT",
    "UNATTACHED-NONLATEST", "DUPLICATE-REQUEST-UUID", "EXPECTED-HEAD-BINDING",
}


def record_digest(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def modern_receipt(repo, before, after, index, operation):
    path = f"evidence/task-operations/{IDS[index - 1]}.json"
    anchor = git(repo, "rev-parse", "HEAD").decode().strip()
    after["history"] = (before["history"] if before else []) + [
        {"kind": "operation", "hash_format": "git-commit-bound", "source": path}]
    request = {"at": f"2026-09-28T{9 + index:02d}:00:00Z", "actor": "agent-7",
               "operation": operation, "sources": [SRC_REL], "operation_id": IDS[index - 1],
               "request_id": IDS[index - 1], "expected": {"head": anchor},
               "reason": after["evidence"], "summary": {"checked_at": "2026-09-28T09:00:00Z"}}
    intent = deepcopy(request)
    intent.pop("operation_id")
    intent.pop("at")
    intent["expected"].pop("head")
    intent["summary"].pop("checked_at")
    return path, {"schema_version": 2, "kind": "ec-task-operation",
                  "operation_id": IDS[index - 1], "task_id": "T-100", "expected_head": anchor,
                  "request_id": IDS[index - 1], "intent_sha256": record_digest(intent),
                  "recorded_at": f"2026-09-28T{9 + index:02d}:00:00Z",
                  "request": request,
                  "before_record": before,
                  "before_record_sha256": record_digest(before) if before is not None else None,
                  "after_record": after, "after_record_sha256": record_digest(after),
                  "source_fingerprints": [fp_entry(digest=sha_of(SRC_BYTES), origin="expected-head-blob")]}


def complete_ledger(repo, *, two=True, final_state="DONE"):
    w(repo, ".gitattributes", b"* -text\n")
    w(repo, SRC_REL, SRC_BYTES)
    commit(repo, "sources")
    first = {"schema_version": 1, "id": "T-100", "state": "CLAIMED", "status": "CLAIMED",
             "owner": "agent-7", "time": "2026-09-28T10:00:00Z", "description": "中文驗收 😀",
             "history": [], "evidence": "initial source", "handoff": None}
    path, receipt = modern_receipt(repo, None, first, 1, "claim")
    w(repo, "governance/tasks/T-100.json", first)
    w(repo, path, receipt)
    commit(repo, "claim")
    if two:
        second = deepcopy(first)
        second.update(state=final_state, status=final_state, evidence="legitimate changed evidence",
                      time="2026-09-28T11:00:00Z")
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
        checks = {"source_fingerprints": "fingerprint_list", "before_record_sha256": "before_record_digest",
                  "after_record": "after_record_profile", "recorded_at": "recorded_at"}
        entries.append({"id": "MISSING-" + field.upper(), "plan": plan, "expected_strict": 1, "expected_check": checks[field]})
    def digest_mismatch(repo):
        complete_ledger(repo)
        mutate_receipt(repo, "after_record_sha256", "f" * 64)
    entries.append({"id": "RECORD-DIGEST-MISMATCH", "plan": digest_mismatch, "expected_strict": 1, "expected_check": "after_record_digest"})
    def true_drift(repo):
        complete_ledger(repo)
        data = json.loads((repo / "governance/tasks/T-100.json").read_text(encoding="utf-8"))
        data["evidence"] = "unrecorded rewrite"
        w(repo, "governance/tasks/T-100.json", data)
        commit(repo, "unrecorded rewrite")
    entries.append({"id": "TRUE-DRIFT", "plan": true_drift, "expected_strict": 1, "expected_rule": "POST_HOC_DRIFT", "expected_check": "current_record"})
    def missing_after_drift(repo):
        true_drift(repo)
        mutate_receipt(repo, "after_record", remove=True)
    entries.append({"id": "PAIRED-NO-AFTER-DRIFT", "plan": missing_after_drift, "expected_strict": 1, "expected_check": "after_record_profile"})
    def swamp(repo):
        complete_ledger(repo)
        current = json.loads((repo / "governance/tasks/T-100.json").read_text(encoding="utf-8"))
        before = deepcopy(current)
        current["evidence"] = "new unrecorded scope"
        path, receipt = modern_receipt(repo, before, current, 3, "progress")
        # This matches current yet fails to attach the new receipt to its history.
        current["history"] = before["history"]
        receipt["after_record_sha256"] = record_digest(current)
        w(repo, "governance/tasks/T-100.json", current)
        w(repo, path, receipt)
        commit(repo, "unattached matching anchor")
    entries.append({"id": "UNATTACHED-ANCHOR", "plan": swamp, "expected_strict": 1, "expected_check": "receipt_attached"})
    def hidden(repo):
        complete_ledger(repo, final_state="CLAIMED")
        destination = repo / "evidence/task-operations/hidden"
        destination.mkdir()
        for path in (repo / "evidence/task-operations").glob("*.json"):
            path.rename(destination / path.name)
        commit(repo, "hidden operations")
    entries.append({"id": "PAIRED-HIDDEN-CLAIMED", "plan": hidden, "expected_strict": 1, "expected_check": "adapter_residual"})
    def unexpected_task(repo):
        complete_ledger(repo)
        w(repo, "governance/tasks/DONE-800.json", task("DONE-800"))
        commit(repo, "unexpected task filename")
    entries.append({"id": "UNEXPECTED-TASK", "plan": unexpected_task, "expected_strict": 1, "expected_check": "adapter_residual"})
    def duplicate_sources(repo):
        complete_ledger(repo)
        entry = fp_entry(digest=sha_of(SRC_BYTES), origin="expected-head-blob")
        mutate_receipt(repo, "source_fingerprints", [entry, deepcopy(entry)])
    entries.append({"id": "DUPLICATE-SOURCE-CONTRACT", "plan": duplicate_sources, "expected_strict": 1, "expected_check": "source_contract_set"})
    for field, value, check, label in (
        ("request_id", None, "request_identity", "MISSING-REQUEST-ID"),
        ("intent_sha256", None, "intent_digest", "MISSING-INTENT"),
        ("before_record", None, "before_record_profile", "MISSING-BEFORE"),
        ("before_record", None, "before_record_profile", "NULL-PROGRESS-BEFORE"),
        ("request", [], "request_profile", "NONOBJECT-REQUEST"),
    ):
        def plan(repo, field=field, value=value, label=label):
            complete_ledger(repo)
            mutate_receipt(repo, field, value, remove=label.startswith("MISSING-"))
        entries.append({"id": label, "plan": plan, "expected_strict": 1, "expected_check": check})
    for value, label in (([SRC_REL, SRC_REL], "DUPLICATE-REQUEST-SOURCES"), ([{}], "NONSTRING-REQUEST-SOURCES")):
        def plan(repo, value=value):
            complete_ledger(repo)
            path = f"evidence/task-operations/{IDS[1]}.json"
            data = json.loads((repo / path).read_text(encoding="utf-8"))
            data["request"]["sources"] = value
            w(repo, path, data)
            commit(repo, "mutate request sources")
        entries.append({"id": label, "plan": plan, "expected_strict": 1,
                        "expected_check": "source_contract_set" if label.startswith("DUPLICATE") else "source_list"})
    for mode, check in (("duplicate", "task_profile"), ("missing", "history_receipt"), ("cross-task", "history_receipt")):
        def plan(repo, mode=mode):
            complete_ledger(repo)
            path = "governance/tasks/T-100.json"
            current = json.loads((repo / path).read_text(encoding="utf-8"))
            if mode == "duplicate":
                current["history"].append(deepcopy(current["history"][-1]))
            elif mode == "missing":
                current["history"][-1]["source"] = f"evidence/task-operations/{IDS[2]}.json"
            else:
                current["id"] = "T-200"
                path = "governance/tasks/T-200.json"
            w(repo, path, current)
            commit(repo, "mutate history")
        entries.append({"id": "HISTORY-" + mode.upper(), "plan": plan, "expected_strict": 1, "expected_check": check})
    def repair(repo):
        complete_ledger(repo, final_state="CLAIMED")
        before = json.loads((repo / "governance/tasks/T-100.json").read_text(encoding="utf-8"))
        after = deepcopy(before)
        after.update(evidence="human instructed structural repair", time="2026-09-28T12:00:00Z")
        path, receipt = modern_receipt(repo, before, after, 3, "repair")
        receipt["kind"] = "ec-task-repair"
        receipt.pop("request_id")
        receipt.pop("intent_sha256")
        receipt["request"].pop("request_id")
        w(repo, "governance/tasks/T-100.json", after)
        w(repo, path, receipt)
        commit(repo, "legitimate repair")
    entries.append({"id": "COMPLETE-REPAIR", "plan": repair, "expected_strict": 0})
    def empty_receipt(repo):
        complete_ledger(repo)
        path = f"evidence/task-operations/{IDS[1]}.json"
        w(repo, path, {"task_id": "T-100", "recorded_at": "2026-09-28T11:00:00Z"})
        commit(repo, "empty receipt")
    entries.append({"id": "PAIRED-EMPTY-RECEIPT", "plan": empty_receipt, "expected_strict": 1, "expected_check": "fingerprint_list"})
    for raw, label in ((b'{"task_id":"T-100","task_id":"T-200"}', "DUPLICATE-JSON-KEY"),
                       (b'{"task_id":"T-100","x":NaN}', "NONFINITE-JSON"),
                       (b'{"task_id":"T-100","x":1e999}', "NONFINITE-EXPONENT"),
                       (b'{"task_id":"T-100","request":{"extra":"\\ud800"}}', "LONE-SURROGATE-RECEIPT")):
        def plan(repo, raw=raw):
            complete_ledger(repo)
            w(repo, f"evidence/task-operations/{IDS[1]}.json", raw)
            commit(repo, "malformed JSON")
        entries.append({"id": label, "plan": plan, "expected_strict": 1,
                        "expected_rule": "RECORD_UNPARSEABLE", "expected_check": "record_parse"})
    def migration(repo):
        complete_ledger(repo)
        mutate_receipt(repo, "kind", "ec-task-migration")
    entries.append({"id": "UNSUPPORTED-MIGRATION", "plan": migration, "expected_strict": 1, "expected_check": "receipt_profile"})
    def nonlatest(repo):
        complete_ledger(repo)
        before = json.loads((repo / f"evidence/task-operations/{IDS[0]}.json").read_text(encoding="utf-8"))["after_record"]
        after = deepcopy(before)
        after["evidence"] = "unattached historical operation"
        path, receipt = modern_receipt(repo, before, after, 3, "progress")
        receipt["recorded_at"] = "2026-09-28T09:00:00Z"
        receipt["request"]["at"] = "2026-09-28T09:00:00Z"
        w(repo, path, receipt)
        commit(repo, "unattached older receipt")
    entries.append({"id": "UNATTACHED-NONLATEST", "plan": nonlatest, "expected_strict": 1, "expected_check": "receipt_attached"})
    def reused_id(repo):
        complete_ledger(repo)
        path = f"evidence/task-operations/{IDS[1]}.json"
        receipt = json.loads((repo / path).read_text(encoding="utf-8"))
        receipt["request_id"] = receipt["request"]["request_id"] = IDS[0]
        intent = deepcopy(receipt["request"])
        intent.pop("operation_id")
        intent.pop("at")
        intent["expected"].pop("head")
        intent["summary"].pop("checked_at")
        receipt["intent_sha256"] = record_digest(intent)
        w(repo, path, receipt)
        commit(repo, "reused ordinary request identity")
    entries.append({"id": "DUPLICATE-REQUEST-UUID", "plan": reused_id, "expected_strict": 1, "expected_check": "request_unique"})
    def head_binding(repo):
        complete_ledger(repo)
        path = f"evidence/task-operations/{IDS[1]}.json"
        receipt = json.loads((repo / path).read_text(encoding="utf-8"))
        receipt["request"]["expected"]["head"] = "0" * 40
        w(repo, path, receipt)
        commit(repo, "different request transport anchor")
    entries.append({"id": "EXPECTED-HEAD-BINDING", "plan": head_binding, "expected_strict": 1, "expected_check": "expected_head_binding"})
    for path, label in (("governance/tasks/T-100.json", "LONE-SURROGATE-TASK"),
                        ("governance/github-snapshot.json", "LONE-SURROGATE-SNAPSHOT")):
        def plan(repo, path=path):
            complete_ledger(repo)
            w(repo, path, b'{"extra":"\\ud800"}')
            commit(repo, "invalid Unicode scalar")
        entry = {"id": label, "plan": plan, "expected_strict": 1,
                 "expected_check": "adapter_residual" if label.endswith("SNAPSHOT") else "record_parse"}
        if label.endswith("TASK"):
            entry["expected_rule"] = "RECORD_UNPARSEABLE"
        entries.append(entry)
    if len(entries) != len(EXPECTED_IDS) or {entry["id"] for entry in entries} != EXPECTED_IDS:
        raise ValueError("paired-control set is incomplete or has duplicate identities")
    return entries
