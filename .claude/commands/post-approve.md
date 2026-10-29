---
description: After Eze approves a PR - merge main in, run everything, squash-merge the PR, then update Linear as told
argument-hint: [pr-number]
---

PR: $ARGUMENTS

This is the only command that merges and the only one that changes Linear statuses. Stop at the first
problem and report it.

1. **Identify the PR.** If no number was given: the PR of the current branch
   (`gh pr view --json number,title,headRefName,url`), else Eze's most recent open PR
   (`gh pr list --author @me --limit 1`). Show number, title and URL and ask Eze to confirm it is the right
   one. Wait.
2. **Check state:** `gh pr view <n> --json state,baseRefName,headRefName,reviewDecision,reviews,mergeable`.
   It must be OPEN with base `main`. GitHub does not let the author approve their own PR, so if there is
   no formal approval, ask Eze to confirm that they approved it. Wait.
3. **Unlock the merge** for this PR (the guard hook requires it, valid 3 hours):
   `mkdir -p .claude/state && printf '{"pr": %s, "created": %s, "linear_issues": []}\n' <n> "$(date +%s)" > .claude/state/post-approve.json`
4. **Update the branch.** `git status --porcelain` must be empty. `git checkout <headRefName>`,
   `git pull --ff-only` if behind its remote, `git fetch origin`, then
   `DURATION="HH:MM" git merge origin/main` (never rebase). DURATION = your estimate of the human time of
   the merge work (small when there are no conflicts, e.g. `00:05`). "Already up to date" makes no commit.
   - Conflicts: resolve them preserving the intent of both sides; explain each non-trivial resolution.
     If a conflict is ambiguous or you aren't confident, stop and ask (`git merge --abort` only if Eze
     says so). Then `git add <files>` and `DURATION="HH:MM" git commit --no-edit`.
   - If the commit-msg hook rejects the merge commit, stop and report.
5. **Run everything** (CLAUDE.md "Development workflow → Checks", the full test suite and ruff on every
   file the PR touches). If anything
   fails: stop and report which tests, the likely cause and a proposed fix. Don't push, don't merge, and
   change nothing beyond the merge resolution.
6. **Push and merge.** `git push` (normal). Then:
   - `gh pr checks <n>`: every check must pass (the repo has no CI today; say "no checks configured").
   - `gh pr view <n> --json reviewDecision,reviews`: if an approval existed before the push and is now
     gone or dismissed, stop and tell Eze.
   - `gh pr merge <n> --squash` (Eze gets a final confirmation prompt). Never `--delete-branch`, never
     `--admin`. Don't delete branches.
   - `git checkout main && git pull --ff-only`.
7. **Linear.** If the PR has no Linear issue (no `EZE-N` in branch, commits or `Refs`), say so, still do
   the "seems to cover" check below, and skip to step 9 unless Eze names issues.
   Otherwise collect the issues this PR solved from the branch name, commit messages, the PR's `Refs`
   lines and the plan file. List them as `<ID>: <title> - <one-line description of what was done>`.
   Then check the milestone's other open issues and the plan's "After the feature" section for issues this
   work seems to cover but that are not on the list, and remind Eze to consider them. Ask which to mark
   Done. Wait.
8. When Eze answers, write the named IDs into the marker
   (`"linear_issues": ["EZE-N", ...]` in `.claude/state/post-approve.json`), then for each one only:
   `save_issue` with `id` and `state: "Done"` and nothing else. Mark only those.
9. Remove the marker (`rm .claude/state/post-approve.json`) and summarize: merged PR, merge commit on
   main, issues marked Done, suggested next step (`/start-session` or `/end-session`).
