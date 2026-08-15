# Charleston City Paper Crossword

An interactive, playable browser crossword built from the Charleston
City Paper's weekly print crossword (syndicated "Jonesin'" puzzles by
Matt Jones).

## Play it

Open `crossword_standalone.html` directly in a browser — it's a
single, dependency-free HTML file (no build step, no external
requests). Progress autosaves to `localStorage`; a status badge shows
whether a finished grid matches the reference solve, when one has
been set for that week's puzzle.

## Contents

- `crossword_standalone.html` — the file to publish. Grid, clues,
  typing/keyboard nav, autosave, completion badge. No admin/debug
  tools.
- `working-files/crossword_0814_full_toolset.html` — a fuller
  reference build with grid-editing and progress export/import still
  present; not meant to be published as-is.
- `skill/` — an Anthropic Claude skill that automates building a new
  week's puzzle: find the current issue, extract the grid from a
  photo via pixel measurement, transcribe clues, fill the template.
- `HANDOFF.md` — full technical detail: data format, the specific UI
  bugs that were found and fixed (and why the fixes work the way they
  do), and open items. Read this before changing code.

## Status

Not yet deployed to a live URL. See `HANDOFF.md` for open items.
