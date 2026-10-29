---
description: Execute the approved plan of the current branch from the first unchecked step
argument-hint: [EZE-N | branch]
---

Argument (optional): $ARGUMENTS

1. Branch = `git branch --show-current`. If it is `main`, stop: there is no plan on main.
   If an argument is given and the branch does not contain it, tell Eze and stop.
2. Load `.claude/plans/<branch with / replaced by ->.md`. If it is missing, stop and suggest `/develop`.
   If its status is not `approved`, show the plan and ask for approval; don't start.
3. From the first unchecked step, for each step:
   - do exactly what the step says, following CLAUDE.md (invariants, conventions, docs workflow);
   - run the relevant tests for what changed (single test file or test, see CLAUDE.md "Commands");
   - when the step is done and its tests pass, tick it (`- [x]`) in the plan file right away.
4. **Deviations:** if a step turns out wrong, incomplete, or the work needs something not in the plan
   (a new file area, a dependency, a behavior change), stop, propose the plan change and wait. Never
   expand scope silently.
5. **Failures:** if a test fails and the fix isn't obvious and inside the step, stop and report the test,
   the error and the likely cause. Don't skip, disable or weaken tests.
6. Don't commit. Stop when every step is ticked or you are blocked, and summarize in a few lines:
   steps done (n/total), tests run and results, what's next (`/commit`, or the blocker).
