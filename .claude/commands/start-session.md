---
description: Start a work session - show what is unfinished, or propose the next iteration from Linear
---

Read-only. Don't start any work. Keep the output short (under ~20 lines).

1. Read `HANDOFF.md` at the repo root. If it is missing, say "No HANDOFF.md" and continue. Show its
   "UNFINISHED - resume here" block verbatim if it says anything other than "Nothing unfinished".
2. Gather, in parallel:
   - `git status --short`, `git branch --show-current`, `git log -1 --oneline`
   - `gh pr list --author @me --state open --json number,title,headRefName,reviewDecision,url`
   - plan files with unchecked steps: `grep -l -- '- \[ \]' .claude/plans/*.md 2>/dev/null`
   - `python3 .claude/hooks/timer.py show`
3. If anything is unfinished (UNFINISHED block, uncommitted changes, a plan with unchecked steps, an open PR
   waiting for Eze's review or for `/post-approve`), list each item in one line and recommend the next
   command (`/continue`, `/commit`, `/post-approve <n>`, or "review PR #n on GitHub"). Then stop.
4. If nothing is unfinished, query Linear (project `congress-bot-76da1c024bec`, team EZE) read-only:
   - milestones in order (`list_milestones`); the next phase is the first milestone with issues whose
     status type is not completed/canceled;
   - in that milestone, the highest-priority issue(s) in Todo/Backlog that are not blocked by an unfinished
     issue (check `blockedBy` relations with `get_issue` and `includeRelations`). Skip "gate" issues
     until the phase's other issues are done.
   Propose one iteration: issue IDs, titles, a 1-2 line summary of the acceptance criteria, and the
   command to start it, e.g. `/develop EZE-5`. Group issues into one iteration only if they are small and
   clearly related.
5. Stop and wait.
