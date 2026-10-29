---
description: Check, commit with DURATION (Clockify), push and open or update the PR into main
---

Never approve or merge in this command.

1. **Preconditions.** `git branch --show-current` must not be `main` (refuse and stop). Read the plan file
   of the branch (`.claude/plans/<branch with / replaced by ->.md`) for the issue IDs and progress.
   No `EZE-N` in the branch = work without a Linear issue: no ID in the subject, PR title
   `<type>: <summary>`, and "None" in the PR's Linear section.
2. **Checks** for the parts touched (`git status --porcelain`, `git diff --name-only main...`), per
   CLAUDE.md "Development workflow → Checks": always the import smoke test and docs check, ruff on the
   changed `.py` files, `alembic check` when `app/models/` changed, and the tests for what changed. If any
   fails, stop and report the output. Don't commit, don't work around it.
3. **Stage deliberately.** Review `git status` and the diff. `git add <paths>` for the files that belong
   to this change only. Never `add -A`/`add .`/`commit -a`. Never stage `.env` files, keys, credentials,
   `HANDOFF.md`, `.claude/plans|state|handoffs`, build output, data dumps in the repo root (`*.csv`,
   `*.sql`, `*.odt`, `*.txt` exports: they can hold real contacts), or files unrelated to the plan (mention
   those to Eze instead).
4. **Times.**
   - Claude time: `python3 .claude/hooks/timer.py show` → `HH:MM`.
   - DURATION: your estimate of how long a human developer would take to write this diff (read it:
     size, complexity, tests, docs), zero-padded `HH:MM`. Not your run time.
5. **Message** (repo convention, conventional commits with the Linear ID):
   ```
   <type>(<scope>): <EZE-N> <imperative summary> [claude HH:MM]

   <optional body: what and why, wrapped at ~100 chars>

   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   ```
   Escape each single quote in the message as `'\''`. Commit exactly as:
   `DURATION="HH:MM" git commit -m '<message>'`
   DURATION is required even while the Clockify commit-msg hook is not installed in this repo (the guard
   enforces it). If the hook rejects the commit (missing env, Clockify error), stop and report its output.
   Don't retry with other flags and never use `--no-verify`.
6. **Record:** `python3 .claude/hooks/timer.py commit <short-sha> <DURATION>`.
7. **Push:** `git push -u origin <branch>` (normal push only).
8. **PR.** `gh pr view --json number,url,state 2>/dev/null` for the branch.
   - Write the body to `.claude/state/pr-body.md`:
     ```markdown
     ## Summary
     <2-5 bullets>
     ## Plan progress
     <n/total steps; list unchecked steps if any>
     ## Tests
     - Added: ... / Modified: ... / Run: <commands> → <results>
     ## Linear
     Refs EZE-N
     Refs EZE-M
     ## Notes for the reviewer
     <risks, decisions, things to check by hand>
     ```
     Never use closing keywords (Closes/Fixes/Resolves/Completes/Implements + ID): Eze decides what is done.
   - No PR: `gh pr create --base main --title "<EZE-N>: <summary>" --body-file .claude/state/pr-body.md`
   - PR exists: `gh pr edit <n> --body-file .claude/state/pr-body.md`
9. **Report:** PR URL, the commit subject, DURATION with one line of reasoning, Claude time, checks run.
