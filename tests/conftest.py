"""Session-scoped fixtures: the planted corpus, its envelope, and a clean control."""

from __future__ import annotations

import pytest
from pathlib import Path

from ledgerwash.engine import run_scan
from ledgerwash.qualify_corpus import build_corpus


@pytest.fixture(scope="session")
def mini_repo(tmp_path_factory) -> Path:
    return build_corpus(tmp_path_factory.mktemp("mini") / "mini-ledger")


@pytest.fixture(scope="session")
def mini_envelope(mini_repo) -> dict:
    return run_scan(mini_repo)


@pytest.fixture(scope="session")
def clean_envelope(tmp_path_factory) -> dict:
    repo = build_corpus(tmp_path_factory.mktemp("clean") / "clean-ledger", planted=False)
    return run_scan(repo)


def by_rule(envelope: dict) -> dict:
    out: dict[str, list[dict]] = {}
    for finding in envelope["findings"]:
        out.setdefault(finding["rule"], []).append(finding)
    return out
