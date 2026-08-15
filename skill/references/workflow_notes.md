# Finding the weekly issue and crossword page

## Where issues are published

Charleston City Paper publishes its full weekly issue as a digital
flipbook on Issuu. The publisher's page, listing all issues newest-first,
is:

    https://issuu.com/charlestoncitypaper

New issues go up on Fridays. A few issue types deviate from the standard
weekly, e.g. special guides like "Best of Charleston" or "Piccolo
Spoleto" guides, or seasonal "Dish Dining Guide" issues — these don't
reliably have a crossword and `fetch_issue.py`'s doc-slug regex already
skips them (it only matches slugs shaped like
`charleston_city_paper_MM_DD_YYYY_-_V.N`).

**Do not construct a doc slug from the date pattern.** An earlier version
of this doc claimed the pattern was `<YYMMDD>fullbookweb` — that's stale
and 404s now. Always resolve the real slug from an `<a href>` on the
listing page (`fetch_issue.py`'s `find_issue()` does this).

## Automated fetch (primary method)

`skill/scripts/fetch_issue.py` (see `fetch-issue/SKILL.md`) does the
whole thing with plain HTTP requests — no `claude-in-chrome`, no visual
page-hunting. This replaced an earlier browser-driven version of this
skill; worth understanding *why* each old assumption broke, since it's
easy to reintroduce the same dead ends if this gets rewritten again:

- **`image.isu.pub/<doc-id>/jpg/page_<n>.jpg` IS reachable from a plain
  HTTP client.** An earlier version of this doc claimed the sandbox
  couldn't reach that host and required routing the fetch through a
  browser tab's `fetch()`. That was never re-verified and turned out to
  be wrong — `curl`/`urllib` reach it fine.
- **`svg.issuu.com/<doc-id>/page_<n>.svg` is strictly better than the
  `.jpg` endpoint anyway** — one fetch gets you both the full-res raster
  page (embedded as a `data:image/jpeg;charset=utf-8;base64,...` URI
  inside an `<image>` element) and the complete vector text layer, so
  there's no reason to hit the `.jpg` endpoint separately.
- **Always send a real browser `User-Agent`.** Bare `curl` (`curl/8.7.1`)
  or Python's default `urllib`/`requests` UA is an obvious bot signature
  and risks getting blocked — this matters more once fetching runs
  unattended (e.g. from a GitHub Action) rather than a one-off manual
  pull. `fetch_issue.py`'s `USER_AGENT` constant is a real Chrome UA
  string; keep sending it on every request to `issuu.com`, `image.isu.pub`,
  and `svg.issuu.com`.
- **Text glyph position is not a `matrix(...)` transform on the `<text>`
  element.** That was true of an older Issuu rendering approach; the
  current one positions each text run via
  `<textPath href="#pN">glyphs</textPath>` inside the `<text>`, where
  `pN` refers to a sibling `<path id="pN" d="Mx,y L...">` elsewhere in
  the SVG. The path's own first `M x,y` command is the run's real
  page-pixel anchor (matches `page.jpg`'s pixel space directly — no unit
  conversion needed). `fetch_issue.py`'s `parse_page_svg()` does this
  parse.
- **Finding the crossword page doesn't need visual judgment either.**
  The old approach required opening the reader's thumbnail-grid view and
  eyeballing which page looked like a crossword, because the page number
  drifts week to week with ad placement. Since the SVG text layer is
  plain text, scanning each page's SVG for the constructor byline
  ("Jonesin'") and stopping at the first hit is faster and removes the
  guesswork — confirmed on a live issue, page 23 was correctly found in
  under 4 seconds for 5 pages scanned.

## Manual/fallback: finding the page visually

Only needed if the automated scan in `fetch_issue.py` can't find a
byline match (e.g. a constructor/byline change, or a special issue with
an unusual layout):

1. Open the issue with `claude-in-chrome` (a plain fetch of the doc page
   won't expose page content in the same way the reader does — Issuu's
   reader is JS-rendered on top of the static page).
2. Navigate the reader (`issuu.com/charlestoncitypaper/docs/<slug>`) and
   click the grid/thumbnail-view icon in its toolbar — it lays out every
   page as a thumbnail in one screenshot, and the crossword grid is
   visually obvious at a glance. Note the page number.
3. Once you have the page number, you can go back to
   `fetch_issue.py`'s underlying functions (`get_doc_id`,
   `parse_page_svg`) rather than redoing the browser-based extraction —
   the only thing the browser was needed for here was picking the page
   number.

## Last week's solution grid

Every issue prints the previous week's completed grid as a small answer
key, positioned near a rotated "Last Week's Solution" sidebar label.
`fetch_issue.py` locates that label in the parsed text-node list and
crops a generous region around it — the crop bounds are a heuristic
(anchor off the label's x position, assume the grid roughly fills the
bottom-right corner of the page) and have only been visually verified on
one issue so far. Confirm the crop visually before relying on it,
especially for the first few weeks this runs — layout could plausibly
shift issue to issue.

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
output (see `build-puzzle-json/SKILL.md` Step 3) rather than assuming
column position implies direction.

Note: on the one issue checked so far, `svg_text.json`'s `flatText` (DOM
document order) already reproduced the Across-then-Down sequence
correctly without needing position-based line reconstruction — the
column-break hazard above is about *visual* column position, not about
DOM order, so don't assume flatText is always safe unread; still
cross-check numbering per Step 3.

The single best confirmation that the grid was read correctly: run
`extract_grid.py`, take its auto-numbering summary (count of Across/Down
entries and the specific numbers used), and compare it against the
numbers in the clue list you transcribed from the same page. These
should match exactly — same count, same numbers, 1 through the highest
clue number with no gaps. If they don't match, first suspect the clue
transcription (easy to mis-read a number in small print) before
suspecting the grid extraction (which is a direct pixel measurement and
has been reliable).
