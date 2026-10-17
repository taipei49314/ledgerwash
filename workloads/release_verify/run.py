"""EC release verification: authenticate transported ZIPs, compare, install, replay."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from workloads.release_verify.common import (OS_NAMES, PYTHONS, RAW_NAMES, REPOSITORY,
                                            check_cell, check_metadata, compare_cells,
                                            loads, read_zip, require, sha)


def main():
    require(os.environ.get("EC_WORKLOAD_REPOSITORY") == REPOSITORY
            and os.environ.get("EC_WORKLOAD_NAME") == "release-verify"
            and Path(os.environ["EC_WORKLOAD_SOURCE"]).resolve() == ROOT, "workload identity")
    source = os.environ["EC_WORKLOAD_SHA"]
    out, work = (Path(os.environ[key]).resolve() for key in ("EC_WORKLOAD_OUT", "EC_WORKLOAD_WORK"))
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PYTHON", "PYTEST", "UV_", "PIP_")) and k != "VIRTUAL_ENV"}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    report = {"source_sha": source, "status": "incomplete", "steps": [],
              "limitations": ["GitHub-hosted producers plus one EC Windows verifier",
                              "artifact API does not directly expose job ID or attempt",
                              "no ledger execution authenticity or PyPI publication claim"]}

    def command(name, args, *, cwd=ROOT, timeout=600):
        timed_out = False
        try:
            process = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False)
            stdout, stderr, code = process.stdout, process.stderr, process.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, code = exc.stdout or b"", exc.stderr or b"", None
            timed_out = True
        (out / (name + ".stdout")).write_bytes(stdout)
        (out / (name + ".stderr")).write_bytes(stderr)
        report["steps"].append({"name": name, "command": list(map(str, args)),
                                "exit_code": code, "timed_out": timed_out,
                                "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr)})
        require(not timed_out and code == 0, f"command failed: {name}; timeout={timed_out}")
        return stdout

    def api(suffix, name):
        request = urllib.request.Request("https://api.github.com/repos/" + REPOSITORY + suffix,
                                         headers={"Accept": "application/vnd.github+json",
                                                  "X-GitHub-Api-Version": "2022-11-28",
                                                  "User-Agent": "ledgerwash-release-verifier"})
        # Public metadata only. No token is read, inherited or sent.
        with urllib.request.urlopen(request, timeout=45) as response:
            require(response.geturl().startswith("https://api.github.com/"), "unexpected API redirect")
            raw = response.read(4 * 1024 * 1024 + 1)
        require(len(raw) <= 4 * 1024 * 1024, "API response bound")
        (out / name).write_bytes(raw)
        return loads(raw)

    try:
        require(re.fullmatch(r"[0-9a-f]{40}", source), "exact source required")
        require(command("source", ["git", "rev-parse", "HEAD"]).decode().strip() == source, "source mismatch")
        require(not command("initial-status", ["git", "status", "--porcelain"]), "dirty source")
        params = loads(Path(os.environ["EC_WORKLOAD_PARAMETERS"]).read_bytes())
        run_id, attempt = params["run_id"], params["attempt"]
        evidence = params["evidence_path"]
        require(re.fullmatch(r"evidence/requests/[0-9a-f-]{36}/[A-Za-z0-9._-]+\.json", evidence),
                "unsafe evidence path")
        ec_sha = os.environ["GITHUB_SHA"]
        require(re.fullmatch(r"[0-9a-f]{40}", ec_sha), "exact EC source required")
        bundle_raw = command("transport-input", ["git", "show", f"{ec_sha}:{evidence}"],
                             cwd=Path(os.environ["GITHUB_WORKSPACE"]))
        require(len(bundle_raw) <= 8 * 1024 * 1024 and sha(bundle_raw) == params["bundle_sha256"],
                "transport bundle hash/size mismatch")
        bundle = loads(bundle_raw)
        require(bundle["source_sha"] == source and str(bundle["run_id"]) == run_id
                and str(bundle["attempt"]) == attempt, "transport input identity")
        run = api(f"/actions/runs/{run_id}", "github-run.json")
        jobs = api(f"/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100", "github-jobs.json")
        artifacts = api(f"/actions/runs/{run_id}/artifacts?per_page=100", "github-artifacts.json")
        expected = check_metadata(source, run_id, attempt, run, jobs, artifacts)
        require(len(bundle["artifacts"]) == 9, "transport must contain nine artifacts")
        by_id = {item["id"]: item for item in bundle["artifacts"]}
        require(len(by_id) == 9 and set(by_id) == {item["id"] for item in expected.values()},
                "transport artifact set mismatch")
        cells, identities = [], []
        for os_name in OS_NAMES:
            for python in PYTHONS:
                metadata = expected[(os_name, python)]
                raw = base64.b64decode(by_id[metadata["id"]]["zip_base64"], validate=True)
                require("sha256:" + sha(raw) == metadata["digest"], "service ZIP digest mismatch")
                (out / (metadata["name"] + ".zip")).write_bytes(raw)
                members = read_zip(raw)
                receipt = check_cell(members, source, run_id, attempt, os_name, python)
                cells.append(members)
                identities.append({"name": metadata["name"], "artifact_id": metadata["id"],
                                   "digest": metadata["digest"], "epochs": receipt["epochs"],
                                   "suite": receipt["suite"], "runtime": receipt["runtime"]})
        report["cross_platform"] = compare_cells(cells)
        report["producers"] = identities
        report["producer_run"] = {"run_id": run_id, "attempt": attempt}

        pins = loads((ROOT / "workloads/release_verify/bootstrap.json").read_bytes())
        uv_pin = pins["uv"]
        bootstrap = work / "bootstrap"
        command("bootstrap-venv", [sys.executable, "-I", "-B", "-m", "venv", str(bootstrap)])
        bootstrap_python = bootstrap / "Scripts/python.exe"
        requirement = work / "uv-requirement.txt"
        requirement.write_text(f"uv @ {uv_pin['url']} --hash=sha256:{uv_pin['sha256']}\n", encoding="utf-8")
        command("uv-bootstrap", [str(bootstrap_python), "-I", "-B", "-m", "pip", "install",
                                  "--isolated", "--disable-pip-version-check", "--no-cache-dir",
                                  "--no-deps", "--require-hashes", "--only-binary=:all:", "-r", str(requirement)])
        uv = bootstrap / "Scripts/uv.exe"
        report["uv_version"] = command("uv-version", [str(uv), "--version"]).decode().strip()
        require(report["uv_version"].split()[:2] == ["uv", uv_pin["version"]], "uv version mismatch")
        constraints = work / "build-constraints.txt"
        constraints.write_text("".join(f"{name}=={version}\n" for name, version in sorted(pins["build_constraints"].items())),
                               encoding="utf-8", newline="\n")
        env.update(UV_PROJECT_ENVIRONMENT=str(work / "installed"), UV_CACHE_DIR=str(work / "uv-cache"),
                   UV_PYTHON_DOWNLOADS="never", UV_NO_MANAGED_PYTHON="1",
                   UV_BUILD_CONSTRAINT=str(constraints), UV_NO_PROGRESS="1", UV_NO_CONFIG="1")
        lock_before = (ROOT / "uv.lock").read_bytes()
        command("lock-check", [str(uv), "lock", "--check", "--python", sys.executable])
        command("locked-sync", [str(uv), "sync", "--locked", "--extra", "dev", "--python", sys.executable])
        require((ROOT / "uv.lock").read_bytes() == lock_before, "uv modified the lock")
        installed = work / "installed/Scripts/python.exe"
        identity = command("installed-identity", [str(installed), "-I", "-B", "-c",
            "import importlib.metadata,json,ledgerwash; print(json.dumps({'distribution':importlib.metadata.version('ledgerwash'),'engine':ledgerwash.__version__,'spec':ledgerwash.SPEC_VERSION,'file':ledgerwash.__file__}))"], cwd=work)
        value = loads(identity)
        require(value["distribution"] == value["engine"] == "0.5.0" and value["spec"] == 5
                and Path(value["file"]).resolve() == ROOT / "src/ledgerwash/__init__.py", "installed identity mismatch")
        command("installed-cli", [str(work / "installed/Scripts/ledgerwash.exe"), "--version"], cwd=work)
        command("suite", [str(installed), "-B", "-m", "pytest", "tests", "-p", "no:cacheprovider",
                          "--basetemp", str(work / "pytest"), "--junitxml", str(out / "suite.xml")], timeout=900)
        command("local-producer", [str(installed), "-B", str(ROOT / "workloads/release_verify/produce.py"),
                "--source", source, "--os", "windows-latest", "--python", "3.12",
                "--run", run_id, "--attempt", attempt, "--out", str(out / "local-producer"),
                "--work", str(work / "fixtures"), "--junit", str(out / "suite.xml")], timeout=600)
        local = {path.name: path.read_bytes() for path in (out / "local-producer").iterdir()}
        local_receipt = check_cell(local, source, run_id, attempt, "windows-latest", "3.12")
        for name in RAW_NAMES:
            require(local[name] == cells[0][name], "installed EC replay differs: " + name)
        report["installed_suite"] = local_receipt["suite"]
        report["lock_sha256"] = sha(lock_before)
        report["build_constraints"] = pins["build_constraints"]
        require(not command("final-status", ["git", "status", "--porcelain"]), "source changed during verification")
        report["status"] = "pass"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (out / "release-result.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                                                  encoding="utf-8", newline="\n")
        (out / "SUMMARY.md").write_text("# LedgerWash release verification\n\n"
            + f"Status: {report['status']}; exact source: `{source}`.\n\n"
            + "GitHub-hosted nine-cell witnesses, independently checked against primary metadata; "
              "EC Windows raw-byte comparison and installed-project replay.\n\n"
            + (report.get("error", "No PyPI publication or ledger authenticity claim.") + "\n"),
            encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
