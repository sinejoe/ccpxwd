#!/usr/bin/env python3
"""
Extract a crossword grid's black/white cell pattern from a photo/scan by
measuring pixel brightness rather than guessing from a visual read.

How it works:
1. Scans for rows/columns that are almost entirely dark across their full
   span -- these are the grid's ruled lines (including the outer border).
   Clusters of adjacent dark rows/cols are collapsed into single boundary
   positions.
2. The boundaries divide the image into an NxN array of cells.
3. Each cell's interior (inset a few px from its border lines, to avoid
   sampling the grid lines themselves) is averaged in grayscale. Black
   squares average very dark (~20-60), white squares very light (~200-255)
   -- the split is normally extremely clean, so a mid threshold is safe.

Usage:
    python3 extract_grid.py <image_path> [--crop x0,y0,x1,y1] [--threshold 150]

If the page has other dark content that confuses row/column detection
(e.g. a solution grid elsewhere on the page, a photo, a dense text block),
pass --crop with a rough bounding box around just the puzzle grid -- eyeball
it from the image, doesn't need to be exact, a few px of margin is fine.

Prints the detected pattern (one row per line, '.'=white '#'=black) and a
sanity-check summary: automatically numbering the grid and counting how many
Across/Down entries it implies. Compare that count (and the specific numbers)
against the clue list transcribed from the same page -- an exact match is
strong confirmation the grid was read correctly.
"""
import sys
import argparse
import numpy as np
from PIL import Image


def cluster_boundaries(dark_idx, gap=3):
    if len(dark_idx) == 0:
        return []
    groups = [[dark_idx[0]]]
    for x in dark_idx[1:]:
        if x - groups[-1][-1] <= gap:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [int(round(np.mean(g))) for g in groups]


def trim_to_largest_regular_run(boundaries):
    """
    Drop outlier boundary lines that aren't part of the actual grid (e.g. a
    stray rule elsewhere on the page) by keeping only the longest run of
    boundaries whose spacing is roughly consistent with each other.
    """
    if len(boundaries) < 3:
        return boundaries
    diffs = [boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1)]
    median = np.median(diffs)
    runs, current = [], [boundaries[0]]
    for i, d in enumerate(diffs):
        if d <= 2 * median:
            current.append(boundaries[i + 1])
        else:
            runs.append(current)
            current = [boundaries[i + 1]]
    runs.append(current)
    return max(runs, key=len)


def find_grid_lines(gray, axis_threshold=0.9):
    """
    Two-stage detection: a full-width/full-height scan only reliably finds
    lines in whichever dimension the grid spans edge-to-edge of the *image*.
    A crossword grid usually doesn't span the full page height (there's a
    caption, clue text, etc. below/around it), so column lines get missed
    on a naive single pass. Instead: find rows using the full width, trim
    outliers to the grid's own regular spacing, use that to bound a column
    scan, then re-find rows bounded by those columns to drop any stray
    unrelated horizontal lines elsewhere on the page.
    """
    row_dark = (gray < 100).mean(axis=1)
    rows = cluster_boundaries(np.where(row_dark > axis_threshold)[0])
    rows = trim_to_largest_regular_run(rows)
    if len(rows) < 2:
        return rows, []

    y0, y1 = rows[0], rows[-1]
    col_dark = (gray[y0:y1, :] < 100).mean(axis=0)
    cols = cluster_boundaries(np.where(col_dark > axis_threshold)[0])
    cols = trim_to_largest_regular_run(cols)
    if len(cols) < 2:
        return rows, cols

    x0, x1 = cols[0], cols[-1]
    row_dark2 = (gray[:, x0:x1] < 100).mean(axis=1)
    rows = cluster_boundaries(np.where(row_dark2 > axis_threshold)[0])
    rows = trim_to_largest_regular_run(rows)

    return rows, cols


def classify_cells(gray, rows, cols, threshold, inset=5):
    n_r, n_c = len(rows) - 1, len(cols) - 1
    pattern = []
    for i in range(n_r):
        line = ''
        for j in range(n_c):
            y0, y1 = rows[i] + inset, rows[i + 1] - inset
            x0, x1 = cols[j] + inset, cols[j + 1] - inset
            if y1 <= y0 or x1 <= x0:
                line += '?'
                continue
            cell = gray[y0:y1, x0:x1]
            line += '#' if cell.mean() < threshold else '.'
        pattern.append(line)
    return pattern


def auto_number(pattern):
    n_r = len(pattern)
    n_c = len(pattern[0])
    black = [[c == '#' for c in row] for row in pattern]
    across, down = {}, {}
    n = 1
    for r in range(n_r):
        for c in range(n_c):
            if black[r][c]:
                continue
            left_black = c == 0 or black[r][c - 1]
            right_white = c < n_c - 1 and not black[r][c + 1]
            up_black = r == 0 or black[r - 1][c]
            down_white = r < n_r - 1 and not black[r + 1][c]
            starts_a = left_black and right_white
            starts_d = up_black and down_white
            if starts_a or starts_d:
                if starts_a:
                    length, cc = 0, c
                    while cc < n_c and not black[r][cc]:
                        length += 1; cc += 1
                    across[n] = length
                if starts_d:
                    length, rr = 0, r
                    while rr < n_r and not black[rr][c]:
                        length += 1; rr += 1
                    down[n] = length
                n += 1
    return across, down


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--crop', help='x0,y0,x1,y1 rough bounding box around the grid')
    ap.add_argument('--threshold', type=int, default=150)
    args = ap.parse_args()

    im = Image.open(args.image).convert('L')
    if args.crop:
        x0, y0, x1, y1 = [int(v) for v in args.crop.split(',')]
        im = im.crop((x0, y0, x1, y1))
    gray = np.array(im)

    rows, cols = find_grid_lines(gray)
    if len(rows) < 3 or len(cols) < 3:
        print("Couldn't find a clean grid line pattern. Try passing --crop "
              "with a tighter bounding box around just the puzzle grid.",
              file=sys.stderr)
        sys.exit(1)

    n_r, n_c = len(rows) - 1, len(cols) - 1
    if n_r != n_c:
        print(f"Warning: detected {n_r} rows but {n_c} columns -- grid is "
              f"usually square. Consider tightening --crop.", file=sys.stderr)

    pattern = classify_cells(gray, rows, cols, args.threshold)

    print(f"Detected {n_r}x{n_c} grid:\n")
    for line in pattern:
        print(line)

    across, down = auto_number(pattern)
    all_nums = list(across.keys()) + list(down.keys())
    print(f"\nAuto-numbering summary: {len(across)} Across entries, "
          f"{len(down)} Down entries, {len(across)+len(down)} total, "
          f"highest number used: {max(all_nums) if all_nums else 0}")
    print("Across numbers:", sorted(across.keys()))
    print("Down numbers:  ", sorted(down.keys()))
    print("\nCompare these counts/numbers against the transcribed clue list. "
          "An exact match confirms the grid was read correctly.")


if __name__ == '__main__':
    main()
