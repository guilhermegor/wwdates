# Ledger — #39 release-workflow-lock

Branch: `fix/39-release-workflow-lock` · Issue: #39 · Class: **ci** (no `src/` diff → no release)

## Goal

Apply #19's `tests.yaml` fix to both release workflows, **remove the silent lock regeneration**, and
close the one thing left unproven about the ledger gate's bot exemption.

## Work

### The release workflows

Both `release_pypi.yaml` and `release_test_pypi.yaml` carried **all three** of #19's defects plus a
fourth unique to them:

- [x] Cache key → `hashFiles('poetry.lock', 'pyproject.toml')` (was manifest-only, so every
      lock-only change was a cache hit and the release built against a stale `.venv`).
- [x] Cache `path:` → `.venv` only (was also caching `poetry.lock`, so a restored cache could
      **overwrite the committed lockfile** before anything validated it).
- [x] `poetry check --lock` promoted to its own **unconditional** step, before the cache restore
      (inside the guarded step it never ran on a warm cache).
- [x] **Deleted the `rm -f poetry.lock; poetry lock --no-cache` fallback** — the exact inverse of
      `ci-lock-fail-loud-not-regenerate`, and worst of all in the release path: the lock governs the
      **build environment**, including `poetry-dynamic-versioning`, the plugin that stamps the
      version. Re-resolving it means publishing a wheel built with a toolchain nobody tested, and a
      published version cannot be un-published.
- [x] Removed the dead win32 transform (`pywin32` is not declared here — see #33), including the
      now-orphaned `mv pyproject.original.toml pyproject.toml` restore.
- [x] Kept the two files' install blocks **identical**, since a rehearsal only rehearses the steps
      the two workflows share.

### The bot exemption (correcting my own caveat)

- [x] **My caveat on #32 was over-cautious.** I recorded the ci/src case as "still unproven" because
      the observed Dependabot PRs touched only `poetry.lock` (class `deps`, exempt by path anyway).
      But the exemption is an early `sys.exit(0)` at `__main__` **before any path classification** —
      paths are never consulted on that branch. #25's log line therefore already proved the
      behaviour for every path class.
- [x] What was genuinely missing was a test **pinning that ordering**: nothing stopped someone
      moving the bot check after the path check, which would break the exemption for exactly the
      ci/src case. Added `tests/integration/test_ledger_gate_cli.py` — 5 tests driving the **real
      CLI** in a throwaway git repo, so the env wiring (`LEDGER_PR_AUTHOR` / `LEDGER_BASE_REF`) is
      exercised rather than assumed.

### The gate's own diagnostic, fixed because it misled me

- [x] Writing this very ledger, I used `## Work — the release workflows`. The gate correctly
      rejected it but reported **"missing the `## Work` section"** — while the section was plainly
      on the page. That sends the reader hunting for the wrong problem; it cost a debug cycle here
      and had already cost one on the #26 ledger.
- [x] The check now detects the near-miss and says what is actually wrong:
      *"the heading `## Work — the release workflows` must be exactly `## Work` — move the qualifier
      into a `###` subsection below it."* Two tests cover it, including one asserting the plain
      "missing" case is **not** swallowed by the new branch.

## Verification

- [x] `poetry check --lock` → exit 0 on `main` **before** making the gate blocking, so the stricter
      gate cannot red a legitimate release.
- [x] `poetry run pytest tests/` → **369 passed** (360 + 4 new + a 2-case parametrise).
- [x] `ruff check` / `ruff format --check` / `yamllint` clean; both workflows parse as valid YAML.
- [x] **Mutation-tested the new tests** — each mutation caught by exactly the right test:

  | Mutation | Result |
  |---|---|
  | disable the bot exemption | the 2 exemption cases **and** the ordering test fail |
  | let path work run *before* the exemption | **only** the ordering test fails |

  Source restored afterwards; `git diff` clean, 5/5 green again.
- [ ] Next real release: confirm the promoted lock gate runs and the build still succeeds. This
      PR cannot exercise the release workflows — that is the point of the deferral note below.

## Deferred (tracked here, not in this PR)

- **The `dev`/`docs` group-exclusion logic in both release workflows is dead, and I left it alone.**
  It greps `[tool.poetry.group.dev]` while `pyproject.toml` declares
  `[tool.poetry.group.dev.dependencies]`, so the pattern never matches and the release always
  installs everything. I nearly "fixed" the grep, then checked what is inside the dev group:
  `build` (line 70) and `twine` (71). Fixing it would make `--without dev` strip them.
  **It would probably still work** — `Build Package` runs `python -m pip install --upgrade build`
  (self-installing) and publishing uses `pypa/gh-action-pypi-publish` via OIDC rather than twine —
  but "probably" is not a good enough basis for a change to the least-rehearsed code in the repo,
  and the only real cost today is wasted install time. Needs its own issue and its own release to
  verify.

## Not done, on purpose

- **No version bump.** Class `ci`: nothing under `src/`, so the wheel is byte-identical to 2.0.0.
  Publishing 2.0.1 for this would be the "minor-bump every merge" habit `s:release` exists to
  prevent, and it cannot be un-published.
- **Did not wait for a real Dependabot `ci` PR** to prove the exemption. That would have meant
  waiting a week for the next `github-actions` bump to confirm something the code order already
  guarantees; the integration test proves it deterministically and keeps proving it.
