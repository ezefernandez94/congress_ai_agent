---
description: Quick read-only status - branch, tree, plan progress, PRs, Claude time, last handoff
---

Read-only and fast: run these in parallel, no Linear calls, then print at most ~10 lines.

- `git branch --show-current` and `git status --short | head -20` (clean / n files changed)
- plan `.claude/plans/<branch with / replaced by ->.md`: done/total checkboxes under "Steps" and the
  first unchecked step (or "no plan")
- `gh pr list --author @me --state open --json number,title,headRefName,reviewDecision,url`
- `python3 .claude/hooks/timer.py show` → Claude time since the last commit
- last handoff: the date in `HANDOFF.md`'s title (or its mtime), else the newest file in `.claude/handoffs/`,
  else "none"

Format:
```
Branch    feat/EZE-12-contact-disambiguation · 3 files changed
Plan      4/7 · next: 5. Agent tool tests
PRs       #14 EZE-12: ... (review required)
Claude    00:42 since last commit
Handoff   2026-10-27 18:10
```
