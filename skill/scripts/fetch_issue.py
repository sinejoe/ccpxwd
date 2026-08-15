#!/usr/bin/env python3
"""
Fetch a Charleston City Paper weekly issue from Issuu and pull the raw
crossword-page material into working-files/<date>/ — no browser required.

Replaces the old claude-in-chrome-driven fetch-issue skill. Everything here
is plain HTTP + regex against static Issuu endpoints:

  - https://issuu.com/charlestoncitypaper                       (publisher listing, finds latest/dated issue)
  - https://issuu.com/charlestoncitypaper/docs/<slug>            (doc page, JSON-LD has the doc id)
  - https://svg.issuu.com/<doc-id>/page_<n>.svg                  (per-page: raster JPEG embedded as a
                                                                    base64 data URI *and* the full vector
                                                                    text layer, in one file)

Discovered/confirmed while building this (see skill/references/workflow_notes.md
for the full writeup):
  - Always send a real browser User-Agent. Bare `curl`/`requests` defaults
    (e.g. "curl/8.7.1", "python-requests/...") are an obvious bot signature
    and risk getting blocked -- see USER_AGENT below.
  - The doc slug is NOT a predictable "<YYMMDD>fullbookweb" pattern anymore
    (that was stale). Pull the real slug from the listing page's <a href>.
  - image.isu.pub/<doc-id>/jpg/page_<n>.jpg IS reachable directly (no
    special browser/CORS requirement) but svg.issuu.com/<doc-id>/page_<n>.svg
    is strictly better: it bundles the same raster image (as an embedded
    base64 JPEG) with the full searchable text layer in one fetch.
  - Text glyphs are positioned via <textPath href="#pID"> referencing a
    sibling <path id="pID" d="Mx,y L...">; the path's own first M x,y is
    the glyph/run's real page-pixel anchor. (Not a matrix() transform on
    the <text> element itself -- that reads as identity/0,0.)
  - The crossword page number drifts weekly. Rather than requiring visual
    judgment (thumbnail grid), this script scans each page's SVG text
    content for the puzzle's byline ("Jonesin'") and stops at the first
    hit -- fast (a few seconds for a ~24-page issue) and reliable since
    the constructor byline is always printed on the page.
"""

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

PUBLISHER_URL = "https://issuu.com/charlestoncitypaper"
DOC_SLUG_RE = re.compile(
    r'href="(/charlestoncitypaper/docs/'
    r'charleston_city_paper_(\d{2})_(\d{2})_(\d{4})_-_[\d.]+)"'
)
CROSSWORD_MARKER = "jonesin"  # case-insensitive substring check
MAX_PAGES = 60  # safety cap; real issues are usually 20-40 pages


def fetch(url: str, timeout: int = 20) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_ok(url: str, timeout: int = 20):
    """Like fetch(), but returns None instead of raising on HTTP error (used for
    the page-existence probe when scanning past the end of an issue)."""
    try:
        return fetch(url, timeout=timeout)
    except HTTPError:
        return None


def find_issue(target_date: str | None) -> tuple[str, str]:
    """Returns (date 'YYYY-MM-DD', doc page url) for the requested date, or the
    newest weekly issue if target_date is None."""
    html = fetch(PUBLISHER_URL + "?ps=48").decode("utf-8", errors="replace")
    candidates = []
    for m in DOC_SLUG_RE.finditer(html):
        path, mm, dd, yyyy = m.groups()
        date = f"{yyyy}-{mm}-{dd}"
        candidates.append((date, "https://issuu.com" + path))
    if not candidates:
        raise RuntimeError("no weekly-issue links found on publisher page")
    candidates.sort(key=lambda c: c[0], reverse=True)
    if target_date is None:
        return candidates[0]
    for date, url in candidates:
        if date == target_date:
            return date, url
    raise RuntimeError(f"no issue found for {target_date}; newest available is {candidates[0][0]}")


def get_doc_id(doc_page_url: str) -> str:
    html = fetch(doc_page_url).decode("utf-8", errors="replace")
    m = re.search(r'"image":"https://image\.isu\.pub/([^/"]+)/jpg/page_1_thumb_large\.jpg"', html)
    if not m:
        raise RuntimeError(f"couldn't find doc id in JSON-LD at {doc_page_url}")
    return m.group(1)


def find_crossword_page(doc_id: str) -> tuple[int, str]:
    """Scans pages 1..N, returns (page number, raw svg text) for the first page
    whose text layer contains the crossword byline marker."""
    for n in range(1, MAX_PAGES + 1):
        url = f"https://svg.issuu.com/{doc_id}/page_{n}.svg"
        data = fetch_ok(url)
        if data is None:
            break  # past the end of the issue
        text = data.decode("utf-8", errors="replace")
        if CROSSWORD_MARKER in text.lower():
            return n, text
    raise RuntimeError(f"scanned pages 1-{n} of doc {doc_id}, no page matched '{CROSSWORD_MARKER}'")


