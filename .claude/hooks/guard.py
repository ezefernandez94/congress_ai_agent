#!/usr/bin/env python3
"""PreToolUse guardrails for the development workflow (see "Development workflow" in CLAUDE.md).

Reads the hook JSON on stdin and answers with a permission decision:
  deny  - the action must never happen (force push, push to main, --no-verify, ...)
  ask   - the action needs Eze's confirmation (merge, branch deletion, reset --hard, ...)
  (no output) - not this hook's business; the normal permission rules apply.

Only the standard library is used. Self-test: python3 .claude/hooks/test_guard.py

Limits: commands are parsed with shlex, including `bash -c "..."`, but code that builds a command at run
time (eval, scripts, aliases) is not seen. The confirmation prompt is the final check, not this file.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
STATE = ROOT / ".claude" / "state"
POST_APPROVE_MARKER = STATE / "post-approve.json"
MARKER_MAX_AGE = 3 * 60 * 60  # seconds
PROTECTED_BRANCHES = {"main", "master"}
DURATION_RE = re.compile(r"^\d{2}:[0-5]\d$")
ISSUE_IN_BRANCH_RE = re.compile(r"\bEZE-\d+", re.IGNORECASE)
# Work without a Linear issue: branch <type>/<slug>, PR title "<type>: ..." or "<type>(scope): ...".
TYPE_TITLE_RE = re.compile(r"^(feat|fix|chore|refactor|test|docs)(\([\w./-]+\))?: \S")
# Linear and GitHub magic words that close an issue when the PR merges. "Refs EZE-12" is the safe form.
CLOSING_RE = re.compile(
    r"\b(close[sd]?|closing|fix(e[sd])?|fixing|resolve[sd]?|resolving|complete[sd]?|completing|"
    r"implement(s|ed|ing)?)\b[\s:]*(#\d+|[A-Z][A-Z0-9]+-\d+|https?://\S+)",
    re.IGNORECASE,
)
SECRET_FILE_RE = re.compile(
    r"(^|/)(\.env(\.[\w.-]+)?|[^/]*\.(pem|key|p12|pfx|keystore|jks|mobileprovision)|id_(rsa|ed25519|ecdsa)"
    r"|credentials(\.json)?|\.clockify_env)$"
)
SECRET_EXCEPTIONS_RE = re.compile(r"\.env\.example$")
SECRET_CONTENT_RE = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}"
    r"|(SECRET_KEY|API_KEY|PASSWORD|TOKEN)\s*[=:]\s*['\"]?[A-Za-z0-9/+_=-]{16,})"
)
WRAPPERS = {"env", "command", "sudo", "time", "nohup", "exec", "builtin", "nice"}
SHELLS = {"bash", "sh", "zsh", "dash"}
READ_ONLY_CMDS = {"cat", "head", "tail", "less", "ls", "stat", "grep", "rg", "diff", "wc", "file", "sed", "awk"}


def decide(decision, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": f"[guard] {reason}",
    }}))
    sys.exit(0)


def deny(reason):
    decide("deny", reason)


def ask(reason):
    decide("ask", reason)


# --------------------------------------------------------------------------- helpers

def git_out(cwd, *args):
    try:
        return subprocess.run(
            ["git", "-C", cwd, *args], check=False, capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:  # noqa: BLE001 - a hook must never crash; no git output means "unknown"
        return ""


def current_branch(cwd):
    return git_out(cwd, "rev-parse", "--abbrev-ref", "HEAD").strip()


def post_approve_marker():
    try:
        data = json.loads(POST_APPROVE_MARKER.read_text())
    except Exception:  # noqa: BLE001 - a missing or corrupt marker means no /post-approve in progress
        return None
    if time.time() - float(data.get("created", 0)) > MARKER_MAX_AGE:
        return None
    return data


def split_segments(command):
    """Split a shell command into simple commands (lists of words)."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments, current = [], []
    for tok in tokens:
        if tok and all(c in ";&|()" for c in tok):
            if current:
                segments.append(current)
            current = []
        elif tok and all(c in "<>" for c in tok):
            current.append(tok)
        else:
            current.append(tok)
    if current:
        segments.append(current)
    # Recurse into `bash -c "..."`.
    expanded = []
    for seg in segments:
        expanded.append(seg)
        for i, word in enumerate(seg[:-1]):
            if os.path.basename(word) in SHELLS and "-c" in seg[i + 1:i + 3]:
                idx = seg.index("-c", i + 1)
                if idx + 1 < len(seg):
                    expanded.extend(split_segments(seg[idx + 1]))
    return expanded


