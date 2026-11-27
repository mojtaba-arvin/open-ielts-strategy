#!/usr/bin/env python3
"""Validate GitHub PR commit authorship and attribution without write credentials."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

NAME = "Mojtaba Arvin"
EMAIL = "m.arvin@live.com"
LOGIN = "mojtaba-arvin"
MARKER = "<!-- maintainer-directed-ai-work -->"
AUTO_LABEL = "allow-automation-commits"
AUTOMATION = {
    "github-actions[bot]": "41898282+github-actions[bot]@users.noreply.github.com",
    "dependabot[bot]": "49699333+dependabot[bot]@users.noreply.github.com",
}
BOT_MARKERS = (
    "[bot]", "dependabot", "github actions", "ai agent", "ai-agent",
    "agent bot", "copilot", "claude", "cursor", "windsurf", "codex",
    "chatgpt", "gemini", "openai", "gpt", "ai assistant", "assistant bot",
)


def is_bot(name, email, login=None, account_type=None):
    if (account_type or "").lower() == "bot":
        return True
    if login and login.lower().endswith("[bot]"):
        return True
    value = (name + " " + email + " " + (login or "")).lower()
    return any(marker in value for marker in BOT_MARKERS)


def validate(pr, commits, expected_head_sha=None):
    errors = []
    labels = {x.get("name", "") for x in pr.get("labels", [])}
    allow_auto = AUTO_LABEL in labels
    maintainer_work = MARKER in (pr.get("body") or "")
    maintainer_commit_seen = False
    if expected_head_sha and (pr.get("head") or {}).get("sha") != expected_head_sha:
        return ["PR head changed during validation; rerun against the event head"]
    if not commits:
        return ["empty PR commit list; refusing to pass"]

    for item in commits:
        c = item.get("commit", {})
        a = c.get("author") or {}
        committer = c.get("committer") or {}
        gh_author = item.get("author") or {}
        gh_committer = item.get("committer") or {}
        name, email = a.get("name") or "", a.get("email") or ""
        login, typ = gh_author.get("login"), gh_author.get("type")
        committer_login = gh_committer.get("login")
        sha = (item.get("sha") or "unknown")[:12]

        if not name or not email:
            errors.append(sha + ": missing author name/email")
        bot_author = is_bot(name, email, login, typ)
        if bot_author:
            expected_email = AUTOMATION.get(login)
            genuine_automation = (
                allow_auto
                and login in AUTOMATION
                and typ == "Bot"
                and email.lower() == expected_email
                and committer_login == login
                and (committer.get("email") or "").lower() == expected_email
            )
            if not genuine_automation:
                errors.append(
                    f"{sha}: bot/agent author rejected or automation provenance incomplete: "
                    f"{name!r} <{email}> login={login!r}"
                )

        # Author attribution and committer identity are separate Git fields.
        # A bot committer is acceptable only for the same approved bot author.
        # GitHub's web-flow committer is permitted; it never changes author attribution.
        if committer_login in AUTOMATION and login != committer_login:
            errors.append(f"{sha}: bot committer does not match the commit author")
        if committer_login and committer_login not in {LOGIN, "web-flow"} | set(AUTOMATION):
            if is_bot(
                committer.get("name") or "", committer.get("email") or "",
                committer_login, gh_committer.get("type")
            ):
                errors.append(f"{sha}: unapproved bot/agent committer: {committer_login!r}")

        if login == LOGIN:
            maintainer_commit_seen = True
            if name != NAME or email.lower() != EMAIL.lower():
                errors.append(
                    f"{sha}: maintainer account must use {NAME} <{EMAIL}>, "
                    f"got {name!r} <{email}>"
                )
        elif email.lower() == EMAIL.lower():
            errors.append(
                f"{sha}: maintainer email must resolve to {LOGIN}, not {login!r}"
            )

        for line in (c.get("message") or "").splitlines():
            if line.lower().startswith("co-authored-by:"):
                identity = line.split(":", 1)[1].strip()
                if is_bot(identity, ""):
                    errors.append(
                        f"{sha}: bot/AI Co-authored-by trailer rejected: {identity!r}"
                    )

    if maintainer_work and not maintainer_commit_seen:
        errors.append(
            "maintainer-directed AI work marker requires at least one commit "
            "authored by mojtaba-arvin"
        )
    return errors


def get_json(url, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "commit-identity-policy-check",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode())


def self_test():
    def item(name, email, login, typ, message="feat: test",
             committer_name=None, committer_email=None, committer_login=None,
             committer_type=None):
        committer_name = committer_name or name
        committer_email = committer_email or email
        committer_login = committer_login if committer_login is not None else login
        committer_type = committer_type if committer_type is not None else typ
        return {
            "sha": "a" * 40,
            "commit": {
                "author": {"name": name, "email": email},
                "committer": {"name": committer_name, "email": committer_email},
                "message": message,
            },
            "author": {"login": login, "type": typ},
            "committer": {"login": committer_login, "type": committer_type},
        }

    maintainer = item(NAME, EMAIL, LOGIN, "User")
    human = item("External Human", "x@example.org", "human", "User")
    assert not validate({"body": "", "labels": []}, [maintainer])
    assert not validate({"body": "", "labels": []}, [human])
    assert validate({"body": "", "labels": []},
                    [item("Copilot", "bot@example.org", "copilot[bot]", "Bot")])
    assert validate({"body": "", "labels": []},
                    [item("Human", "h@e.org", "human", "User",
                          "feat: test\n\nCo-authored-by: Copilot <copilot[bot]@users.noreply.github.com>")])
    assert validate({"body": "", "labels": []},
                    [item("Human", "h@e.org", "human", "User",
                          "feat: test\n\nCo-authored-by: Dependabot <dev@users.noreply.github.com>")])
    assert not validate({"body": MARKER, "labels": []}, [maintainer])
    assert not validate({"body": MARKER, "labels": []}, [maintainer, human])
    assert validate({"body": MARKER, "labels": []}, [human])
    assert validate({"body": "", "labels": []},
                    [item(NAME, "wrong@example.org", LOGIN, "User")])
    bot_email = AUTOMATION["github-actions[bot]"]
    genuine = item("github-actions[bot]", bot_email, "github-actions[bot]", "Bot")
    assert validate({"body": "", "labels": []}, [genuine])
    genuine_action = item(
        "github-actions[bot]", bot_email, "github-actions[bot]", "Bot",
        committer_name="github-actions[bot]", committer_email=bot_email,
        committer_login="github-actions[bot]", committer_type="Bot"
    )
    assert not validate({"body": "", "labels": [{"name": AUTO_LABEL}]}, [genuine_action])
    spoofed = item(
        "github-actions[bot]", bot_email, "github-actions[bot]", "Bot",
        committer_name="Maintainer", committer_email=EMAIL,
        committer_login=LOGIN, committer_type="User"
    )
    assert validate({"body": "", "labels": [{"name": AUTO_LABEL}]}, [spoofed])
    assert validate({"body": "", "labels": []}, [maintainer], "b" * 40)
    assert not validate(
        {"body": "", "labels": [], "head": {"sha": "a" * 40}},
        [maintainer], "a" * 40
    )
    web_flow = item(
        NAME, EMAIL, LOGIN, "User", committer_name="GitHub",
        committer_email="noreply@github.com", committer_login="web-flow",
        committer_type="User"
    )
    assert not validate({"body": "", "labels": []}, [web_flow])
    print("PASS: commit identity policy self-tests")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--pr-number", type=int, default=int(os.getenv("PR_NUMBER", "0")))
    parser.add_argument("--expected-head-sha", default=os.getenv("PR_HEAD_SHA"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    if not (args.repository and args.pr_number):
        if args.self_test and not args.pr_number:
            return 0
        parser.error("--repository and --pr-number are required")
    if not args.expected_head_sha:
        parser.error("--expected-head-sha or PR_HEAD_SHA is required")

    base = "https://api.github.com/repos/" + args.repository
    pr = get_json(base + "/pulls/" + str(args.pr_number), args.token)
    commits, page = [], 1
    while True:
        batch = get_json(
            base + f"/pulls/{args.pr_number}/commits?per_page=100&page={page}",
            args.token,
        )
        if not isinstance(batch, list):
            raise RuntimeError("GitHub API returned a non-list commit response")
        commits.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    errors = validate(pr, commits, args.expected_head_sha)
    print(f"Checked {len(commits)} commits in {args.repository}#{args.pr_number}")
    if errors:
        print("\n".join("ERROR: " + error for error in errors))
        return 1
    print("PASS: author attribution, committer metadata, and co-author trailers")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as error:
        print(f"ERROR: GitHub API HTTP {error.code}: {error.reason}", file=sys.stderr)
        sys.exit(2)
    except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as error:
        print(f"ERROR: identity validation incomplete: {error}", file=sys.stderr)
        sys.exit(2)
