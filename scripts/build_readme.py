#!/usr/bin/env python3
"""Render README.md from data/entries.yml.

The YAML file is the only place facts are edited. This script fails if the
README drifts, if a claim has no source, or if the forbidden word appears.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "entries.yml"
README = ROOT / "README.md"

FORBIDDEN = re.compile(r"\btested\b", re.IGNORECASE)
# The tagline says "Not tested." A project may also say it is "untested".
# Any other use of the word is a claim that a television was tried.
DISCLAIMER = re.compile(r"\b(?:not tested|untested)\b", re.IGNORECASE)

ROOT_RANK = {"no": 0, "depends": 1, "unknown": 2, "yes": 3}
UNDO_RANK = {"yes": 0, "partial": 1, "unknown": 2, "no": 3}
PC_RANK = {"no": 0, "depends": 1, "unknown": 2, "yes": 3}

KIND_ORDER = [
    "on-device-settings",
    "dns-block",
    "clean-launcher",
    "ad-free-client",
    "adb-debloat",
    "homebrew",
    "firmware-root",
]
KIND_LABEL = {
    "on-device-settings": "On-device settings",
    "dns-block": "DNS blocking",
    "clean-launcher": "Clean launcher",
    "ad-free-client": "Ad-free client",
    "adb-debloat": "ADB debloat",
    "homebrew": "Homebrew",
    "firmware-root": "Firmware / root",
}

ENUM_ROOT = set(ROOT_RANK)
ENUM_UNDO = set(UNDO_RANK)
ENUM_PC = set(PC_RANK)
SOURCE_KEYS = (
    "kinds",
    "root",
    "reversible",
    "undo",
    "pc_needed",
    "platforms",
    "stars",
    "last_commit",
    "license",
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def has_forbidden(text: str) -> bool:
    return bool(FORBIDDEN.search(DISCLAIMER.sub(" ", text)))


def load() -> dict:
    if not DATA.is_file():
        fail(f"missing {DATA}")
    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("entries.yml must be a mapping")
    return data


def require_url(entry_id: str, key: str, url: object) -> str:
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        fail(f"{entry_id}: sources.{key} must be an http(s) URL")
    return url


def validate(data: dict) -> None:
    raw = DATA.read_text(encoding="utf-8")
    if has_forbidden(raw):
        fail("data/entries.yml contains the forbidden word")

    platforms = data.get("platforms")
    entries = data.get("entries")
    if not isinstance(platforms, list) or not platforms:
        fail("platforms must be a non-empty list")
    if not isinstance(entries, list) or not entries:
        fail("entries must be a non-empty list")

    ids = []
    by_id = {}
    for entry in entries:
        if not isinstance(entry, dict):
            fail("each entry must be a mapping")
        eid = entry.get("id")
        if not isinstance(eid, str) or not re.fullmatch(r"[a-z0-9-]+", eid):
            fail(f"bad id: {eid!r}")
        if eid in by_id:
            fail(f"duplicate id {eid}")
        ids.append(eid)
        by_id[eid] = entry
        for key in ("name", "author", "undo", "note"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                fail(f"{eid}: {key} must be a non-empty string")
        if entry.get("repo") is None:
            if entry.get("branch") is not None:
                fail(f"{eid}: branch must be null when repo is null")
            if not isinstance(entry.get("url"), str):
                fail(f"{eid}: url is required when repo is null")
        else:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", str(entry.get("repo"))):
                fail(f"{eid}: repo must be owner/name")
            if not isinstance(entry.get("branch"), str) or not entry["branch"]:
                fail(f"{eid}: branch is required for a GitHub repo")
        if entry.get("root") not in ENUM_ROOT:
            fail(f"{eid}: bad root")
        if entry.get("reversible") not in ENUM_UNDO:
            fail(f"{eid}: bad reversible")
        if entry.get("pc_needed") not in ENUM_PC:
            fail(f"{eid}: bad pc_needed")
        kinds = entry.get("kinds")
        if not isinstance(kinds, list) or not kinds or any(k not in KIND_LABEL for k in kinds):
            fail(f"{eid}: kinds must use the documented vocabulary")
        plats = entry.get("platforms")
        if not isinstance(plats, list) or not plats:
            fail(f"{eid}: platforms must be a non-empty list")
        stars = entry.get("stars")
        if stars != "unknown" and not isinstance(stars, int):
            fail(f"{eid}: stars must be an integer or 'unknown'")
        last = entry.get("last_commit")
        if last != "unknown" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(last)):
            fail(f"{eid}: last_commit must be YYYY-MM-DD or 'unknown'")
        if not isinstance(entry.get("license"), str) or not entry["license"].strip():
            fail(f"{eid}: license must be an SPDX id or 'unknown'")
        if not isinstance(entry.get("archived"), bool):
            fail(f"{eid}: archived must be a boolean")
        sources = entry.get("sources")
        if not isinstance(sources, dict):
            fail(f"{eid}: sources must be a mapping")
        for key in SOURCE_KEYS:
            require_url(eid, key, sources.get(key))
        if has_forbidden(entry["undo"]) or has_forbidden(entry["note"]):
            fail(f"{eid}: note or undo contains the forbidden word")
        badge = entry.get("badge")
        if badge is not None and (not isinstance(badge, str) or not badge.strip()):
            fail(f"{eid}: badge must be a non-empty string when set")
        if isinstance(badge, str) and has_forbidden(badge):
            fail(f"{eid}: badge contains the forbidden word")

    known_platforms = []
    for platform in platforms:
        pid = platform.get("id")
        if not isinstance(pid, str):
            fail("platform missing id")
        known_platforms.append(pid)
        for key in ("title", "start_here", "start_here_text"):
            if not isinstance(platform.get(key), str) or not platform[key].strip():
                fail(f"{pid}: {key} is required")
        require_url(pid, "start_here_source", platform.get("start_here_source"))
        starter = platform["start_here"]
        if starter not in by_id:
            fail(f"{pid}: start_here {starter} is not an entry")
        if pid not in by_id[starter]["platforms"]:
            fail(f"{pid}: start_here {starter} does not list this platform")
        if has_forbidden(platform["start_here_text"]):
            fail(f"{pid}: start here text contains the forbidden word")
        caveat = platform.get("caveat")
        if caveat is not None:
            if not isinstance(caveat, str) or not caveat.strip():
                fail(f"{pid}: caveat must be a non-empty string when set")
            require_url(pid, "caveat_source", platform.get("caveat_source"))
            if has_forbidden(caveat):
                fail(f"{pid}: caveat contains the forbidden word")

    for entry in entries:
        for pid in entry["platforms"]:
            if pid not in known_platforms:
                fail(f"{entry['id']}: unknown platform {pid}")

    for item in data.get("left_out") or []:
        if not isinstance(item, dict):
            fail("left_out items must be mappings")
        for key in ("name", "why"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                fail(f"left_out missing {key}")
        require_url(item["name"], "url", item.get("url"))
        if has_forbidden(item["why"]):
            fail(f"left_out {item['name']} contains the forbidden word")

    for key in ("safety", "how_to_read", "tagline", "ai_disclosure"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            fail(f"{key} is required")
        if has_forbidden(data[key]):
            fail(f"{key} contains the forbidden word")


def md(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def link(url: str) -> str:
    return f"[src]({url})"


def project_url(entry: dict) -> str:
    if entry.get("repo"):
        return f"https://github.com/{entry['repo']}"
    return entry["url"]


def author_cell(entry: dict) -> str:
    author = md(entry["author"])
    if entry.get("repo"):
        login = entry["repo"].split("/")[0]
        return f"[{author}](https://github.com/{login})"
    return author


def kind_cell(entry: dict) -> str:
    labels = [KIND_LABEL[k] for k in KIND_ORDER if k in entry["kinds"]]
    return f"{md(', '.join(labels))} {link(entry['sources']['kinds'])}"


def value_cell(entry: dict, field: str) -> str:
    return f"{md(str(entry[field]))} {link(entry['sources'][field])}"


def undo_cell(entry: dict) -> str:
    status = md(str(entry["reversible"]))
    how = md(entry["undo"])
    src = entry["sources"]["undo"]
    rev = entry["sources"]["reversible"]
    if src == rev:
        return f"{status} — {how} {link(src)}"
    return f"{status} {link(rev)} — {how} {link(src)}"


def stars_cell(entry: dict) -> str:
    stars = entry["stars"]
    shown = f"{stars:,}" if isinstance(stars, int) else "unknown"
    return f"{shown} {link(entry['sources']['stars'])}"


def rank(entry: dict) -> tuple:
    return (
        ROOT_RANK[entry["root"]],
        UNDO_RANK[entry["reversible"]],
        PC_RANK[entry["pc_needed"]],
        entry["name"].lower(),
    )


def render_table(rows: list[dict]) -> str:
    header = (
        "| Tool | Kind | Root | Undo | PC | Stars | Last commit | License |\n"
        "| --- | --- | --- | --- | --- | ---: | --- | --- |"
    )
    body = []
    for entry in rows:
        name = md(entry["name"])
        if entry.get("archived"):
            name += " (archived)"
        tool = f"[{name}]({project_url(entry)})<br>{author_cell(entry)}"
        if entry.get("badge"):
            tool += f"<br>{md(entry['badge'])}"
        cells = [
            tool,
            kind_cell(entry),
            value_cell(entry, "root"),
            undo_cell(entry),
            value_cell(entry, "pc_needed"),
            stars_cell(entry),
            value_cell(entry, "last_commit"),
            value_cell(entry, "license"),
        ]
        body.append("| " + " | ".join(cells) + " |")
    return header + "\n" + "\n".join(body)


def render(data: dict) -> str:
    by_id = {entry["id"]: entry for entry in data["entries"]}
    lines = [
        "<!-- Generated from data/entries.yml by scripts/build_readme.py. Do not edit by hand. -->",
        "",
        "# awesome-tv-debloat",
        "",
        data["tagline"].strip(),
        "",
        data["ai_disclosure"].strip(),
        "",
        "## Safety",
        "",
        data["safety"].strip(),
        "",
        "## How to read this",
        "",
        data["how_to_read"].strip(),
        "",
    ]

    for platform in data["platforms"]:
        pid = platform["id"]
        starter = by_id[platform["start_here"]]
        rows = [entry for entry in data["entries"] if pid in entry["platforms"]]
        rest = [entry for entry in rows if entry["id"] != starter["id"]]
        ordered = [starter] + sorted(rest, key=rank)
        lines.append(f"## {platform['title']}")
        lines.append("")
        lines.append(
            f"**Start here: [{md(starter['name'])}]({project_url(starter)})** "
            f"by {author_cell(starter)}. {md(platform['start_here_text'])} "
            f"{link(platform['start_here_source'])}"
        )
        lines.append("")
        if platform.get("caveat"):
            lines.append(
                f"**Caveat.** {md(platform['caveat'])} "
                f"{link(platform['caveat_source'])}"
            )
            lines.append("")
        lines.append(
            f"{len(ordered)} entries. The first row is the start-here pick. "
            "The rows after it run from the smaller change to the larger one: "
            "no root before root, a full way back before a partial one, "
            "and no computer before a computer."
        )
        lines.append("")
        lines.append(render_table(ordered))
        lines.append("")
        lines.append("Notes")
        lines.append("")
        for entry in ordered:
            lines.append(f"- **{md(entry['name'])}.** {md(entry['note'])}")
        lines.append("")

    lines.append("## Related lists")
    lines.append("")
    lines.append(
        "[Awesome Android TV FOSS Apps](https://github.com/Generator/Awesome-Android-TV-FOSS-Apps) "
        "is a separate curated list of free and open-source Android TV apps. "
        "This repository does not copy its wording or its layout."
    )
    lines.append("")
    lines.append("## Left out")
    lines.append("")
    lines.append(
        "These came up while gathering the tables. They are omitted because a "
        "cell would have been a guess, or because the project is not itself a way to strip ads."
    )
    lines.append("")
    for item in data.get("left_out") or []:
        lines.append(f"- [{md(item['name'])}]({item['url']}). {md(item['why'])}")
    lines.append("")
    lines.append("## License")
    lines.append("")
    lines.append(
        "This list is [CC0-1.0](LICENSE). Each linked project keeps the license named in its row. "
        "Names of television brands belong to their owners."
    )
    lines.append("")
    text = "\n".join(lines)
    if has_forbidden(text):
        fail("generated README contains the forbidden word")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if README.md does not match the YAML",
    )
    args = parser.parse_args()
    data = load()
    validate(data)
    text = render(data)
    if args.check:
        current = README.read_text(encoding="utf-8") if README.is_file() else ""
        if current != text:
            fail("README.md does not match data/entries.yml. Run scripts/build_readme.py")
        print(f"README.md matches data/entries.yml ({len(data['entries'])} entries)")
        return
    README.write_text(text, encoding="utf-8")
    print(f"wrote {README} ({len(data['entries'])} entries)")


if __name__ == "__main__":
    main()
