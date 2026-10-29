#!/usr/bin/env python3
"""Claude's active working time, for the "[claude HH:MM]" tag in commit messages.

Hooks (settings.json):
    timer.py prompt   UserPromptSubmit: a turn starts (time since the last Stop was Eze's, not counted)
    timer.py stop     Stop: add the time since the turn started (or since the previous Stop, when another
                      Stop hook made Claude continue)

Commands (used by /commit, /status, /end-session):
    timer.py show                       Claude time since the last commit, HH:MM (includes the current turn)
    timer.py commit <sha> <HH:MM>       record a commit (Claude time + DURATION) and reset the counter
    timer.py session                    session totals as JSON
    timer.py end-session                print the totals and start a new session

State: .claude/state/time.json (gitignored). Time spent waiting on a permission prompt inside a turn is
counted; idle time between turns is not.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
STATE_FILE = ROOT / ".claude" / "state" / "time.json"


def load():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:  # noqa: BLE001 - missing or corrupt state starts a fresh timer
        return {"since_commit": 0.0, "turn_start": None, "session_start": time.time(), "commits": []}


def save(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(STATE_FILE)


def hhmm(seconds):
    minutes = max(1, round(seconds / 60)) if seconds > 0 else 0
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def running(state, now):
    start = state.get("turn_start")
    return max(0.0, now - start) if start else 0.0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    now = time.time()
    state = load()
    if cmd in ("prompt", "stop"):
        sys.stdin.read()  # hook payload, not needed
        if cmd == "prompt":
            state["turn_start"] = now
        else:
            state["since_commit"] = state.get("since_commit", 0.0) + running(state, now)
            state["turn_start"] = now  # a blocked Stop keeps counting until the real one
        save(state)
    elif cmd == "show":
        print(hhmm(state.get("since_commit", 0.0) + running(state, now)))
    elif cmd == "commit" and len(sys.argv) == 4:
        claude = state.get("since_commit", 0.0) + running(state, now)
        state.setdefault("commits", []).append(
            {"sha": sys.argv[2], "duration": sys.argv[3], "claude": hhmm(claude), "claude_seconds": claude, "at": now})
        state["since_commit"] = 0.0
        state["turn_start"] = now if state.get("turn_start") else None
        save(state)
        print(hhmm(claude))
    elif cmd in ("session", "end-session"):
        commits = state.get("commits", [])
        human = sum(int(c["duration"][:2]) * 60 + int(c["duration"][3:]) for c in commits)
        claude = sum(c.get("claude_seconds", 0) for c in commits) + state.get("since_commit", 0.0) + running(state, now)
        print(json.dumps({
            "session_start": time.strftime("%Y-%m-%d %H:%M", time.localtime(state.get("session_start", now))),
            "commits": len(commits),
            "claude_time": hhmm(claude),
            "human_estimate": f"{human // 60:02d}:{human % 60:02d}",
            "uncommitted_claude_time": hhmm(state.get("since_commit", 0.0) + running(state, now)),
            "detail": [{k: c[k] for k in ("sha", "duration", "claude")} for c in commits],
        }, indent=1))
        if cmd == "end-session":
            save({"since_commit": state.get("since_commit", 0.0) + running(state, now), "turn_start": now,
                  "session_start": now, "commits": []})
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
