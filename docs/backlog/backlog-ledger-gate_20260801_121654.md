# Ledger — #15 backlog-ledger-gate

Branch: `chore/15-backlog-ledger-gate` · Issue: #15 · Class: **ci** (no `src/` diff → no release)

## Goal

Enforce one shape for `docs/backlog/` ledgers. `filings-cvm` and `filings-b3` both gate it with
`bin/check_backlog_ledger.py` + a test; here the convention exists only by word of mouth, so it
will drift with every new branch.

## Work

- [x] `bin/check_backlog_ledger.py` + `tests/unit/test_check_backlog_ledger.py` (15 tests).
- [x] Required shape enforced: H1 `Ledger — #<issue> <slug>`; metadata line
      `Branch: … · Issue: #<n> · Class: **<src|ci|docs>**`; `## Goal`; `## Work` with at least one
      checkbox. `## Deferred …` / `## Not done, on purpose` stay optional — a branch with nothing
      deferred should not be made to write a section saying so. Two cross-checks beyond the
      literal spec, both cheap and both catching real copy-paste drift: the H1's issue number must
      equal the metadata line's, and the H1's slug must equal the filename's topic.
- [x] Registered as a local hook in `.pre-commit-config.yaml`, alongside `check-docstrings`, with
      `files: ^docs/backlog/.*\.md$`.
- [x] **Migrated `dehydrate-calendars_20260704_130854.md`.** Only the headings changed: added the
      H1/metadata/`## Goal` headings and renamed `## Done` → `## Work`. Every content line is
      untouched (diff: 10 insertions, 2 deletions — the 2 being the old H1 and `## Done`).
      `## Open / to-do` was **kept verbatim** rather than renamed to `## Deferred`: its items are
      almost all `- [x]` done, so "Deferred" would misdescribe the record. The checker permits
      extra sections, so uniformity did not require falsifying the history.
- [x] Verified `rtk pre-commit run check-backlog-ledger --all-files` → **Passed** across all five
      ledgers, and confirmed it genuinely **fails** on a malformed one staged in-repo (5 errors
      reported, exit 1) — not merely on a scratch file outside the repo.

## Deliberate divergence from the sibling repos' version

`filings-cvm`'s `check_backlog_ledger.py` answers a *different* question: it imports
`bin/pr_gate.py`, classifies the branch's diff by path risk, and **requires a ledger to exist**
whenever a `src`/`ci` path is touched — while barely checking the ledger's content (name + any
checkbox).

This port keeps only the shape half, because:

- wwdates has **no `bin/pr_gate.py`**, so the risk-class axis does not exist here. Porting it
  would have meant inventing a second, drifting copy of "what counts as src/ci".
- Issue #15 explicitly rejected mandatory existence ("making one mandatory would block trivial fix
  branches for no gain"), which is the same rule the import exists to serve.

Dropping that half removes the dependency *and* all the git merge-base/`--cached` diff machinery:
pre-commit already hands the hook exactly the ledger paths being committed. What remains is a pure
`check()` over injected text, unit-testable with no working tree — the one design idea worth
keeping from the original.

## Bug found by the negative test, in this gate itself

The first negative run **passed when it should have failed**. The path filter was
`str_path.startswith("docs/backlog/")`, which silently returns False for an **absolute** path — so
handed absolute paths the gate checked nothing and reported success. Replaced with a parent-segment
match (`PurePath(p).parent.as_posix().endswith("docs/backlog")`), covered by two regression tests
(`test_absolute_paths_are_still_checked`, `test_is_ledger_path_rejects_a_lookalike_directory`).

Worth recording because it is the same failure shape as the CI cache bug found in #13 this session:
**a gate that examines nothing reports success**, and only a deliberate should-fail case exposes it.

## Deferred (tracked here, not in this PR)

- Nothing.

## Not done, on purpose

- Requiring a ledger to *exist* for every branch. The gate checks the shape of ledgers that are
  there; making one mandatory would block trivial fix branches for no gain.
