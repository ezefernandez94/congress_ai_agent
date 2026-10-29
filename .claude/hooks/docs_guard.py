#!/usr/bin/env python3
"""Keep docs/ consistent and in sync with the code.

Usage:
    python3 .claude/hooks/docs_guard.py check   # validate docs/, print problems, exit 1 if any
    python3 .claude/hooks/docs_guard.py stop    # Claude Code "Stop" hook (reads JSON on stdin)

In "stop" mode the script can block Claude from finishing (exit code 2, message on stderr) in two cases:
  1. docs/ has format or consistency errors (duplicate IDs, dangling references, index mismatch, ...).
  2. Source files changed but nothing under docs/ did.

Each message is shown once per distinct problem (and again after 30 minutes), so it can never trap
Claude in a loop. Only the standard library is used.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
DOCS = ROOT / "docs"
STATE_FILE = ROOT / ".claude" / ".docs_guard_state.json"
REMIND_AGAIN_AFTER = 30 * 60  # seconds

KINDS = {
    "REQ": {
        "file": "requirements.md",
        "statuses": {"active", "planned", "superseded"},
        "required": ["Status", "Source", "Added"],
        "dates": ["Added"],
        "pending": {"planned"},  # statuses that may carry "Will supersede"
    },
    "ADR": {
        "file": "architecture.md",
        "statuses": {"proposed", "accepted", "superseded"},
        "required": ["Status", "Date"],
        "dates": ["Date"],
        "pending": {"proposed"},
    },
    "UC": {
        "file": "use-cases.md",
        "statuses": {"planned", "unverified", "implemented", "deprecated"},
        "required": ["Status", "Actor", "Requirements", "Tests"],
        "dates": [],
        "pending": set(),
    },
}

ID_RE = re.compile(r"\b(?:REQ|UC|ADR)-\d{3}\b")
HEADING_RE = re.compile(r"^### ((?:REQ|UC|ADR)-\d{3})\s*[—–-]\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^- ([A-Za-z][A-Za-z ]*?):\s*(.*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Files that count as "source" for the docs-sync reminder.
SOURCE_RE = re.compile(r"^(app/.+\.(py|html)|scripts/.+\.py)$")
IGNORE_RE = re.compile(
    r"(^|/)(__pycache__|tests)/"
    r"|(^|/)(test_[^/]*\.py|conftest\.py)$"
)


# --------------------------------------------------------------------------- parsing

def parse(kind, errors):
    """Return (entries, index) for one docs file. Appends format problems to `errors`."""
    spec = KINDS[kind]
    path = DOCS / spec["file"]
    entries, index = {}, {}
    current, in_fence = None, False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            eid = m.group(1)
            if not eid.startswith(kind + "-"):
                errors.append(f"{spec['file']}:{n}: {eid} does not belong in this file (expected {kind}-NNN)")
            if eid in entries:
                errors.append(f"{spec['file']}:{n}: duplicate ID {eid} (first defined on line {entries[eid]['line']})")
            current = {"title": m.group(2), "fields": {}, "line": n}
            entries.setdefault(eid, current)
            continue
        if line.startswith("## "):
            current = None
            continue
        if current is not None and line.startswith("- "):
            f = FIELD_RE.match(line)
            if f:
                current["fields"].setdefault(f.group(1).strip(), f.group(2).strip())
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if re.fullmatch(kind + r"-\d{3}", cells[0]):
                index[cells[0]] = cells[2].lower() if len(cells) > 2 else ""
    return entries, index


def ids_in(value):
    return ID_RE.findall(value or "")


# --------------------------------------------------------------------------- validation

def validate():
    """Return a list of problems, or None when there is no docs/ folder to check."""
    if not DOCS.exists():
        return None
    errors, parsed = [], {}
    for kind, spec in KINDS.items():
        if not (DOCS / spec["file"]).exists():
            errors.append(f"docs/{spec['file']} is missing")
            continue
        parsed[kind] = parse(kind, errors)

    for kind, (entries, index) in parsed.items():
        spec = KINDS[kind]
        fname = spec["file"]

        for eid, e in entries.items():
            f, where = e["fields"], f"{fname}:{e['line']}: {eid}"
            for key in spec["required"]:
                if key not in f:
                    errors.append(f"{where}: missing field '{key}'")
            status = f.get("Status", "").lower()
            if status and status not in spec["statuses"]:
                errors.append(f"{where}: invalid status '{status}' (allowed: {', '.join(sorted(spec['statuses']))})")
            for key in spec["dates"]:
                if key in f and not DATE_RE.match(f[key]):
                    errors.append(f"{where}: '{key}' must look like YYYY-MM-DD, got '{f[key]}'")

            # Supersession links (only requirements and decisions can be superseded).
            if "superseded" in spec["statuses"]:
                by = [i for i in ids_in(f.get("Superseded by")) if i.startswith(kind)]
                if status == "superseded" and not by:
                    errors.append(f"{where}: status is superseded but 'Superseded by' is missing")
                if by and status != "superseded":
                    errors.append(f"{where}: has 'Superseded by' but status is '{status}'")
                for target in by:
                    t = entries.get(target)
                    if not t:
                        errors.append(f"{where}: 'Superseded by' points to unknown {target}")
                    elif eid not in ids_in(t["fields"].get("Supersedes")):
                        errors.append(f"{where}: superseded by {target}, but {target} does not list 'Supersedes: {eid}'")
                for target in ids_in(f.get("Supersedes")):
                    t = entries.get(target)
                    if not t:
                        errors.append(f"{where}: 'Supersedes' points to unknown {target}")
                    else:
                        if t["fields"].get("Status", "").lower() != "superseded":
                            errors.append(f"{where}: supersedes {target}, but {target} is not marked superseded")
                        if eid not in ids_in(t["fields"].get("Superseded by")):
                            errors.append(f"{where}: supersedes {target}, but {target} does not list 'Superseded by: {eid}'")
                for target in ids_in(f.get("Will supersede")):
                    if target not in entries:
                        errors.append(f"{where}: 'Will supersede' points to unknown {target}")
                    if status not in spec["pending"]:
                        errors.append(f"{where}: 'Will supersede' is only for {'/'.join(sorted(spec['pending']))} entries; "
                                      f"use 'Supersedes' once it ships")

        # Index table must match the entries.
        if entries and not index:
            errors.append(f"{fname}: the Index table is missing or has no {kind}-NNN rows")
        for eid in sorted(set(entries) - set(index)):
            errors.append(f"{fname}: {eid} is not in the Index table")
        for eid in sorted(set(index) - set(entries)):
            errors.append(f"{fname}: Index lists {eid} but there is no entry for it")
        for eid in sorted(set(entries) & set(index)):
            actual = entries[eid]["fields"].get("Status", "").lower()
            if actual and index[eid] != actual:
                errors.append(f"{fname}: Index says {eid} is '{index[eid]}' but the entry says '{actual}'")

    # Every ID mentioned anywhere must exist.
    known = {eid for entries, _ in parsed.values() for eid in entries}
    for kind, spec in KINDS.items():
        path = DOCS / spec["file"]
        if not path.exists():
            continue
        in_fence = False
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for ref in sorted(set(ids_in(line)) - known):
                errors.append(f"{spec['file']}:{n}: reference to unknown {ref}")
    return errors


# --------------------------------------------------------------------------- docs-sync reminder

def changed_files():
    """Paths with uncommitted changes, or None if git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain=v1", "-uall"],
            check=False, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    paths = []
    for line in out.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip().strip('"'))
    return paths