def parse_page_svg(svg_text: str):
    """Returns (jpeg_bytes, text_nodes) where text_nodes is [{x, y, text}, ...]
    in document order with real page-pixel coordinates."""
    img_m = re.search(r'href="data:image/jpeg;charset=utf-8;base64,([^"]+)"', svg_text)
    if not img_m:
        raise RuntimeError("no embedded JPEG found in page svg")
    jpeg_bytes = base64.b64decode(img_m.group(1))

    paths = {pid: d for d, pid in re.findall(r'<path d="([^"]+)" id="([^"]+)"', svg_text)}

    def first_point(d: str):
        m = re.match(r"M([\d.\-]+),([\d.\-]+)", d)
        return (float(m.group(1)), float(m.group(2))) if m else (None, None)

    nodes = []
    flat_parts = []
    for attrs, href, txt in re.findall(
        r'<text\b([^>]*)>\s*<textPath href="#([^"]+)"[^>]*>(.*?)</textPath>\s*</text>',
        svg_text,
        re.DOTALL,
    ):
        x, y = first_point(paths.get(href, ""))
        nodes.append({"x": x, "y": y, "text": txt.strip()})
        # Collapse (not strip) whitespace here: a whitespace-only run is a real
        # word-separating space in the source layout, and stripping it to ''
        # before joining would glue adjacent words together (e.g. "Dumb"+"or"
        # -> "Dumbor" instead of "Dumb or").
        flat_parts.append(re.sub(r"\s+", " ", txt))
    return jpeg_bytes, nodes, re.sub(r" +", " ", "".join(flat_parts)).strip()


def find_prior_solution_crop(jpeg_bytes: bytes, nodes):
    """Best-effort crop of the printed 'Last Week's Solution' grid, anchored off
    that label's text-node position. NOT pixel-verified across issues -- treat
    the output as a candidate crop for a human/agent to confirm, same as the
    project's existing pixel-measure-then-cross-check pattern for the live grid."""
    try:
        from PIL import Image
        from io import BytesIO
    except ImportError:
        return None

    label_nodes = [n for n in nodes if n["text"] in ("Last", "Week&#39;s", "Week's", "Solution")]
    if not label_nodes:
        return None
    label_x = label_nodes[0]["x"]
    if label_x is None:
        return None

    im = Image.open(BytesIO(jpeg_bytes))
    w, h = im.size
    left = int(label_x) + 15
    right = w - 5
    bottom = h - 5
    top = max(0, bottom - (right - left) - 40)  # generous, roughly-square guess
    if left >= right or top >= bottom:
        return None
    crop = im.crop((left, top, right, bottom))
    out = BytesIO()
    crop.save(out, format="JPEG", quality=92)
    return out.getvalue()


def week_before(date_str: str) -> str:
    import datetime
    d = datetime.date.fromisoformat(date_str) - datetime.timedelta(days=7)
    return d.isoformat()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="issue date YYYY-MM-DD (default: newest available)")
    ap.add_argument("--output-root", default="working-files", help="base dir for output (default: working-files)")
    ap.add_argument("--skip-prior-solution", action="store_true", help="don't attempt the last-week's-solution crop")
    args = ap.parse_args()

    date, doc_url = find_issue(args.date)
    print(f"issue: {date}  {doc_url}", file=sys.stderr)

    doc_id = get_doc_id(doc_url)
    print(f"doc id: {doc_id}", file=sys.stderr)

    page_num, svg_text = find_crossword_page(doc_id)
    print(f"crossword page: {page_num}", file=sys.stderr)

    jpeg_bytes, nodes, flat = parse_page_svg(svg_text)

    out_dir = Path(args.output_root) / date
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "page.jpg").write_bytes(jpeg_bytes)

    (out_dir / "svg_text.json").write_text(json.dumps({
        "source": f"svg.issuu.com/{doc_id}/page_{page_num}.svg",
        "nodes": nodes,
        "flatText": flat,
    }, indent=2))

    (out_dir / "meta.json").write_text(json.dumps({
        "date": date,
        "docId": doc_id,
        "pageNumber": page_num,
        "sourceUrl": doc_url,
        "puzzleTitle": None,   # TODO: transcribe from flatText / page image
        "byline": None,        # TODO: transcribe from flatText / page image
        "constructor": None,
    }, indent=2))

    print(f"wrote {out_dir}/page.jpg, svg_text.json, meta.json", file=sys.stderr)

    if not args.skip_prior_solution:
        crop_bytes = find_prior_solution_crop(jpeg_bytes, nodes)
        if crop_bytes:
            prior_date = week_before(date)
            prior_dir = Path(args.output_root) / prior_date
            prior_dir.mkdir(parents=True, exist_ok=True)
            crop_path = prior_dir / "printed_solution_grid_CANDIDATE.jpg"
            crop_path.write_bytes(crop_bytes)
            print(
                f"wrote candidate prior-week solution crop to {crop_path} "
                f"(unverified bounds -- confirm visually before using; corresponds to "
                f"the puzzle from {prior_date})",
                file=sys.stderr,
            )

            # Record where this crop came from, merged into the *prior* week's
            # own meta.json (which already exists if that week was fetched
            # normally) so a later build step can link players back to the
            # actual source page instead of just asserting "official". Merge,
            # don't overwrite -- that file may already carry hand-filled
            # puzzleTitle/byline/constructor from Step 2 of that earlier run.
            prior_meta_path = prior_dir / "meta.json"
            prior_meta = json.loads(prior_meta_path.read_text()) if prior_meta_path.exists() else {}
            # Trailing /<page> deep-links the Issuu viewer straight to that page's
            # spread -- the doc_url on its own just opens the issue at page 1.
            # (The doc slug's own "_-_30.3" suffix looked like it might encode a
            # page/version number but doesn't; this /<n> suffix is the real thing.)
            prior_meta["officialSolutionUrl"] = f"{doc_url}/{page_num}"
            prior_meta["officialSolutionPage"] = page_num
            prior_meta_path.write_text(json.dumps(prior_meta, indent=2))
        else:
            print("no 'Last Week's Solution' label found on this page; skipped crop", file=sys.stderr)


if __name__ == "__main__":
    main()
