# Charleston City Paper Crossword — handoff to Claude Code

## What this is

An interactive, playable browser crossword built from the Charleston
City Paper's weekly print crossword (syndicated "Jonesin'" puzzles by
Matt Jones, at least as of Aug 2026). Built and heavily iterated in a
claude.ai chat session using the Artifacts feature; the person wants
to keep developing it in Claude Code instead, and eventually publish a
standalone version to a real host (Netlify/GitHub Pages/etc).

Read this whole file before touching code. Almost every design
decision below exists because of a specific bug that was found and
fixed in the original session — the comments in the code explain the
"why" inline, but this file has the connective tissue between them.

## Folder contents

- `index.html` — **the file to actually publish.**
  Stripped down for a public end-user: grid, clues, typing, keyboard
  nav, autosave via `localStorage`, and a completion badge that
  compares against an embedded reference solve if one's been set. No
  admin/debug tools (see "Feature history" below for why they were
  removed).
- `working-files/crossword_0814_full_toolset.html` — the fuller
  version with grid-editing, letter-check, and progress-code
  export/import still in it. Useful as reference for how those
  features worked, or if a future "admin mode" build ever wants them
  back. Not meant to be published as-is.
- `skill/` — an Anthropic-skill package (`SKILL.md` + assets) that
  automates finding the paper's current issue, extracting a puzzle
  grid from a photo via actual pixel measurement, and filling in this
  template for a new week. This is the reusable machinery; read
  `skill/SKILL.md` and `skill/references/workflow_notes.md` before
  building a new week's puzzle. **If porting this project to Claude
  Code, consider whether this becomes a Claude Code skill/command
  instead** — the workflow (fetch issue → find puzzle page → extract
  grid → transcribe clues → fill template) is identical either way.

## Both HTML files are single-file, dependency-free

No build step, no external CDN/font/script requests, no
`window.storage` dependency in `index.html` (that was
Claude's artifact-only storage API — deliberately removed in favor of
plain `localStorage`, since there's no server here and a cookie would
be the wrong tool: this is pure client-side persistence with no HTTP
round-trip to piggyback on). Editing either file directly is safe and
expected.

## How the puzzle data is structured (read before editing)

**As of Aug 2026, `index.html` is a static shell — it has no puzzle data
hardcoded in it.** On load it fetches `puzzles/index.json` (an array of
`{id, date, title, file}`, newest first) and then fetches that entry's
`file` (a per-week JSON, e.g. `puzzles/2026-08-14.json`) via
`loadPuzzleData()`, near the top of the `<script>`. This replaced an
earlier design where every new week meant hand-editing constants inside
`index.html` itself — which is also what caused a real bug (the
`<title>`/header staying stuck on whichever puzzle was last pasted in).

A puzzle JSON file (`puzzles/YYYY-MM-DD.json`) has:
- `id` — becomes `PUZZLE_ID`, the string that scopes the localStorage
  key. Must be unique per puzzle (date-based slug) or two different
  puzzles will clobber each other's saved progress.
- `date`, `kicker`, `title`, `subtitle` — header text, written directly
  into the DOM via `textContent` (not `innerHTML`), so use real unicode
  punctuation (curly quotes, em dash) in the JSON rather than HTML
  entities.
- `pattern` — 15 strings of 15 chars, `.` = white, `#` = black.
- `across` / `down` — arrays of `[number, "clue text"]`.
- `solutionSalt` — this puzzle's `SOLUTION_SALT` (see "Reference
  solve" below).
- `solutionHashesFile` — path to this puzzle's hashes file, e.g.
  `puzzles/2026-08-14.solution-hashes.txt`.

`puzzles/index.json` is what makes "load a specific past week" possible
— `index.html?puzzle=<id>` looks up that id in the index and loads its
file instead of defaulting to entry `[0]` (the newest). No UI exposes
this yet (no past-weeks picker), but the data layer is already there
for one — see "Known open items" below.

The grid's numbering (which cell gets which clue number, which cells
start Across/Down words) is **computed at runtime** from `pattern` —
standard crossword numbering rules, implemented in `computeNumbers()`.
Never hand-number anything; if `pattern` is right, the numbering is
automatically right.

### Building a new week's puzzle now

1. Run the skill's extraction workflow (below) as before.
2. Create `puzzles/YYYY-MM-DD.json` with the new `pattern`/`across`/
   `down`/header fields and a fresh `id` (e.g.
   `ccp-YYYY-MM-DD-slug`) and `solutionSalt`.
3. Prepend a new entry to `puzzles/index.json` (newest first) pointing
   at that file.
4. Once a reference solve is ready, use the admin panel
   (`?admin=1`) to generate that week's `solutionHashesFile` and save
   it to the path named in the JSON.
5. `index.html` itself does not need to change for a routine weekly
   puzzle anymore.

