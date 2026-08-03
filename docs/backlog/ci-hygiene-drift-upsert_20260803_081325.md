# Ledger — #33 ci-hygiene-drift-upsert

Branch: `chore/33-ci-hygiene-drift-upsert` · Issue: #33 · Class: **ci** (no `src/` diff → no release)

## Goal

Close two items that were recorded as *deferred* in earlier ledgers with no issue of their own: the
dead win32 transform in `tests.yaml`, and the never-executed **write** half of the drift detector's
`upsert_issue`.

## Work

- [x] **Removed the win32 transform** from `tests.yaml`'s `Install Dependencies`. wwdates declares
      no `pywin32` — verified: zero hits in `pyproject.toml`; the `win32` strings in `poetry.lock`
      are transitive wheel *filenames*, not declarations. The step now just installs. Left a comment
      saying why, so it is not "restored" as a template drift-fix later.
- [x] **Covered `upsert_issue`'s write half** with 5 tests driving a stubbed `_api`:
      - no open tracker → exactly **one POST** to `/issues` with title, body and label;
      - an existing tracker → **one PATCH** to `/issues/{n}` and **no POST** (the dedupe the #12
        ledger called the part most likely to be wrong);
      - the GET filters by `state=open` **and** the label;
      - the written body carries the marker `find_open_drift_issue` matches on — and that function
        is then run against the produced body, closing the loop between the two halves;
      - a "could not check" error still reaches the body.

## Why the existing tests did not already cover this

Every prior test does `monkeypatch.setattr(drift, "upsert_issue", …)` — it **replaces the function
being named**. That tests whether `main` *decides* to call it; the function's own body never runs.
Combined with there having been no real drift, the GET→PATCH-or-POST logic had executed **nowhere**:
not in production, not in CI, not in a test.

Generalisable: *a test that stubs the function in its own name is testing the caller, not the unit.*

## Verification

- [x] `poetry run pytest tests/unit/test_check_calendar_drift.py` → **38 passed** (33 + 5).
- [x] **Mutation-tested, because a test that cannot fail proves nothing** (see
      `every-gate-needs-a-should-fail-test`):
      - forcing `upsert_issue` to always POST → only
        `test_upsert_issue_updates_in_place_when_one_exists` fails. Exactly the intended detector.
      - dropping `_ISSUE_MARKER` from the body → the marker tests fail, including the loop-closing
        one.
      - source restored afterwards; `git diff` clean and the suite green again.
- [x] No network: `_api` is monkeypatched, so the `conftest.py` socket guard stays intact.

## Deferred (tracked here, not in this PR)

- **`release_pypi.yaml` and `release_test_pypi.yaml` carry the same dead win32 transform** — and
  something worse next to it, found while checking whether to remove it there too:

  ```
  if ! poetry check --lock; then
    rm -f poetry.lock
    poetry lock --no-cache
  ```

  That is the exact anti-pattern `tests.yaml` was deliberately fixed away from
  (`ci-lock-fail-loud-not-regenerate`): it **silently re-resolves every dependency** to the latest
  in-range version, producing a non-reproducible build — **in the release path**. Deliberately not
  touched here: the release workflows are the least-rehearsed code in the repo (the Test PyPI run
  does not share every step), so they deserve one considered PR rather than a drive-by edit inside a
  hygiene change. Filed separately.
  **RESOLVED 2026-08-03 as #39 / PR #40** — which also found that both release workflows carried all
  three of #19's cache defects on top of the regeneration fallback, and that the ledger gate crashed
  outright on Windows (cp1252 could not encode its status glyphs). No longer open work.

## Not done, on purpose

- Did not remove the transform from the two release workflows, for the reason above — removing it
  there means opening that file, and that file needs the lock-regeneration decision made at the same
  time.
