"""Red-team harness for ledgerwash.

Each case builds a fresh git repo carrying an ec-ledger ledger, applies an
attack mutation, and runs the real `ledgerwash scan` at HEAD. The consumer
gate is the exit code (0 = pass). A weakening that survives as exit 0 is a
bypass. Controls must block.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

LEDGERWASH = ["uv", "run", "--project",
              r"C:\Users\play\.zcode\workspace\default\ledgerwash", "ledgerwash"]
WORK = Path(__file__).parent / "work"

SRC_REL = "evidence/results/analysis.csv"
SRC_BYTES = b"task,verdict\nT-100,PASS\nT-101,PASS\n"


def run(cmd, cwd, timeout=180):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          shell=False, timeout=timeout)


def _rmtree(path: Path):
    import os
    import stat

    def force(func, target, exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=force)


def w(repo: Path, rel: str, data):
    target = repo / rel
    if data is None:
        target.unlink(missing_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        target.write_bytes(data)
    else:
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")


def commit(repo: Path, msg: str, amend=False):
    run(["git", "add", "-A"], repo)
    args = ["git", "commit", "-q", "-m", msg]
    if amend:
        args = ["git", "commit", "-q", "--amend", "-m", msg]
    run(args, repo)


def task(tid, *, state="DONE", status="DONE", time="2026-09-28T12:00:00Z", **extra):
    d = {"schema_version": 1, "status": status, "state": state,
         "time": time, "owner": "agent-7", "title": f"task {tid}"}
    d.update(extra)
    return d


def receipt(tid, *, recorded_at="2026-09-28T10:00:00Z", at="2026-09-28T09:00:00Z",
            before=None, after=None, fps=None, expected_head=None, **extra):
    d = {
        "task_id": tid,
        "recorded_at": recorded_at,
        "request": {"actor": "agent-7", "at": at, "op": "run_analysis"},
        "before_record_sha256": before or "0" * 64,
        "after_record_sha256": after or "1" * 64,
    }
    if fps is not None:
        d["source_fingerprints"] = fps
    if expected_head is not None:
        d["expected_head"] = expected_head
    d.update(extra)
    return d


def fp_entry(source=SRC_REL, digest=None, hf="raw-git-blob-bytes",
             origin="new-utf8-blob-in-containing-commit"):
    return {"hash_format": hf, "origin": origin, "source": source,
            "sha256": digest or "f" * 64}


def sha_of(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def build_repo(case_id: str, plan) -> Path:
    """plan(write, commit_fn, repo) builds the base; returns nothing."""
    repo = WORK / case_id
    if repo.exists():
        _rmtree(repo)
    repo.mkdir(parents=True)
    run(["git", "init", "-q", "-b", "main"], repo)
    run(["git", "config", "user.email", "rt@rt.local"], repo)
    run(["git", "config", "user.name", "rt"], repo)
    run(["git", "config", "core.autocrlf", "false"], repo)
    plan(repo)
    return repo


def scan(repo: Path):
    proc = run(list(LEDGERWASH) + ["scan", str(repo), "--at", "HEAD"], repo)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"raw": (proc.stdout + proc.stderr)[:800]}
    return {
        "exit": proc.returncode,
        "verdict": payload.get("verdict"),
        "findings": [{"rule": f.get("rule"), "severity": f.get("severity")}
                     for f in payload.get("findings", [])],
        "residuals": len(payload.get("residuals", [])),
        "raw": payload.get("raw"),
    }


def std_base(with_fingerprints=True, n_receipts=1, **_):
    """Commit1: sources; Commit2: one DONE task + its receipts (valid digests)."""

    def plan(repo: Path):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        digest = sha_of(SRC_BYTES)
        fps = [fp_entry(digest=digest)] if with_fingerprints else None
        rec = receipt("T-100", fps=fps)
        # self-consistent chain fields
        rec["after_record_sha256"] = sha_of(json.dumps({"task_id": "T-100", "v": 1}))
        w(repo, "governance/tasks/T-100.json", task("T-100"))
        w(repo, "evidence/task-operations/r1.json", rec)
        commit(repo, "ledger")
    return plan


CASES = []


def case(case_id, category, plan, hypothesis, note=""):
    CASES.append({"id": case_id, "category": category, "plan": plan,
                  "hypothesis": hypothesis, "note": note})


def main(selected=None):
    from cases import register, register_more
    register(case, std_base)
    register_more(case, std_base)
    from cases import register_last
    register_last(case, std_base)
    from cases import register_final
    register_final(case, std_base)
    from cases import register_a4c
    register_a4c(case, std_base)
    results = []
    for c in CASES:
        if selected and c["id"] not in selected:
            continue
        repo = build_repo(c["id"], c["plan"])
        result = scan(repo)
        result.update(case=c["id"], category=c["category"],
                      hypothesis=c["hypothesis"], note=c["note"])
        results.append(result)
        rules = "; ".join(f"{f['rule']}({f['severity']})" for f in result["findings"]) or "-"
        flag = "BYPASS" if result["exit"] == 0 else "BLOCK/ERR"
        print(f"{flag:<9} {c['id']:<24} exit={result['exit']} "
              f"verdict={result['verdict']} residuals={result['residuals']}  {rules}")
    out = Path(__file__).parent / "results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n{len(results)} cases -> {out}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