def strip_prefix(seg):
    """Return (env assignments, words) without leading VAR=value and wrapper commands."""
    env, words = {}, list(seg)
    while words:
        w = words[0]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w):
            key, _, value = w.partition("=")
            env[key] = value
            words.pop(0)
        elif os.path.basename(w) in WRAPPERS:
            words.pop(0)
            while words and words[0].startswith("-"):
                words.pop(0)
        else:
            break
    return env, words


def short_flags(args):
    """Letters of clustered short options such as -am -> {'a', 'm'}."""
    letters = set()
    for a in args:
        if re.match(r"^-[A-Za-z]+$", a):
            letters.update(a[1:])
    return letters


def has_any(args, *names):
    return any(a == n or a.startswith(n + "=") for a in args for n in names)


# --------------------------------------------------------------------------- git

def parse_git(words, cwd):
    """Return (subcommand, args, cwd, config overrides) for a `git ...` word list."""
    i, configs = 1, []
    while i < len(words):
        w = words[i]
        if w == "-C" and i + 1 < len(words):
            path = words[i + 1]
            cwd = path if os.path.isabs(path) else os.path.join(cwd, path)
            i += 2
        elif w == "-c" and i + 1 < len(words):
            configs.append(words[i + 1])
            i += 2
        elif w in ("--git-dir", "--work-tree", "--namespace") and i + 1 < len(words):
            i += 2
        elif w.startswith("-"):
            i += 1
        else:
            return w, words[i + 1:], cwd, configs
    return "", [], cwd, configs


def check_staged_secrets(cwd):
    names = git_out(cwd, "diff", "--cached", "--name-only").split()
    bad = [n for n in names if SECRET_FILE_RE.search(n) and not SECRET_EXCEPTIONS_RE.search(n)]
    if bad:
        deny(f"Staged files look like secrets: {', '.join(bad)}. Unstage them (git restore --staged <file>).")
    diff = git_out(cwd, "diff", "--cached", "-U0", "--no-color")
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++") and SECRET_CONTENT_RE.search(line):
            deny("A staged line looks like a secret (key, token or password). Review `git diff --cached`.")


