# Ledger — #18 cookie-popup-probe

Branch: `fix/18-cookie-popup-probe` · Issue: #18 · Class: **src** (ships in the wheel → release)

## Goal

`PlaywrightScraper._handle_cookie_popup` blocked for a hard-coded **30 s per page** on a site that
has no consent banner at all, and logged the routine outcome at `error`. Make the absent-banner
case cheap and quiet, while keeping a genuinely unclickable banner loud.

## Work

- [x] Confirm the premise before changing anything. `federalholidays.net` HTML contains **zero**
      `accept` / `cookie` / `consent` / `onetrust` / `cookiebot` matches, so `text=Accept All`
      could never match and the full 30 s was paid on every navigation. Also confirmed
      `us/federal_holidays_web.py` is the **only** module in the package that drives Playwright —
      the BR sources do not — so a single English selector is sufficient and no i18n work is in
      scope.
- [x] Probe before clicking. `_handle_cookie_popup` now waits for the banner with a short bounded
      budget and returns early when it does not appear. Both call sites (`navigate()` and the
      json-steps runner, neither of which passes an argument) get the fix without changing.
- [x] Split the two outcomes that were previously one `except`:
      - banner absent → `info`, "No cookie consent banner found; nothing to accept". The normal
        case, not a failure.
      - banner present but the click fails → `error`. A real problem, still loud.
- [x] Replace the magic numbers with named module constants, matching the file's existing
      `_WEB_EXTRA_HINT` convention: `_COOKIE_ACCEPT_SELECTOR`, `_COOKIE_PROBE_TIMEOUT_MS`
      (**1 000**), `_DEFAULT_TIMEOUT_MS` (**30 000**).
- [x] Fix the docstring that claimed `3000ms` while the code said `30_000` — it now documents the
      probe budget and states explicitly that it is *not* the page-load timeout.
- [x] Fix `int_default_timeout: int = 10`. Ten milliseconds feeds `page.goto`, so any caller
      relying on the default could not load a page at all; the sole real call site
      (`federal_holidays_web.py:134`) only worked because it passes `5000` explicitly. Now
      defaults to `_DEFAULT_TIMEOUT_MS`, matching Playwright's own `set_default_timeout` default,
      so the seam behaves like the library it wraps.
- [x] `timeout=` is still honoured, so a source whose banner is injected late can widen the probe
      without touching the seam.
- [x] Tests: `tests/unit/test_playwright_wd.py` — **new file, the module had no tests at all**.
      8 tests over fake locators, so nothing launches a browser and the `conftest.py` socket guard
      stays intact.

## Verification

- `poetry run pytest tests/unit/` → **321 passed** (313 before + 8 new).
- `ruff check` / `ruff format --check` / `mypy` / `pydocstyle` → all clean.
- **Measured end-to-end against the live page** (outside the test suite, which cannot open a
  socket), scraping 2026:

  | | Elapsed | Rows |
  |---|---|---|
  | Pre-fix budget (30 000 ms probe) | **34.83 s** | 11 |
  | This fix (1 000 ms probe) | **6.38 s** | 11 |

  Identical output, **28.4 s saved per page**. The US web source sweeps `year-1 … year` by default
  (2 pages), so the weekly drift job saves **~57 s per US sweep** — matching the estimate on the
  issue.

## Deferred (tracked here, not in this PR)

- The `visible=True` branch of `selector_exists` calls `locator.first.is_visible()`, which ignores
  the `timeout` argument entirely — an instant check wearing a timeout parameter. Not touched
  here because other callers depend on current behaviour, and the cookie probe deliberately does
  not use that helper (see below).

## Not done, on purpose

- **Did not reuse `selector_exists()` for the probe**, even though the issue suggested it. It logs
  a `warning` whenever the selector is missing, which is precisely the mis-levelled noise this fix
  exists to remove — routing the probe through it would have reintroduced the defect one severity
  lower. The probe instead calls `locator.wait_for(state="visible", …)` directly, which is the same
  primitive `selector_exists` uses, and keeps the absent case at `info`.
- **Did not flip `bool_accept_cookies` to `False`** or delete the cookie handling. No page this
  library scrapes has a banner, so both were on the table; keeping it on at ~1 s preserves the
  vendored seam's usefulness for a future source that does show one.
- **Did not widen the selector** beyond `text=Accept All`. A single English string is correct for
  the only Playwright-driven source in the package; widening it should be a deliberate edit made
  when a non-English source is actually added, not speculative matching now.
