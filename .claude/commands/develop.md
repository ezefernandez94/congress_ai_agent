---
description: Plan an iteration - resolve Linear issues or a milestone, create the branch, write the plan, stop for approval
argument-hint: <EZE-N [EZE-M ...] | milestone name | "description" (no Linear issue)>
---

Target: $ARGUMENTS

Write no code in this command. It ends when the plan is shown.

1. **Resolve the target in Linear (read-only).**
   - Issue IDs: `get_issue` for each (description, acceptance criteria, milestone, relations).
   - A milestone name: list its unfinished issues, propose how to slice them into iterations (one issue
     or a small group of related ones per branch/PR, in dependency and priority order) and ask which to
     start with. Stop until Eze answers.
   - If an issue is blocked by an unfinished issue, say so and ask before continuing.
   - A free-text description (no `EZE-N`, not a milestone name): work without a Linear issue. Search
     Linear once for an open issue that already covers it; if one does, suggest using it and ask. Otherwise
     continue with no Linear: branch `<type>/<short-slug>`, `Linear: none` in the plan.
   - If an ID or milestone doesn't resolve, say so and stop.
2. **Branch.** `git status --porcelain` must be empty; if not, show it and ask what to do (don't stash or
   discard on your own). Then:
   `git checkout main && git pull --ff-only && git checkout -b <type>/<EZE-N>-<short-slug>`
   type = feat | fix | chore | refactor | test | docs; slug = 2-5 kebab-case words; for a group use the
   main issue's ID. If the branch already exists, ask.
3. **Project rules first.** For a new feature or behavior change run `/new-requirement`; for a library,
   data model or pattern choice plan a `/record-decision` step; for user-visible changes plan
   `/update-use-cases` (CLAUDE.md "Documentation workflow"). A conflict found by `/new-requirement` stops
   everything until Eze decides.
4. **Clarify.** Ask the questions you need (acceptance criteria that are vague, "Decision needed" items in
   the issue). Use AskUserQuestion when the options are clear.
5. **Write the plan** at `.claude/plans/<branch-name with / replaced by ->.md`:

   ```markdown
   # <EZE-N[, EZE-M] | type>: <title>
   Branch: <branch> · Created: <YYYY-MM-DD> · Status: awaiting approval · Linear: <IDs | none>

   ## Scope
   <what is in and, explicitly, what is out>
   ## Acceptance criteria
   - [ ] <from Linear, one per line, plus any agreed in step 4>
   ## Steps
   - [ ] 1. <small, ordered, each verifiable; include docs steps (REQ/ADR/UC) and tests>
   ## Test matrix
   | Kind | Test | Why |
   | Existing, sufficient | ... | ... |
   | To modify | ... | ... |
   | To create (test_ucNNN_...) | ... | ... |
   ## After the feature
   - /commit opens the PR into main with "Refs <IDs>"
   - Eze reviews and approves on GitHub, then /post-approve <pr>
   - Linear issues this likely completes: <IDs>
   - Known follow-ups: <...>
   ## Risks and open questions
   - ...
   ```
6. **Show the plan and STOP.** No code until Eze approves it. After approval, set `Status: approved` in the
   plan and work through it with `/continue`. Anything outside the plan needs Eze's approval first.