def check_git(env, words, cwd):
    sub, args, cwd, configs = parse_git(words, cwd)
    if any(c.lower().startswith("core.hookspath") for c in configs):
        deny("Changing core.hooksPath would skip the Clockify commit-msg hook.")
    if has_any(args, "--no-verify"):
        deny("--no-verify skips the Clockify commit-msg hook. Never use it.")
    branch = current_branch(cwd)

    if sub == "config" and any(a.lower().startswith("core.hookspath") for a in args):
        deny("Changing core.hooksPath would skip the Clockify commit-msg hook.")

    if sub == "commit":
        if "n" in short_flags(args):
            deny("`-n` is --no-verify for git commit. Never skip the commit-msg hook.")
        if branch in PROTECTED_BRANCHES:
            deny(f"Never commit on {branch}. Work on a feature branch (see /develop).")
        if "a" in short_flags(args) or has_any(args, "--all"):
            deny("No blind staging: stage files by name with `git add <paths>`, then commit without -a.")
        duration = env.get("DURATION")
        if not duration:
            deny('Commit without DURATION. Use: DURATION="HH:MM" git commit -m \'...\' (see /commit).')
        if not DURATION_RE.match(duration):
            deny(f'DURATION must be zero-padded HH:MM (got "{duration}").')
        check_staged_secrets(cwd)
        if has_any(args, "--amend"):
            ask("--amend runs the Clockify hook again and creates a second time entry. Confirm.")
        return

    if sub == "merge":
        if has_any(args, "--abort", "--quit"):
            return
        if branch in PROTECTED_BRANCHES:
            deny(f"Never merge locally into {branch}. PRs are merged on GitHub by /post-approve.")
        if has_any(args, "--ff-only"):
            return
        duration = env.get("DURATION")
        if not duration or not DURATION_RE.match(duration):
            deny('A merge commit runs the Clockify hook: use DURATION="HH:MM" git merge ... (see /post-approve).')
        return

    if sub == "pull":
        if has_any(args, "--rebase") or "r" in short_flags(args):
            ask("pull --rebase rewrites the branch. Never rebase a branch with an open PR. Confirm.")
        if not has_any(args, "--ff-only"):
            if branch in PROTECTED_BRANCHES:
                deny(f"On {branch} only `git pull --ff-only` is allowed.")
            duration = env.get("DURATION")
            if not duration or not DURATION_RE.match(duration):
                deny("Use `git pull --ff-only`, or fetch and merge with DURATION (merge commits run the hook).")
        return

    if sub == "push":
        if has_any(args, "--force", "--force-with-lease", "--force-if-includes", "--mirror") or "f" in short_flags(args):
            deny("Force pushes are never allowed (including --force-with-lease).")
        if has_any(args, "--all", "--tags"):
            deny("Push one branch explicitly: git push -u origin <branch>.")
        if has_any(args, "--delete", "--prune") or "d" in short_flags(args):
            ask("This push deletes a remote branch. Confirm.")
        refspecs = [a for a in args if not a.startswith("-")][1:]  # first positional is the remote
        for spec in refspecs:
            if spec.startswith("+"):
                deny(f"`{spec}` is a forced refspec. Force pushes are never allowed.")
            if spec.startswith(":"):
                ask(f"`{spec}` deletes a remote branch. Confirm.")
            dst = spec.split(":")[-1].replace("refs/heads/", "")
            src = spec.split(":")[0]
            if dst in PROTECTED_BRANCHES or (dst == "HEAD" and branch in PROTECTED_BRANCHES) or (
                    ":" not in spec and src == "HEAD" and branch in PROTECTED_BRANCHES):
                deny(f"Never push to {dst if dst != 'HEAD' else branch}. Push the feature branch and open a PR.")
        if not refspecs and branch in PROTECTED_BRANCHES:
            deny(f"You are on {branch}: never push it. Push the feature branch and open a PR.")
        return

    if sub == "rebase":
        ask("Rebase rewrites history. Never rebase a branch with an open PR. Confirm.")
    if sub == "reset" and has_any(args, "--hard", "--merge", "--keep"):
        ask("git reset --hard discards work. Confirm.")
    if sub == "clean" and ("f" in short_flags(args) or has_any(args, "--force")):
        ask("git clean -f deletes untracked files. Confirm.")
    if sub == "branch" and (has_any(args, "--delete") or short_flags(args) & {"d", "D"}):
        ask("Deleting a branch. Confirm.")
    if sub == "branch" and (short_flags(args) & {"m", "M", "f"} or has_any(args, "--force", "--move")):
        ask("Renaming or forcing a branch. Confirm.")
    if sub in ("checkout", "restore") and ("." in args or "--" in args) and not has_any(args, "--staged"):
        ask("This discards uncommitted changes in the working tree. Confirm.")
    if sub == "stash" and args[:1] and args[0] in ("drop", "clear"):
        ask("This deletes stashed work. Confirm.")
    if sub == "update-ref" and "-d" in args:
        ask("Deleting a ref. Confirm.")
    if sub == "add" and (has_any(args, "--all", "--update", "-A", "-u") or short_flags(args) & {"A", "u"}
                         or any(a in (".", ":/", "*", "./") for a in args)):
        deny("No blind staging (add -A / add . / add -u). Stage files by name after checking `git status`.")
    if sub == "tag" and short_flags(args) & {"d", "f"}:
        ask("Deleting or moving a tag. Confirm.")


# --------------------------------------------------------------------------- gh

def option_value(args, *names):
    for i, a in enumerate(args):
        for n in names:
            if a == n and i + 1 < len(args):
                return args[i + 1]
            if a.startswith(n + "="):
                return a.split("=", 1)[1]
    return None


