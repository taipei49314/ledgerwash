"""Exact-source red-team and coverage acceptance through the approved EC pool."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = {"pytest", "colorama", "iniconfig", "packaging", "pluggy", "pygments"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    for key in ("EC_WORKLOAD_SOURCE", "EC_WORKLOAD_OUT", "EC_WORKLOAD_WORK", "EC_WORKLOAD_SHA"):
        if not os.environ.get(key):
            raise RuntimeError("run only through the approved EC pool workload")
    if (os.environ.get("EC_WORKLOAD_REPOSITORY") != "taipei49314/ledgerwash"
            or os.environ.get("EC_WORKLOAD_NAME") != "redteam-verify"
            or Path(os.environ["EC_WORKLOAD_SOURCE"]).resolve() != ROOT):
        raise RuntimeError("unexpected workload identity")
    expected = os.environ["EC_WORKLOAD_SHA"]
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise RuntimeError("an exact reviewed source SHA is required")
    out = Path(os.environ["EC_WORKLOAD_OUT"]).resolve()
    work = Path(os.environ["EC_WORKLOAD_WORK"]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join((str(ROOT / "src"), str(ROOT))),
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_PLUGINS", None)
    steps = []
    problems = []

    def run(name, command, *, seed="1", timeout=300):
        started = time.monotonic()
        timed_out = False
        try:
            process = subprocess.run(command, cwd=ROOT, env=dict(env, PYTHONHASHSEED=seed),
                                     capture_output=True, timeout=timeout, check=False)
            code, stdout, stderr = process.returncode, process.stdout, process.stderr
        except subprocess.TimeoutExpired as exc:
            code, timed_out, stdout, stderr = 2, True, exc.stdout or b"", exc.stderr or b""
        except OSError as exc:
            code, stdout, stderr = 2, b"", str(exc).encode("utf-8")
        (out / f"{name}.stdout").write_bytes(stdout)
        (out / f"{name}.stderr").write_bytes(stderr)
        steps.append({"name": name, "command": command, "exit_code": code,
                      "elapsed_seconds": round(time.monotonic() - started, 3),
                      "timed_out": timed_out, "pythonhashseed": seed,
                      "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr)})
        return code, stdout, stderr

    code, source, _ = run("source", ["git", "rev-parse", "--verify", "HEAD"])
    actual = source.decode("ascii", "replace").strip()
    if code or actual != expected:
        problems.append("source SHA mismatch or unreadable source")
    code, status, _ = run("clean-source", ["git", "status", "--porcelain", "-z"])
    if code or status:
        problems.append("source checkout is not clean")

    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    equality = None
    lock = ROOT / "uv.lock"
    lock_bytes = None
    requirements = []
    if not problems:
        try:
            lock_bytes = lock.read_bytes()
            packages = tomllib.loads(lock_bytes.decode("utf-8"))["package"]
            selected = [p for p in packages if p["name"] in DEPENDENCIES]
            if {p["name"] for p in selected} != DEPENDENCIES or len(selected) != len(DEPENDENCIES):
                raise ValueError("dependency lock does not contain the six expected packages")
            for package in sorted(selected, key=lambda p: p["name"]):
                wheels = package["wheels"]
                if len(wheels) != 1 or not wheels[0]["url"].endswith("-none-any.whl"):
                    raise ValueError("expected one pure-Python wheel per dependency")
                wheel = wheels[0]
                if not wheel["url"].startswith("https://files.pythonhosted.org/packages/"):
                    raise ValueError("unexpected wheel host")
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", wheel["hash"]):
                    raise ValueError("expected SHA-256 wheel hash")
                requirements.append(f"{package['name']} @ {wheel['url']} --hash={wheel['hash']}")
            req = work / "requirements.txt"
            req.write_text("\n".join(requirements) + "\n", encoding="utf-8", newline="\n")
            (out / "requirements.txt").write_bytes(req.read_bytes())
        except (OSError, ValueError, KeyError, TypeError) as exc:
            problems.append(f"dependency lock invalid: {exc}")

    python = work / "venv" / "Scripts" / "python.exe"
    if not problems:
        code, _, _ = run("venv", [sys.executable, "-I", "-B", "-m", "venv", str(work / "venv")])
        if code:
            problems.append("isolated venv creation failed")
    if not problems:
        code, _, _ = run("dependencies", [str(python), "-I", "-B", "-m", "pip", "install",
            "--isolated", "--disable-pip-version-check", "--no-cache-dir", "--no-deps",
            "--require-hashes", "--only-binary=:all:", "-r", str(work / "requirements.txt")])
        if code:
            problems.append("hash-pinned dependency installation failed")

    if not problems:
        command = [str(python), "-X", "utf8", "-B"]
        code, _, _ = run("suite", command + ["-m", "pytest", "tests", "-p", "no:cacheprovider",
            "--basetemp", str(work / "pytest"), "--junitxml", str(out / "suite.xml")])
        try:
            cases = ET.parse(out / "suite.xml").getroot().findall(".//testcase")
            counts = {"tests": len(cases),
                      "failures": sum(c.find("failure") is not None for c in cases),
                      "errors": sum(c.find("error") is not None for c in cases),
                      "skipped": sum(c.find("skipped") is not None for c in cases)}
        except (OSError, ET.ParseError) as exc:
            problems.append(f"JUnit missing or unreadable: {exc}")
        if code or not counts["tests"] or any(counts[k] for k in ("failures", "errors", "skipped")):
            problems.append("suite failed, ran zero tests or skipped tests")
        code, stdout, _ = run("qualify", command + ["-m", "ledgerwash", "qualify"])
        if code or b"qualify ok:" not in stdout:
            problems.append("qualify failed or did not confirm planted rule coverage")
        corpus = work / "replay-ledger"
        builder = ("from pathlib import Path; from ledgerwash.qualify_corpus import build_corpus; "
                   "import sys; build_corpus(Path(sys.argv[1]))")
        code, _, _ = run("replay-fixture", command + ["-c", builder, str(corpus)])
        if code:
            problems.append("replay fixture creation failed")
        else:
            code, pin, _ = run("replay-pin", ["git", "-C", str(corpus), "rev-parse", "HEAD"])
            epoch = pin.decode("ascii", "replace").strip()
            if code or not re.fullmatch(r"[0-9a-f]{40}", epoch):
                problems.append("replay fixture pin unavailable")
            else:
                scan = command + ["-m", "ledgerwash", "scan", str(corpus), "--at", epoch]
                c1, first, _ = run("replay-seed1", scan, seed="1")
                c2, second, _ = run("replay-seed17", scan, seed="17")
                equality = c1 == c2 == 1 and bool(first) and first == second
                try:
                    envelope = json.loads(first)
                    equality = equality and envelope["run"]["epoch"] == epoch
                    equality = equality and envelope["verdict"] == "block"
                    equality = equality and len({f["rule"] for f in envelope["findings"]}) == 14
                except (ValueError, KeyError, TypeError):
                    equality = False
                if not equality:
                    problems.append("independent process scan replay differs or lacks all 14 planted rules")
        code, _, _ = run("redteam", command + ["-m", "tests.redteam.replay",
            "--out", str(out / "redteam"), "--work", str(work / "redteam"),
            "--candidate-sha", expected], timeout=900)
        if code:
            problems.append("redteam controls, full case set or raw replay failed")
        code, final, _ = run("final-source", ["git", "rev-parse", "--verify", "HEAD"])
        if code or final.decode("ascii", "replace").strip() != expected:
            problems.append("validation changed the source SHA")
        code, status, _ = run("final-status", ["git", "status", "--porcelain", "-z"])
        if code or status:
            problems.append("validation changed the source checkout")

    result = {"schema_version": 1, "task": "LW-002", "requested_sha": expected,
              "actual_sha": actual, "runtime": {"python": sys.version, "platform": platform.platform()},
              "uv_lock_sha256": digest(lock_bytes) if lock_bytes is not None else None,
              "requirements": requirements,
              "steps": steps, "suite": counts, "raw_json_equal": equality,
              "test_sources_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes())
                                      for p in sorted((ROOT / "tests").rglob("*.py"))},
              "passed": not problems, "problems": problems,
              "limitations": ["one EC Windows Python runtime; no new cross-OS matrix claim",
                              "synthetic regressions; no artifact authenticity or model accuracy claim"]}
    with (out / "result.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    lines = ["# ledgerwash red-team acceptance", "", f"Result: {'FAIL' if problems else 'PASS'}", "",
             f"Source: `{actual}` (requested `{expected}`)", f"Suite: {counts}",
             f"Raw replay JSON equal: {equality}", "", "Evidence: result.json, suite.xml and raw logs.", ""]
    lines += [f"- {problem}" for problem in problems]
    lines += ["", "Scope: one EC Windows runtime, all tests and frozen A1-A9 gates.",
              "Artifact authenticity and cross-platform replay remain unassessed.", ""]
    (out / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
