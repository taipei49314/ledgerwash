"""Isolated CLI replay, recording all case outputs and exact judge/fixture identities."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from tests.redteam.harness import build_repo, original_cases

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def baseline_source(work):
    manifest = json.loads((ROOT / "tests/redteam/baseline.json").read_text(encoding="utf-8"))
    archive = ROOT / manifest["archive"]
    if sha(archive.read_bytes()) != manifest["archive_sha256"]:
        raise ValueError("baseline source archive hash mismatch")
    destination = work / "baseline"
    destination.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            relative = Path(member.filename)
            allowed = member.filename == "src/" or member.filename.startswith("src/ledgerwash/")
            if relative.is_absolute() or ".." in relative.parts or not allowed:
                raise ValueError("unexpected baseline source archive member")
        zipped.extractall(destination)
    return destination / "src", manifest["judge_sha"]


def scan(repo, epoch, source, judge_sha, out, label, *, seed="1", strict=False, timeout=120):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("PYTHON") and not key.startswith("PYTEST")}
    env.update(PYTHONPATH=str(source), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PYTHONHASHSEED=seed, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    identity_path = out / f"{label}.judge.json"
    wrapper = (
        "import json,pathlib,runpy,sys,ledgerwash; "
        "actual=pathlib.Path(ledgerwash.__file__).resolve(); "
        "expected=pathlib.Path(sys.argv[1]).resolve()/'ledgerwash'/'__init__.py'; "
        "assert actual==expected, 'judge source import mismatch'; "
        "pathlib.Path(sys.argv[2]).write_text(json.dumps({'file':str(actual),"
        "'version':ledgerwash.__version__,'spec':ledgerwash.SPEC_VERSION}),encoding='utf-8'); "
        "sys.argv=['ledgerwash',*sys.argv[3:]]; runpy.run_module('ledgerwash',run_name='__main__')"
    )
    command = [sys.executable, "-X", "utf8", "-B", "-c", wrapper, str(source),
               str(identity_path), "scan", str(repo), "--at", epoch]
    if strict:
        command += ["--require-complete"]
    try:
        process = subprocess.run(command, cwd=repo.parent, env=env, capture_output=True, timeout=timeout)
        code, stdout, stderr, timed_out = process.returncode, process.stdout, process.stderr, False
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr, timed_out = 2, exc.stdout or b"", exc.stderr or b"", True
    (out / f"{label}.stdout").write_bytes(stdout)
    (out / f"{label}.stderr").write_bytes(stderr)
    result = {"judge_sha": judge_sha, "judge_source": str(source), "fixture_sha": epoch,
              "command": command, "exit_code": code, "timed_out": timed_out,
              "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr), "seed": seed}
    try:
        envelope = json.loads(stdout)
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        result.update(verdict=envelope["verdict"], run=envelope["run"],
                      findings=envelope["findings"], residuals=envelope["residuals"],
                      coverage=envelope.get("coverage"), judge_identity=identity)
        if (envelope["run"]["epoch"] != epoch or code not in (0, 1)
                or (code == 0) != (envelope["verdict"] == "pass")
                or identity["version"] != envelope["run"]["ledgerwash_version"]
                or identity["spec"] != envelope["run"]["spec_version"]):
            raise ValueError("epoch mismatch or engine error")
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, OSError) as exc:
        result["error"] = str(exc)
    return result


def replay(out, work, *, candidate_sha=None):
    out.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    baseline, pinned = baseline_source(work)
    judges = [("baseline", baseline, pinned)]
    if candidate_sha:
        judges.append(("candidate", ROOT / "src", candidate_sha))
    records, problems = [], []
    for case in original_cases():
        repo = work / case["id"]
        epoch = build_repo(repo, case["plan"])
        item = {"case": case["id"], "category": case["category"], "fixture_sha": epoch, "judges": {}}
        for name, source, judge_sha in judges:
            first = scan(repo, epoch, source, judge_sha, out, f"{case['id']}-{name}-seed1")
            second = scan(repo, epoch, source, judge_sha, out, f"{case['id']}-{name}-seed17", seed="17")
            first["raw_replay_equal"] = (first["stdout_sha256"] == second["stdout_sha256"]
                                          and first["exit_code"] == second["exit_code"])
            item["judges"][name] = first
            if first.get("error") or second.get("error") or not first["raw_replay_equal"]:
                problems.append(f"{case['id']}/{name}: engine error, malformed output or nondeterminism")
            if case["category"] == "control" and (first["exit_code"] != 1 or first.get("verdict") != "block"):
                problems.append(f"{case['id']}/{name}: positive block control failed")
        records.append(item)
    baseline_pass = sum(item["judges"]["baseline"]["exit_code"] == 0 for item in records)
    if baseline_pass != 17:
        problems.append(f"baseline expected 17 pass and 4 block, got {baseline_pass} pass")
    a4c = next(item for item in records if item["case"] == "A4C-OPEN-TASK-HIDDEN")
    if not any(f["rule"] == "STATUS_STATE_MISMATCH" for f in a4c["judges"]["baseline"].get("findings", [])):
        problems.append("A4C expected visible status mismatch warning")
    a4b = next(item for item in records if item["case"].startswith("A4B-"))
    if (a4b["judges"]["baseline"]["exit_code"] != 1 or not any(
            f["rule"] == "NO_OPERATION_HISTORY" for f in a4b["judges"]["baseline"].get("findings", []))):
        problems.append("A4B expected explicit NO_OPERATION_HISTORY block")
    result = {"schema_version": 1, "original_case_count": len(records), "baseline_sha": pinned,
              "candidate_sha": candidate_sha, "baseline_pass": baseline_pass,
              "baseline_block": len(records) - baseline_pass, "cases": records,
              "passed": not problems, "problems": problems,
              "meaning": "harness controls and reproducibility passed, not all attacks detected"}
    (out / "results.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--candidate-sha")
    args = parser.parse_args()
    result = replay(args.out.resolve(), args.work.resolve(), candidate_sha=args.candidate_sha)
    print(json.dumps({key: result[key] for key in ("original_case_count", "baseline_pass", "baseline_block", "passed", "problems")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
