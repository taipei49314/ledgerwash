"""Narrow EC legacy-row continuity, not full migration/authority verification.

A task JSON's introduction cannot establish task birth when the same record is
bound to its actual parent's ledger. Even this binding cannot authenticate a
self-consistent forged parent. Coverage deliberately remains incomplete.
"""

from __future__ import annotations

import hashlib
import json
import re

from ledgerwash.epoch import EpochError
from ledgerwash.models import strict_eq

from .ec_ledger import decode

MANIFEST = "governance/task-store.json"
LEDGER = "LEDGER.md"
ARCHIVES = "governance/task-history"
TASK_FIELDS = {"schema_version", "id", "description", "status", "state", "owner",
               "time", "evidence", "handoff", "history"}
MANIFEST_FIELDS = {"schema_version", "kind", "hash_format", "ledger_sha256", "tasks", "migration"}
MIGRATION_FIELDS = {"source", "sha256", "at", "actor", "task_id", "source_commit"}
HISTORY_FIELDS = {"kind", "source", "sha256", "line", "row_sha256"}
TASK_ID = re.compile(r"T-\d+(?:[a-z]|-[a-z]+)?\Z")
STATE = re.compile(r"^(TODO|CLAIMED|BLOCKED|DONE|SUPERSEDED|CANCELLED)\b")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _exact(value, fields):
    return isinstance(value, dict) and value.keys() == fields


def _cells(line):
    """EC six-column grammar: escaped delimiters and backtick runs stay literal."""
    parts, current, fence, i = [], [], 0, 0
    while i < len(line):
        char = line[i]
        if char == "\\" and fence == 0 and i + 1 < len(line):
            current.extend(line[i:i + 2])
            i += 2
            continue
        if char == "`":
            end = i
            while end < len(line) and line[end] == "`":
                end += 1
            length = end - i
            fence = length if fence == 0 else (0 if fence == length else fence)
            current.append(line[i:end])
            i = end
            continue
        if char == "|" and fence == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        i += 1
    parts.append("".join(current).strip())
    if parts[0] or parts[-1] or fence:
        raise ValueError("ambiguous legacy row")
    return parts[1:-1]


class MigrationContinuity:
    """Per-scan caches keep archive/manifest work independent of task count."""

    def __init__(self, epoch):
        self.epoch = epoch
        self._blobs = {}
        self._contexts = {}

    def _blob(self, commit, path):
        key = (commit, path)
        if key not in self._blobs:
            modes = self.epoch.file_modes_at(commit)
            self._blobs[key] = (self.epoch.blob_at(commit, path)
                                if modes.get(path) in {"100644", "100755"} else None)
        return self._blobs[key]

    def _manifest(self, commit):
        raw = self._blob(commit, MANIFEST)
        value = decode(raw) if raw is not None else None
        if (not _exact(value, MANIFEST_FIELDS)
                or type(value["schema_version"]) is not int or value["schema_version"] != 1
                or value["kind"] != "ec-task-store"
                or value["hash_format"] != "canonical-json-utf8"
                or not isinstance(value["ledger_sha256"], str)
                or not HEX64.fullmatch(value["ledger_sha256"])
                or not isinstance(value["tasks"], list)
                or not _exact(value["migration"], MIGRATION_FIELDS)):
            raise ValueError("unsupported migration manifest")
        return value

    def _context(self, birth):
        if birth in self._contexts:
            return self._contexts[birth]
        # Cache a failed binding too; malformed audited data is not an escape.
        self._contexts[birth] = None
        manifest = self._manifest(birth)
        current = self._manifest(self.epoch.sha)
        migration = manifest["migration"]
        if not strict_eq(migration, current["migration"]):
            return None
        parent = self.epoch.parent(birth)
        if not parent or migration["source_commit"] != parent:
            return None
        if MANIFEST in self.epoch.file_modes_at(parent):
            return None
        sha = migration["sha256"]
        if not isinstance(sha, str) or not HEX64.fullmatch(sha):
            return None
        path = f"{ARCHIVES}/ledger-before-{sha}.md"
        if migration["source"] != path:
            return None
        archive = self._blob(birth, path)
        if (archive is None or _hash(archive) != sha
                or archive != self._blob(self.epoch.sha, path)
                or archive != self._blob(parent, LEDGER)):
            return None
        entries = {}
        for entry in manifest["tasks"]:
            if (not _exact(entry, {"id", "sha256"})
                    or not isinstance(entry["id"], str) or not TASK_ID.fullmatch(entry["id"])
                    or entry["id"] in entries or not isinstance(entry["sha256"], str)
                    or not HEX64.fullmatch(entry["sha256"])):
                return None
            entries[entry["id"]] = entry["sha256"]
        rows = {}
        for number, raw in enumerate(archive.splitlines(), 1):
            line = raw.decode("utf-8-sig")
            if not line.startswith("| T-"):
                continue
            cells = _cells(line)
            if len(cells) != 6 or not TASK_ID.fullmatch(cells[0]) or cells[0] in rows:
                return None
            rows[cells[0]] = (number, raw, cells)
        context = (parent, migration, entries, rows)
        self._contexts[birth] = context
        return context

    def matches(self, task, birth):
        """Fail closed on absent/unsupported bindings; never alter coverage."""
        try:
            data = task.data
            if (not _exact(data, TASK_FIELDS) or type(data["schema_version"]) is not int
                    or data["schema_version"] != 1 or data["id"] != task.id
                    or not isinstance(data["history"], list) or len(data["history"]) != 1):
                return False
            history = data["history"][0]
            if (not _exact(history, HISTORY_FIELDS) or history["kind"] != "migration"
                    or type(history["line"]) is not int or history["line"] <= 0):
                return False
            context = self._context(birth)
            if context is None:
                return False
            parent, migration, entries, rows = context
            if task.path in self.epoch.file_modes_at(parent):
                return False
            original = self._blob(birth, task.path)
            if (original is None or self._blob(self.epoch.sha, task.path) is None
                    or not strict_eq(data, decode(original))
                    or entries.get(task.id) != _hash(_canonical(data))
                    or history["source"] != migration["source"]
                    or history["sha256"] != migration["sha256"]):
                return False
            number, raw, cells = rows[task.id]
            if history["line"] != number or history["row_sha256"] != _hash(raw):
                return False
            status = STATE.match(cells[2].replace("**", ""))
            if not status:
                return False
            expected = dict(zip(("id", "description", "status", "owner", "time", "evidence"), cells))
            expected["state"] = status[1]
            return all(strict_eq(data[key], value) for key, value in expected.items())
        except (ValueError, KeyError, TypeError, UnicodeError, EpochError):
            return False
