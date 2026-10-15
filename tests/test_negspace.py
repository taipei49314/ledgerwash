"""Spec 5 negative-space rules: each fires on its plant; carve-outs stay silent.

Fixtures control per-commit git dates so DONE_TIME_BACKDATED's birth
corroboration is exercised in both directions. Frozen-rule behavior is not
re-asserted here except where it interacts with the new rules.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ledgerwash.engine import run_scan
from tests.conftest import by_rule


def git(repo: Path, *args, date: str = "2026-01-01T00:00:00+00:00"):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    proc = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, *args],
                          cwd=repo, env=env, capture_output=True, check=True, timeout=60)
    return proc.stdout


def commit(repo: Path, msg: str, date: str):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD").decode("ascii").strip()


def write(repo: Path, rel: str, value):
    dest = repo / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    dest.write_text(text, encoding="utf-8", newline="\n")


def task(tid: str, *, state: str = "DONE", time: str | None = "2026-06-02T00:00:00Z", **extra):
    data = {"schema_version": 1, "id": tid, "state": state, "status": state,
            "owner": "agent-7", "description": f"task {tid}"}
    if time is not None:
        data["time"] = time
    data.update(extra)
    return data


def receipt(tid: str, *, recorded_at: str | None = "2026-06-01T00:00:00Z", **extra):
    data = {"kind": "ec-task-operation", "schema_version": 2, "task_id": tid,
            "request": {"at": "2026-06-01T00:00:00Z", "actor": "agent-7", "operation": "update"}}
    if recorded_at is not None:
        data["recorded_at"] = recorded_at
    data.update(extra)
    return data


def build(tmp_path: Path, plan) -> dict:
    repo = tmp_path / "ledger"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "ns@ns.invalid")
    git(repo, "config", "user.name", "ns")
    git(repo, "config", "core.autocrlf", "false")
    write(repo, ".gitattributes", "* -text\n")
    plan(repo)
    return run_scan(repo)


# ----------------------------------------------------------- era alive base

def era_base(repo):
    write(repo, "evidence/task-operations/era.json", receipt("T-099"))
    write(repo, "governance/tasks/T-099.json", task("T-099", state="CLAIMED"))
    commit(repo, "era receipt at 2026-01-01 (recorded_at 2026-06-01)",
           date="2026-01-01T00:00:00+00:00")


# ------------------------------------------------- DONE_TIME_UNESTABLISHED

def test_unestablished_missing_empty_redacted_time_fire(tmp_path):
    def plan(repo):
        era_base(repo)
        write(repo, "governance/tasks/T-800.json", task("T-800", time=None))
        write(repo, "governance/tasks/T-801.json", task("T-801", time=""))
        write(repo, "governance/tasks/T-802.json", task("T-802", time="2026-07-27T15:2xZ"))
        write(repo, "governance/tasks/T-803.json", task("T-803", time="yesterday-ish"))
        commit(repo, "done tasks with unusable closure times",
               date="2026-06-02T00:00:00+00:00")
    findings = by_rule(build(tmp_path, plan))["DONE_TIME_UNESTABLISHED"]
    assert [f["locator"] for f in findings] == [
        "T-800:state=DONE", "T-801:state=DONE", "T-802:state=DONE", "T-803:state=DONE",
    ]
    assert all(f["severity"] == "high" for f in findings)


def test_unestablished_requires_loaded_receipts(tmp_path):
    """Zero loaded receipts keeps residual semantics (SPEC §3): no finding."""

    def plan(repo):
        write(repo, "governance/tasks/T-800.json", task("T-800", time=None))
        commit(repo, "done task, no receipt system", date="2026-01-01T00:00:00+00:00")
    envelope = build(tmp_path, plan)
    assert envelope["findings"] == []
    assert any("no operation receipts" in r["reason"] for r in envelope["residuals"])


def test_unestablished_leaves_receipt_backed_tasks_alone(tmp_path):
    def plan(repo):
        era_base(repo)
        write(repo, "governance/tasks/T-800.json", task("T-800", time=None))
        write(repo, "evidence/task-operations/r800.json", receipt("T-800"))
        commit(repo, "receipt-backed done task", date="2026-06-02T00:00:00+00:00")
    assert build(tmp_path, plan)["findings"] == []


# ---------------------------------------------------- DONE_TIME_BACKDATED

def test_backdated_fires_when_birth_contradicts_pre_system_claim(tmp_path):
    def plan(repo):
        era_base(repo)
        write(repo, "governance/tasks/T-800.json", task("T-800", time="2025-01-01T00:00:00Z"))
        commit(repo, "backdated done task born inside the receipt era",
               date="2026-06-02T00:00:00+00:00")
    findings = by_rule(build(tmp_path, plan))["DONE_TIME_BACKDATED"]
    (finding,) = findings
    assert finding["severity"] == "high"
    assert finding["locator"] == "T-800:state=DONE"
    assert "2025-01-01T00:00:00Z" in finding["message"]
    assert "2026-06-02" in finding["message"]
    assert "NO_OPERATION_HISTORY" not in by_rule(build(tmp_path, plan))  # era carve-out holds


def test_backdated_carve_out_for_genuine_legacy(tmp_path):
    """File born before the first receipt: the pre-system claim stands, silent."""

    def plan(repo):
        write(repo, "governance/tasks/T-800.json", task("T-800", time="2025-01-01T00:00:00Z"))
        commit(repo, "legacy task born pre-receipt-system", date="2025-06-01T00:00:00+00:00")
        era_base(repo)
    envelope = build(tmp_path, plan)
    assert envelope["findings"] == []


def test_backdated_inera_close_stays_noh_territory(tmp_path):
    """Usable in-era closure time: NO_OPERATION_HISTORY fires, BACKDATED must not."""

    def plan(repo):
        era_base(repo)
        write(repo, "governance/tasks/T-800.json", task("T-800", time="2026-07-01T00:00:00Z"))
        commit(repo, "in-era done task", date="2026-07-02T00:00:00+00:00")
    rules = by_rule(build(tmp_path, plan))
    assert [f["locator"] for f in rules["NO_OPERATION_HISTORY"]] == ["T-800:state=DONE"]
    assert "DONE_TIME_BACKDATED" not in rules


# ---------------------------------------------------- ERA_UNDETERMINABLE

def test_era_undeterminable_fires_once_and_noh_stays_silent(tmp_path):
    def plan(repo):
        write(repo, "governance/tasks/T-800.json", task("T-800", time="2026-07-01T00:00:00Z"))
        write(repo, "evidence/task-operations/rn1.json", receipt("T-801", recorded_at=""))
        write(repo, "evidence/task-operations/rn2.json", receipt("T-801", recorded_at=None))
        write(repo, "governance/tasks/T-801.json", task("T-801", state="CLAIMED"))
        commit(repo, "era-dead ledger", date="2026-01-01T00:00:00+00:00")
    rules = by_rule(build(tmp_path, plan))
    (era,) = rules["ERA_UNDETERMINABLE"]
    assert era["severity"] == "warn"
    assert era["locator"] == "ledger"
    assert "NO_OPERATION_HISTORY" not in rules  # era death must not become a false NOH wave
    assert "DONE_TIME_UNESTABLISHED" not in rules  # T-800 has a usable time


def test_era_undeterminable_silent_when_a_receipt_is_dated(tmp_path):
    def plan(repo):
        era_base(repo)
        write(repo, "governance/tasks/T-800.json", task("T-800", time=None))
        commit(repo, "mixed receipts", date="2026-06-02T00:00:00+00:00")
    rules = by_rule(build(tmp_path, plan))
    assert "ERA_UNDETERMINABLE" not in rules
    assert [f["locator"] for f in rules["DONE_TIME_UNESTABLISHED"]] == ["T-800:state=DONE"]


# --------------------------------------------------------- RECEIPT_ORPHAN

def test_receipt_orphan_fires_and_empty_ids_stay_residuals(tmp_path):
    def plan(repo):
        era_base(repo)
        write(repo, "evidence/task-operations/orphan.json", receipt("T-999"))
        ghost = receipt("T-800")
        ghost["task_id"] = ""
        write(repo, "evidence/task-operations/empty-id.json", ghost)
        typed = receipt("T-800")
        typed["task_id"] = 7
        write(repo, "evidence/task-operations/typed-id.json", typed)
        commit(repo, "orphaned receipt", date="2026-06-02T00:00:00+00:00")
    envelope = build(tmp_path, plan)
    rules = by_rule(envelope)
    (orphan,) = rules["RECEIPT_ORPHAN"]
    assert orphan["severity"] == "warn"
    assert orphan["path"].endswith("orphan.json")
    assert orphan["locator"] == "orphan.json"
    assert not [f for f in rules.get("RECEIPT_ORPHAN", []) if f["path"].endswith(("empty-id.json", "typed-id.json"))]
    assert any(r["reason"] == "receipt has no string task_id" and r["path"].endswith("typed-id.json")
               for r in envelope["residuals"])


# ---------------------------------------------------------- PIN_NOT_COMMIT

def test_pin_not_commit_fires_on_existing_blob_and_tree_pins(tmp_path):
    def plan(repo):
        write(repo, "evidence/notes/note.md", "note bytes\n")
        commit(repo, "note", date="2026-01-01T00:00:00+00:00")
        blob = git(repo, "rev-parse", "HEAD:evidence/notes/note.md").decode().strip()
        tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
        era_base(repo)
        write(repo, "evidence/task-operations/rblob.json",
              receipt("T-800", expected_head=blob))
        write(repo, "governance/tasks/T-800.json", task("T-800"))
        write(repo, "evidence/task-operations/rtree.json",
              receipt("T-801", expected_head=tree))
        write(repo, "governance/tasks/T-801.json", task("T-801"))
        commit(repo, "non-commit expected_head pins", date="2026-06-02T00:00:00+00:00")
    rules = by_rule(build(tmp_path, plan))
    kinds = sorted(f["message"].split()[5] for f in rules["PIN_NOT_COMMIT"])
    assert kinds == ["blob", "tree"]
    assert all(f["severity"] == "warn" for f in rules["PIN_NOT_COMMIT"])
    assert "PIN_LOCAL_MISSING" not in rules


def test_pin_not_commit_keeps_missing_and_commit_pins_frozen(tmp_path):
    def plan(repo):
        era_base(repo)
        head = git(repo, "rev-parse", "HEAD").decode().strip()
        write(repo, "evidence/task-operations/rdead.json",
              receipt("T-800", expected_head="9" * 40))
        write(repo, "governance/tasks/T-800.json", task("T-800"))
        write(repo, "evidence/task-operations/rlive.json",
              receipt("T-099", expected_head=head))
        commit(repo, "dead and live pins", date="2026-06-02T00:00:00+00:00")
    rules = by_rule(build(tmp_path, plan))
    assert [f["rule"] for f in rules["PIN_LOCAL_MISSING"]] == ["PIN_LOCAL_MISSING"]
    assert "PIN_NOT_COMMIT" not in rules


# ------------------------------------------------- frozen-rule interaction

def test_planted_corpus_negspace_matrix(mini_envelope, negspace_envelope):
    """The qualify corpora carry the frozen spec 5 plants (docs/redteam/spec5-PREREG.md)."""
    mini = by_rule(mini_envelope)
    assert sorted(f["locator"] for f in mini["DONE_TIME_BACKDATED"]) == ["T-912:state=DONE"]
    assert sorted(f["locator"] for f in mini["DONE_TIME_UNESTABLISHED"]) == [
        "T-910:state=DONE", "T-914:state=DONE",
    ]
    assert [f["locator"] for f in mini["RECEIPT_ORPHAN"]] == ["r915.json"]
    assert [f["rule"] for f in mini["PIN_NOT_COMMIT"]] == ["PIN_NOT_COMMIT"]
    assert "ERA_UNDETERMINABLE" not in mini
    ns = by_rule(negspace_envelope)
    assert [f["locator"] for f in ns["ERA_UNDETERMINABLE"]] == ["ledger"]
    assert sorted(f["locator"] for f in ns["DONE_TIME_UNESTABLISHED"]) == ["T-800:state=DONE"]
    assert [f["locator"] for f in ns["RECEIPT_ORPHAN"]] == ["rn3.json"]
    assert "NO_OPERATION_HISTORY" not in ns
    assert "DONE_TIME_BACKDATED" not in ns


def test_commit_dates_reader_is_deterministic(tmp_path):
    def plan(repo):
        write(repo, "a.txt", "a\n")
        commit(repo, "first", date="2025-06-01T12:34:56+00:00")
        era_base(repo)
    repo = tmp_path / "ledger"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "ns@ns.invalid")
    git(repo, "config", "user.name", "ns")
    git(repo, "config", "core.autocrlf", "false")
    plan(repo)
    from ledgerwash.epoch import Epoch

    epoch = Epoch(repo)
    births = epoch.birth_map("governance/tasks")
    dates = epoch.commit_dates(births.values())
    assert dates[births["governance/tasks/T-099.json"]] == "2026-01-01T00:00:00+00:00"
    assert set(epoch.object_types(births.values())) == set(births.values())
