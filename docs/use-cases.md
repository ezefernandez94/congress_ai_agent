# Use cases

What a person can do with the product, step by step. This is the source for tests: each use case should end
up with at least one test named `test_ucNNN_<scenario>`. Maintained by Claude Code through the
`/update-use-cases` skill. Check the file with `python3 .claude/hooks/docs_guard.py check`.

**Rules**

- IDs are permanent (`UC-NNN`). Entries are never deleted: a removed behaviour becomes `deprecated`.
- Statuses: `planned` (agreed, not built), `unverified` (the product is believed to do this, but no test or
  manual check confirms it), `implemented` (built and covered by a test or checked by the user),
  `deprecated` (no longer offered).
- Every entry was reconstructed from the code on 2026-10-28. They are `unverified`: the test suite is empty.
- "User" means an active user in `bot_users`; "Owner" is a user with `is_owner`; "Visitor" is anyone else.
- Keep the Index table in sync with the entries. The validator checks it.

## Index

| ID | Title | Status |
|----|-------|--------|
| UC-001 | Save a contact from a text message | unverified |
| UC-002 | Save a contact from a voice note | unverified |
| UC-003 | Save a contact from a badge photo | unverified |
| UC-004 | Log a conversation with someone already saved | unverified |
| UC-005 | Turn a commitment into a task | unverified |
| UC-006 | See and complete pending tasks | unverified |
| UC-007 | Get briefed before a meeting | unverified |
| UC-008 | Enrich a contact from LinkedIn | unverified |
| UC-009 | Draft a follow-up email | unverified |
| UC-010 | Receive the morning digest | unverified |
| UC-011 | Turn my digest on or off | unverified |
| UC-012 | Add or remove a user | unverified |
| UC-013 | Find my Telegram ID | unverified |
| UC-014 | Sign in to the web UI | unverified |
| UC-015 | Manage and export records in the web UI | unverified |
| UC-016 | Chat with the agent from the web | unverified |
| UC-017 | See my recent contacts | unverified |
| UC-018 | Prepare before the conference | unverified |
| UC-019 | Export everything after the conference | unverified |
| UC-020 | A stranger messages the bot | unverified |

## Capture

### UC-001 — Save a contact from a text message
- Status: unverified
- Actor: User
- Requirements: REQ-001, REQ-019
- Tests: tests/test_repositories/test_person_repo.py::test_uc001_contact_saved_and_found (storage only; the agent flow is untested)

1. The user writes "Just met Ana Pérez, CTO at Acme, interested in a pilot".
2. The agent calls `create_contact` (creating the company if new) and replies with what was saved and any tasks.

Alternate: a long or complex request first gets "⏳ On it...".
Expected: one `people` row linked to a `companies` row; the reply names the person.

### UC-002 — Save a contact from a voice note
- Status: unverified
- Actor: User
- Requirements: REQ-002
- Tests: none yet

1. The user sends a voice note.
2. The bot replies "🎙 Transcribing...", transcribes it, then sends "_Heard: <transcript>_" and the agent's reply.

Alternate: transcription fails → "Sorry, I couldn't transcribe that voice note. Please try again." and nothing
is saved.
Expected: the history stores `[Voice note]: <transcript>`.

### UC-003 — Save a contact from a badge photo
- Status: unverified
- Actor: User
- Requirements: REQ-003
- Tests: none yet

1. The user sends a badge photo, optionally with a caption.
2. The bot replies "📸 Reading badge...", sends the largest photo size to the agent, which saves the contact.

Alternate: an unreadable field is left empty, not guessed.
Expected: the history stores `[Badge photo] <caption>`, not the image.

### UC-004 — Log a conversation with someone already saved
- Status: unverified
- Actor: User
- Requirements: REQ-004, REQ-006
- Tests: none yet

1. The user describes a conversation with a saved contact.
2. The agent calls `log_interaction`; the interaction is stored and the contact's last (and, if empty, first)
   interaction date is set.

Alternate: no match → the agent says so. Several matches → the agent lists them and asks which one.
Expected: nothing is written when the name is ambiguous.

## Tasks

### UC-005 — Turn a commitment into a task
- Status: unverified
- Actor: User
- Requirements: REQ-005
- Tests: none yet

