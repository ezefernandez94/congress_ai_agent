# Use guide

How to use the product, by task: what to send or click, what the bot does in response, and the options
and replies along the way. `docs/use-cases.md` lists the same behavior as numbered scenarios for tests;
this guide is for the people using it. Maintained by Claude Code through the `/update-use-cases` skill
(see CLAUDE.md → Documentation workflow).

Roles used below:

- **User**: anyone with access (an active bot user who belongs to a workspace).
- **Owner**: a user with the owner flag. Owners come from `TELEGRAM_ALLOWED_USER_IDS`. Until workspace
  roles replace it (EZE-52), being an owner is what lets someone manage users.
- **Workspace**: one organization. Every user belongs to exactly one. Today everyone is in the workspace
  called "Default".

## Contents

1. [How access works](#how-access-works)
2. [First setup: the owners](#first-setup-the-owners)
3. [Getting access as a new person](#getting-access-as-a-new-person)
4. [Adding a user](#adding-a-user)
5. [Removing or restoring a user](#removing-or-restoring-a-user)
6. [Seeing who has access](#seeing-who-has-access)
7. [Signing in to the web UI](#signing-in-to-the-web-ui)
8. [Saving a contact](#saving-a-contact)
9. [Logging a conversation](#logging-a-conversation)
10. [Tasks](#tasks)
11. [Briefs, enrichment and follow-ups](#briefs-enrichment-and-follow-ups)
12. [The morning digest](#the-morning-digest)
13. [Chatting from the web](#chatting-from-the-web)
14. [Managing records on the web](#managing-records-on-the-web)
15. [Scripts](#scripts)
16. [Command reference](#command-reference)

## How access works

Every Telegram message and command, and every web page, goes through the same check first:

1. The sender's Telegram ID is looked up in the users table. Unknown or revoked → no access.
2. Their workspace membership is looked up. No workspace → no access.
3. With both, the bot knows who is acting, in which workspace and with which role, and goes on.

Without access the bot does not answer at all (it only logs the attempt), and the web UI sends you to
the login page. If the database can't be reached, access is denied too: the bot never fails open.

The only exception is `/whoami`, which anyone can use (see [Getting access](#getting-access-as-a-new-person)).

## First setup: the owners

Done by whoever deploys the bot, not from Telegram.

1. Put the owners' Telegram IDs in `TELEGRAM_ALLOWED_USER_IDS` (comma-separated, for example
   `123,456`) and start the app.
2. At startup each listed ID becomes an active owner. An owner with no workspace yet joins "Default" as
   an admin.
3. Owners can now use the bot and add everyone else.

Things to know:

- The list only **adds** owners. Removing an ID from the env revokes nothing; it stays an owner.
- Restarting with the same list changes nothing: an owner who already has a workspace keeps it.

## Getting access as a new person

1. Send `/whoami` to the bot.
2. The bot replies with your Telegram ID and tells you to send it to someone who already uses the bot.
3. Once an owner has added you (next section), send `/start`. The bot replies with the list of commands.

Until you are added, the bot ignores everything else you send.

## Adding a user

Only owners can add users. The new person joins **the owner's workspace** as a member.

### From Telegram

Send `/adduser <telegram id> [name]`, for example `/adduser 123456789 Ana Pérez`. The name is optional.

| Situation | What happens | Reply |
|---|---|---|
| New ID | The person gets access and joins your workspace | "✅ `<id>` can now use the bot. They should send /start." |
| Revoked user of your workspace | Their access is restored | Same as above |
| Already has access in your workspace | Nothing changes | "That user already has access." |
| Belongs to another workspace | Nothing changes: a user belongs to one workspace only | "That user belongs to another workspace." |
| No ID given | Nothing changes | The usage line, and how to get an ID with /whoami |
| ID is not a number | Nothing changes | "`<text>` is not a valid Telegram ID." |
| You are not an owner | Nothing changes | "Only an owner can add users." |

### From the web

1. Open **Users** (only owners see this menu item).
2. Fill in the Telegram user ID and, optionally, a display name, and submit.
3. The page shows "User added", and the person joins your workspace.

Errors: an ID that isn't a number shows "Telegram user ID must be a number"; someone from another
workspace shows "That user belongs to another workspace". To restore a revoked user on the web, use their
access toggle (next section).

## Removing or restoring a user

Only owners can remove users. Removing revokes access in Telegram and on the web at once: the person's
next message is ignored, and their next web request logs them out.

### From Telegram

Send `/removeuser <telegram id>`.

| Situation | What happens | Reply |
|---|---|---|
| Active user | Access is revoked | "🚫 `<id>` can no longer use the bot." |
| Your own ID | Refused | "You can't revoke your own access." |
| An owner | Refused | Remove their ID from `TELEGRAM_ALLOWED_USER_IDS` first, or startup re-seeds them |
| Unknown ID | Nothing changes | "No such user." |
| ID is not a number | Nothing changes | "`<text>` is not a valid Telegram ID." |
| You are not an owner | Nothing changes | "Only an owner can remove users." |

To restore someone, add them again with `/adduser`.

### From the web

On **Users**, use the person's access toggle to revoke or restore them. You can't deactivate your own
account ("You cannot deactivate your own account").

## Seeing who has access

- **Telegram:** `/users` lists every user with their ID and flags: owner, revoked, and whether they get
  the digest.
- **Web:** the **Users** page (owners only) shows the same, with Owner/Member badges.

## Signing in to the web UI

1. Open the site. You land on `/login`.
2. Sign in with the Telegram button. The app checks the signature and age of the login, and that you have
   access (see [How access works](#how-access-works)).
3. You land on the dashboard. **Logout** ends the session.

Notes:

- Bad signature, an old login or no access → back to the login page.
- If your access is revoked while signed in, your next request logs you out.
- On a local development run there is no login: you are signed in as the first owner. If no owner is
  seeded, the login page says to set `TELEGRAM_ALLOWED_USER_IDS` and restart.
- A user who isn't an owner opening **Users** is sent back with "That page is restricted to owners."

## Saving a contact

Tell the bot about someone you met, in any of three ways. The bot saves the person (and their company if
it's new) and replies with what it saved and any tasks it created.

- **Text:** for example "Just met Ana Pérez, CTO at Acme, interested in a pilot". Longer requests first
  get "⏳ On it...".
- **Voice note:** the bot replies "🎙 Transcribing...", then "_Heard: <transcript>_" so you can check it,
  then its answer. If transcription fails: "Sorry, I couldn't transcribe that voice note. Please try
  again." and nothing is saved.
- **Badge photo** (optionally with a caption): the bot replies "📸 Reading badge..." and saves what it can
  read. Anything unreadable is left empty, never guessed.

Saving a contact never looks them up on LinkedIn; that only happens when you ask (see
[enrichment](#briefs-enrichment-and-follow-ups)).

## Logging a conversation

Describe a conversation with someone already saved ("Talked to Ana again, she wants pricing"). The bot
stores it and updates the contact's last interaction date.

- No contact matches → the bot says so.
- Several contacts match → the bot lists them and asks which one. Nothing is saved until you answer.

## Tasks

- **Creating:** mention a commitment ("I'll send her the deck by Friday"). The bot creates a task linked to
  the person, with a type, priority and due date, and confirms the date. An invalid date is dropped and
  the task is saved without one.
- **Listing:** send `/tasks` (up to 10 pending tasks, by priority), ask the bot, or open **Tasks** on the
  web.
- **Completing:** ask the bot ("mark the deck task done"), by ID or title, or use the **complete** button
  on the web. If nothing matches: "Task not found".

## Briefs, enrichment and follow-ups

- **Brief:** "Brief me on Ana". The bot reads what is stored about her and replies with a short brief and
  talking points. It calls no external service. Several matches → it asks which one. Nothing stored → it
  says so and offers to enrich.
- **Enrichment:** ask to enrich a contact, or give their LinkedIn URL. The bot fetches the LinkedIn
  profile (a paid lookup) and stores the headline and summary. Without a LinkedIn URL nothing is fetched.
  On an error: "Enrichment failed: ...".
- **Web search:** ask for news about a person or company.
- **Follow-up draft:** ask for a follow-up to a contact, optionally with a tone (warm, professional,
  casual) and points to include. The bot writes a draft from the stored record and asks whether to adjust
  it. **It never sends anything.**

## The morning digest

- **Automatic:** every day at the configured time (`DIGEST_HOUR`:`DIGEST_MINUTE` in the `TIMEZONE` setting),
  every active user with the digest on gets it in Telegram: pending tasks, today's meetings, priority
  contacts, overdue follow-ups and one recommended action. If sending to one person fails, the others
  still get it.
- **On demand:** send `/digest`, or ask the bot.
- **Turning it off or on:** `/digest_off` replies "🔕 Morning digest turned off."; `/digest_on` replies
  "✅ You'll get the morning digest." Only your own setting changes. Owners can change anyone's setting on
  the web **Users** page ("Digest preference updated").

## Chatting from the web

Open **Chat**. It shows your last 20 messages, including the ones from Telegram: it's the same
conversation. Send a message and the bot answers as it would in Telegram. An empty message is ignored.

## Managing records on the web

1. From the dashboard, open any list: people, companies, tasks, opportunities, interactions, meetings,
   notes or conferences.
2. Filter and page through it; create, view, edit or delete records.
3. Download any list as CSV (every column except the search embeddings).

**Conferences:** activating a conference makes it the one the bot uses in its answers and the digest.

## Scripts

Run by the person operating the deployment.

- **Before the conference:** `scripts/seed_conference.py` asks for the conference's name, dates, location
  and goals and saves it as active. `scripts/batch_enrich.py --input attendees.csv` saves and enriches each
  row (one per second) and writes a summary to `enriched_contacts_summary.txt`.
- **After the conference:** `scripts/export_crm.py --format csv` writes contacts, interactions, tasks and
  opportunities to one CSV each. `--format airtable` or `notion` prints "not yet implemented".

## Command reference

| Command | Who | What it does |
|---|---|---|
| `/start`, `/help` | User | Welcome message and the command list |
| `/whoami` | Anyone | Shows your Telegram ID and how to get access |
| `/digest` | User | Sends the digest now |
| `/digest_on`, `/digest_off` | User | Turns your morning digest on or off |
| `/tasks` | User | Up to 10 pending tasks |
| `/contacts` | User | Up to 10 contacts added in the last 3 days |
| `/users` | User | Everyone with access, with their flags |
| `/adduser <id> [name]` | Owner | Gives someone access in your workspace |
| `/removeuser <id>` | Owner | Revokes someone's access |
| Any text, voice note or photo | User | Goes to the assistant |
