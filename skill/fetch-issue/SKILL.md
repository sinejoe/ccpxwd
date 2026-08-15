---
name: charleston-citypaper-fetch-issue
description: Find this week's (or a specific week's) Charleston City Paper issue on Issuu, locate the crossword page inside it, and save the raw page image plus its SVG text layer to working-files/ for a later parsing step. Use this when the user asks to "find/fetch/grab this week's crossword", "check for the new issue", or otherwise wants the raw source material pulled down -- NOT when they already have an image, and NOT when they're ready to turn already-fetched material into puzzles/*.json (that's the separate charleston-citypaper-build-puzzle-json skill).
---

# Fetch this week's Charleston City Paper issue

First half of the two-step weekly pipeline. This skill's only job is to
locate the crossword page for a given week and save two raw artifacts to
`working-files/<date>/` — it does **not** parse the grid or clues. Hand
off to `charleston-citypaper-build-puzzle-json` for that.

Splitting it this way matters because this half is the fragile,
judgment-heavy part (page numbers drift, Issuu's rendering can change,
finding the right page is a visual task) while the parsing half is
mechanical and should be re-runnable without re-fetching anything if the
JSON comes out wrong.

## Step 1 — Find the issue and the crossword page

Read `../references/workflow_notes.md` in full — it has the exact Issuu
URL pattern, how to pull the document ID from the JSON-LD block, and how
to use the reader's thumbnail-grid view to spot the crossword page
visually. This part is genuinely variable week to week; don't guess a
page number from memory, verify it against what's actually on the page.

Confirm before continuing: the issue date (from the doc slug, e.g.
`260814fullbookweb` → 2026-08-14) and the page number within it.

## Step 2 — Capture the full-resolution page image

With the crossword page open in `claude-in-chrome`, fetch the
full-resolution image (`image.isu.pub/<doc-id>/jpg/page_<n>.jpg`) *inside
the browser tab* — not via `bash`/`web_fetch`, which can't reach that
host (see workflow_notes.md item 5 for why).

Get the bytes out of the browser and onto disk via a base64 round-trip,
since page tools return text, not binary:

1. Use `javascript_tool` to `fetch()` the image, read it as a `Blob`,
   convert to a base64 string (`FileReader.readAsDataURL` then strip the
   `data:image/jpeg;base64,` prefix, or equivalent), and return that
   string as the tool result.
2. `Write` the base64 text to `working-files/<date>/page.jpg.b64`.
3. Decode it to real binary with `base64 -d`:
   ```bash
   base64 -d working-files/<date>/page.jpg.b64 > working-files/<date>/page.jpg
   ```
4. Confirm it's a valid image (`file working-files/<date>/page.jpg` should
   say JPEG) before moving on, then delete the `.b64` intermediate.

## Step 3 — Capture the SVG text layer

Still on the same page, extract the real glyph-position text layer
instead of relying on a screenshot read — see workflow_notes.md item 6
for how to find the right `<svg>` (the one with thousands of `<text>`
children) and why this matters (it caught a real duplicate-clue-text
case before that a screenshot read couldn't have distinguished).

Via `javascript_tool`, collect every `<text>` node's content and its
`transform="matrix(...)"` position, and return it as JSON shaped like:

```json
[
  {"x": 123.4, "y": 88.1, "text": "1"},
  {"x": 140.2, "y": 88.1, "text": "Add "},
  ...
]
```

`Write` this directly to `working-files/<date>/svg_text.json` — no
base64 needed, it's already text.

## Step 4 — Save fetch metadata

`Write` `working-files/<date>/meta.json`:

```json
{
  "date": "2026-08-14",
  "docId": "<issuu doc id>",
  "pageNumber": 23,
  "sourceUrl": "https://issuu.com/charlestoncitypaper/docs/260814fullbookweb",
  "puzzleTitle": "“And My Ax!”",
  "byline": "Jonesin' by Matt Jones — swapping one for the other.",
  "constructor": "Matt Jones"
}
```

`puzzleTitle`/`byline` are printed on the page itself near the grid —
transcribe them now while you're already looking at the page, so the
build step doesn't have to re-derive them from raw text-node positions.

## Step 5 — Done

Tell the user the raw material is saved to `working-files/<date>/`
(`page.jpg`, `svg_text.json`, `meta.json`) and that
`charleston-citypaper-build-puzzle-json` is the next step to turn it into
`puzzles/<date>.json`.
