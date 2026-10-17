"""Hosted pre-publication readback of an externally pinned EC manifest and bytes."""
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

REPOSITORY = "taipei49314/ledgerwash"
SOURCE = "85cf8e6f99fcc576240cb6783b65b98a3341dfb1"
FILES = {"ledgerwash-0.5.0-py3-none-any.whl", "ledgerwash-0.5.0.tar.gz"}
HOSTS = {"github.com", "api.github.com", "release-assets.githubusercontent.com"}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def check_url(url):
    parsed = urllib.parse.urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname in HOSTS and parsed.port in (None, 443)
            and not parsed.username and not parsed.password, "unexpected asset host")


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit=4 * 1024 * 1024):
    check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "ledgerwash-publish-readback"})
    with urllib.request.build_opener(Redirects()).open(req, timeout=45) as response:
        raw = response.read(limit + 1)
    require(len(raw) <= limit, "asset size bound")
    return raw


def main():
    require(os.environ["GITHUB_REPOSITORY"] == REPOSITORY
            and os.environ["GITHUB_REF"] == "refs/heads/main", "publish only from repository main")
    expected = os.environ["ACCEPTED_MANIFEST_SHA256"]
    require(re.fullmatch("[0-9a-f]{64}", expected), "accepted manifest digest required")
    api = "https://api.github.com/repos/" + REPOSITORY
    tag = json.loads(fetch(api + "/git/ref/tags/v0.5.0"))
    require(tag["object"]["sha"] == SOURCE and tag["object"]["type"] == "commit", "release tag changed")
    release = json.loads(fetch(api + "/releases/tags/v0.5.0"))
    require(release["id"] == 415919933 and not release["draft"] and not release["prerelease"], "release identity")
    assets = release["assets"]

    def asset(name):
        found = [item for item in assets if item["name"] == name]
        require(len(found) == 1, "missing/duplicate release asset: " + name)
        item = found[0]
        require(item["browser_download_url"] == f"https://github.com/{REPOSITORY}/releases/download/v0.5.0/{name}",
                "unexpected asset URL")
        raw = fetch(item["browser_download_url"], 32 * 1024 * 1024)
        require(item["size"] == len(raw) and item["digest"] == "sha256:" + hashlib.sha256(raw).hexdigest(),
                "GitHub asset digest mismatch")
        return raw

    raw_manifest = asset("pypi-manifest.json")
    require(hashlib.sha256(raw_manifest).hexdigest() == expected, "accepted manifest changed")
    manifest = json.loads(raw_manifest)
    require(manifest["schema_version"] == 1 and manifest["status"] == "pass"
            and manifest["repository"] == REPOSITORY and manifest["tag"] == "v0.5.0"
            and manifest["source_sha"] == SOURCE and manifest["tag_run"] == "39048676325"
            and manifest["tag_attempt"] == "1", "acceptance identity")
    require(manifest["tag_ci"] == {"conclusion": "success", "jobs": 9, "source_sha": SOURCE}
            and manifest["installed_suite"] == {"tests": 154, "failures": 0, "errors": 0, "skipped": 0}, "acceptance failed")
    require(re.fullmatch("[0-9a-f]{40}", manifest["ec_commit"])
            and re.fullmatch("[0-9a-f]{40}", manifest["harness_sha"])
            and re.fullmatch("[1-9][0-9]+", manifest["ec_run"])
            and re.fullmatch("[1-9][0-9]*", manifest["ec_attempt"]), "EC receipt identity")
    entries = manifest["distributions"]
    require(len(entries) == 2 and {x["filename"] for x in entries} == FILES, "distribution filenames")
    root = Path("release")
    (root / "dist").mkdir(parents=True, exist_ok=False)
    (root / "pypi-manifest.json").write_bytes(raw_manifest)
    sums = [expected + "  pypi-manifest.json\n"]
    for item in entries:
        raw = asset(item["filename"])
        require(len(raw) == item["size"] and hashlib.sha256(raw).hexdigest() == item["sha256"], "EC-built bytes differ")
        (root / "dist" / item["filename"]).write_bytes(raw)
        sums.append(item["sha256"] + "  dist/" + item["filename"] + "\n")
    (root / "SHA256SUMS").write_text("".join(sums), encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
