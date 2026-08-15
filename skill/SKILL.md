---
name: charleston-citypaper-crossword
description: Build a playable, interactive browser crossword from the Charleston City Paper's weekly print crossword puzzle. Use this whenever the user asks for "this week's crossword", "the new Charleston City Paper puzzle", asks you to check/find/fetch/grab the latest issue's crossword, mentions reusing "the crossword template" for a new puzzle, or uploads a photo/screenshot of a Charleston City Paper crossword page. Covers finding the current issue on Issuu, locating the crossword page, extracting the grid layout via pixel analysis (not a visual guess), transcribing the clues, and producing the interactive HTML artifact with autosave and NYT-style keyboard navigation.
---

# Charleston City Paper Crossword Builder

Turns a photo (or a freshly-fetched issue page) of the Charleston City
Paper's weekly crossword into a fully playable browser artifact: 15x15
(or whatever size the actual puzzle is) grid on the left, Across/Down
clues in two columns on the right, arrow-key navigation, click-to-select
clues, and autosaving progress via the artifact's persistent storage.

## When the user already has an image

If a puzzle photo/screenshot is already uploaded, skip straight to
**Step 2**.

## Step 1 — Find the current issue and crossword page

If the user wants "this week's" puzzle rather than a specific upload,
see `references/workflow_notes.md` for the Issuu URL pattern, how to
locate the newest issue, and where the crossword page tends to sit
within it. Fetch/screenshot that page as an image before continuing.

This part is genuinely variable week to week (page numbers shift,
Issuu's rendering can change) — don't guess at a page image URL from
memory; verify it against what's actually on the page each time.

## Step 2 — Extract the grid with pixel analysis, not by eye

Do NOT hand-transcribe the black/white square layout by looking at the
image — it's easy to get subtly wrong in a way that looks plausible but
throws off every clue number after the mistake. Instead:

```
python3 scripts/extract_grid.py <path-to-puzzle-image>
```

This measures actual pixel brightness per cell rather than guessing, and
prints:
- the detected pattern (`.`/`#` per row)
- an auto-numbering summary: how many Across/Down entries it implies,
  and their exact numbers

If the page has other dark content near the grid (a solution grid,
photos, dense text) that confuses line detection, pass a rough crop:

```
python3 scripts/extract_grid.py <image> --crop x0,y0,x1,y1
```

(Eyeball the crop box from the image — doesn't need to be pixel-exact,
the script finds the precise grid lines within it.)

**Verify before moving on:** compare the script's Across/Down numbers
against the clue numbers you can see printed on the page. They should
match exactly, 1 through the highest number, no gaps. If they don't,
re-crop and re-run rather than proceeding with a mismatch — see
`references/workflow_notes.md` for troubleshooting.

## Step 3 — Transcribe the clues

Read the Across and Down clue lists directly from the image/page and
transcribe them verbatim (typos in a clue are far more noticeable to the
user than a grid issue would be, so take care here). Keep the exact
clue numbers as printed.

**Read `references/workflow_notes.md`'s clue-layout section before
transcribing** — this puzzle's two printed text columns do NOT align
with the Across/Down split (the Down list starts partway down the left
column and continues into the right column), which has caused real
transcription errors before. Verify each clue's direction against the
grid's own auto-numbering rather than assuming column position implies
direction.

## Step 4 — Fill in the template

Copy `assets/crossword_template.html` and edit these pieces (each is
clearly marked with a comment in the file):

- Header: kicker (publication + date), title, subtitle
- `pattern` array: the `.`/`#` rows from Step 2
- `ACROSS` / `DOWN` arrays: `[number, "clue text"]` pairs from Step 3
- `PUZZLE_ID`: a unique string for this puzzle (e.g.
  `ccp-YYYY-MM-DD-slug`) — this keys the autosave storage, so each
  week's puzzle needs its own ID or progress from a prior week will
  bleed into the new one

Everything else (grid rendering, numbering, keyboard navigation,
autosave, clue-click highlighting) is generic and shouldn't need
changes.

## Step 5 — Test before presenting

Before handing the file to the user, sanity-check it actually runs:

```bash
python3 -c "
import re
html = open('PATH_TO_FILE.html').read()
open('/tmp/_check.js','w').write(re.search(r'<script>(.*)</script>', html, re.S).group(1))
"
node --check /tmp/_check.js
```

A `node --check` pass only catches syntax errors — it will NOT catch a
`const`/`let` name colliding with a browser global (e.g. `top`, `name`,
`location`, `history`, `status`, `event`, `frames`), which produces a
silent syntax error only inside an actual browser/DOM context. If
you've renamed anything in the template, run it through jsdom too:

```bash
pip install jsdom --break-system-packages -q   # (jsdom is actually an npm package)
npm install jsdom --silent
node -e "
const { JSDOM } = require('jsdom');
const fs = require('fs');
const html = fs.readFileSync('PATH_TO_FILE.html','utf8');
const dom = new JSDOM(html, { runScripts: 'dangerously', resources: 'usable' });
dom.window.onerror = (m,s,l) => console.log('ERROR', m, 'line', l);
setTimeout(()=> console.log('grid cells:', dom.window.document.getElementById('grid').children.length), 300);
"
```
`grid cells: 225` (or N*N for the actual grid size) confirms it rendered
without error.

## Step 6 — Save to outputs and present

Save to `/mnt/user-data/outputs/`, then use `present_files`. Mention
that progress autosaves per-puzzle (keyed by `PUZZLE_ID`), so closing
and reopening won't lose their work, and that a new week's puzzle
starts with a blank grid since it's a different `PUZZLE_ID`.

## Optional: baking in a reference solve

The template has a `const SOLUTION = null;` near the top of the
script. If the user later hands over a "progress code" (the same
base64 string their own "Copy progress code" button produces) after
finishing the puzzle themselves, decode it and populate `SOLUTION`
with the resulting row strings, then rebuild and republish. Once set,
the completion status automatically starts comparing the solver's
grid against it and reports a match/mismatch count.

This is explicitly NOT an official answer key — it's just whatever
solve that person chose to submit — so the UI language is deliberately
soft ("differs from our reference solve in N spots", never "wrong" or
"error"), and no individual cells get flagged. Keep any future
comparison feature honoring that same framing: informational, not a
grading experience. Only do this when the user explicitly provides a
solve; never fabricate or guess one.
