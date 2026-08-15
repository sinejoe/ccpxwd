# Finding the weekly issue and crossword page

## Where issues are published

Charleston City Paper publishes its full weekly issue as a digital
flipbook on Issuu. The publisher's page, listing all issues newest-first,
is:

    https://issuu.com/charlestoncitypaper

New issues go up on Fridays. Individual issue URLs follow the pattern:

    https://issuu.com/charlestoncitypaper/docs/YYMMDDfullbookweb

e.g. `250110fullbookweb` = issue dated 2025-01-10. (A few issue types
deviate, e.g. special guides like "Best of Charleston" or "Piccolo
Spoleto" guides use a different slug — skip those, look for the
standard weekly issue instead, usually named with just the date.)

## Workflow

1. `web_fetch` (or `web_search` if fetch is blocked) the publisher page
   above to find the newest weekly issue's URL and its date.
2. Open that issue with `claude-in-chrome` (a plain `web_fetch` of the
   doc page won't expose page content — Issuu's reader is entirely
   JS-rendered, and there is no downloadable PDF: check for a download
   link/button in the page DOM if you want to confirm this for a given
   publication, but as of this writing Charleston City Paper's issues
   don't have it enabled).
3. **Get the document ID.** Once the page has loaded, its `<script>`
   tags include a JSON-LD block (`@type: "DigitalDocument"`) with an
   `image` field shaped like
   `https://image.isu.pub/<doc-id>/jpg/page_1_thumb_large.jpg` — pull
   `<doc-id>` out of that URL. You'll use it for both of the next two
   steps.
4. **Find the crossword page.** The fastest way: navigate the reader
   iframe (`issuu.com/rd4?p=1&d=<doc-slug>&u=charlestoncitypaper`) and
   click the grid/thumbnail-view icon in its toolbar — it lays out
   every page as a thumbnail in one screenshot, and the crossword grid
   is visually obvious at a glance. Page number drifts week to week
   with ad placement (page 30 one week, page 23 the next), so don't
   assume last week's number. Note the page number once you spot it.
5. **Pull the page image and run grid extraction — inside the browser,
   not the sandbox.** `image.isu.pub` isn't on the sandbox's network
   allowlist, so `bash`/`web_fetch` can't download
   `image.isu.pub/<doc-id>/jpg/page_<n>.jpg` directly. The browser tab
   *can* reach it though (no CORS/allowlist issue there), so run the
   extraction algorithm itself as injected JavaScript via
   `claude-in-chrome:javascript_tool`, operating on a `<canvas>`
   `getImageData()` of the fetched image, rather than trying to get the
   raw file into the sandbox. Port of `scripts/extract_grid.py`'s
   approach for in-browser use:
   - Load the full-page JPEG into an `Image()` (`crossOrigin =
     'anonymous'`), draw to a canvas, `getImageData`.
   - The crossword grid is usually a small part of a busy full
     newspaper page (classifieds, other content sharing the page), so
     a full-page-width scan for grid lines will typically find
     nothing — first locate a rough bounding box (e.g. scan a
     downscaled preview for a dense band of short alternating
     dark/light runs, which is what a grid looks like at low res),
     then run the real boundary detection restricted to that crop.
   - Same three-stage boundary detection as the script: full-width row
     scan → column scan bounded by those rows → re-scan rows bounded
     by those columns. Also add an end-trimming pass that drops any
     boundary whose gap to its neighbor is much smaller than the
     median spacing (a near-duplicate detection of the same physical
     line) — this came up on a page where the crop's left/top edge
     produced one spurious extra boundary right next to the real one.
   - Classify each cell by mean grayscale brightness inside its
     interior (same threshold approach as the script, ~140 works well
     against JPEG compression noise — the script's default of 150 is
     also reasonable, tune per-image if the split isn't clean).
   - Run the same auto-numbering sanity check as always before trusting
     the result.
6. **Get clue text from the page's real SVG text layer, not a
   screenshot read.** Issuu renders each visible page/spread as an SVG
   with individually-positioned `<text>` elements (one per glyph or
   word-fragment) alongside the raster image — this is effectively a
   perfect, non-OCR transcription straight from the source. Find it
   with `document.querySelectorAll('svg')` and pick the one with the
   most `<text>` children (thousands, not a handful) for the page
   you're on. Each text node's `transform="matrix(...)"` encodes its
   position; group nodes by their y-translate (rounded — glyphs on the
   same line share the same y) and concatenate in y-then-document-order
   to reconstruct lines. This is worth doing even when a screenshot
   read looks unambiguous, and is essential for confirming anything
   that looks like a possible duplicate or OCR error — e.g. it caught
   and *confirmed* (not fixed) a case where two different clue numbers
   were printed with genuinely identical text in the original, which
   would have looked exactly as suspicious either way and needed
   checking against the actual glyph positions rather than assumed to
   be a misread.
7. Fill in `assets/crossword_template.html` per the main SKILL.md.



The single best confirmation that the grid was read correctly: run
`extract_grid.py`, take its auto-numbering summary (count of Across/Down
entries and the specific numbers used), and compare it against the
numbers in the clue list you transcribed from the same page. These
should match exactly — same count, same numbers, 1 through the highest
clue number with no gaps. If they don't match, first suspect the clue
transcription (easy to mis-read a number in small print) before
suspecting the grid extraction (which is a direct pixel measurement and
has been reliable).

## Clue-list layout convention (read this before transcribing)

This puzzle's clue text is laid out in two printed columns, but the
column break does NOT align with the Across/Down split — that caused a
real transcription error once (Across 51 and Down 51 got swapped, and
an Across clue got mis-copied from a nearby Down clue) by assuming each
printed column was one clue direction.

The actual layout: **all Across clues run first, in the left column,
starting right under the grid.** The Down clues start immediately
after the last Across clue — still in the same left column — and then
break into the right column partway through once the left column runs
out of vertical space. So the top of the right column is a
**continuation of the Down list**, not a new section, and won't have
its own "Down" header.

When transcribing: read the left column top-to-bottom first to find
where "Across" ends and "Down" begins (there's a "Down" heading marking
that transition, but the Across list can also wrap partway down the
same column before it — don't assume everything above the visible
"Down" heading is Across without checking each clue number against the
grid's own numbering). Then continue the Down list into the right
column. Cross-check every clue number against the grid's auto-numbering
output (see above) rather than assuming column position implies
direction.
