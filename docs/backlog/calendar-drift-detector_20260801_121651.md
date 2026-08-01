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

## Work

- [ ] `bin/check_calendar_drift.py` — compare **dates only, never names** (B3 publishes an event
      feed with free-text wording) across the four pairs:
      `DatesBRB3`↔`DatesBRB3Web`, `DatesBRAnbima`↔`DatesBRAnbimaWeb`,
      `DatesBRFebraban`↔`DatesBRFebrabanWeb`, `DatesUSFederalHolidays`↔`DatesUSFederalHolidaysWeb`.
      `DatesUSNasdaq` is web-only — no offline twin, skip it.
- [ ] Reuse the filings-cvm structure rather than reinventing it: `build_issue_body()` with a
      hidden `_ISSUE_MARKER`, `find_open_drift_issue()` matching on label + marker,
      `upsert_issue()` doing `GET issues?state=open&labels=…` then `PATCH` or `POST`, `_api()`
      over `GITHUB_TOKEN`, `main()` returning `0` unconditionally.
- [ ] Known-exceptions allowlist as a module-level constant, each entry commented with its PR #10
      evidence so widening it is a deliberate edit:
      - B3 offline-only dates falling on a **weekend** (B3 omits them — no session to cancel);
      - the **2021 São Paulo** municipal/state dates (scrape-only; B3 stopped observing them).
- [ ] Clamp the comparison span per pair — FEBRABAN's endpoint only serves a narrow year window,
      so diffing years the source never publishes would manufacture false drift.
- [ ] `.github/workflows/calendar-drift.yaml` — weekly `schedule` (odd minute, UTC) +
      `workflow_dispatch: {}`; `permissions: {contents: read, issues: write}`;
      `concurrency: {group: calendar-drift, cancel-in-progress: false}`;
      `poetry install --extras web` + `poetry run playwright install --with-deps chromium`
      (`DatesUSFederalHolidaysWeb` drives Playwright via
      `_internal/utils/webdriver_tools/playwright_wd.py`);
      env `GITHUB_TOKEN: ${{ github.token }}`, `GITHUB_REPOSITORY: ${{ github.repository }}`.
- [ ] Put the non-blocking rationale in the workflow header comment: a B3/ANBIMA outage and a real
      drift are indistinguishable in a red check, so a red check must never gate a PR. The script
      always `sys.exit(0)`; only an unhandled crash reddens the run, and a reddened *scheduled* run
      gates nothing.
- [ ] `tests/unit/test_check_calendar_drift.py` — unit only, socket guard intact (no
      `allow_network`): identical sets → no problems; extra web date → reported; allowlisted
      weekend / 2021-SP date → not reported; `main()` returns `0` even with problems;
      `find_open_drift_issue()` against a fixture issue list.
- [ ] Verify on the remote: dispatch manually, confirm it installs Chromium, reaches all four
      sources, exits 0, and opens **one** issue. Re-dispatch and confirm the second run *updates*
      that same issue instead of opening a second — the marker/label dedupe is the part most
      likely to be wrong.

## Deferred (tracked here, not in this PR)

- **24 December.** It will surface as a B3 offline-vs-web difference in every year it falls on a
  weekday, for as long as `bool_add_christmas_eve` stays `False`. Decide during implementation
  whether to allowlist it (with a pointer to the open decision) or leave it as the standing nag,
  and record which was chosen here.

## Not done, on purpose

- Flipping `bool_add_christmas_eve` — still open in
  `dehydrate-calendars_20260704_130854.md`. This job gives that decision more evidence; it does
  not resolve it.
- Making the check blocking, or moving it into the test suite. Both defeat the reason it exists.
