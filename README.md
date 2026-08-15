# Charleston City Paper Crossword

An interactive, playable browser crossword built from the Charleston
City Paper's weekly print crossword (syndicated "Jonesin'" puzzles by
Matt Jones).

## Play it

Live at https://ccpx.fyi. Locally, serve the directory (e.g.
`python3 -m http.server 8842`, or `docker compose up -d` for the
Jekyll build) rather than opening `index.html` via `file://` — it
fetches puzzle data with `fetch()`, which most browsers block on
`file://` URLs.

Progress autosaves to `localStorage`; a status badge shows whether a
finished grid matches the reference solve, when one has been set for
that week's puzzle.

## Contents

- `index.html` — static shell: grid, clues, typing/keyboard nav,
  autosave, completion badge. Loads puzzle data at runtime rather
  than hardcoding it.
- `puzzles/index.json` — list of available puzzles (`{id, date,
  title, file}`, newest first). `index.html` picks the entry matching
  `?puzzle=<id>` or defaults to the newest.
- `puzzles/<date>.json` — one week's grid pattern, across/down clues,
  header text, and a pointer to that week's solution-hash file.
- `puzzles/<date>.solution-hashes.txt` — salted per-answer hashes
  used to check a finished grid against the reference solve, without
  shipping the plaintext solution.
- `skill/` — a Claude Code skill that automates building a new week's
  puzzle: `skill/fetch-issue/` finds the current issue on Issuu and
  saves the raw page image/text layer; `skill/build-puzzle-json/`
  parses that into a new `puzzles/<date>.json` entry.
- `_config.yml` — Jekyll config for GitHub Pages; excludes non-app
  files (docs, `skill/`, working files) from the published site.
- `docker-compose.yml` — local Jekyll container for testing the
  GitHub Pages build (including the `_config.yml` exclude list)
  before pushing.

## Status

Live at https://ccpx.fyi. See `CLAUDE.md` for project-specific
instructions on working in this repo.