1. The user mentions a commitment ("I'll send her the deck by Friday").
2. The agent creates a task linked to the person, with type, priority and due date, and confirms the date.

Alternate: an invalid date is dropped and the task is saved without one.

### UC-006 — See and complete pending tasks
- Status: unverified
- Actor: User
- Requirements: REQ-005, REQ-020, REQ-017
- Tests: none yet

1. The user sends `/tasks`, asks the agent, or opens Tasks on the web.
2. Pending tasks are shown by priority (up to 10 on Telegram).
3. The user completes one by asking the agent (by ID or title) or with the web "complete" button.

Alternate: no task matches → "Task not found".
Expected: status `completed` and `completed_at` set.

## Intel and follow-up

### UC-007 — Get briefed before a meeting
- Status: unverified
- Actor: User
- Requirements: REQ-007, REQ-006
- Tests: none yet

1. The user writes "Brief me on Ana".
2. The agent calls `get_contact_brief`, then `generate_meeting_prep`, and replies with a short brief.

Alternate: several matches → the agent asks which one. No stored data → it says so and offers enrichment.
Expected: no call to Proxycurl or Tavily.

### UC-008 — Enrich a contact from LinkedIn
- Status: unverified
- Actor: User
- Requirements: REQ-008
- Tests: none yet