The grid's numbering (which cell gets which clue number, which cells
start Across/Down words) is **computed at runtime** from `pattern` —
standard crossword numbering rules, implemented in `computeNumbers()`.
Never hand-number anything; if `pattern` is right, the numbering is
automatically right.

### Building a new week's puzzle: verify before trusting

The single most important lesson from the original session: **do not
hand-transcribe the grid from a photo, and do not assume a clue's
direction from which printed column it's in.** Both caused real,
shipped bugs (a swapped Across/Down clue, a duplicated clue, a grid
extraction that missed some black squares). The skill's approach —
and the one to keep using — is:

1. Extract the black/white pattern via actual pixel brightness
   measurement (`skill/scripts/extract_grid.py`, or the in-browser
   port described in `workflow_notes.md` if fetching the image
   requires a browser context the sandbox can't reach directly).
2. Auto-number the resulting grid and count Across/Down entries.
3. Compare that count and the specific numbers used against the
   clue numbers printed on the page. An exact match (same numbers,
   1 through the highest, no gaps) is strong confirmation the grid
   is right. This has caught real extraction errors before — trust
   it over eyeballing.
4. Transcribe clue text from the page's own text layer when
   possible (Issuu serves an SVG with individually-positioned
   `<text>` glyphs alongside the raster image — far more reliable
   than reading a screenshot). See `workflow_notes.md` for how to
   find and use it.
5. Don't assume printed column position implies Across vs. Down —
   this specific puzzle's clue layout runs Across-then-Down
   continuously, breaking to a second text column mid-list, which
   does NOT align with the direction split. Read the actual "Down"
   heading position.

## Feature history — what was removed and why

The original build had, and then lost, these features (still present
in `working-files/crossword_0814_full_toolset.html`):

- **"Fix grid squares" (manual black/white toggle edit mode).** A
  safety net for correcting grid extraction errors at solve-time.
  Removed from the public build because by the time a puzzle ships,
  the auto-numbering cross-check (above) should already have caught
  any extraction error — this was a build-time tool wearing a
  runtime costume.
- **"Check letters" (blank-count) / "Reveal letter".** Reveal never
  actually worked (there was no answer key to reveal from) and just
  showed an apologetic message. Check-letters duplicated what the
  completion badge now does automatically. Both cut for being
  redundant/dead weight in the minimal build.
- **"Copy progress code" / "Restore from code" (export/import).**
  This existed to solve a real problem: **every time a new artifact
  version was shipped in claude.ai, it got entirely separate storage
  from the old one** — even with an identical `PUZZLE_ID` — so a
  finished solve could be silently lost on the next update. That's an
  artifact-hosting quirk, not something a stably-hosted standalone
  page needs (a real URL doesn't churn artifact identity on every
  edit the way iterating in chat did). Cut for the public build; kept
  in the full-toolset version since it's still how a solve should be
  handed off for baking into `SOLUTION` (see below) if this ever goes
  back through a Claude chat loop instead of Claude Code.

## Reference solve ("SOLUTION")

There is no plaintext reference solve anywhere in this repo or shipped page
(added Aug 2026, after the person explicitly asked that a view-source/bot
couldn't recover the answer letters). Instead, each week's puzzle JSON
points (via `solutionHashesFile`) at a file like
`puzzles/2026-08-14.solution-hashes.txt`, holding one salted SHA-256 hash
per Across/Down entry (`1A-<hash>`, `1D-<hash>`, ...). The browser hashes
whatever the player typed for each entry and compares hashes — this can
report *how many answers* don't match, never *which letters* are right, and
the actual solve can't be recovered from the repo even by someone with full
read access to it.

If that file is missing/unfetchable, the completion badge just says "Grid
complete" (no reference solve available). Once loaded, the badge reports
either "matches" or "differs ... in N answer(s)".

**Security note, stated plainly:** this is still a deterrent, not a vault.
`SOLUTION_SALT` (in `index.html`) is public by necessity — the client has to
use it too — so it doesn't add secrecy beyond namespacing the hashes. Per-
answer hashing was a deliberate tradeoff for a mismatch *count*: hashing the
whole grid as one blob would be strictly more secure (no oracle) but could
only report a binary match/no-match, and the person preferred the count. A
scripted client could in principle narrow down individual answers faster
than blind guessing by watching the count shift as it tries words — same
category of accepted risk as the `ADMIN_HASH` gate below. What this *does*
achieve: nobody reading the repo, `index.html`'s source, or
`solution-hashes.txt` directly can recover the answer text.

**Framing rules the person was explicit about, twice — do not
deviate:**
- Never call anything "wrong" or flag individual incorrect cells.
  "Differs from our reference solve", never "error".
- Always make clear this is *a* submitted solve, not an official
  answer key — "we're not the official puzzle master".
- The badge is a persistent, always-current indicator, **not a
  popup**. An earlier version used a modal that fired once per
  completion; the person explicitly asked for it to be removed in
  favor of a quiet status badge, because repeatedly clearing/refilling
  cells while double-checking kept re-triggering it.

The solution-hashes file still has to be baked/replaced at build/publish
time and redeployed — there's no server, so nothing can write to it at
runtime for real. What *does* exist now (added Aug 2026, after
explicit discussion) is an admin-only helper that generates a
paste-ready solution-hashes file from whatever grid you've solved in
the normal UI, so you don't have to hand-hash 78+ answers yourself:

- Load the page with `?admin=1` in the URL — this reveals a
  passphrase-gated panel (hidden from normal players; the panel
  itself is inert without the passphrase, and easy to miss since it's
  a small dashed box below the footer, not a popup). The SHA-256 hash
  of the passphrase lives in the script as `ADMIN_HASH`; the
  passphrase itself isn't stored anywhere in the repo, only given to
  the person who set it up.
- This is explicitly **not** real security — it's a deterrent against
  casual snooping, not a determined attacker (the hash is visible in
  page source and could be brute-forced offline). Accepted tradeoff:
  the thing being gated is "who can suggest a reference solve", not
  sensitive data, and real GitHub-OAuth-backed auth would require
  moving off static GitHub Pages onto something with a backend, which
  was explicitly ruled out in favor of staying dependency-free.
- Once unlocked, solve the puzzle in the actual grid (same UI
  everyone else uses), then click "Generate solution-hashes file from
  my grid" — it reads the live `grid` state, not a separate code/import
  step, so it can't drift out of sync with whatever puzzle is
  currently loaded. Paste the output over the file named in that
  puzzle's `solutionHashesFile` and redeploy.
- This intentionally does **not** revive the old base64
  export/import ("progress code") flow from
  `working-files/crossword_0814_full_toolset.html` as the *primary*
  path — going straight from live grid to paste-ready hashes skips a
  decode step. That mechanism is still there in the full-toolset
  build, and was in fact used once already: a saved progress code
  from that build was decoded outside the app to cross-check this
  week's solution-hashes file before it shipped.

## UI/UX details worth preserving (each fixed a reported bug)

- **Arrow keys are NYT-style, not naive.** Pressing an arrow
  perpendicular to the current direction re-orients in place
  (doesn't move) if the current cell has a word in that direction;
  only moves if it doesn't. Same-direction presses move normally,
  skipping black squares. Typing auto-advances to the next *empty*
  cell in the word (skipping already-filled ones), wraps to the first
  empty cell if it reaches the end, and jumps to the next word
  entirely if the current one's already full. All of this lives in
  `arrowMove()` and `nextTypingCell()` — don't simplify it back to
  "always move + always advance one cell", that was the original
  (wrong) behavior.
- **Clicking a grid cell preserves current orientation** unless you
  click the *same* cell twice (which toggles it). This broke once
  because a `focus` event listener was pre-empting the `click`
  handler's same-cell detection — focus fires before click in
  browsers, so if a focus listener moves `cur` first, every click
  looks like a "repeat click on the current cell" to the handler that
  runs after it. Selection logic lives entirely in the `click`
  listener now; there's no `focus` listener doing extra work.
- **Typing over an existing letter must replace it, not insert
  beside it.** Fixed by calling `setSelectionRange(0, value.length)`
  on focus, so the existing character is always selected before a new
  keystroke lands — otherwise the browser's actual caret position
  after a programmatic `.value` assignment isn't reliably at the end,
  and with `caret-color: transparent` (intentional — no visible
  cursor blinking in a tiny grid cell) the person has no way to see
  where it actually is.
- **Backspace/Delete always clears the current cell first**, and only
  steps backward once that cell is already empty.
- **The active clue and its "crossing" clue (the other-direction word
  at the current cell) both auto-scroll into view, instantly, not
  smoothly.** `scrollIntoView({block:'nearest', behavior:'instant'})`
  on both — a `behavior:'smooth'` default was reported as
  "distracting". The crossing clue gets a lighter highlight (CSS
  `border-left` + color change), deliberately NOT `font-weight`,
  because bold glyphs are wider than regular ones and changing weight
  on scroll/navigate was reflowing the clue column's line-wrapping —
  reported as "jumpy".
- **Across and Down are two independently-scrolling columns**, not
  one shared scroll region — `overflow-y: auto` lives on each
  `.cluecol`, not on the shared `#cluesPanel` wrapper.
- **"Focus mode"** hides the header/toolbar and sizes the grid off
  *measured* available height (`getBoundingClientRect()` +
  `window.innerHeight`), not a flat `100vh` guess — this specifically
  matters if the page is ever embedded somewhere with its own chrome
  above it (that was true of the claude.ai artifact viewer; may not
  apply to a standalone host, but the measurement approach is strictly
  more correct either way, so keep it). The hamburger toggle button
  that reveals the (now much smaller) toolbar in focus mode must
  stay above the dropdown panel in stacking order (`z-index`) or
  there's no way to click it again to close the menu — this broke
  once already.
- **The completion badge (`#completionStatus`) is a single DOM element
  that gets moved, not duplicated**, between `#leftCol` (normal mode,
  below the grid) and `#focusBadgeRow` (focus mode, a full-width row
  spanning under grid+clues) via `appendChild()` in the focus/exit
  click handlers. In focus mode the badge pushes *both* the grid and
  clues up, not just the grid column — that's why it lives in its own
  full-width sibling row after `#app`, not inside `#leftCol`.
  `sizeFocusMode()` measures `#focusBadgeRow`'s actual `offsetHeight`
  (not a guessed constant) so `#app` shrinks by exactly the right
  amount and the badge never lands below the fold; it's re-run
  whenever the badge's own height can change (i.e. from inside
  `updateCompletionStatus()`), since a longer "N mismatched" message
  wraps to more lines than "Grid complete".
- **The "Restored your progress from last time" banner was removed
  entirely** (not just hidden) — if old answers reappear in the grid
  on load, that's self-evidently "you remembered them"; a banner
  saying so was redundant. Don't re-add `#banner`/`showBanner()`.
- **Esc exits focus mode**, matching the standard convention for
  fullscreen-ish views. Wired as a `document`-level `keydown` listener
  that calls the same exit button's `click()` handler, so it stays in
  sync with the mouse-driven exit path rather than duplicating its
  logic.

## Testing approach used so far

The claude.ai sandbox had no real browser, so testing was done with
`jsdom` + Node: load the HTML, `runScripts: 'dangerously'`, mock
`window.storage`/`localStorage` as needed, dispatch synthetic
click/input/keydown events, assert on resulting DOM state. It caught
real bugs (see history above) but jsdom's CSS engine is limited —
`getComputedStyle()` on shorthand properties with `var()` was
unreliable, so some CSS correctness was verified by reading the
stylesheet text directly rather than trusting computed-style
assertions.

**In Claude Code, prefer real browser testing** (Playwright/Puppeteer,
or just manually opening the file) over the jsdom workaround — it'll
catch more, faster, and CSS assertions will actually be trustworthy.

## Known open items / things not yet done

- Deployed to GitHub Pages at https://sinejoe.github.io/ccpxwd/ (custom
  domain https://ccpx.fyi) as of Aug 2026. Every push to `main`
  auto-redeploys.
- **GitHub Pages serves every tracked file in the repo by default** —
  there's no per-file publish list, `index.html` is just what `/`
  happens to resolve to. `_config.yml`'s `exclude:` list (added Aug
  2026, after noticing repo docs and legacy build files were reachable
  at their own public URL) is what actually keeps `CLAUDE.md`,
  `HANDOFF.md`, `README.md`, `START_HERE_PROMPT.md`, `skill/`, and
  `working-files/` from getting a live `ccpx.fyi/<path>` URL. Keep it
  in sync if a new top-level repo/skill doc gets added — default to
  excluding anything that isn't part of the actual app
  (`index.html`, `puzzles/`, `CNAME`).
- No mechanism exists yet for updating a puzzle's reference solve
  after initial publish other than using the admin panel and
  redeploying.
- The skill's weekly-build workflow has only been exercised for two
  issues (Aug 7 and Aug 14, 2026) — page-number-drift and layout
  changes week to week are anticipated but not yet battle-tested
  beyond that.
- **Past-weeks menu, not yet built.** `puzzles/index.json` already
  lists every published week and `index.html?puzzle=<id>` already
  loads any of them (see "How the puzzle data is structured" above) —
  the data layer supports a picker, but no UI exposes it yet. Adding
  one is mostly a small dropdown/list in the hamburger menu that reads
  `puzzles/index.json` and links to `?puzzle=<id>`.
- **Weekly Issuu fetch is still a manual/chat-driven workflow**, not
  automated in this repo. It's split into two sub-skills as of Aug
  2026 — `skill/fetch-issue/SKILL.md` (find the issue/page, save raw
  material to `working-files/<date>/`) and
  `skill/build-puzzle-json/SKILL.md` (parse that into
  `puzzles/<date>.json`) — specifically so a future automation only has
  to replace the first half. It relies on `claude-in-chrome` to render
  Issuu's JS-only reader and read its SVG text layer — none of that
  runs in a plain script yet.
  A real automation (e.g. a scheduled GitHub Action) would need its
  own approach for finding the crossword page and getting clue text
  without a browser-rendered SVG text layer (OCR, or an Issuu API
  call, are the two obvious candidates, neither implemented). Discussed
  Aug 2026; not started.