def check_pr_text(args, cwd):
    """PR conventions: base main, title starts with the Linear ID, no closing keywords."""
    base = option_value(args, "--base", "-B")
    if base is not None and base != "main":
        deny("PRs always target main (--base main).")
    title = option_value(args, "--title", "-t")
    if title is not None:
        issue = ISSUE_IN_BRANCH_RE.search(current_branch(cwd))
        if issue and not re.match(re.escape(issue.group(0)) + r"\b", title, re.IGNORECASE):
            deny(f'The PR title must start with the Linear ID of the branch: "{issue.group(0).upper()}: ..." '
                 f'(got "{title}").')
        if not issue and not TYPE_TITLE_RE.match(title):
            deny(f'Without a Linear issue the PR title starts with the type: "chore: ..." (got "{title}").')
    body = option_value(args, "--body", "-b") or ""
    body_file = option_value(args, "--body-file", "-F")
    if body_file and body_file != "-":
        path = body_file if os.path.isabs(body_file) else os.path.join(cwd, body_file)
        try:
            body += "\n" + Path(path).read_text()
        except OSError:
            pass
    for text in (title or "", body):
        m = CLOSING_RE.search(text)
        if m:
            deny(f'"{m.group(0)}" would close the issue on merge. Use non-closing references: "Refs EZE-12".')


def check_gh(words, cwd):
    args = words[1:]
    if len(args) >= 2 and args[0] == "pr":
        action, rest = args[1], args[2:]
        if action == "merge":
            if has_any(rest, "--delete-branch") or "d" in short_flags(rest):
                deny("Never delete branches when merging (no --delete-branch).")
            if has_any(rest, "--admin", "--auto"):
                deny("No --admin or --auto merges.")
            if not has_any(rest, "--squash") and "s" not in short_flags(rest):
                deny("PRs are merged with --squash (see CLAUDE.md).")
            numbers = [a for a in rest if re.match(r"^#?\d+$", a)]
            marker = post_approve_marker()
            if not marker:
                deny("gh pr merge only runs inside /post-approve (no active post-approve marker).")
            if not numbers or int(numbers[0].lstrip("#")) != int(marker.get("pr", -1)):
                deny(f"Merge exactly the PR confirmed in /post-approve: gh pr merge {marker.get('pr')} --squash.")
            ask(f"Final confirmation: merge PR #{marker.get('pr')} into main with squash?")
        if action == "review":
            if has_any(rest, "--approve") or "a" in short_flags(rest):
                deny("Never approve PRs. Eze reviews and approves them.")
            ask("Posting a PR review. Confirm.")
        if action in ("create", "edit"):
            check_pr_text(rest, cwd)
            return
        if action in ("close", "reopen", "lock"):
            ask(f"gh pr {action} changes the PR state. Confirm.")
    if args[:1] == ["api"]:
        joined = " ".join(args)
        method = (option_value(args, "-X", "--method") or "").upper()
        if re.search(r"/pulls/\d+/merge\b", joined):
            deny("Merging through the API is not allowed. Use gh pr merge inside /post-approve.")
        if re.search(r"/reviews\b", joined) and re.search(r"event[=:]\s*['\"]?APPROVE", joined, re.IGNORECASE):
            deny("Never approve PRs.")
        if method == "DELETE":
            ask("This API call deletes something on GitHub. Confirm.")
        if re.search(r"/(branches/[^/\s]+/protection|rulesets|hooks|actions/secrets)", joined) and method in ("PUT", "POST", "PATCH"):
            ask("This changes repository settings. Confirm.")
    if args[:1] == ["repo"] and len(args) > 1 and args[1] in ("delete", "edit", "archive", "rename"):
        deny(f"gh repo {args[1]} changes the repository itself. Eze does that by hand.")
    if args[:1] == ["release"] and len(args) > 1 and args[1] == "delete":
        ask("Deleting a release. Confirm.")


# --------------------------------------------------------------------------- bash

HOOKS_PATH_RE = re.compile(r"\.git/hooks")
WRITE_CMDS = {"cp", "mv", "rm", "chmod", "chown", "ln", "install", "truncate", "tee", "dd", "touch", "rsync",
              "patch", "unlink", "shred"}
INTERPRETERS = {"python", "python3", "node", "perl", "ruby", "php"}


