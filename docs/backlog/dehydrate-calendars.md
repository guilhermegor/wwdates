# Work ledger — `feat/dehydrate-calendars`

Branch-scoped record of what was done and what remains, so knowledge survives across sessions.
Tracked in git but **excluded from the published docs site** (`exclude_docs` in `mkdocs.yml`).

> Scope note: this is **project/branch state** — distinct from the generalizable BlueprintX
> lessons captured in `docs/blueprintx-lessons.md` (git-ignored) and the global store
> `~/.claude/memory/lessons/`. Lessons = reusable, scaffold-backportable; this backlog =
> what happened on *this* branch and what is still open.

## Done

- Dehydrated the BR/US holiday calendars from `stpstone` into `wwdates`, laid out as
  `wwdates.<country>.<provider>` (one public class per module).
- Split the 8-class calendar mixin chain into one file per class under
  `_internal/utils/calendars/`; cache + vendored helpers (parsers, webdriver_tools) under
  `_internal/utils/`.
- ANBIMA read routes through `tabular_reader` + a `FileContract` (never raw `pd.read_excel`);
  extended `read_table` with headerless-Excel support.
- Reused the repo's own `typing` chassis (discarded stpstone's duplicate); broke the
  cache→calendar circular import; swapped `CreateLog`→`LogEmitter`, `PickleFiles`→stdlib pickle.
- **US federal holidays reworked into two classes:** `DatesUSFederalHolidays` (offline, via the
  `holidays` package, applies the §6103 observed-day rule — emits statutory + observed) and
  `DatesUSFederalHolidaysWeb` (the Playwright live scrape).
- **Playwright is now an optional `web` extra** (`pip install "wwdates[web]"` +
  `playwright install chromium`); base install is browser-free; the Web class raises a clear
  `ImportError` when the extra is absent.
- **`LogEmitter`**: no logger → print to screen; logger → route to it (restored stpstone
  convenience).
- Public API: country subpackages re-export providers; `__version__` via `importlib.metadata`;
  removed the `main.py` placeholder and dead `run` target.
- Tooling: `install_dist_locally` (Makefile + tasks.sh); docs-deploy workflow (`docs.yaml`);
  **changelog auto-regenerated on merge to main** (`changelog.yaml`) + local `make changelog`.
- Docs: Home, Usage, Examples, API Reference, FAQ, Contributing, Changelog; logo on README +
  docs homepage; tagline → "Global calendar system."; version-badge CSS; sidebar-title hidden.
- Optimized the logo PNGs (were 715 KB / 4.9 MB → ~116 KB / 163 KB) to pass the large-file hook.
- Version bumped to `0.1.0`. All gates green (ruff, mypy, docstring, 277 tests, mkdocs strict,
  wheel build). PR **#1** open against `main`.

## Open / to-do

- [ ] **`add_holidays()` is broken on providers** (pre-existing, flagged, NOT fixed): providers
      don't call `super().__init__()`, so `_added_holidays` is never initialised and
      `add_holidays()` would `AttributeError`. Fix once, in the base or each provider ctor, with
      a test. Affects every provider.
- [ ] **Maintainer setup for the changelog action:** create a fine-grained PAT (Contents: write)
      as the `CHANGELOG_TOKEN` secret and add it to the branch-protection **bypass** list, or the
      auto-changelog push to protected `main` will fail. Documented in `docs/contributing.md`.
- [ ] **PyPI publishing setup:** decide token vs OIDC trusted-publisher; the pending trusted
      publisher is configured but the workflow still uses `PYPI_TOKEN`. (See earlier session
      discussion.)
- [ ] **Orphan assets:** `assets/logo_lorem_ipsum.png` (22 KB) is unused; decide keep/delete.
      `assets/logo_wwdates_description.png` (163 KB) is no longer referenced (README/docs use the
      `_no_description` variant) — keep as an alt or remove.
- [ ] **`docs.yaml` / `changelog.yaml` first runs** are untested on the real remote (need the
      branch merged + secrets set).
