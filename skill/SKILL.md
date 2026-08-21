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
   the raw page image + SVG text layer to `working-files/<date>/`. Runs
   as a plain script (`skill/scripts/fetch_issue.py`, no browser
   automation needed) — see that skill for the (rare) manual fallback.
2. **`build-puzzle-json/SKILL.md`** — takes that `working-files/<date>/`
   directory and turns it into `puzzles/<date>.json` (grid pattern,
   clues, header text) plus a new entry in `puzzles/index.json`. Pure
   parsing, no network access, safe to re-run as many times as needed
   while fixing a transcription error. Its final step also upgrades
   *last* week's puzzle to an official-solution match using the
   solution grid crop step 1 just produced — see "Baking in the
   official solve" below; this is a standard part of every weekly run,
   not a separate later task.

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

## Baking in the official solve (standard last step of every weekly run)

Every issue prints the *previous* week's completed grid as a small
solution key, and `fetch_issue.py` (step 1 above) already crops it to
`working-files/<the-prior-week's-date>/printed_solution_grid_CANDIDATE.jpg`
and merges `officialSolutionUrl`/`officialSolutionPage` into that prior
week's `meta.json` — see `fetch-issue/SKILL.md` ("Last week's solution
grid"). Once this week's puzzle is built and published, use that crop
to upgrade *last* week's already-published `puzzles/<prior-date>.json`
to `solutionSource: "official"`:

1. Confirm the crop's bounds visually (`page.jpg`/the candidate crop
   image) — re-crop tighter if other page content bled in.
2. Transcribe the solved grid's letters, respecting the prior week's
   already-published `pattern` for black-cell positions (don't
   re-derive black positions from the image — the pattern is already
   known-good).
3. Compute one `<num><A/D>-<sha256hex>` line per Across/Down entry —
   `sha256hex(solutionSalt + word)`, salt and numbering both coming
   from the prior week's `puzzles/<prior-date>.json` — and write them
   to that puzzle's `solutionHashesFile` path. Cross-check the derived
   Across/Down numbering against that file's existing `across`/`down`
   clue-number lists before trusting the transcription (same
   verification spirit as build-puzzle-json Step 3).
4. Set `"solutionSource": "official"` and `"officialSolutionUrl"` (from
   that prior week's `meta.json`) on `puzzles/<prior-date>.json`.
5. Verify in a real browser: fill the prior week's grid with the
   transcribed letters and confirm the completion badge shows the
   "match ... official answer key" wording, not a mismatch.

Skip this only if the crop is unusable (bad bounds, obscured page) or
the prior week has no published puzzle to upgrade (e.g. a gap week) —
otherwise treat it as required, not optional. Framing rules for any
match/mismatch UI are in the repo's `CLAUDE.md`: never call anything
"wrong", never flag individual cells, always make clear it's *a*
submitted solve (or here, the official key), not a live-graded answer.

## Reference solve for the current week (no official key exists yet)

There is no on-site admin panel for this — that was a deliberately
removed feature (see `HANDOFF.md` history) and stays removed. Instead,
this week's puzzle gets a *reference* (non-official) solve straight
from a live solve session:

1. Serve the repo locally and open this week's puzzle in a Playwright
   browser window; the user solves it there like a normal player.
2. Once they say it's done, read the finished grid back out —
   `localStorage.getItem('crossword:<id>')` (autosaved as
   `{"rows":[...]}`, `#`=black/`.`=empty) is the simplest source, or
   read each `.cell input`'s value directly from the DOM.
3. Compute `sha256hex(solutionSalt + word)` per Across/Down entry (same
   method as "Baking in the official solve" above) and write
   `puzzles/<date>.solution-hashes.txt`.
4. Leave `solutionSource` unset (defaults to `"reference"`) on
   `puzzles/<date>.json` — this is a submitted solve, not an official
   answer key, per the framing rules in `CLAUDE.md`.

When that puzzle's official printed key shows up the *following* week,
the "Baking in the official solve" step above overwrites this file and
flips `solutionSource` to `"official"` — the reference solve is just a
placeholder until then.
