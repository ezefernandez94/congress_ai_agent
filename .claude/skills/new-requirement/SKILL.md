---
name: new-requirement
description: Check a new feature request or behavior change against docs/requirements.md BEFORE any code is written, flag conflicts or duplicates with existing requirements, and record the new requirement. Use this whenever the user asks to add, change, remove or reverse app behavior ("add...", "I want the app to...", "instead of X do Y", "remove...", "support..."), or proposes a feature, even if they never mention requirements or docs.
---

# New requirement

Goal: no behavior change gets built until it has been compared with what the project already promises.

## 1. Read

1. Open `docs/requirements.md` and read the **Index** first. Open full entries only for IDs that look related
   (same area, same nouns, same Telegram command, agent tool, web page or endpoint).
2. Skim the headings in `docs/architecture.md`. Open an ADR if the request touches a library, a data model,
   or a pattern.
3. Re-read "Invariants worth preserving" in CLAUDE.md. They are constraints too.

## 2. Restate

Write the request as one testable sentence: "When X, the app does Y." Show it to the user only if the
request was ambiguous.

## 3. Compare

For every related `active` or `planned` requirement, and every relevant ADR or invariant, ask: can both be
true at once? Look for:

- **Contradiction**: same situation, different outcome.
- **Constraint violation**: breaks an accepted ADR or an invariant (for example, a separate web password
  login contradicts ADR-008, which reuses the `bot_users` allowlist through the Telegram Login Widget).
- **Duplicate**: already required, or already built.
- **Hidden dependency**: it forces a decision on a `proposed` ADR or a `planned` requirement.

## 4. If there is a conflict or a duplicate: STOP

Do not write code and do not edit the docs yet. Tell the user, in this shape:

> **Conflict with REQ-0xx — "<title>"**
> New request: <one line>. Existing: <one-line quote>. Why they clash: <one sentence>.
> Options: (a) drop the new request, (b) override it and supersede REQ-0xx, (c) adjust the request so both
> hold: <suggestion>.
> My recommendation: <one option and why>.

Wait for the answer. A hidden dependency is not a conflict: mention it and continue.

## 5. Record

After there is no conflict, or after the user has decided:

1. New ID = highest existing REQ number + 1, zero-padded to three digits.
2. Append the entry, using the template at the bottom of `docs/requirements.md`.
   - Status `active` if it is being built now, `planned` if later.
   - `Source: user-request` only if the user actually asked for it. Anything you added on your own is
     `claude-suggested`.
   - Date: run `date +%F`.
3. Add its row to the Index table.
4. If the user overrode an older requirement: set the old one to `superseded` with
   `Superseded by: REQ-NNN`, add `Supersedes: REQ-xxx` to the new one, and update both Index rows.
   **Never delete an entry.**
5. If the new requirement is `planned` and will replace an `active` one only when it ships, use
   `Will supersede: REQ-xxx` instead. The old one stays `active` until then.
6. Run `python3 .claude/hooks/docs_guard.py check` and fix whatever it reports.

## 6. Hand off

- The request needs a technical choice (library, data model, pattern): run `/record-decision`.
- Once the behavior is built: run `/update-use-cases`.
