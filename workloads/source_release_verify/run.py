"""T-554: fixed v0.5.0 archive and installed distribution acceptance on EC."""
from __future__ import annotations

import base64
import csv
import configparser
from email.parser import BytesParser
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from workloads.source_release_verify.common import MAX_ARCHIVE, compare_git, read_archive, require, sha
from workloads.release_verify.common import check_metadata, junit_counts, loads

REPOSITORY = "taipei49314/ledgerwash"
SOURCE = "85cf8e6f99fcc576240cb6783b65b98a3341dfb1"
TAG = "v0.5.0"
TAG_RUN = "39048676325"
TAG_ATTEMPT = "1"
DIST = "ledgerwash-0.5.0"
HOSTS = {"github.com", "api.github.com", "codeload.github.com"}
DEPENDENCIES = {"pytest", "colorama", "iniconfig", "packaging", "pluggy", "pygments"}


def check_url(url):
    parsed = urllib.parse.urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname in HOSTS
            and parsed.port in (None, 443) and not parsed.username and not parsed.password,
            "unexpected download host/scheme")


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def metadata(raw):
    value = BytesParser().parsebytes(raw)
    require(value["Name"] == "ledgerwash" and value["Version"] == "0.5.0"
            and value["Requires-Python"] == ">=3.11", "distribution metadata identity")
    require(value["License-Expression"] == "Apache-2.0"
            and "LICENSE" in value.get_all("License-File", []), "distribution license metadata")
    require(value["Description-Content-Type"] == "text/markdown", "README metadata")
    require(value.get_all("Provides-Extra", []) == ["dev"]
            and [re.sub(r"\s+", "", item).replace("'", '"') for item in value.get_all("Requires-Dist", [])]
            == ['pytest>=8;extra=="dev"'], "unexpected dependency declaration")
    return {key: value[key] for key in ("Name", "Version", "Requires-Python", "License-Expression")}


