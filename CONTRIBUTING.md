# Contributing

Edit `data/entries.yml`, then regenerate the README:

```sh
pip install -r requirements.txt
python scripts/build_readme.py
python scripts/build_readme.py --check
```

Do not edit `README.md` by hand. CI rejects a drift between the YAML and the README.

## What an entry is

One public project that strips ads from a smart TV, or that is the installer the project's own docs require. Forks that only repeat an upstream README stay out. Say so in `left_out` with a link.

## Fields

```yaml
  - id: example-tool
    name: Example Tool
    author: github-login
    repo: owner/name          # or null, and then set url
    branch: main              # or null when repo is null
    url: https://example.com  # only when repo is null
    platforms: [android-tv]
    kinds: [clean-launcher]
    root: "no"                # yes, no, depends, unknown
    reversible: "yes"         # yes, partial, no, unknown
    undo: "How the project says to put it back."
    pc_needed: "no"           # yes, no, depends, unknown
    stars: 0                  # integer, or unknown when there is no GitHub repo
    last_commit: "2026-01-02" # YYYY-MM-DD, or unknown
    license: MIT              # SPDX id, or unknown
    archived: false
    note: "One or two sentences of scope the table cannot hold."
    sources:
      kinds: https://github.com/owner/name/blob/main/README.md
      root: https://github.com/owner/name/blob/main/README.md
      reversible: https://github.com/owner/name/blob/main/README.md
      undo: https://github.com/owner/name/blob/main/README.md
      pc_needed: https://github.com/owner/name/blob/main/README.md
      platforms: https://github.com/owner/name/blob/main/README.md
      stars: https://api.github.com/repos/owner/name
      last_commit: https://github.com/owner/name/commits/main
      license: https://github.com/owner/name/blob/main/LICENSE
```

Quote `yes` and `no`. Unquoted, YAML reads them as booleans.

`platforms` must use an id already listed under `platforms:`.

`kinds` must be one or more of:

- `dns-block` — DNS blocking
- `clean-launcher` — a home screen without the stock ad rows
- `ad-free-client` — an app that replaces an ad-supported client
- `adb-debloat` — disables or uninstalls packages over ADB
- `homebrew` — a store or installer for other apps on the TV
- `firmware-root` — root, a firmware change, or a root-only service

## Rules for a cell

- Take the cell from that project's README or code. Link that page in `sources`.
- If the project does not say, write `unknown` and still link the page you checked.
- Do not write that a television was tried. This repository has no television.
- Credit the author. One short quotation from their README is the most you should copy.
- Do not copy wording or layout from [Awesome Android TV FOSS Apps](https://github.com/Generator/Awesome-Android-TV-FOSS-Apps).
- Stars and `last_commit` for GitHub repos are refreshed by `.github/workflows/refresh-stats.yml`. Leave other fields alone in that job.

## Start here

Each platform has a `start_here` id. Point it at the option whose own README describes the smallest reversible change: no root and a documented way back, before a package cleanup, before root.

## Weekly stats

`scripts/refresh_stats.py` rewrites only the `stars` and `last_commit` lines of entries that have a GitHub `repo`. It needs `GITHUB_TOKEN`. If the API call fails, it leaves the file untouched. The weekly workflow then runs `scripts/build_readme.py` so the README in that pull request matches.
