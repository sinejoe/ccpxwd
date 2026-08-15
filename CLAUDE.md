# Project instructions for Claude Code

See `README.md` for the file manifest and puzzle data format.

`HANDOFF.md` (removed from the repo, still recoverable via
`git log --diff-filter=D -- HANDOFF.md` / `git show <sha>:HANDOFF.md`)
documented several UI behaviors in `index.html` that look like
simplification targets but are deliberate regression fixes: arrow-key
nav, click-vs-focus orientation handling, typing-replaces-not-inserts,
backspace order, instant vs. smooth scroll, and focus-mode sizing.
Before "cleaning up" any of that logic, check the git history for the
reasoning rather than assuming it's leftover complexity.

## Testing

Prefer real browser testing (Playwright, or just opening the file)
over jsdom. `file://` URLs are blocked by some sandboxed browser
tools — serve the directory locally instead, e.g.
`python3 -m http.server 8842`.

## Building a new week's puzzle

Start at `skill/SKILL.md` — it routes to the two sub-skills:
`skill/fetch-issue/SKILL.md` (find the issue/crossword page on Issuu,
save the raw page image + SVG text layer to `working-files/<date>/`)
and `skill/build-puzzle-json/SKILL.md` (parse that raw material into
`puzzles/<date>.json` + `puzzles/index.json`). Pixel-measure the grid
from the source image, auto-number it, and cross-check the
count/numbering against the puzzle's printed clue numbers before
trusting a transcription. Don't hand-transcribe the grid or assume a
clue's Across/Down direction from its printed column position — both
have caused real shipped bugs.

## `SOLUTION` / reference-solve framing

If asked to add a way to submit or update a reference solve, discuss
the approach with the user first — the previous export/import feature
was deliberately removed (see `HANDOFF.md`), not an oversight. Keep
the existing framing rules: never call a mismatch "wrong" or flag
individual cells, always make clear this is *a* submitted solve, not
an official answer key, and keep the completion indicator a persistent
badge, never a popup.
