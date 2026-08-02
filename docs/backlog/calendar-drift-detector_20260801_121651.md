# Ledger — #12 calendar-drift-detector

Branch: `feat/12-calendar-drift-detector` · Issue: #12 · Class: **ci** (no `src/` diff → no release)

## Goal

Detect, weekly and automatically, when the offline calendars diverge from the pages their
publishers keep live. Equivalence was verified **once, by hand**, in PR #10 (ANBIMA 2001–2099:
empty symmetric difference). `tests/conftest.py` blocks sockets by design, so no test can ever
re-check it — a scheduled, non-blocking job is the complement to a network-blocked suite, not a
workaround for it. Divergence becomes one self-filing tracking issue, never a red required check.

Model to copy in shape: `filings-cvm/bin/check_contract_drift.py` +
`filings-cvm/.github/workflows/contract-drift.yaml` (that repo's issue #98).

**Shipped in PR #17 (`555277f`), issue #12 closed 2026-08-01.**

## Work

- [x] `bin/check_calendar_drift.py` — compare **dates only, never names** (B3 publishes an event
      feed with free-text wording) across the four pairs:
      `DatesBRB3`↔`DatesBRB3Web`, `DatesBRAnbima`↔`DatesBRAnbimaWeb`,
      `DatesBRFebraban`↔`DatesBRFebrabanWeb`, `DatesUSFederalHolidays`↔`DatesUSFederalHolidaysWeb`.
      `DatesUSNasdaq` is web-only — no offline twin, skip it.
- [x] Reuse the filings-cvm structure rather than reinventing it: `build_issue_body()` with a
      hidden `_ISSUE_MARKER`, `find_open_drift_issue()` matching on label + marker,
      `upsert_issue()` doing `GET issues?state=open&labels=…` then `PATCH` or `POST`, `_api()`
      over `GITHUB_TOKEN`, `main()` returning `0` unconditionally.
- [x] Known-exceptions allowlist as a module-level constant, each entry commented with its PR #10
      evidence so widening it is a deliberate edit:
      - B3 offline-only dates falling on a **weekend** (B3 omits them — no session to cancel);
      - the **2021 São Paulo** municipal/state dates (scrape-only; B3 stopped observing them).
- [x] Clamp the comparison span per pair — **implemented as a runtime derivation from the web
      side**, not a per-pair constant: `DatesBRB3Web` and `DatesBRAnbimaWeb` take no year range at
      all (they publish what they publish), so `clamp_to_web_span()` reads min/max year off the
      fetched set. A hard-coded span would rot the moment B3 publishes another year.
- [x] `.github/workflows/calendar-drift.yaml` — weekly `schedule` (`37 6 * * 1`) +
      `workflow_dispatch: {}`; `permissions: {contents: read, issues: write}`;
      `concurrency: {group: calendar-drift, cancel-in-progress: false}`;
      `poetry install --extras web` + `poetry run playwright install --with-deps chromium`.
- [x] Put the non-blocking rationale in the workflow header comment **and** the module docstring.
- [x] `tests/unit/test_check_calendar_drift.py` — **33 tests**, socket guard intact throughout (no
      `allow_network` anywhere). The tests written after their code were **mutation-checked**:
      disabling the weekend allowance, dropping Christmas Eve from the allowlist, removing the span
      clamp and making `main()` return 1 each turned exactly the intended test red, then restored.
- [x] Verify on the remote: run
      [30725271837](https://github.com/guilhermegor/wwdates/actions/runs/30725271837) —
      `workflow_dispatch` on `main`, **cold runner, no cache**, all 10 steps green including the
      Chromium install. Output: `no calendar drift detected (0 source(s) could not be checked)` —
      all four pairs fetched live, zero divergence. Independently reconfirms PR #10's hand
      verification from a clean environment.

## Two bugs found by running it before shipping

Both were caught because the job was exercised against the real sources *before* merge, not after:

- [x] **The `*Web` classes cache by default.** A drift detector that reads a cache cannot detect
      drift — and a *partial* cache from an earlier failed fetch is reported **as** drift.
      Measured: 2 of 22 US dates served stale → **9 false positives**. Had it shipped, the first CI
      run would have filed fabricated findings and the natural "fix" would have been widening the
      allowlist, permanently blinding the job. Fixed with an `_uncached()` wrapper at the registry
      plus a test asserting it for every pair.
- [x] **Read failures opened the drift issue.** federalholidays.net timed out mid-testing, which
      showed an outage filing a "calendar drift" issue naming no drift — the cry-wolf that makes a
      drift job worse than nothing. `collect_drift()` now returns `(problems, errors)` separately;
      errors never open the issue, they only ride along in the body when one opens for real drift.

## Deferred (tracked here, not in this PR)

- **24 December — decided: allowlisted.** `b3_known_web_only()` excuses it for every year the
  source returns. B3 publishes it as a genuine closure in every year it falls on a weekday while
  `DatesBRB3` defaults to `bool_add_christmas_eve=False`, so unexcused the job would restate the
  same *known* disagreement every single week — noise that drowns the signal it exists to carry.
  The decision on the default itself stays open in `dehydrate-calendars_20260704_130854.md`.
- **The upsert's write half is unverified.** `POST` (open) and `PATCH` (update) never ran, because
  there was no drift to trigger them. The pure helpers are unit-tested and `_api()` was verified
  live on the `GET`, but the open-then-update pair is unproven. Symptom to watch on the first real
  drift: a finding in the logs with no issue opened. Recorded on issue #12 too.

## Not done, on purpose

- Flipping `bool_add_christmas_eve` — still open in
  `dehydrate-calendars_20260704_130854.md`. This job gives that decision more evidence; it does
  not resolve it.
- Making the check blocking, or moving it into the test suite. Both defeat the reason it exists.
- Fixing `PlaywrightScraper`'s 30 s cookie-popup timeout, surfaced by this job's first run and
  filed as **#18**. Out of scope here — the sweep degrades correctly (`could not check`, never
  drift); the timeout is latency and log noise, not incorrectness.

## Lesson captured

`drift-job-must-disable-the-client-cache` — BlueprintX store + README index +
`docs/blueprintx-lessons.md`. The general rule: **cache/retry/timeout policy is a property of the
caller's intent, not the client**; when a job reuses a production client for a purpose it was not
written for, audit every default it carries. Sibling of the existing
`probe-injects-fail-fast-retry-not-patient-production-policy` (same shape, one knob over).