def wheel_check(raw, source_files):
    files = read_archive(raw, "zip")
    info = DIST + ".dist-info/"
    package = {path.removeprefix("src/"): data for path, data in source_files.items()
               if path.startswith("src/ledgerwash/")}
    require({p for p in files if not p.startswith(info)} == set(package), "wheel payload set")
    require(all(files[p] == data for p, data in package.items()), "wheel source differs")
    require(set(files) - set(package) == {info + name for name in
            ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")},
            "unexpected wheel metadata files")
    require(files[info + "licenses/LICENSE"] == source_files["LICENSE"], "wheel license differs")
    entry = configparser.ConfigParser(interpolation=None)
    entry.read_string(files[info + "entry_points.txt"].decode("utf-8"))
    require(entry.sections() == ["console_scripts"] and not entry.defaults()
            and dict(entry["console_scripts"]) == {"ledgerwash": "ledgerwash.cli:main"}, "console entry point")
    wheel_metadata = BytesParser().parsebytes(files[info + "WHEEL"])
    require(wheel_metadata.get_all("Tag") == ["py3-none-any"]
            and wheel_metadata["Root-Is-Purelib"] == "true"
            and wheel_metadata["Wheel-Version"] == "1.0", "wheel platform tag")
    rows = list(csv.reader(io.StringIO(files[info + "RECORD"].decode("utf-8"))))
    require(len(rows) == len(files) and {r[0] for r in rows} == set(files), "wheel RECORD path set")
    for path, digest, size in rows:
        if path == info + "RECORD":
            require(not digest and not size, "RECORD self entry")
        else:
            encoded = base64.urlsafe_b64encode(bytes.fromhex(sha(files[path]))).rstrip(b"=").decode()
            require(digest == "sha256=" + encoded and size == str(len(files[path])), "RECORD mismatch")
    return metadata(files[info + "METADATA"])


def main():
    require(os.environ.get("EC_WORKLOAD_REPOSITORY") == REPOSITORY
            and os.environ.get("EC_WORKLOAD_NAME") == "source-release-verify"
            and Path(os.environ["EC_WORKLOAD_SOURCE"]).resolve() == ROOT, "EC workload identity")
    harness_sha = os.environ["EC_WORKLOAD_SHA"]
    require(re.fullmatch(r"[0-9a-f]{40}", harness_sha), "exact harness SHA required")
    require(loads(Path(os.environ["EC_WORKLOAD_PARAMETERS"]).read_bytes()) == {}, "no parameters admitted")
    out, work = (Path(os.environ[k]).resolve() for k in ("EC_WORKLOAD_OUT", "EC_WORKLOAD_WORK"))
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(
        ("PYTHON", "PYTEST", "UV_", "PIP_", "GIT_CONFIG", "GH_", "GITHUB_TOKEN", "ACTIONS_ID_TOKEN"))
           and k != "VIRTUAL_ENV"}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    report = {"schema_version": 1, "status": "incomplete", "source_sha": SOURCE,
              "harness_sha": harness_sha, "repository": REPOSITORY, "tag": TAG,
              "ec_run": os.environ["GITHUB_RUN_ID"], "ec_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
              "ec_commit": os.environ["GITHUB_SHA"],
              "tag_run": TAG_RUN, "tag_attempt": TAG_ATTEMPT, "steps": [],
              "limitations": ["One EC Windows runtime for distribution installation",
                  "The preserved suite includes deliberately frozen PR2 baseline controls",
                  "No PyPI publication or signing credentials in this workload"]}

    def command(name, args, cwd=work, timeout=600):
        args = list(map(str, args))
        try:
            done = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False)
            stdout, stderr, code = done.stdout, done.stderr, done.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, code = exc.stdout or b"", exc.stderr or b"", None
        (out / (name + ".stdout")).write_bytes(stdout)
        (out / (name + ".stderr")).write_bytes(stderr)
        report["steps"].append({"name": name, "command": args, "exit_code": code,
                                "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr)})
        require(code == 0, "command failed/timed out: " + name)
        return stdout

    def download(url, name, limit=4 * 1024 * 1024):
        check_url(url)
        request = urllib.request.Request(url, headers={"User-Agent": "ledgerwash-source-verifier",
                                         "Accept": "application/vnd.github+json"})
        with urllib.request.build_opener(Redirects()).open(request, timeout=45) as response:
            check_url(response.geturl())
            raw = response.read(limit + 1)
            require(len(raw) <= limit, "download size bound")
            report.setdefault("downloads", []).append({"url": url, "final_url": response.geturl(),
                                                        "size": len(raw), "sha256": sha(raw), "file": name})
        (out / name).write_bytes(raw)
        return raw

    def api(suffix, name):
        return loads(download("https://api.github.com/repos/" + REPOSITORY + suffix, name))

    try:
        require(command("harness-source", ["git", "rev-parse", "HEAD"], ROOT).decode().strip() == harness_sha,
                "harness SHA mismatch")
        require(not command("harness-clean", ["git", "status", "--porcelain"], ROOT), "dirty harness")
        release = api("/releases/tags/" + TAG, "release.json")
        tag = api("/git/ref/tags/" + TAG, "tag.json")
        require(release["id"] == 415919933 and release["tag_name"] == TAG and release["published_at"]
                and not release["draft"] and not release["prerelease"], "release identity/state")
        require(tag["object"] == {"sha": SOURCE, "type": "commit",
                "url": f"https://api.github.com/repos/{REPOSITORY}/git/commits/{SOURCE}"}, "tag target changed")
        run = api(f"/actions/runs/{TAG_RUN}", "tag-run.json")
        jobs = api(f"/actions/runs/{TAG_RUN}/attempts/{TAG_ATTEMPT}/jobs?per_page=100", "tag-jobs.json")
        artifacts = api(f"/actions/runs/{TAG_RUN}/artifacts?per_page=100", "tag-artifacts.json")
        check_metadata(SOURCE, TAG_RUN, TAG_ATTEMPT, run, jobs, artifacts)
        require(run["event"] == "push" and run["head_branch"] == TAG, "not the final tag CI")
        for job in jobs["jobs"]:
            for name in ("qualify (red-by-design self-check)", "Produce exact-source release witnesses"):
                require(any(step["name"] == name and step["conclusion"] == "success"
                            for step in job["steps"]), "missing successful CI step")
        report["tag_ci"] = {"conclusion": "success", "jobs": 9, "source_sha": SOURCE}

        reference = work / "reference"
        command("reference-init", ["git", "init", str(reference)])
        command("reference-fetch", ["git", "-c", "credential.helper=", "-c", "core.hooksPath=" + os.devnull,
            "fetch", "--depth=1", "https://github.com/" + REPOSITORY + ".git", SOURCE], reference)
        require(command("reference-pin", ["git", "rev-parse", "FETCH_HEAD"], reference).decode().strip() == SOURCE,
                "fetched source mismatch")
        tree = command("reference-tree", ["git", "ls-tree", "-rz", SOURCE], reference)
        expected = {}
        for line in tree.rstrip(b"\0").split(b"\0"):
            identity, name = line.split(b"\t", 1)
            mode, kind, blob = identity.decode().split()
            require(kind == "blob", "unexpected Git entry")
            expected[name.decode("utf-8")] = (mode, blob)
        files = None
        for kind in ("zip", "tar.gz"):
            raw = download(f"https://github.com/{REPOSITORY}/archive/refs/tags/{TAG}.{kind}",
                           "source." + kind, MAX_ARCHIVE)
            members = read_archive(raw, kind, "ledgerwash-0.5.0")
            manifest = compare_git(members, expected)
            if files is not None:
                require(members == files, "ZIP/TAR content mismatch")
            files = members
        report["source_files"] = manifest
        source = work / "verified-source"
        for path, data in files.items():
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        env["SOURCE_DATE_EPOCH"] = command("source-date", ["git", "show", "-s", "--format=%ct", SOURCE], reference).decode().strip()

        pins = loads((ROOT / "workloads/release_verify/bootstrap.json").read_bytes())
        uv_pin = pins["uv"]
        command("bootstrap-venv", [sys.executable, "-I", "-B", "-m", "venv", work / "bootstrap"])
        bootstrap = work / "bootstrap/Scripts/python.exe"
        req = work / "uv-requirement.txt"
        req.write_text(f"uv @ {uv_pin['url']} --hash=sha256:{uv_pin['sha256']}\n", encoding="utf-8")
        command("uv-bootstrap", [bootstrap, "-I", "-B", "-m", "pip", "install", "--isolated",
            "--disable-pip-version-check", "--no-cache-dir", "--no-deps", "--require-hashes",
            "--only-binary=:all:", "-r", req])
        uv = work / "bootstrap/Scripts/uv.exe"
        require(command("uv-version", [uv, "--version"]).decode().split()[:2] == ["uv", uv_pin["version"]], "uv version")
        constraints = work / "build-constraints.txt"
        constraints.write_text("".join(f"{k}=={v}\n" for k, v in sorted(pins["build_constraints"].items())), encoding="utf-8")
        env.update(UV_CACHE_DIR=str(work / "uv-cache"), UV_PYTHON_DOWNLOADS="never", UV_NO_MANAGED_PYTHON="1",
                   UV_BUILD_CONSTRAINT=str(constraints), UV_NO_PROGRESS="1", UV_NO_CONFIG="1")
        dist = out / "dist"
        # uv's default builds sdist first, then builds the wheel FROM that sdist.
        command("build-distributions", [uv, "build", "--no-sources", "--python", sys.executable,
                                       "--out-dir", dist, source], timeout=600)
        wheel, sdist = dist / (DIST + "-py3-none-any.whl"), dist / (DIST + ".tar.gz")
        require({p.name for p in dist.iterdir() if p.name != ".gitignore"} == {wheel.name, sdist.name}, "distribution set")
        report["wheel_metadata"] = wheel_check(wheel.read_bytes(), files)
        packed = read_archive(sdist.read_bytes(), "tar.gz", DIST)
        require("PKG-INFO" in packed, "missing sdist metadata")
        report["sdist_metadata"] = metadata(packed.pop("PKG-INFO"))
        require(all(p in files and files[p] == data for p, data in packed.items()), "sdist changed or added source")
        required = {p for p in files if p.startswith("src/")} | {"pyproject.toml", "README.md", "LICENSE"}
        require(required <= packed.keys(), "sdist missing required source")

        command("installed-venv", [sys.executable, "-I", "-B", "-m", "venv", work / "installed"])
        installed = work / "installed/Scripts/python.exe"
        pip = [installed, "-I", "-B", "-m", "pip", "install", "--isolated", "--disable-pip-version-check",
               "--no-cache-dir", "--no-deps"]
        command("install-wheel", [*pip, "--no-index", wheel])
        selected = [p for p in tomllib.loads(files["uv.lock"].decode())["package"] if p["name"] in DEPENDENCIES]
        require(len(selected) == len(DEPENDENCIES) and {p["name"] for p in selected} == DEPENDENCIES, "dev lock set")
        requirements = []
        for package in selected:
            require(len(package["wheels"]) == 1, "dev lock wheel count")
            item = package["wheels"][0]
            require(item["url"].startswith("https://files.pythonhosted.org/packages/")
                    and item["url"].endswith("-none-any.whl")
                    and re.fullmatch("sha256:[0-9a-f]{64}", item["hash"]), "dev lock pin")
            requirements.append(f"{package['name']} @ {item['url']} --hash={item['hash']}\n")
        dev_req = work / "dev-requirements.txt"
        dev_req.write_text("".join(requirements), encoding="utf-8")
        command("install-test-dependencies", [*pip, "--require-hashes", "--only-binary=:all:", "-r", dev_req])
        # Stage original tests plus their static inputs outside source. src is NOT on sys.path.
        stage = work / "installed-suite"
        for path, data in files.items():
            if path.startswith(("tests/", "src/")) or path in ("SPEC.md", "workloads/release_verify/common.py"):
                target = stage / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        runner = stage / "run_installed_suite.py"
        runner.write_text("""import importlib.metadata,json,pathlib,sys,pytest,ledgerwash
root=pathlib.Path(__file__).resolve().parent
site=pathlib.Path(sys.prefix).resolve()/'Lib'/'site-packages'
def identity():
    assert importlib.metadata.version('ledgerwash') == ledgerwash.__version__ == '0.5.0'
    assert ledgerwash.SPEC_VERSION == 5
    for name,module in list(sys.modules.items()):
        if name == 'ledgerwash' or name.startswith('ledgerwash.'):
            assert pathlib.Path(module.__file__).resolve().is_relative_to(site), (name,module.__file__)
    assert str(root/'src') not in sys.path
identity()
sys.path.append(str(root))
code=pytest.main(['tests','--import-mode=append','-p','no:cacheprovider','--basetemp',sys.argv[1],'--junitxml',sys.argv[2]])
identity()
print(json.dumps({'ledgerwash':ledgerwash.__file__,'version':ledgerwash.__version__,'spec':ledgerwash.SPEC_VERSION}))
raise SystemExit(code)
""", encoding="utf-8")
        command("installed-suite", [installed, "-I", "-B", runner, work / "pytest", out / "suite.xml"], stage, 900)
        report["installed_suite"] = junit_counts((out / "suite.xml").read_bytes())
        require(report["installed_suite"]["tests"] == 154, "fixed release suite count changed")
        command("installed-cli", [work / "installed/Scripts/ledgerwash.exe", "--version"])
        output = command("installed-qualify", [installed, "-I", "-B", "-m", "ledgerwash", "qualify"])
        require(b"qualify ok:" in output, "qualify did not confirm rule coverage")
        require(not command("final-harness-status", ["git", "status", "--porcelain"], ROOT), "harness modified")
        report["distributions"] = [{"filename": p.name, "sha256": sha(p.read_bytes()), "size": p.stat().st_size}
                                    for p in (wheel, sdist)]
        report["build_constraints"] = pins["build_constraints"]
        report["status"] = "pass"
        (out / "pypi-manifest.json").write_text(json.dumps({k: report[k] for k in
            ("schema_version", "status", "repository", "tag", "source_sha", "harness_sha", "ec_run", "ec_attempt", "ec_commit", "tag_run",
             "tag_attempt", "tag_ci", "installed_suite", "distributions")}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (out / "source-release-result.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        (out / "SUMMARY.md").write_text(f"# Fixed v0.5.0 source/distribution verification\n\nStatus: {report['status']}\n\n"
            f"Source: {SOURCE}; harness: {harness_sha}\n\n" + report.get("error", "See source-release-result.json and preserved raw evidence.") + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
