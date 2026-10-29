#!/usr/bin/env python3
"""Self-test for guard.py: feeds it hook payloads and checks the decision.

    python3 .claude/hooks/test_guard.py

Runs against a throwaway git repository (branches main and feat/EZE-1-x) in a temporary folder, so
nothing in the real repository is touched. Exit 1 if any case fails.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "guard.py"


def run(root, tool, tool_input, cwd):
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd)})
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    out = subprocess.run([sys.executable, str(GUARD)], check=False, input=payload, capture_output=True, text=True, env=env).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "pass"


def main():
    tmp = Path(tempfile.mkdtemp())
    repo = tmp / "repo"
    repo.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True)
    g("init", "-q", "-b", "main")
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
    (repo / "body.md").write_text("Summary\n\nCloses EZE-12\n")
    (repo / "okbody.md").write_text("Summary\n\nRefs EZE-12\n")
    marker = repo / ".claude" / "state" / "post-approve.json"

    B = lambda cmd: ("Bash", {"command": cmd})
    on_main = [
        ("commit on main", B('DURATION="00:30" git commit -m "x"'), "deny"),
        ("push main explicit", B("git push origin main"), "deny"),
        ("push HEAD on main", B("git push origin HEAD"), "deny"),
        ("bare push on main", B("git push"), "deny"),
        ("local merge into main", B('DURATION="00:05" git merge feat/EZE-1-x'), "deny"),
        ("pull ff-only on main", B("git pull --ff-only"), "pass"),
        ("pull without ff-only on main", B("git pull origin main"), "deny"),
        ("create branch", B("git checkout -b feat/EZE-1-x"), "pass"),
    ]
    on_feat = [
        ("commit with duration", B("DURATION=\"00:30\" git commit -m 'feat(x): EZE-1 thing [claude 00:10]'"), "pass"),
        ("commit without duration", B("git commit -m 'x'"), "deny"),
        ("commit bad duration", B('DURATION="1:3" git commit -m x'), "deny"),
        ("commit --no-verify", B('DURATION="00:30" git commit --no-verify -m x'), "deny"),
        ("commit -n", B('DURATION="00:30" git commit -nm x'), "deny"),
        ("commit -a", B('DURATION="00:30" git commit -am x'), "deny"),
        ("commit --amend", B('DURATION="00:05" git commit --amend --no-edit'), "ask"),
        ("hooksPath override", B('DURATION="00:30" git -c core.hooksPath=/dev/null commit -m x'), "deny"),
        ("hidden in bash -c", B("bash -c 'git push --force origin feat/EZE-1-x'"), "deny"),
        ("chained force push", B("cd . && git push -f"), "deny"),
        ("force-with-lease", B("git push --force-with-lease origin feat/EZE-1-x"), "deny"),
        ("plus refspec", B("git push origin +feat/EZE-1-x"), "deny"),
        ("push to main refspec", B("git push origin feat/EZE-1-x:main"), "deny"),
        ("push feature", B("git push -u origin feat/EZE-1-x"), "pass"),
        ("delete remote branch", B("git push origin --delete feat/EZE-1-x"), "ask"),
        ("delete remote via colon", B("git push origin :feat/EZE-1-x"), "ask"),
        ("delete local branch", B("git branch -D old"), "ask"),
        ("reset hard", B("git reset --hard HEAD~1"), "ask"),
        ("clean -fd", B("git clean -fd"), "ask"),
        ("rm -rf", B("rm -rf build"), "ask"),
        ("rm -r -f split", B("rm -r -f build"), "ask"),
        ("rebase", B("git rebase main"), "ask"),
        ("add -A", B("git add -A"), "deny"),
        ("add .", B("git add ."), "deny"),
        ("add paths", B("git add app/agent/tools.py app/web/templates/base.html"), "pass"),
        ("merge main with duration", B('DURATION="00:10" git merge origin/main'), "pass"),
        ("merge main without duration", B("git merge origin/main"), "deny"),
        ("approve PR", B("gh pr review 3 --approve"), "deny"),
        ("approve via api", B("gh api repos/o/r/pulls/3/reviews -f event=APPROVE"), "deny"),
        ("merge via api", B("gh api -X PUT repos/o/r/pulls/3/merge"), "deny"),
        ("merge without marker", B("gh pr merge 3 --squash"), "deny"),
        ("PR closing keyword", B("gh pr create --base main --title 'EZE-12: x' --body-file body.md"), "deny"),
        ("PR wrong base", B("gh pr create --base dev --title 'EZE-12: x' --body-file okbody.md"), "deny"),
        ("PR title without ID", B("gh pr create --base main --title 'x' --body-file okbody.md"), "deny"),
        ("PR title with another ID", B("gh pr create --base main --title 'EZE-12: x' --body-file okbody.md"), "deny"),
        ("PR ok", B("gh pr create --base main --title 'EZE-1: x' --body-file okbody.md"), "pass"),
        ("edit hook via sed", B("sed -i 's/a/b/' .git/hooks/commit-msg"), "deny"),
        ("redirect into hook", B("echo x > .git/hooks/commit-msg"), "deny"),
        ("cp over hook", B("cp /tmp/x .git/hooks/commit-msg"), "deny"),
        ("patch hook", B("patch .git/hooks/commit-msg < /tmp/p"), "deny"),
        ("python writes hook", B("python3 -c \"open('.git/hooks/commit-msg','w')\""), "deny"),
        ("read hook", B("cat .git/hooks/commit-msg"), "pass"),
        ("stat hook among other cmds", B("stat .git/hooks/commit-msg; uvx ruff check app 2>&1"), "pass"),
        ("diff hook into scratch", B("diff -u .git/hooks/commit-msg new > /tmp/p.patch"), "pass"),
        ("read clockify env", B("cat ~/.clockify_env"), "deny"),
        ("Edit hook file", ("Edit", {"file_path": str(repo / ".git/hooks/commit-msg")}), "deny"),
        ("Edit normal file", ("Edit", {"file_path": str(repo / "app/agent/tools.py")}), "pass"),
        ("Linear read", ("mcp__linear-server__list_issues", {"project": "x"}), "pass"),
        ("Linear status without marker", ("mcp__linear-server__save_issue", {"id": "EZE-5", "state": "Done"}), "deny"),
        ("Linear comment", ("mcp__linear-server__save_comment", {"issueId": "EZE-5", "body": "x"}), "ask"),
    ]
    with_marker = [
        ("merge with marker, right PR", B("gh pr merge 3 --squash"), "ask"),
        ("merge with marker, other PR", B("gh pr merge 4 --squash"), "deny"),
        ("merge with marker, no squash", B("gh pr merge 3 --merge"), "deny"),
        ("merge deleting branch", B("gh pr merge 3 --squash --delete-branch"), "deny"),
        ("Linear status, named issue", ("mcp__linear-server__save_issue", {"id": "EZE-5", "state": "Done"}), "ask"),
        ("Linear status, other issue", ("mcp__linear-server__save_issue", {"id": "EZE-6", "state": "Done"}), "deny"),
        ("Linear status plus edits", ("mcp__linear-server__save_issue", {"id": "EZE-5", "state": "Done", "title": "x"}), "deny"),
    ]

    failures = 0

    def check(cases):
        nonlocal failures
        for name, (tool, inp), expected in cases:
            got = run(repo, tool, inp, repo)
            ok = got == expected
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:34s} expected {expected:5s} got {got}")

    no_issue = [
        ("no-issue PR typed title", B("gh pr create --base main --title 'chore: tooling' --body-file okbody.md"), "pass"),
        ("no-issue PR scoped title", B("gh pr create --base main --title 'chore(workflow): x' --body-file okbody.md"), "pass"),
        ("no-issue PR bare title", B("gh pr create --base main --title 'tooling' --body-file okbody.md"), "deny"),
    ]

    check(on_main)
    g("checkout", "-q", "-b", "chore/tooling")
    check(no_issue)
    g("checkout", "-q", "-b", "feat/EZE-1-x")
    check(on_feat)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"pr": 3, "created": time.time(), "linear_issues": ["EZE-5"]}))
    check(with_marker)
    marker.write_text(json.dumps({"pr": 3, "created": time.time() - 4 * 3600, "linear_issues": ["EZE-5"]}))
    check([("merge with expired marker", B("gh pr merge 3 --squash"), "deny")])
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
