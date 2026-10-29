# Requirements

What the product must do, plus the constraints it must respect. Maintained by Claude Code through the
`/new-requirement` skill (see CLAUDE.md → Documentation workflow). Check the file with
`python3 .claude/hooks/docs_guard.py check`.

**Rules**

- IDs are permanent (`REQ-NNN`). Entries are never deleted: a replaced requirement becomes `superseded`.
- Statuses: `active` (in force today), `planned` (agreed, not built yet), `superseded` (replaced; see "Superseded by").
- Source: `user-request`, `claude-suggested` (needs the user's confirmation) or `backfill: <file>`
  (reconstructed from an existing document or the code; the user should confirm it).
- Every entry below dated 2026-10-28 was reconstructed from CLAUDE.md, README.md and the code. Correct them
  if they are wrong.
- Keep the Index table in sync with the entries. The validator checks it.

## Index

| ID | Title | Status | Area |
|----|-------|--------|------|
| REQ-001 | Capture a contact from a text message | active | Capture |
| REQ-002 | Capture a contact from a voice note | active | Capture |
| REQ-003 | Capture a contact from a badge photo | active | Capture |
| REQ-004 | Log an interaction with an existing contact | active | Capture |
| REQ-005 | Turn commitments into tasks | active | Tasks |
| REQ-006 | Never guess which contact the user means | active | Agent |
| REQ-007 | Brief me on a contact before a meeting | active | Intel |
| REQ-008 | LinkedIn enrichment only on request | active | Intel |
| REQ-009 | Web search about a person or company | active | Intel |
| REQ-010 | Follow-up drafts from stored context, never sent automatically | active | Follow-up |
| REQ-011 | Morning digest | active | Digest |
| REQ-012 | Each user turns their own digest on or off | active | Digest |
| REQ-013 | Conference summary | active | Digest |
| REQ-014 | Only allowlisted Telegram users can use the product | active | Access |
| REQ-015 | Owners add and remove users | active | Access |
| REQ-016 | Web UI behind the same allowlist | active | Web |
| REQ-017 | Manage and export every record from the web | active | Web |
| REQ-018 | One conversation across Telegram and the web | active | Agent |
| REQ-019 | Short, mobile-friendly replies | active | Agent |
| REQ-020 | Quick Telegram commands for tasks and recent contacts | active | Telegram |
| REQ-021 | Pre-conference seeding and bulk enrichment | active | Scripts |
| REQ-022 | Post-conference CRM export | active | Scripts |
| REQ-023 | Semantic search over contacts and interactions | planned | Search |
| REQ-024 | Each organization's data is isolated in its own workspace | planned | Tenancy |
| REQ-025 | Every member sees everything in their workspace | planned | Tenancy |
| REQ-026 | Admins see everything, members see only their own records | planned | Tenancy |
| REQ-027 | Every record remembers who created it | planned | Tenancy |
| REQ-028 | Workspace admins and members | planned | Access |
| REQ-029 | Platform admins create workspaces | planned | Access |
| REQ-030 | Joining is by invitation only | planned | Access |
| REQ-031 | Usage metering per workspace | planned | Usage |
| REQ-032 | Usage quotas per workspace | planned | Usage |
| REQ-033 | An organization can get its own deployment | planned | Deployment |
| REQ-034 | Any member creates and manages events | planned | Events |
| REQ-035 | Records can be assigned to one event | planned | Events |
| REQ-036 | Export and delete a workspace's data | planned | Privacy |
| REQ-037 | Event lifecycle and attendance | planned | Events |
| REQ-038 | Bulk-assign records to an event from the web | planned | Events |

## Capture

### REQ-001 — Capture a contact from a text message
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-001, ADR-003

When the user writes that they met someone, the agent saves a contact (name plus whatever role, company,
type, interest, how they met and notes were given) and confirms what it saved.

### REQ-002 — Capture a contact from a voice note
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-002, ADR-004

When the user sends a Telegram voice note, it is transcribed, the transcript is echoed back so the user can
check it, and the text is handled like a typed message. A failed transcription produces an apology, not a crash.

### REQ-003 — Capture a contact from a badge photo
- Status: active
- Source: backfill: code (app/bot/handlers.py)
- Added: 2026-10-28
- Related: UC-003

When the user sends a photo of a conference badge (optionally with a caption), the agent reads name,
company and role, saves the contact, and leaves out any field it cannot read rather than guessing.

### REQ-004 — Log an interaction with an existing contact
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-004

When the user describes a conversation with someone already saved, the agent records it (summary, topics,
sentiment, commitments) and updates the contact's first and last interaction dates.

## Tasks

### REQ-005 — Turn commitments into tasks
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-005, UC-006

When a commitment is mentioned ("I'll send them the deck"), the agent creates a task with type, priority and
due date, and confirms the due date. Users can list pending tasks and mark them completed.

## Agent

### REQ-006 — Never guess which contact the user means
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-004, UC-007

When a name matches more than one contact, the agent shows the matches and asks which one; it never picks
one silently. Known gap: `log_interaction` and `get_contact_brief` follow this, but `create_task`,
`get_pending_tasks`, `enrich_contact`, `draft_followup` and `generate_meeting_prep` take the first match.

### REQ-018 — One conversation across Telegram and the web
- Status: active
- Source: backfill: code (app/services/conversation.py)
- Added: 2026-10-28
- Related: UC-016, ADR-011

When a user talks to the agent on Telegram or in the web chat, both share one history, keyed by their
Telegram user ID, and the agent sees the last 20 messages.

### REQ-019 — Short, mobile-friendly replies
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: ADR-003

Replies are brief and readable on a phone: briefs at most 5 bullets, task lists at most 7 items, follow-up
drafts at most 6 sentences, emojis only where they help scanning.

## Intel

### REQ-007 — Brief me on a contact before a meeting
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-007

When the user asks to be briefed on someone, the agent returns what is stored (bio, enrichment, recent
interactions, open tasks) and a short pre-meeting brief built only from stored data, with no external calls.

### REQ-008 — LinkedIn enrichment only on request
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-008, ADR-005

Proxycurl is called only when the user asks for enrichment or gives a LinkedIn URL, never when a contact is
created. The result is stored on the contact with its source and date.

### REQ-009 — Web search about a person or company
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: ADR-005

When the user asks for news or background, the agent searches the web (Tavily, last 90 days by default) and
answers from the results.

## Follow-up

### REQ-010 — Follow-up drafts from stored context, never sent automatically
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-009

When the user asks for a follow-up, the agent drafts a short email in the requested tone (warm, professional
or casual) from the contact's stored record only, flags missing information, and never sends it.

## Digest

### REQ-011 — Morning digest
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-010, ADR-009

Every day at DIGEST_HOUR:DIGEST_MINUTE in TIMEZONE (default 07:30), each active user who receives the digest
gets pending tasks by priority, today's meetings, priority contacts, overdue follow-ups and one recommended
action. The same digest is available on demand with `/digest` and through the agent. One failed delivery does
not stop the others.

### REQ-012 — Each user turns their own digest on or off
- Status: active
- Source: backfill: README.md
- Added: 2026-10-28
- Related: UC-011

`/digest_on` and `/digest_off` change only the sender's own preference; owners can also change it for anyone
from the web users page.

### REQ-013 — Conference summary
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28

When asked for a conference summary, the agent reports totals of contacts, interactions, opportunities and
pending tasks. (The spec asked for a fuller summary of contacts, opportunities and follow-ups; today it is
counts only.)

## Access

### REQ-014 — Only allowlisted Telegram users can use the product
- Status: active
- Source: backfill: README.md
- Added: 2026-10-28
- Related: UC-020, ADR-006

Only active users in `bot_users` get a response; everyone else is ignored, except for `/whoami`, which tells
anyone their Telegram ID. IDs in TELEGRAM_ALLOWED_USER_IDS (and the legacy TELEGRAM_ALLOWED_USER_ID) are added
as owners at startup; removing them from the env revokes nothing. A database error denies access.

### REQ-015 — Owners add and remove users
- Status: active
- Source: backfill: README.md
- Added: 2026-10-28
- Related: UC-012, UC-013, ADR-006

Owners add a user with `/adduser <telegram id> [name]` (re-enabling a revoked one) and revoke with
`/removeuser <telegram id>`. Non-owners cannot do either, nobody can revoke themselves, and owners cannot be
revoked this way. `/users` lists everyone with their flags.

## Web

### REQ-016 — Web UI behind the same allowlist
- Status: active
- Source: backfill: README.md
- Added: 2026-10-28
- Related: UC-014, ADR-007, ADR-008

The same service serves a browser UI. In production people sign in with the Telegram Login Widget and only
active bot users get in; revoking someone in Telegram locks them out of the web on their next request. In
development the UI signs in as the first owner. Pages that manage users are owner-only.

### REQ-017 — Manage and export every record from the web
- Status: active
- Source: backfill: README.md
- Added: 2026-10-28
- Related: UC-015, ADR-007

The web UI has a dashboard and list, filter, create, view, edit, delete and CSV export for people, companies,
tasks, opportunities, interactions, meetings, notes and conferences, plus completing a task and activating a
conference.

## Telegram

### REQ-020 — Quick Telegram commands for tasks and recent contacts
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-006, UC-017

`/tasks` lists up to 10 pending tasks, `/contacts` lists up to 10 contacts added in the last 3 days, and
`/start` and `/help` show the command list.

## Scripts

### REQ-021 — Pre-conference seeding and bulk enrichment
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-018

A script creates the active conference interactively (name, dates, location, goals), and another loads an
attendee CSV (full_name, company, linkedin_url, contact_type), enriches each row at most once per second and
writes a summary file.

### REQ-022 — Post-conference CRM export
- Status: active
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: UC-019

A script exports contacts, interactions, tasks and opportunities to one CSV file each. Airtable and Notion
are accepted options but not implemented yet.

## Search

### REQ-023 — Semantic search over contacts and interactions
- Status: planned
- Source: backfill: CLAUDE.md
- Added: 2026-10-28
- Related: ADR-002

Contacts and interactions get embeddings after creation, without blocking the reply, and search uses them
so that a description ("the robotics investor from the panel") finds the right person. Today search is
case-insensitive text matching only and no embeddings are generated, although the `embedding` columns exist.

## Tenancy

### REQ-024 — Each organization's data is isolated in its own workspace
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Related: ADR-013, ADR-014

Every record (people, companies, interactions, meetings, notes, tasks, opportunities, events and
conversation messages) belongs to exactly one workspace, which stands for one organization. A user never
sees, finds, edits, or gets in a digest, summary or export anything from another workspace, whether through
Telegram, the web UI, the agent or the scripts. Each user belongs to exactly one workspace.

### REQ-025 — Every member sees everything in their workspace
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Related: REQ-024, REQ-026

Every member of a workspace sees and edits every record in it, whoever created it.

### REQ-026 — Admins see everything, members see only their own records
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Will supersede: REQ-025
- Related: REQ-027, REQ-028

Once this ships, workspace admins still see every record in their workspace, while a member sees only the
records they created. Records never cross workspaces either way (REQ-024); this is only about members of
the same workspace. Companies stay visible to every member of the workspace, whoever created them: they
are mostly public information, and hiding them causes duplicates (Eze, 2026-10-29). Still to be defined:
whether this is a per-workspace setting or applies to every workspace. Events stay visible to all
members.

### REQ-027 — Every record remembers who created it
- Status: planned
- Source: claude-suggested (confirmed by Eze 2026-10-29)
- Added: 2026-10-28
- Related: REQ-026

From the first multi-workspace release, every record stores the user who created it, so REQ-026 can be
turned on later without guessing who owns existing records. Records created before that release have no
creator.

## Access (multi-workspace)

### REQ-028 — Workspace admins and members
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Will supersede: REQ-015
- Related: REQ-034, ADR-013

Each person in a workspace is either an admin or a member. Admins manage the people of their own workspace
(add, remove, change role) and have no power over any other workspace. Nobody can remove themselves. Any
member can create events (REQ-034).

### REQ-029 — Platform admins create workspaces
- Status: planned
- Source: claude-suggested (confirmed by Eze 2026-10-29)
- Added: 2026-10-28
- Related: REQ-028, REQ-031, REQ-032

The Telegram IDs in TELEGRAM_ALLOWED_USER_IDS become platform admins. Platform admins create workspaces,
name each one's first admin, and set quotas. Being a platform admin does not show a workspace's records:
a platform admin sees them only in a workspace they belong to.

### REQ-030 — Joining is by invitation only
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Will supersede: REQ-014
- Related: REQ-028, REQ-029

Nobody can use the bot or the web UI without first being invited into a workspace. Anyone else is ignored,
except for `/whoami`. The invitation mechanism is still to be defined. As today, a database error denies
access.

## Usage

### REQ-031 — Usage metering per workspace
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Related: ADR-015, REQ-029

Every paid external call (Anthropic tokens, Whisper audio, Proxycurl lookups, Tavily searches) is recorded
with its workspace, the user who triggered it and its estimated cost. Platform admins can see usage per
workspace and per user for any period. The platform owner pays for all of it.

### REQ-032 — Usage quotas per workspace
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Related: ADR-015, REQ-031

Each workspace has a usage quota set by a platform admin. Once the quota is used up, the bot and the web
chat stop making paid calls for that workspace and say why, while reading and editing records keeps
working. The quota is per calendar month and shared by every member of the workspace; there are no
per-user limits, although usage is still recorded per user (REQ-031). The workspace's admins are warned
at 80% of the quota (claude-suggested, confirmed by Eze 2026-10-29).

## Deployment

### REQ-033 — An organization can get its own deployment
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Related: ADR-014

The same code can run as a dedicated deployment for one organization, with its own bot, database and API
keys, through configuration alone (no fork). A dedicated deployment behaves like the shared one.

## Events

### REQ-034 — Any member creates and manages events
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Updated: 2026-10-29
- Related: REQ-035, REQ-037, ADR-016

Any member of a workspace creates and edits events (conferences) in it: name, location, start and end
dates, and goals. A workspace can have any number of events, and all its members see them. Deleting an
event should be rare; when it happens, every record assigned to it becomes unassigned and nothing else is
deleted. Only workspace admins delete events. The single global "active conference" goes away; REQ-037
replaces it.

### REQ-035 — Records can be assigned to one event
- Status: planned
- Source: user-request
- Added: 2026-10-28
- Updated: 2026-10-29
- Related: REQ-034, REQ-037, REQ-038, REQ-018, ADR-016

When a user creates or edits a contact, company, interaction, meeting, note, task or opportunity, from the
agent or the web, they can assign it to at most one event of their workspace or leave it unassigned. While
the user is attending an ongoing event (REQ-037), new records they create are assigned to it by default
unless they say otherwise. Any event can be assigned by hand, whatever its dates. Conversations are not
linked to events: a user keeps one conversation (REQ-018).

## Privacy

### REQ-036 — Export and delete a workspace's data
- Status: planned
- Source: claude-suggested (confirmed by Eze 2026-10-29)
- Added: 2026-10-28
- Related: REQ-024, REQ-029

On request, a platform admin can export everything a workspace holds and delete all of it, including
conversation messages and usage records. Contacts are personal data about third parties held for another
organization (GDPR, Argentina's Ley 25.326).

### REQ-037 — Event lifecycle and attendance
- Status: planned
- Source: user-request
- Added: 2026-10-29
- Related: REQ-034, REQ-035, ADR-016, ADR-017

An event is upcoming before its start date, ongoing from its start date through its end date, and
finished after that. On the morning an event starts, the bot asks each member of the workspace whether
they are attending. When a user says yes, the event becomes their active event, and the bot reminds them
that new contacts and companies will be assigned to it unless they say otherwise. Once the event is
finished it is nobody's default any more. Attendance is per user (one member can attend while another
does not); dates are read in the event's own timezone; a user can mark themselves as attending at any time
during the event (for example after missing the question); and when a user attends two overlapping
ongoing events, the agent asks which one to use (claude-suggested, confirmed by Eze 2026-10-29).

### REQ-038 — Bulk-assign records to an event from the web
- Status: planned
- Source: user-request
- Added: 2026-10-29
- Related: REQ-035, REQ-017

On the contacts and companies lists of the web UI, a user selects several records with checkboxes and, in
one action, assigns them to an event of their workspace, moves them to another event, or clears their
event.

## Template

```markdown
### REQ-NNN — Short title
- Status: active | planned | superseded
- Source: user-request | claude-suggested | backfill: <file>
- Added: YYYY-MM-DD
- Will supersede: REQ-NNN        (planned entry that will replace an older one when it ships)
- Supersedes: REQ-NNN            (shipped entry; the older one must be superseded and point back)
- Superseded by: REQ-NNN         (only when status is superseded)
- Related: UC-NNN, ADR-NNN

One or two testable sentences: "When X, the app does Y."
```
