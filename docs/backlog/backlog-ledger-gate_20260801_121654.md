# Ledger — #15 backlog-ledger-gate

Branch: `chore/15-backlog-ledger-gate` · Issue: #15 · Class: **ci** (no `src/` diff → no release)

## Goal

Enforce one shape for `docs/backlog/` ledgers. `filings-cvm` and `filings-b3` both gate it with
`bin/check_backlog_ledger.py` + a test; here the convention exists only by word of mouth, so it
will drift with every new branch.

## Work

- [ ] `bin/check_backlog_ledger.py` + `tests/unit/test_check_backlog_ledger.py`, ported from
      `filings-cvm`.
- [ ] Required shape: H1 `Ledger — #<issue> <slug>`; a metadata line
      `Branch: … · Issue: #<n> · Class: **<src|ci|docs>**`; then `## Goal`, `## Work` (checkbox
      list), and where applicable `## Deferred (tracked here, not in this PR)` and
      `## Not done, on purpose`.
- [ ] Register as a local hook in `.pre-commit-config.yaml`, matching how the existing
      `bin/check_docstrings.py` and `bin/check_unix_filenames.sh` hooks are declared.
- [ ] **Migrate `dehydrate-calendars_20260704_130854.md`** — it uses the older shape
      (`# Work ledger — feat/dehydrate-calendars`, `## Done` / `## Open / to-do`). Rewrite its
      headings rather than loosening the checker: one changed file beats a permanently forked
      gate. It is the 1.0.0 release record — preserve every line, change only the headings.
- [ ] Verify: `rtk pre-commit run check-backlog-ledger --all-files` passes on the migrated file
      and on the four ledgers added alongside issues #12–#15, and fails on a deliberately
      malformed scratch ledger.

## Deferred (tracked here, not in this PR)

- Nothing.

## Not done, on purpose

- Requiring a ledger to *exist* for every branch. The gate checks the shape of ledgers that are
  there; making one mandatory would block trivial fix branches for no gain.
