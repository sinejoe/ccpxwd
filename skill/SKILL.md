---
name: charleston-citypaper-crossword
description: Router for the Charleston City Paper weekly crossword pipeline. Use this to figure out which of the two sub-skills applies -- charleston-citypaper-fetch-issue (find the week's issue/crossword page on Issuu, save the raw page image + SVG text layer) or charleston-citypaper-build-puzzle-json (parse already-fetched raw material into puzzles/<date>.json). If the user's intent is already clear ("find this week's crossword" vs. "build the JSON from what we fetched"), invoke that sub-skill directly instead of this one.
---

# Charleston City Paper Crossword — weekly pipeline

Turning a new week's print crossword into a playable entry in this repo
is a two-step pipeline, split into two sub-skills so the fragile,
judgment-heavy step (finding the right page on Issuu) and the
deterministic step (parsing it into JSON) can be run and re-run
independently:

1. **`fetch-issue/SKILL.md`** — locates the current (or a specified)
   week's issue on Issuu, finds the crossword page inside it, and saves
   the raw page image + SVG text layer to `working-files/<date>/`. This
   is the part that needs a live browser (`claude-in-chrome`) and human
   judgment about which page is actually the crossword.
2. **`build-puzzle-json/SKILL.md`** — takes that `working-files/<date>/`
   directory and turns it into `puzzles/<date>.json` (grid pattern,
   clues, header text) plus a new entry in `puzzles/index.json`. Pure
   parsing, no network access, safe to re-run as many times as needed
   while fixing a transcription error.

If the user already has a puzzle photo/screenshot instead of wanting a
fresh Issuu fetch, skip step 1: save the image directly to
`working-files/<date>/page.jpg`, get clue text by reading the image
yourself (there's no SVG text layer for an uploaded photo, so
`svg_text.json` won't exist — transcribe carefully and lean harder on
the auto-numbering cross-check in step 2), write a minimal
`working-files/<date>/meta.json` (date, title, byline), then go straight
to `build-puzzle-json`.

`index.html` itself is a static shell that fetches whatever
`puzzles/index.json` points to — a routine new week never requires
editing `index.html`. Puzzle JSON schema lives inline in
`build-puzzle-json/SKILL.md` Step 4 — that's the authoritative
reference.

## Optional: baking in a reference solve

This is a separate, later, on-site step — not part of either sub-skill
above. Once a puzzle is published, load the live page with `?admin=1`,
enter the passphrase, solve the puzzle in the normal grid, and use the
"Generate solution-hashes file from my grid" button to produce that
puzzle's `solutionHashesFile` contents. Framing rules for any
match/mismatch UI are in the repo's `CLAUDE.md`: never call anything
"wrong", never flag individual cells, always make clear it's *a*
submitted solve, not an official answer key.
