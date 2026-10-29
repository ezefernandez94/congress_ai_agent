---
name: record-decision
description: Record an architecture decision in docs/architecture.md and check it against the existing decisions. Use whenever a library, framework, data model, storage format, API shape, background-job or deployment approach is chosen, changed or reversed; whenever a new dependency is proposed; and whenever the user says "let's go with X" about a technical approach, even if they do not ask for it to be documented.
---

# Record a decision

Claude proposes; **only the user accepts.** Never mark a decision `accepted` unless the user clearly chose it.

## 1. Read

1. Open `docs/architecture.md` and read the **Index** first, then the entries that look related.
2. Re-read "Invariants worth preserving" in CLAUDE.md.

## 2. Check for a clash

Does the decision contradict an `accepted` ADR or an invariant? If so, **stop** and tell the user:

> **Clashes with ADR-00x — "<title>"**
> New decision: <one line>. Existing: <one line>. Options: (a) don't, (b) supersede ADR-00x, (c) adjust so
> both hold. My recommendation: <one option and why>.

Wait for the answer before writing anything.

## 3. Write the entry

1. New ID = highest existing ADR number + 1, zero-padded to three digits. Date: run `date +%F`.
2. Use the template at the bottom of `docs/architecture.md`. Keep Context, Decision and Consequences to a few
   lines each, and name the alternatives that were rejected in Context.
3. Status:
   - `accepted` only after the user explicitly chose it ("let's go with it", "yes, do it").
   - Otherwise `proposed`, and say in your reply which decision is still pending.
4. Link the requirements it serves in `Related:` and add the row to the Index table.
5. If it reverses an earlier decision: set the old entry to `superseded` with `Superseded by: ADR-NNN`, add
   `Supersedes: ADR-xxx` to the new one, and update both Index rows. **Never delete an entry.**
   If it will replace an accepted ADR only once implemented, use `Will supersede:` on the `proposed` entry.

## 4. New dependencies

Adding a package to `pyproject.toml` (and so `uv.lock`), or a vendored script under `app/web/static/`,
needs an ADR and the user's approval **before** you install it. Say why FastAPI, SQLAlchemy, the packages
already in `pyproject.toml`, the standard library or the existing web stack (Jinja2 + HTMX) cannot do the
job. A new external API (paid or not) counts as a dependency too.

## 5. Finish

1. Run `python3 .claude/hooks/docs_guard.py check` and fix what it reports.
2. If the decision creates a hard rule that future code must follow, suggest adding one line to the
   "Invariants worth preserving" list in CLAUDE.md. Do not edit CLAUDE.md without the user's approval.
