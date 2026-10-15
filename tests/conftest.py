"""Session-scoped fixtures: the planted corpora, their envelopes, a clean control."""

from __future__ import annotations

import pytest
from pathlib import Path

from ledgerwash.engine import run_scan
from ledgerwash.qualify_corpus import build_corpus, build_negspace_corpus


@pytest.fixture(scope="session")
def mini_repo(tmp_path_factory) -> Path:
    return build_corpus(tmp_path_factory.mktemp("mini") / "mini-ledger")


@pytest.fixture(scope="session")
def mini_envelope(mini_repo) -> dict:
    return run_scan(mini_repo)


@pytest.fixture(scope="session")
def negspace_repo(tmp_path_factory) -> Path:
    return build_negspace_corpus(tmp_path_factory.mktemp("negspace") / "negspace-ledger")


@pytest.fixture(scope="session")
def negspace_envelope(negspace_repo) -> dict:
    return run_scan(negspace_repo)


@pytest.fixture(scope="session")
def clean_envelope(tmp_path_factory) -> dict:
    repo = build_corpus(tmp_path_factory.mktemp("clean") / "clean-ledger", planted=False)
    return run_scan(repo)


def by_rule(envelope: dict) -> dict:
    out: dict[str, list[dict]] = {}
    for finding in envelope["findings"]:
        out.setdefault(finding["rule"], []).append(finding)
    return out
