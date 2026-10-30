#!/usr/bin/env python3
"""Update stars and last_commit in data/entries.yml from the GitHub API.

Editorial fields are not rewritten. Entries without a GitHub repo are skipped.
A failed lookup leaves the file unchanged and exits non-zero.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "entries.yml"

ENTRY_RE = re.compile(r"^  - id: (\S+)\s*$")
FIELD_RE = {
    "repo": re.compile(r"^    repo: (\S+)\s*$"),
    "branch": re.compile(r"^    branch: (\S+)\s*$"),
    "stars": re.compile(r"^    stars: .*$"),
    "last_commit": re.compile(r"^    last_commit: .*$"),
}


def api_get(url: str, token: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "awesome-tv-debloat-refresh",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch(repo: str, branch: str, token: str) -> tuple[int, str]:
    info = api_get(f"https://api.github.com/repos/{repo}", token)
    if not isinstance(info, dict) or "stargazers_count" not in info:
        raise RuntimeError(f"{repo}: missing stargazers_count")
    commits = api_get(
        f"https://api.github.com/repos/{repo}/commits?per_page=1&sha={branch}",
        token,
    )
    if not isinstance(commits, list) or not commits:
        raise RuntimeError(f"{repo}: no commits on {branch}")
    date = commits[0]["commit"]["committer"]["date"][:10]
    return int(info["stargazers_count"]), date


def parse_entries(text: str) -> list[dict]:
    entries = []
    current = None
    for index, line in enumerate(text.splitlines()):
        matched = ENTRY_RE.match(line)
        if matched:
            current = {"id": matched.group(1), "lines": {}}
            entries.append(current)
            continue
        if current is None:
            continue
        for key, pattern in FIELD_RE.items():
            found = pattern.match(line)
            if found:
                current["lines"][key] = index
                if key in ("repo", "branch"):
                    value = found.group(1)
                    current[key] = None if value == "null" else value
                break
    return entries


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN is not set", file=sys.stderr)
        sys.exit(1)
    text = DATA.read_text(encoding="utf-8")
    lines = text.splitlines()
    entries = parse_entries(text)
    updates = []
    for entry in entries:
        repo = entry.get("repo")
        if not repo:
            continue
        for key in ("stars", "last_commit", "branch"):
            if key not in entry["lines"] or (key == "branch" and not entry.get("branch")):
                print(f"error: {entry['id']} is missing {key}", file=sys.stderr)
                sys.exit(1)
        try:
            stars, last_commit = fetch(repo, entry["branch"], token)
        except (urllib.error.URLError, TimeoutError, KeyError, RuntimeError) as exc:
            print(f"error: {entry['id']}: {exc}", file=sys.stderr)
            sys.exit(1)
        star_line = f"    stars: {stars}"
        commit_line = f'    last_commit: "{last_commit}"'
        if lines[entry["lines"]["stars"]] != star_line or lines[entry["lines"]["last_commit"]] != commit_line:
            updates.append((entry["id"], stars, last_commit))
            lines[entry["lines"]["stars"]] = star_line
            lines[entry["lines"]["last_commit"]] = commit_line
    if not updates:
        print("stats already match the GitHub API")
        return
    DATA.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    for eid, stars, last_commit in updates:
        print(f"updated {eid}: {stars} stars, {last_commit}")


if __name__ == "__main__":
    main()
