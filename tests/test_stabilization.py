"""v0.3 regressions: immutable epochs, strict drift and unorderable receipts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

import pytest

from ledgerwash.adapters import ec_ledger
from ledgerwash.cli import main
from ledgerwash.engine import run_scan
from ledgerwash.epoch import Epoch

TASK = "governance/tasks/T-1.json"
RECEIPT = "evidence/task-operations/receipt.json"
NOTE = "evidence/notes/result.txt"


def git(repo, *args):
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
               GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
    return subprocess.run(
        ["git", "-c", "user.name=fixture", "-c", "user.email=t@t.invalid",
         "-c", "core.autocrlf=false", *args],
        cwd=repo, env=env, check=True, capture_output=True,
    ).stdout.decode("utf-8").strip()


def write(repo, path, value):
    dest = repo / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True) + "\n"
    dest.write_text(text, encoding="utf-8", newline="\n")


def commit(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def task_record():
    return {"schema_version": 1, "id": "T-1", "state": "CLAIMED",
            "status": "CLAIMED", "owner": "HOST", "time": "2026-01-01T00:00:00Z"}


def receipt_record(task, *, note="result v1\n"):
    return {
        "task_id": "T-1", "recorded_at": "2026-01-01T00:00:01Z",
        "request": {"at": "2026-01-01T00:00:00Z", "actor": "HOST"},
        "after_record": task,
        "source_fingerprints": [{
            "source": NOTE, "sha256": hashlib.sha256(note.encode()).hexdigest(),
            "hash_format": "raw-git-blob-bytes",
            "origin": "new-utf8-blob-in-containing-commit",
        }],
    }


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "ledger"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    write(repo, ".gitattributes", "* -text\n")
    task = task_record()
    write(repo, TASK, task)
    write(repo, NOTE, "result v1\n")
    write(repo, RECEIPT, receipt_record(task))
    commit(repo, "birth")
    return repo


@pytest.mark.parametrize("ref", ["main", None])
def test_epoch_keeps_resolved_tree_and_history_after_ref_moves(repo, ref):
    epoch = Epoch(repo, ref)
    birth = epoch.sha
    write(repo, NOTE, "result v2\n")
    write(repo, "docs/new/added.md", "later\n")
    write(repo, "evidence/task-operations/later.json", receipt_record(task_record()))
    commit(repo, "move ref")
    assert epoch.read_bytes(NOTE) == b"result v1\n"
    assert epoch.read_text(NOTE) == "result v1\n"
    assert epoch.list_dir("evidence/task-operations") == ["receipt.json"]
    assert "docs/new/added.md" not in epoch.tree_files()
    assert "docs/new" not in epoch.tree_dirs()
    assert not epoch.path_exists("docs/new")
    assert epoch.birth_map("evidence/task-operations") == {RECEIPT: birth}


def test_scan_pins_before_adapter_reads_even_if_branch_moves(repo, monkeypatch):
    birth = git(repo, "rev-parse", "HEAD")
    original_load = ec_ledger.load

    def move_then_load(epoch):
        write(repo, TASK, {**task_record(), "state": "DONE", "status": "DONE"})
        write(repo, "docs/after-pin.md", "later\n")
        commit(repo, "move during scan")
        return original_load(epoch)

    monkeypatch.setattr(ec_ledger, "load", move_then_load)
    envelope = run_scan(repo, ref="main")
    assert envelope["run"]["epoch"] == birth
    assert envelope["findings"] == []
    assert envelope["residuals"] == []


def test_receipt_birth_on_nonchecked_out_branch(repo):
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-b", "reviewed")
    other = "evidence/task-operations/branch.json"
    write(repo, "evidence/notes/branch.txt", "branch evidence\n")
    receipt = receipt_record(task_record())
    receipt["source_fingerprints"] = [{
        "source": "evidence/notes/branch.txt",
        "sha256": hashlib.sha256(b"branch evidence\n").hexdigest(),
        "hash_format": "raw-git-blob-bytes", "origin": "new-utf8-blob-in-containing-commit",
    }]
    write(repo, other, receipt)
    branch = commit(repo, "branch birth")
    git(repo, "checkout", "main")
    assert git(repo, "rev-parse", "HEAD") == base
    assert Epoch(repo, branch).birth_map("evidence/task-operations")[other] == branch
    envelope = run_scan(repo, ref=branch)
    assert envelope["findings"] == []
    assert envelope["residuals"] == []


def test_recreated_receipt_uses_its_new_birth(repo):
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "rm", RECEIPT)
    commit(repo, "remove receipt")
    note = "result v2\n"
    write(repo, NOTE, note)
    write(repo, RECEIPT, receipt_record(task_record(), note=note))
    new = commit(repo, "recreate receipt")
    assert Epoch(repo).birth_map("evidence/task-operations")[RECEIPT] == new
    assert Epoch(repo, old).birth_map("evidence/task-operations")[RECEIPT] == old
    assert run_scan(repo)["findings"] == []
    assert run_scan(repo, ref=old)["findings"] == []


def test_renamed_receipt_has_birth_for_new_path(repo):
    renamed = "evidence/task-operations/renamed.json"
    git(repo, "mv", RECEIPT, renamed)
    new = commit(repo, "rename receipt")
    assert Epoch(repo).birth_map("evidence/task-operations")[renamed] == new
    envelope = run_scan(repo)
    assert envelope["findings"] == []
    assert envelope["residuals"] == []


@pytest.mark.parametrize("before,after", [([1], [True]), ([[1]], [[True]]),
                                        ([{"value": 1}], [{"value": True}])])
def test_nested_type_drift_reports_high_instead_of_crashing(repo, before, after, capsys):
    original = {**task_record(), "values": before}
    write(repo, TASK, original)
    write(repo, RECEIPT, receipt_record(original))
    commit(repo, "record nested values")
    write(repo, TASK, {**original, "values": after})
    commit(repo, "coerce values")
    assert main(["scan", str(repo)]) == 1
    envelope = json.loads(capsys.readouterr().out)
    drift = [f for f in envelope["findings"] if f["rule"] == "POST_HOC_DRIFT"]
    assert len(drift) == 1
    assert drift[0]["severity"] == "high"
    assert "values" in drift[0]["message"]
    assert drift[0]["before"] != drift[0]["after"]


@pytest.mark.parametrize("stamp,rule", [(None, None), ("", None),
    ("broken", "TIMESTAMP_MALFORMED"), ("2026-01-01T00:0xZ", "TIMESTAMP_REDACTED")])
def test_unorderable_receipt_skips_entire_task_chain_and_anchor(repo, stamp, rule):
    task = task_record()
    first = receipt_record({**task, "owner": "previous"})
    first.update(recorded_at="2026-01-01T00:00:01Z", after_record_sha256="a" * 64)
    middle = receipt_record(task)
    middle.update(recorded_at=stamp, before_record_sha256="a" * 64,
                  after_record_sha256="b" * 64)
    last = receipt_record({**task, "owner": "outdated"})
    last.update(recorded_at="2026-01-01T00:00:03Z", before_record_sha256="b" * 64)
    write(repo, RECEIPT, first)
    write(repo, "evidence/task-operations/middle.json", middle)
    write(repo, "evidence/task-operations/last.json", last)
    commit(repo, "unknown ordering")
    envelope = run_scan(repo)
    rules = {f["rule"] for f in envelope["findings"]}
    assert "CHAIN_BREAK" not in rules
    assert "POST_HOC_DRIFT" not in rules
    if rule:
        assert rule in rules
    assert any(r["path"].endswith("middle.json") and "ordering" in r["reason"]
               for r in envelope["residuals"])
    # A separate task with complete timestamps must still expose a real break/drift.
    second = {**task, "id": "T-2"}
    write(repo, "governance/tasks/T-2.json", second)
    write(repo, "evidence/task-operations/a2.json", {
        "task_id": "T-2", "recorded_at": "2026-01-01T00:00:01Z",
        "after_record_sha256": "c" * 64,
    })
    write(repo, "evidence/task-operations/b2.json", {
        "task_id": "T-2", "recorded_at": "2026-01-01T00:00:02Z",
        "before_record_sha256": "d" * 64, "after_record": {**second, "owner": "old"},
    })
    commit(repo, "independent task")
    findings = run_scan(repo)["findings"]
    assert any(f["rule"] == "CHAIN_BREAK" and f["locator"].startswith("T-2:") for f in findings)
    assert any(f["rule"] == "POST_HOC_DRIFT" and f["locator"].startswith("T-2:") for f in findings)


@pytest.mark.parametrize("task_id", [None, 0, True, [], {}])
def test_nonstring_receipt_task_id_is_residual_without_crash(repo, task_id):
    receipt = receipt_record(task_record())
    receipt["task_id"] = task_id
    write(repo, RECEIPT, receipt)
    commit(repo, "malformed task id")
    envelope = run_scan(repo)
    assert {"path": RECEIPT, "reason": "receipt has no string task_id"} in envelope["residuals"]
    signing = next(o for o in envelope["observations"] if o["kind"] == "self_signing")
    assert signing["actor_equals_owner"] == {"same": 0, "differ": 0}


def test_missing_receipt_task_id_is_residual(repo):
    receipt = receipt_record(task_record())
    del receipt["task_id"]
    write(repo, RECEIPT, receipt)
    commit(repo, "missing task id")
    envelope = run_scan(repo)
    assert {"path": RECEIPT, "reason": "receipt has no string task_id"} in envelope["residuals"]
