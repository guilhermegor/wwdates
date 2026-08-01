# Work ledger — `feat/dehydrate-calendars`

Branch-scoped record of what was done and what remains, so knowledge survives across sessions.
Tracked in git but **excluded from the published docs site** (`exclude_docs` in `mkdocs.yml`).

> Scope note: this is **project/branch state** — distinct from the generalizable BlueprintX
> lessons captured in `docs/blueprintx-lessons.md` (git-ignored) and the global store
> `~/.claude/memory/lessons/`. Lessons = reusable, scaffold-backportable; this backlog =
> what happened on *this* branch and what is still open.

## Done

- [x] Dehydrated the BR/US holiday calendars from `stpstone` into `wwdates`, laid out as
  `wwdates.<country>.<provider>` (one public class per module).
- [x] Split the 8-class calendar mixin chain into one file per class under
  `_internal/utils/calendars/`; cache + vendored helpers (parsers, webdriver_tools) under
  `_internal/utils/`.
- [x] ANBIMA read routes through `tabular_reader` + a `FileContract` (never raw `pd.read_excel`);
  extended `read_table` with headerless-Excel support.
- [x] Reused the repo's own `typing` chassis (discarded stpstone's duplicate); broke the
  cache→calendar circular import; swapped `CreateLog`→`LogEmitter`, `PickleFiles`→stdlib pickle.
- [x] **US federal holidays reworked into two classes:** `DatesUSFederalHolidays` (offline, via the
  `holidays` package, applies the §6103 observed-day rule — emits statutory + observed) and
  `DatesUSFederalHolidaysWeb` (the Playwright live scrape).
- [x] **Playwright is now an optional `web` extra** (`pip install "wwdates[web]"` +
  `playwright install chromium`); base install is browser-free; the Web class raises a clear
  `ImportError` when the extra is absent.
- [x] **`LogEmitter`**: no logger → print to screen; logger → route to it (restored stpstone
  convenience).
- [x] Public API: country subpackages re-export providers; `__version__` via `importlib.metadata`;
  removed the `main.py` placeholder and dead `run` target.
- [x] Tooling: `install_dist_locally` (Makefile + tasks.sh); docs-deploy workflow (`docs.yaml`);
  changelog regenerated at release time via `make changelog` (see the changelog decision below).
- [x] Docs: Home, Usage, Examples, API Reference, FAQ, Contributing, Changelog; logo on README +
  docs homepage; tagline → "Global calendar system."; version-badge CSS; sidebar-title hidden.
- [x] Optimized the logo PNGs (were 715 KB / 4.9 MB → ~116 KB / 163 KB) to pass the large-file hook.
- [x] **`add_holidays()` fixed across all providers.** Two bugs, both provider-only (the abc facade
  masked them): (1) providers skip `super().__init__()` → `_added_holidays` was never
  initialised (`AttributeError`); (2) providers override `holidays()`, shadowing the mixin
  merge, so injected holidays never reached `holidays()` / the working-day set. Reworked to a
  **source-hook**: providers now implement `_source_holidays()`, and a single inherited
  `holidays()` (in `DateManipulation`) appends the runtime additions. `_added_holidays` is
  lazily initialised via `_get_added_holidays()`, independent of `__init__`. Regression test
  `test_nasdaq_add_holidays_merges_into_provider` added.
- [x] **Rich-by-default screen logging.** New `LogsEmitter(LogEmitter)` (`_internal/utils/
  logs_emitter.py`) delegates to `logs.py`'s `CreateLog`; wired as `CacheManager`'s default sink,
  so with no logger injected the screen line is now
  `YYYY-MM-DD,HH:MM:SS.mmm INFO {Class} [method] msg` (was bare `[INFO] msg`); inject a logger to
  route there instead. Fixed a latent `logs.py` bug: the caller-context stack-walker used a
  `startswith` skip-set (`"utils.typing"`) that never matched the package-qualified module names —
  switched to last-dotted-component matching so `{Class}` resolves. Base `LogEmitter` stays
  minimal/injectable. Regression test + blueprintx lesson (`rich-default-log-emitter`) captured.
- [x] Version bumped to `0.1.0`. All gates green (ruff, mypy, docstring, 279 tests, mkdocs strict,
  wheel build). PR **#1** open against `main`.

## Open / to-do
- [x] **Changelog moved off CI-push-to-protected-main (no PAT, no bypass).** Deleted
      `changelog.yaml` (it pushed to protected `main`, forcing a `CHANGELOG_TOKEN` PAT +
      branch-protection bypass — the same long-lived secret just removed from PyPI). `CHANGELOG.md`
      is now regenerated from tags by `cz changelog` at **docs-build time** (`docs.yaml`), never
      committed to `main`; `make changelog` remains for local preview. Docs, Makefile + tasks.sh
      updated; blueprintx lesson `changelog-no-ci-push-to-protected-main` captured. **No maintainer
      setup required.**
