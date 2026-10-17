"""Produce raw release witnesses on hosted CI or in an installed EC environment."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
# Fixture helpers are repository code, but never add src: product imports must
# resolve through the actual editable installation exercised by CI/uv.
sys.path.insert(0, str(ROOT))
from workloads.release_verify.common import (MODES, RAW_NAMES, SCENARIOS, SEEDS,
                                            check_envelope, junit_counts, require, sha)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--os", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--run", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", ""))
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.source), "exact source SHA required")
    out, work = args.out.resolve(), args.work.resolve()
    require(not out.exists() and not work.exists(), "fresh producer paths required")
    out.mkdir(parents=True)
    work.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PYTHON", "PYTEST", "GIT_"))}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_NOSYSTEM="1", GIT_ATTR_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    # Builders inherit the same isolated Git configuration as scan subprocesses.
    for key in list(os.environ):
        if key.startswith("GIT_"):
            del os.environ[key]
    os.environ.update({k: v for k, v in env.items() if k.startswith("GIT_")})
    receipt = {"schema_version": 1, "repository": "taipei49314/ledgerwash",
               "source_sha": args.source, "run_id": args.run, "run_attempt": args.attempt,
               "cell": {"os": args.os, "python": args.python},
               "runtime": {"system": platform.system(), "python": platform.python_version(),
                           "platform": platform.platform(), "executable": sys.executable},
               "epochs": {}, "commands": [], "files": {}, "status": "incomplete"}

    def run(command, cwd=ROOT, seed="1"):
        try:
            return subprocess.run(command, cwd=cwd, env=dict(env, PYTHONHASHSEED=seed),
                                  capture_output=True, timeout=180, check=False)
        except subprocess.TimeoutExpired as exc:
            (out / "timeout.stdout").write_bytes(exc.stdout or b"")
            (out / "timeout.stderr").write_bytes(exc.stderr or b"")
            receipt["timeout"] = {"command": list(map(str, command)), "cwd": str(cwd), "seed": seed}
            raise

    try:
        actual = run(["git", "rev-parse", "HEAD"])
        require(actual.returncode == 0 and actual.stdout.decode().strip() == args.source,
                "checkout source mismatch")
        require(run(["git", "status", "--porcelain"]).stdout == b"", "dirty initial source")
        import ledgerwash
        from ledgerwash.qualify_corpus import build_corpus, build_negspace_corpus
        from tests.test_migration import migration_repo
        require(Path(ledgerwash.__file__).resolve() == ROOT / "src/ledgerwash/__init__.py",
                "installed module is not the candidate source")
        require(ledgerwash.__version__ == "0.5.0" and ledgerwash.SPEC_VERSION == 5,
                "engine version mismatch")
        suite = args.junit.read_bytes()
        receipt["suite"] = junit_counts(suite)
        (out / "suite.xml").write_bytes(suite)
        qualified = run([sys.executable, "-B", "-m", "ledgerwash", "qualify"])
        receipt["qualify"] = {"exit_code": qualified.returncode,
                              "stdout": qualified.stdout.decode("utf-8"),
                              "stderr": qualified.stderr.decode("utf-8")}
        require(qualified.returncode == 0 and b"qualify ok" in qualified.stdout, "qualify failed")
        for case in SCENARIOS:
            parent = work / case
            parent.mkdir()
            if case.startswith("migration-"):
                repo, _, _ = migration_repo(parent, "lf" if case == "migration-lf" else "forged-parent")
                repo = repo.rename(parent / "ledger")
            elif case == "era":
                repo = build_negspace_corpus(parent / "ledger")
            else:
                repo = build_corpus(parent / "ledger", planted=case == "main")
            pin = run(["git", "rev-parse", "HEAD"], cwd=repo)
            require(pin.returncode == 0, "fixture pin missing")
            epoch = pin.stdout.decode("ascii").strip()
            receipt["epochs"][case] = epoch
            for mode in MODES:
                for seed in SEEDS:
                    command = [sys.executable, "-B", "-m", "ledgerwash", "scan",
                               "ledger", "--at", epoch]
                    if mode == "strict":
                        command.append("--require-complete")
                    for transport in ("stdout", "file"):
                        name = f"{case}.{mode}.s{seed}.{transport}.json"
                        destination = out / name
                        invocation = command + (["--out", str(destination)] if transport == "file" else [])
                        process = run(invocation, cwd=parent, seed=seed)
                        receipt["commands"].append({"output": name, "command": invocation,
                                                    "seed": seed, "exit_code": process.returncode,
                                                    "stderr": process.stderr.decode("utf-8", "replace")})
                        if transport == "stdout":
                            destination.write_bytes(process.stdout)
                        else:
                            require(not process.stdout, "--out unexpectedly emitted stdout")
                        raw = destination.read_bytes()
                        expected_code = check_envelope(raw, case, mode, epoch)
                        require(process.returncode == expected_code and not process.stderr,
                                "unexpected scan result")
                    require((out / f"{case}.{mode}.s{seed}.stdout.json").read_bytes()
                            == (out / f"{case}.{mode}.s{seed}.file.json").read_bytes(),
                            "stdout/file bytes differ")
                require((out / f"{case}.{mode}.s1.stdout.json").read_bytes()
                        == (out / f"{case}.{mode}.s17.stdout.json").read_bytes(), "seed bytes differ")
        require(run(["git", "status", "--porcelain"]).stdout == b"", "dirty final source")
        receipt["source_clean"] = True
        receipt["status"] = "pass"
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        for name in (*RAW_NAMES, "suite.xml"):
            if (out / name).is_file():
                raw = (out / name).read_bytes()
                receipt["files"][name] = {"sha256": sha(raw), "bytes": len(raw)}
        (out / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                                          encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
