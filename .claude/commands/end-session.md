---
description: Archive the previous handoff and write a new HANDOFF.md for the next session
---

Don't change Linear. Don't commit.

1. If `HANDOFF.md` exists, move it to `.claude/handoffs/<YYYY-MM-DD-HHMM>.md` (use its own date if it
   has one, else `date +%Y-%m-%d-%H%M`; create the folder if needed).
2. Gather: `git branch --show-current`, `git log -1 --oneline`, `git status --short`,
   `gh pr list --author @me --state open --json number,title,reviewDecision,url`, the plan file's progress
   (done/total, next unchecked step), and `python3 .claude/hooks/timer.py end-session` (prints this
   session's totals and starts a new session count).
3. Write `HANDOFF.md` at the repo root:

   ```markdown
   # Handoff — <YYYY-MM-DD HH:MM>

   ## UNFINISHED - resume here
   <exactly what was started and not finished, and the next concrete step (command + what to do)>
   <or: "Nothing unfinished.">

   ## State
   - Branch: ... · Last commit: ...
   - Uncommitted changes: <none | list>
   - Open PRs: #n <title> — <waiting for review | approved, run /post-approve n | ...>
   - Plan: <file> — <done>/<total>, next: <step>

   ## This session
   - Worked on: ...
   - Decisions (and why): ...
   - Linear issues touched: ...
   - Open questions / blockers: ...
   - Gotchas: ...
   - Totals: <commits> commits · Claude <HH:MM> · human estimate <HH:MM>
   ```
4. If the session produced a rule that belongs in CLAUDE.md, propose it (text and section) at the end of
   your reply. Don't add it yourself.
