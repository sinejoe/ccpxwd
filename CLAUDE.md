# Project instructions for Claude Code

Read `HANDOFF.md` in full before touching code in this repo. It has
the file manifest, the puzzle data format, and — most importantly — a
list of specific UI bugs that were already found and fixed, with why
each fix works the way it does (arrow-key nav, click-vs-focus
orientation handling, typing-replaces-not-inserts, backspace order,
instant vs. smooth scroll, focus-mode sizing). Don't re-simplify
anything HANDOFF.md flags as deliberate — those aren't leftover
complexity, they're regression fixes.

## Testing

Prefer real browser testing (Playwright, or just opening the file)
over jsdom. `file://` URLs are blocked by some sandboxed browser
tools — serve the directory locally instead, e.g.
`python3 -m http.server 8842`.

## Building a new week's puzzle

Use `skill/SKILL.md` — pixel-measure the grid from the source image,
auto-number it, and cross-check the count/numbering against the
puzzle's printed clue numbers before trusting a transcription. Don't
hand-transcribe the grid or assume a clue's Across/Down direction from
its printed column position — both have caused real shipped bugs.

## `SOLUTION` / reference-solve framing

If asked to add a way to submit or update a reference solve, discuss
the approach with the user first — the previous export/import feature
was deliberately removed (see `HANDOFF.md`), not an oversight. Keep
the existing framing rules: never call a mismatch "wrong" or flag
individual cells, always make clear this is *a* submitted solve, not
an official answer key, and keep the completion indicator a persistent
badge, never a popup.
