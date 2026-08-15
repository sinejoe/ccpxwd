---
name: charleston-citypaper-build-puzzle-json
description: Parse an already-fetched Charleston City Paper crossword page (working-files/<date>/page.jpg + svg_text.json + meta.json, produced by the charleston-citypaper-fetch-issue skill) into puzzles/<date>.json and add it to puzzles/index.json. Use this once the raw page image and SVG text layer are already saved to working-files/ and the user wants them turned into this week's playable puzzle data. Do NOT use this to go fetch a new issue -- that's the separate charleston-citypaper-fetch-issue skill.
---

# Build this week's puzzle JSON

Second half of the two-step weekly pipeline. Deterministic and
mechanical by design — everything here operates on files already sitting
in `working-files/<date>/`, with no network fetching, so it's safe to
re-run as many times as needed while chasing down a transcription error
without touching Issuu again.

If `working-files/<date>/` doesn't exist or is missing `page.jpg` /
`svg_text.json` / `meta.json`, stop and run
`charleston-citypaper-fetch-issue` first.

## Step 1 — Extract the grid pattern

```bash
python3 ../scripts/extract_grid.py working-files/<date>/page.jpg
```

If other dark page content confuses line detection, pass a rough crop
(`--crop x0,y0,x1,y1` — doesn't need to be pixel-exact). This prints the
detected `.`/`#` pattern and an auto-numbering summary: how many
Across/Down entries it implies and their exact numbers. **Keep this
summary** — it's the cross-check for Step 3.

## Step 2 — Reconstruct clue text from the SVG text layer

Read `working-files/<date>/svg_text.json`. Group nodes by their `y`
value (rounded — glyphs on the same printed line share the same
y-translate), concatenate within each group in x-order, and read lines
top-to-bottom to reconstruct the clue list text.

**Read the clue-layout convention in
`../references/workflow_notes.md` ("Clue-list layout convention") before
splitting into Across vs. Down** — this puzzle's two printed text columns
do NOT align with the Across/Down split; assuming they do has caused a
real shipped bug (a swapped clue pair) before. All Across clues run
first in the left column; Down starts partway down that same column and
continues into the right column, so the top of the right column is a
continuation of Down, not a new section.

## Step 3 — Verify before trusting either extraction

Compare the auto-numbering summary from Step 1 against the clue numbers
you transcribed in Step 2: same count, same specific numbers, 1 through
the highest with no gaps. If they don't match, first suspect the clue
transcription (easy to misread a number in small print) before
suspecting the grid extraction (a direct pixel measurement, historically
reliable). Do not proceed to Step 4 on a mismatch — re-crop/re-parse
instead.

## Step 4 — Write puzzles/<date>.json

Schema (authoritative — `index.html`'s `loadPuzzleData()` consumes this
shape directly):

```json
{
  "id": "ccp-<date>-<short-slug-from-title>",
  "date": "<date>",
  "kicker": "Charleston City Paper · <MM.DD.YYYY>",
  "title": "<puzzleTitle from meta.json>",
  "subtitle": "<byline from meta.json>",
  "solutionSalt": "ccpxwd-<year>-ref-solve",
  "solutionHashesFile": "puzzles/<date>.solution-hashes.txt",
  "pattern": [ /* 15 rows from Step 1 */ ],
  "across": [ /* [number, "clue text"] from Step 2 */ ],
  "down": [ /* [number, "clue text"] from Step 2 */ ]
}
```

Use real unicode punctuation (curly quotes, em dash) in the JSON
strings, not HTML entities — `index.html` writes these fields via
`textContent`, not `innerHTML`.

`solutionHashesFile` does not need to exist yet — the completion badge
just shows "Grid complete" with no match/mismatch comparison until
someone solves the puzzle via the site's `?admin=1` panel and generates
that file. That's a separate, later step, not part of this skill.

## Step 5 — Add it to puzzles/index.json

Prepend a new entry (newest first):

```json
{ "id": "<id>", "date": "<date>", "title": "<title>", "file": "puzzles/<date>.json" }
```

## Step 6 — Validate before handing back

```bash
python3 -c "import json; json.load(open('puzzles/<date>.json')); json.load(open('puzzles/index.json'))"
```

Then serve the repo locally (`python3 -m http.server 8842`) and check in
a real browser (Playwright, or just open it) that:
- `document.getElementById('grid').children.length` is `SIZE*SIZE`
  (225 for a 15×15).
- The Across/Down list lengths on the page match Step 1's auto-numbering
  counts.
- The header (kicker/title/subtitle) and `<title>` show this week's
  puzzle, not a stale one.

Only report success once these checks pass.
