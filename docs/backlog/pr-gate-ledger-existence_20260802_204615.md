# Ledger — #26 pr-gate-ledger-existence

Branch: `chore/26-pr-gate-ledger-existence` · Issue: #26 · Class: **ci** (no `src/` diff → no release)

## Goal

Add the half of the ledger gate that #15 left out: **require a ledger to exist** when a branch's
diff touches a `src`/`ci` path, using a ported `bin/pr_gate.py` as the single definition of what
those classes mean. #15 shipped shape-only.

## Work

- [x] Ported `bin/pr_gate.py` from `filings-cvm` — **the whole 650-line file, verbatim**, per the
      user's explicit decision. I recommended porting only `_RISK_RULES` + `classify_risk` (~40
      lines, the only part wwdates uses) and flagged the dead-code cost; the call was to take the
      full file for parity. Recorded here so the choice is not mistaken for an oversight.
- [x] Wired `classify_risk` into `bin/check_backlog_ledger.py`, applied **per path**
      (set-membership) rather than to the whole list.
- [x] Trigger: `src` + `ci` require a ledger; `docs`, `tests`, `deps`, `other` are exempt. No
      opt-out escape hatch — chosen over a `[no-ledger]` flag, which erodes once habitual.
- [x] Bot exemption on the **existence** half only, keyed on the PR **author**
      (`LEDGER_PR_AUTHOR`), never `GITHUB_ACTOR`.
- [x] Diff-based, not per-commit: merge-base with `main`, `--cached`.
- [x] `always_run: true` + `pass_filenames: false` on the pre-commit hook.
- [x] CI step `Run Work-Ledger Enforcement` for gate parity, plus `fetch-depth: 0` on checkout.
- [x] 20 new unit tests (35 total in the file), including the mandatory should-fail case.

## Verification

- [x] Classifier smoke-checked against 10 representative paths — all 10 land in the expected class.
- [x] `poetry run pytest tests/unit/` — see the PR body for the count.
- [x] **The should-fail case, asserted on the message, not just the exit code**: a diff touching
      `src/wwdates/us/federal_holidays.py` with no ledger produces the "adds no … work ledger"
      error. Per `every-gate-needs-a-should-fail-test`, a gate is only proven by a case that fails.
- [x] **Per-path regression pinned**: the test asserts
      `classify_risk(["bin/lint_yaml.sh", "tests/unit/test_x.py"]) == "tests"` *and* that
      `requires_ledger` on the same list is `True` — so if someone "simplifies" it to the
      whole-list call, the test names exactly what broke.
- [x] This branch is its own live case: it touches `bin/` and `.github/` (both `ci`), so the gate
      demands this file. Verified by running the real hook, not just the function.

## Deferred (tracked here, not in this PR)

- **`bin/pr_gate.py`'s `main()` is dead code here** — no workflow invokes it, and it raises
  `KeyError` on `PR_NUMBER` outside a CI PR context, so it fails safe. A prominent status block at
  the top of the module records this, along with the statements in its prose that are true of
  `filings-cvm` and **false here** (no auto-merge, no `pr-quality-gate` ruleset, no `risk:*`
  labels, no `bin/enable_repo_rules.sh`, English docs not pt-BR). Left in place per the verbatim-port
  decision; **do not wire it up** without reading that block.
- Adopting the rest of the gate (auto-merge, labels, size buckets) would need the repo settings and
  ruleset it depends on. Not in scope, and not currently wanted.

## Not done, on purpose

- **No `[no-ledger]` opt-out.** Considered as the answer to #15's "trivial fix branches" worry and
  rejected: the trivial case #15 actually meant is docs/tests-only, which the `src`/`ci` trigger
  already exempts (PR #28, a one-line docs fix, needed no ledger). A general escape hatch would be
  reached for habitually and would void the gate — the same dynamic as blanket `--no-verify`.
- **`src`-only trigger** (dropping `ci`) — rejected: CI changes are exactly the ones whose reasoning
  is invisible in the diff, and dropping them would fork the rule away from both sibling repos.
