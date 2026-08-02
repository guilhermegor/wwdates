# Ledger — #14 masthead-logo-drop-version-pill

Branch: `docs/14-masthead-logo-drop-version-pill` · Issue: #14 · Class: **docs** (no `src/` diff → no release)

## Goal

Put the logo in the docs top bar next to `wwdates`, and delete the bespoke four-file stack that
injects a version pill into the masthead. Material's native `theme.logo` / `theme.favicon` already
places the image left of the site name with **no custom CSS** — it is what `filings-cvm` and
`filings-b3` use, and neither has a version pill. Two lines of config replace four files.

## Work

- [x] `mkdocs.yml` — added under `theme:`: `logo:` and `favicon:`, both
      `assets/logo_wwdates_no_description.png`. Asset confirmed present (and a second copy exists
      at the repo root `assets/`, used by the README).
- [x] `mkdocs.yml` — removed `custom_dir: overrides`, the whole `hooks:` block, and the
      `extra_javascript:` block.
- [x] Deleted `overrides/main.html`; `overrides/` is now gone.
- [x] Deleted `mkdocs_hooks.py`.
- [x] Deleted `docs/javascripts/header-version.js`; `docs/javascripts/` is now gone.
- [x] **Kept the file**, trimmed: `version-badge.css` → `docs/stylesheets/extra.css`, retaining
      only the `@media (min-width: 76.25em)` sidebar-title rule and dropping `.md-header__version`
      / `.md-header__title`. Chose to keep rather than drop: verified below that the rule is
      **load-bearing** — without it the site name renders twice on desktop.
- [x] **Grepped before deleting.** The only references to `mkdocs_hooks.py`, `code_version`,
      `header-version.js`, `version-badge.css` or `overrides` anywhere in the repo were inside
      `mkdocs.yml` itself and the two files being deleted. `Makefile`, `tasks.sh`,
      `docs/contributing.md`, `.gitignore` and `bin/check_docstrings.py` reference **none** of
      them, so nothing else needed updating. (One historical mention survives in
      `docs/backlog/dehydrate-calendars_20260704_130854.md` — a past-tense release record, left
      as-is.)

## Verification — done, at the rendered-DOM level

`poetry run mkdocs build --strict` → **exit 0**, clean. Then served `site/` and measured the real
computed layout in a browser (stronger than reading the markup, which cannot show whether CSS
actually applied):

**Desktop, 1440×900**

| Check | Result |
|---|---|
| Logo present in masthead | yes, `.md-header .md-logo img` |
| Logo actually loaded | `complete`, natural **600×280**, rendered **51×24** |
| Position | `left: 119`, **left of the title**, vertically centred on the same row |
| Version pill / `code-version` meta | **0 occurrences** |
| Sidebar duplicated title | `display: none` — the kept rule works |
| `extra.css` loaded | yes |

**Mobile, 700×900**

| Check | Result |
|---|---|
| Sidebar title | `display: block` — correctly *not* hidden; the media query is properly scoped |
| Header logo | hidden by **Material's own stock CSS**, with the drawer logo shown instead at 103×48. Not a regression — this repo now ships no custom header CSS at all |
| Horizontal overflow | none |

Screenshot reviewed: logo sits left of `wwdates`, no pill, sidebar lists nav items with no
duplicated heading.

Remaining: confirm the deployed site after merge at https://guilhermegor.github.io/wwdates/.

## Deferred (tracked here, not in this PR)

- Nothing.

## Not done, on purpose

- `mike` doc versioning (`extra.version.provider: mike`, used by both filings repos). This repo
  deliberately avoids `gh-pages`/`mike`; its docs deploy is the Actions-native path in `docs.yaml`.
- **Correction to this ledger's own premise.** It claimed removing the pill "loses the only
  in-page version indicator". That is **false**: Material's repository widget in the top-right
  already renders the latest release tag, and the built site shows **`v1.0.0`** there. So the
  four-file stack was duplicating information the stock theme displays for free — which
  strengthens the case for deleting it, rather than being a cost of doing so. The PyPI badge and
  changelog page remain as before.

## Observation, not a change

The logo renders 51×24 in the masthead from a 600×280 source — a wide logotype scaled to the
header's 24px height, so the wordmark is small. This is exactly how `filings-cvm` and `filings-b3`
render theirs, and is inherent to Material's fixed header height, not to this change. A
header-optimised (squarer, mark-only) asset would read better at that size; out of scope here.
