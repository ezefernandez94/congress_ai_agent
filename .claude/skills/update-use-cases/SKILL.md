---
name: update-use-cases
description: Add or update use cases in docs/use-cases.md after user-visible behavior is added, changed or removed, and derive tests from them. Use whenever a feature ships or changes what a person can do in the app, whenever the user asks for tests, test coverage or "what can a user do", and when finishing any task that touched Telegram commands or handlers, agent tools, web pages, endpoints, scheduled jobs or scripts.
---

# Update use cases

`docs/use-cases.md` lists what a person can do in the app. It is also where tests come from.

## 1. Read

Open `docs/use-cases.md` and read the **Index** first. Open the entries related to the behavior that changed,
and the requirements they point to in `docs/requirements.md`.

## 2. Add, change or retire entries

- New behavior: add a `UC-NNN` entry using the template at the bottom of the file. New ID = highest existing
  UC number + 1, zero-padded to three digits.
- Changed behavior: edit the existing entry. Keep its ID.
- Removed behavior: set `Status: deprecated`. **Never delete an entry.**
- Update the Index table to match.

Every use case must list at least one requirement in `Requirements:`. If none fits, the behavior has no
requirement yet: run `/new-requirement` first.

## 3. Choose the status honestly

| Situation | Status |
|---|---|
| Agreed but not built | `planned` |
| Built, but no test and the user has not confirmed it | `unverified` |
| Built and a passing test covers it, or the user confirmed it works | `implemented` |

Never set `implemented` just because the code looks right.

## 4. Tests

Write tests when the user asks for them, or when behavior changed and no test covers the use case.

1. One test per main flow and one per alternate flow in the entry.
2. Name them `test_ucNNN_<scenario>` in lowercase, for example `test_uc006_ambiguous_name_returns_matches`.
   Start the docstring with `UC-NNN: <title>`.
3. Follow the testing rules in CLAUDE.md "Development workflow → Tests" (real PostgreSQL with pgvector;
   mock only external services: Anthropic, OpenAI, Telegram, Proxycurl, Tavily).
4. Run the tests with `uv run pytest` (commands are in CLAUDE.md "Commands").
5. Put the passing tests in the entry's `Tests:` field as pytest node IDs
   (`tests/test_agent/test_tools.py::test_uc006_...`), then set the status.

## 5. Finish

1. Run `python3 .claude/hooks/docs_guard.py check` and fix what it reports.
2. Tell the user: use cases added, changed or deprecated; tests written and their result; any behavior that
   has no requirement.