def writes_hooks(seg):
    """True when one simple command could modify .git/hooks (reading it is fine)."""
    words = strip_prefix(seg)[1]
    for i, tok in enumerate(words):
        if tok in (">", ">>", ">|") and i + 1 < len(words) and HOOKS_PATH_RE.search(words[i + 1]):
            return True
    if not words or not any(HOOKS_PATH_RE.search(w) for w in words):
        return False
    name = os.path.basename(words[0])
    if name in WRITE_CMDS or name in INTERPRETERS:
        return True
    if name in ("sed", "perl") and any(w.startswith("-i") or w == "--in-place" for w in words):
        return True
    return name not in READ_ONLY_CMDS | {"git", "echo", "printf", "file", "md5sum", "sha256sum", "bat"}


def check_bash(command, cwd):
    if re.search(r"clockify_env", command, re.IGNORECASE):
        deny("~/.clockify_env holds the Clockify API key. Don't read or change it.")
    if HOOKS_PATH_RE.search(command) and any(writes_hooks(s) for s in split_segments(command)):
        deny("The commit-msg hook and the Clockify integration must not be modified.")
    for seg in split_segments(command):
        env, words = strip_prefix(seg)
        if not words:
            continue
        name = os.path.basename(words[0])
        if name == "git":
            check_git(env, words, cwd)
        elif name == "gh":
            check_gh(words, cwd)
        elif name == "rm":
            flags = short_flags(words[1:])
            recursive = flags & {"r", "R"} or has_any(words[1:], "--recursive")
            force = "f" in flags or has_any(words[1:], "--force")
            if recursive and force:
                ask(f"`{' '.join(words)}` deletes files recursively. Confirm.")
        elif name == "find" and ("-delete" in words or "-exec" in words and "rm" in words):
            ask("find with -delete / -exec rm deletes files. Confirm.")


# --------------------------------------------------------------------------- files and Linear

def check_file_edit(tool_input):
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    resolved = os.path.realpath(os.path.expanduser(path))
    if "/.git/hooks/" in resolved or resolved.endswith("/.git/hooks"):
        deny("The commit-msg hook and the Clockify integration must not be modified.")
    if os.path.basename(resolved) == ".clockify_env":
        deny("~/.clockify_env holds the Clockify API key. Don't read or change it.")
    guarded = {ROOT / ".claude" / "settings.json", ROOT / ".claude" / "hooks" / "guard.py",
               ROOT / ".claude" / "hooks" / "timer.py"}
    if Path(resolved) in {p.resolve() for p in guarded}:
        ask("This file enforces the workflow guardrails. Confirm the change.")


LINEAR_READ_PREFIXES = ("get_", "list_", "search_", "extract_")


def check_linear(tool_name, tool_input):
    action = tool_name.split("__")[-1]
    if action.startswith(LINEAR_READ_PREFIXES):
        return
    if action == "save_issue" and tool_input.get("id") and ("state" in tool_input):
        marker = post_approve_marker()
        allowed = {str(i).upper() for i in (marker or {}).get("linear_issues", [])}
        issue = str(tool_input["id"]).upper()
        if not marker or issue not in allowed:
            deny("Linear statuses change only in /post-approve, for the issues Eze named.")
        extra = set(tool_input) - {"id", "state"}
        if extra:
            deny(f"In /post-approve only the status changes (remove {', '.join(sorted(extra))}).")
        ask(f"Mark {issue} as {tool_input['state']} in Linear?")
    ask("Linear is read-only outside /post-approve. Approve only if Eze asked for this write.")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - an unreadable payload is passed through, never a crash
        return
    tool, tool_input = data.get("tool_name", ""), data.get("tool_input") or {}
    cwd = data.get("cwd") or str(ROOT)
    if tool == "Bash":
        check_bash(tool_input.get("command", ""), cwd)
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        check_file_edit(tool_input)
    elif tool == "Read" and os.path.basename(tool_input.get("file_path", "")) == ".clockify_env":
        deny("~/.clockify_env holds the Clockify API key. Don't read it.")
    elif tool.startswith("mcp__linear-server__"):
        check_linear(tool, tool_input)


if __name__ == "__main__":
    main()