def sync_problem():
    """Return (message, fingerprint) when source changed without docs changing, else None."""
    paths = changed_files()
    if paths is None:
        return None
    source = sorted(p for p in paths if SOURCE_RE.match(p) and not IGNORE_RE.search(p))
    if not source or any(p.startswith("docs/") for p in paths):
        return None
    sig = []
    for p in source:
        try:
            st = (ROOT / p).stat()
            sig.append((p, st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append((p, "deleted", 0))
    shown = "\n".join(f"  - {p}" for p in source[:10]) + (f"\n  ... and {len(source) - 10} more" if len(source) > 10 else "")
    message = (
        "Source files changed but nothing under docs/ was updated:\n"
        f"{shown}\n"
        "Before finishing:\n"
        "  - New or changed user-visible behaviour -> /update-use-cases (docs/use-cases.md)\n"
        "  - New or changed requirement            -> /new-requirement (docs/requirements.md)\n"
        "  - Architecture or dependency decision   -> /record-decision (docs/architecture.md)\n"
        "If none of these apply (pure refactor, typo fix), say so in your final message and finish. "
        "This reminder will not repeat for the same set of changes."
    )
    return message, hashlib.sha1(repr(sig).encode()).hexdigest()


# --------------------------------------------------------------------------- state and entry points

def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def already_told(state, key, fingerprint):
    prev = state.get(key) or {}
    return prev.get("hash") == fingerprint and time.time() - prev.get("ts", 0) < REMIND_AGAIN_AFTER


def cmd_check():
    errors = validate()
    if errors is None:
        print("No docs/ folder found; nothing to check.")
        return 0
    if errors:
        print(f"{len(errors)} problem(s) in docs/:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("docs/ OK")
    return 0


def cmd_stop():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    if payload.get("stop_hook_active"):
        return 0  # already continuing because of a previous Stop hook

    state = load_state()

    errors = validate()
    if errors:
        fp = hashlib.sha1("\n".join(errors).encode()).hexdigest()
        if not already_told(state, "errors", fp):
            state["errors"] = {"hash": fp, "ts": time.time()}
            save_state(state)
            print("docs/ has problems. Fix them before finishing "
                  "(run `python3 .claude/hooks/docs_guard.py check` to re-check):\n"
                  + "\n".join(f"  - {e}" for e in errors), file=sys.stderr)
            return 2
    elif "errors" in state:
        state.pop("errors")
        save_state(state)

    problem = sync_problem()
    if problem:
        message, fp = problem
        if not already_told(state, "sync", fp):
            state["sync"] = {"hash": fp, "ts": time.time()}
            save_state(state)
            print(message, file=sys.stderr)
            return 2
    return 0


def main(argv):
    if len(argv) != 2 or argv[1] not in ("check", "stop"):
        print(__doc__)
        return 64
    return cmd_check() if argv[1] == "check" else cmd_stop()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