- [x] **Release pipeline hardened: real test gate + tag-driven dynamic versioning.**
      (1) Dropped the self-attested `tests_passed` input; both release workflows now `needs:` a
      `run_tests` job (full-matrix `tests.yaml`), so publish is gated on tests actually passing.
      (2) Version is now the **git tag** via `poetry-dynamic-versioning`: `pyproject` holds a
      `0.0.0` stub, the release workflow tags `vX.Y.Z` and builds with `python -m build` (Test PyPI
      uses `POETRY_DYNAMIC_VERSIONING_BYPASS`). Deleted `make bump_version` (now offline-only).
      Locally verified: tag→`wwdates-9.9.8`, bypass→`9.9.9`, no-tag→dev version; `install_dist_
      locally` green. Two blueprintx lessons captured (`release-gate-runs-tests-not-attestation`,
      `versioning-origin-dependent-tag-driven-online`). Split into two revertable commits.
- [x] **PyPI publishing switched to OIDC trusted publishing** (own commit for easy rollback).
      Both release workflows now publish via `pypa/gh-action-pypi-publish@release/v1` under the
      existing `id-token: write` / `environment: release` — no `PYPI_TOKEN` / `TEST_PYPI_TOKEN`
      secret. Docs (`contributing.md`, `CLAUDE.md`) updated; blueprintx lesson
      `pypi-oidc-trusted-publishing` captured. **Maintainer action:** register a trusted publisher
      on **both** pypi.org and test.pypi.org (owner `guilhermegor`, repo `wwdates`, the workflow
      filename, environment `release`); use a *pending publisher* for the first release. Roll back
      this commit to return to token-based publishing if OIDC misbehaves.
- [x] **Orphan assets deleted:** removed `assets/logo_lorem_ipsum.png` and
      `assets/logo_wwdates_description.png`; only `logo_wwdates_no_description.png` (the sole
      referenced variant) remains.
- [x] **Placeholder-version ripple fixed** in the docs badge + local smoke. `mkdocs_hooks.py` now
      derives the masthead version from `git describe --tags --always` (falls back to pyproject
      then `?`) instead of the `0.0.0` stub — verified badge renders `v6d445f3` now / `v0.2.0` on a
      tag. `install_dist_locally` (Makefile + tasks.sh) reports the built wheel's real version
      (e.g. `wwdates-0.0.0.post15.dev0+6d445f3`) rather than the editable `0.0.0`. `docs_server`
      needed no change (it feeds through the same hook). Lesson updated with the ripple note.
- [x] **`docs.yaml` proven on the remote:** ran green and the site is **live** at
      https://guilhermegor.github.io/wwdates/ (HTTP 200). Root cause of the initial 404 was Pages
      never being enabled (`gh-deploy` publishes the branch but can't enable serving) — fixed by
      enabling Pages this session. (Being migrated to a self-enabling Actions deploy in PR #5.)
- [x] **BR calendars are offline-first (issue #7), and `DatesBRB3Web` now really scrapes B3.**
      All three BR providers gained the two-class shape the US side already used: offline class
      = default, `*Web` class = the publisher's live page. **The offline source is
      `holidays.B3`, not `holidays.Brazil`** — the issue proposed the latter, but it is the
      statutory-only set and omits Carnaval (Mon+Tue) and Corpus Christi, so it would have
      silently marked Carnaval a working day. Equivalence was verified **before** switching the
      default: over ANBIMA's full published span (2001–2099) the offline set and the fetched
      workbook have an **empty symmetric difference**; FEBRABAN matches too (checked live for
      2025–2026 — the years its endpoint serves). B3 = that set plus the last working day of
      each year, computed locally.
      **`DatesBRB3Web` was rewritten** (per review: it fetched ANBIMA, never B3) to scrape B3's
      own trading calendar. That page is an event feed, so closures are identified by B3's own
      wording (`"não haverá negociação"`), never by event name — US holidays listed for
      reference, `Câmara de Câmbio` notes and reduced-hours sessions all correctly stay working
      days. It reconciles exactly against the offline class: every offline-only date is a
      weekend (B3 omits those — no session to cancel), and the only scrape-only dates are 2021's
      São Paulo municipal/state holidays, which B3 stopped observing afterwards.
      **Two latent cache bugs fixed at the root:** `cache_df` keys ignored the constructor args
      that change the frame, so `DatesBRB3Web(bool_add_christmas_eve=True)` was served the
      no-Christmas-Eve cache and two `DatesBRFebrabanWeb` instances with different year ranges
      collided. The decorator already supported callable keys — only its `key: str` annotation
      blocked them. Also removed two stale `type: ignore[override]` comments that mypy had been
      flagging on `main`.
- [ ] **Decide `bool_add_christmas_eve`'s default.** B3's own page publishes 24 December as a
      genuine closure ("não haverá negociação") in every year it falls on a weekday (2021, 2024,
      2025, 2026), which means the offline class's `bool_add_christmas_eve=False` default
      disagrees with the exchange. Left unchanged — flipping it is a behaviour change beyond
      issue #7's scope — but it is now evidence-backed, not a matter of taste.
- [x] **OIDC `release_*` workflows proven live on the remote (2026-08-01).** Both trusted
      publishers were corrected to the per-index environments (`release_test_pypi` /
      `release_pypi`) and both workflows published end-to-end with no stored token, during the
      `1.0.0` release: Test PyPI run 30696472307 (18/18 jobs green) and PyPI run 30696729122
      (20/20 jobs green, twine uploaded both artifacts with attestations). Tag `v1.0.0` exists and
      the GitHub release is not a draft. Install-verified from both indices
      (`wwdates.__version__ == "1.0.0"` in a clean venv).
      Earlier failure mode, now resolved: Test PyPI returned `invalid-publisher` while the
      publisher env was the generic `release`.
