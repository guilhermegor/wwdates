# Ledger — #14 masthead-logo-drop-version-pill

Branch: `docs/14-masthead-logo-drop-version-pill` · Issue: #14 · Class: **docs** (no `src/` diff → no release)

## Goal

Put the logo in the docs top bar next to `wwdates`, and delete the bespoke four-file stack that
injects a version pill into the masthead. Material's native `theme.logo` / `theme.favicon` already
places the image left of the site name with **no custom CSS** — it is what `filings-cvm` and
`filings-b3` use, and neither has a version pill. Two lines of config replace four files.

## Work

- [ ] `mkdocs.yml` — add under `theme:`:
      `logo: assets/logo_wwdates_no_description.png` and
      `favicon: assets/logo_wwdates_no_description.png`
      (the asset already exists at `docs/assets/logo_wwdates_no_description.png`).
- [ ] `mkdocs.yml` — remove `custom_dir: overrides`, the whole `hooks:` block, and the
      `extra_javascript:` block.
- [ ] Delete `overrides/main.html` and the now-empty `overrides/`.
- [ ] Delete `mkdocs_hooks.py` — its only purpose is `config.extra.code_version`.
- [ ] Delete `docs/javascripts/header-version.js` and the now-empty `docs/javascripts/`.
- [ ] `docs/stylesheets/version-badge.css` → strip the `.md-header__version` and
      `.md-header__title` rules; keep only the `@media (min-width: 76.25em)` rule that hides the
      duplicated sidebar title; rename to `docs/stylesheets/extra.css` and update `extra_css:`.
      If that single rule does not justify a file once the header renders with the logo, dropping
      it entirely is also fine — record which was chosen.
- [ ] **Grep before deleting:** references to `mkdocs_hooks.py` or the version badge in
      `.gitignore`, `Makefile`, `tasks.sh`, `docs/contributing.md`, and `bin/check_docstrings.py`
      (which may scan `mkdocs_hooks.py`).
- [ ] Verify: `make docs_server` — logo in the top bar next to `wwdates`, no version pill, no
      duplicated sidebar title on desktop, favicon in the browser tab. Then
      `poetry run mkdocs build --strict` clean. Confirm the deployed site after merge at
      https://guilhermegor.github.io/wwdates/.

## Deferred (tracked here, not in this PR)

- Nothing.

## Not done, on purpose

- `mike` doc versioning (`extra.version.provider: mike`, used by both filings repos). This repo
  deliberately avoids `gh-pages`/`mike`; its docs deploy is the Actions-native path in `docs.yaml`.
  Losing the version pill therefore loses the only in-page version indicator — accepted, since the
  PyPI badge and the changelog page both carry it.