1. The user asks to enrich a contact, or gives their LinkedIn URL.
2. The agent calls `enrich_contact`; Proxycurl's headline and summary are stored with `enrichment_source =
   proxycurl` and `enriched_at`.

Alternate: no LinkedIn URL on the contact or in the message → nothing is fetched. A Proxycurl error → "Enrichment failed: ...".
Expected: creating a contact never calls Proxycurl.

### UC-009 — Draft a follow-up email
- Status: unverified
- Actor: User
- Requirements: REQ-010
- Tests: none yet

1. The user asks for a follow-up to a contact, optionally with tone and points to include.
2. The agent returns a draft built from the stored record and asks whether to adjust it.

Expected: nothing is sent; no external API other than Anthropic is called.

## Digest

### UC-010 — Receive the morning digest
- Status: unverified
- Actor: User
- Requirements: REQ-011
- Tests: none yet

1. At the configured time, every active user with the digest on gets the digest in Telegram.
2. Any user can get it on demand with `/digest` or by asking the agent.

Alternate: no recipients → nothing is sent. A failed send to one user → the others still get it.

### UC-011 — Turn my digest on or off
- Status: unverified
- Actor: User
- Requirements: REQ-012
- Tests: none yet

1. The user sends `/digest_off` (or `/digest_on`).
2. The bot confirms; only the sender's `receives_digest` changes.

Alternate: an owner toggles anyone's digest from the web users page.

## Access

### UC-012 — Add or remove a user
- Status: unverified
- Actor: Owner
- Requirements: REQ-015, REQ-024
- Tests: tests/test_bot/test_router_users.py::test_uc012_adduser_joins_adders_workspace, tests/test_bot/test_router_users.py::test_uc012_adduser_refuses_user_in_other_workspace, tests/test_bot/test_router_users.py::test_uc012_adduser_reenables_revoked_member, tests/test_bot/test_auth.py::test_uc012_authorize_returns_caller, tests/test_bot/test_auth.py::test_uc012_authorize_without_membership_denies, tests/test_bot/test_auth.py::test_uc012_authorize_db_error_denies, tests/test_bot/test_auth.py::test_uc012_seeded_owner_becomes_admin_of_default, tests/test_bot/test_auth.py::test_uc012_seeding_keeps_existing_membership, tests/test_core/test_tenancy.py::test_uc012_member_resolves_to_workspace, tests/test_core/test_tenancy.py::test_uc012_user_without_membership_denied, tests/test_core/test_tenancy.py::test_uc012_unknown_user_denied, tests/test_core/test_tenancy.py::test_uc012_inactive_member_denied, tests/test_web/test_auth.py::test_uc012_web_member_gets_caller, tests/test_web/test_auth.py::test_uc012_web_user_without_membership_redirected_to_login, tests/test_web/test_auth.py::test_uc012_web_db_error_denies, tests/test_web/test_auth.py::test_uc012_web_add_joins_adders_workspace, tests/test_web/test_auth.py::test_uc012_web_add_refuses_user_in_other_workspace (removing a user is still untested)

1. The owner sends `/adduser <telegram id> [name]` (or adds them on the web Users page).
2. The new person joins the owner's workspace and can use the bot (a revoked user is re-enabled). The bot
   tells them to send /start.
3. Later the owner sends `/removeuser <telegram id>`; that person is ignored from then on, in Telegram and the web.

Alternate: a non-owner → "Only an owner can add users." / "...remove users.". Bad ID → "not a valid Telegram ID".
Already active → "That user already has access." Someone in another workspace → "That user belongs to
another workspace." A user with no workspace is ignored like an unknown one. Removing yourself → refused. Removing an owner → refused,
with a hint to remove them from the env first. Unknown ID → "No such user."

### UC-013 — Find my Telegram ID
- Status: unverified
- Actor: Visitor
- Requirements: REQ-014
- Tests: none yet

1. Anyone sends `/whoami`.
2. The bot replies with their Telegram ID and how to get access.

### UC-020 — A stranger messages the bot
- Status: unverified
- Actor: Visitor
- Requirements: REQ-014
- Tests: none yet

1. Someone not in `bot_users`, revoked, or without a workspace sends any message or command other than
   `/whoami`.
2. The bot does not answer and logs `unauthorized_message`.

Alternate: the database is unreachable → the message is also ignored (fail closed).

## Web

### UC-014 — Sign in to the web UI
- Status: unverified
- Actor: User
- Requirements: REQ-016
- Tests: none yet

1. In production the user opens the site, lands on `/login` and signs in with the Telegram widget.
2. `/auth/telegram` checks the signature and age, and that the account is an active bot user, then opens a session.

Alternate: bad signature, stale payload or unknown user → back to login. Revoked mid-session → the next request
logs them out. In development the user is signed in as the first owner; with no owner seeded the login page
explains how to seed one. A non-owner opening the users page is redirected with an error.

### UC-015 — Manage and export records in the web UI
- Status: unverified
- Actor: User
- Requirements: REQ-017
- Tests: none yet

1. The user opens the dashboard, then any entity list (people, companies, tasks, opportunities, interactions,
   meetings, notes, conferences).
2. They filter, page, create, view, edit or delete records, or download the list as CSV.

Alternate: activating a conference makes it the one the agent uses.
Expected: the CSV has every column except embeddings.

### UC-016 — Chat with the agent from the web
- Status: unverified
- Actor: User
- Requirements: REQ-018
- Tests: none yet

1. The user opens `/chat`; it shows the last 20 messages, including those from Telegram.
2. They send a message; the agent replies and the log refreshes.

Alternate: an empty message is ignored.

## Telegram

### UC-017 — See my recent contacts
- Status: unverified
- Actor: User
- Requirements: REQ-020
- Tests: none yet

1. The user sends `/contacts`.
2. The bot lists up to 10 contacts added in the last 3 days with their role.

Alternate: none → "No contacts added in the last 3 days."

## Scripts

### UC-018 — Prepare before the conference
- Status: unverified
- Actor: Owner
- Requirements: REQ-021
- Tests: none yet

1. The owner runs `scripts/seed_conference.py` and answers the prompts; the conference is saved as active.
2. They run `scripts/batch_enrich.py --input attendees.csv`; each row is saved and enriched, one per second.
3. A summary is printed and written to `enriched_contacts_summary.txt`.

### UC-019 — Export everything after the conference
- Status: unverified
- Actor: Owner
- Requirements: REQ-022
- Tests: none yet

1. The owner runs `scripts/export_crm.py --format csv`.
2. Contacts, interactions, tasks and opportunities are written to one CSV file each.

Alternate: `--format airtable` or `notion` prints "not yet implemented".

## Template

```markdown
### UC-NNN — Short title
- Status: planned | unverified | implemented | deprecated
- Actor: User
- Requirements: REQ-NNN
- Tests: tests/test_x/test_y.py::test_ucNNN_scenario  (or "none yet")

1. Step the user takes.
2. What the app does.

Alternate: other paths, including errors.
Expected: anything a test should assert.
```
