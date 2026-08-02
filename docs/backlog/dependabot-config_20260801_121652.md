# Ledger — #13 dependabot-config

Branch: `chore/13-dependabot-config` · Issue: #13 · Class: **ci** (no `src/` diff → no release)

## Goal

Give the repo dependency automation it currently lacks — there is no `.github/dependabot.yml`.
Both `filings-cvm` and `filings-b3` already converged on one tested configuration; porting it
yields grouped, predictable PRs instead of manual bumps nobody remembers.

## Work

- [x] `.github/dependabot.yml`, ported from `filings-cvm/.github/dependabot.yml`:
      - `pip` / `/` / weekly · `versioning-strategy: lockfile-only` (this repo commits
        `poetry.lock` and CI refuses to re-lock) · group `python-minor-patch` (`*`, minor+patch) ·
        `ignore` pandas major bumps · `open-pull-requests-limit: 5` ·
        `commit-message.prefix: chore(deps)`.
      - `github-actions` / `/` / weekly · group `github-actions` (`*`) ·
        `commit-message.prefix: chore(ci)`.
- [x] **No `labels:` key** — Dependabot posts an error comment when a referenced label does not
      exist (the reason filings-cvm dropped it; see its PR #79/#80). The rationale comment was
      adapted, not copied: filings-cvm keys auto-merge off `bin/pr_gate.py` path labels, a script
      wwdates does not have, so here the only reason is Dependabot's missing-label error.
- [x] Carry over the explanatory header comments verbatim in spirit — they are why the settings
      survive review instead of being "simplified" away later.
- [x] Check the version floors first. **The plan's premise was wrong**: `pyproject.toml` declares
      `python = ">=3.10,<4.0"`, so **3.10 is the floor a grouped bump must not break**, not 3.9.
      `tests.yaml`'s matrix still lists `"3.9"` — see "Deferred" below.
- [ ] Verify: Dependabot parsed the file (repo → Insights → Dependency graph → Dependabot), and
      the first PR it opens is grouped and carries the `chore(deps)` / `chore(ci)` prefix.
      *(Post-merge — Dependabot only reads the file from the default branch.)*

## Also fixed here — `tests.yaml` could not have gated a single Dependabot PR

The floor check above pulled a thread that ended in a CI cache bug. **In scope, not deferred**:
`tests.yaml` is the gate this whole config depends on, and as written it was incapable of
reporting on a Dependabot PR at all. Shipping the config without this would have shipped a no-op.

### 1. The matrix lied about the floor

`["3.9", "3.10", "3.11", "3.12", "3.13"]` while `pyproject.toml` requires `>=3.10`. Now
`["3.10", "3.11", "3.12", "3.13", "3.14"]`, matching `filings-cvm`.

- `requirements.txt` (`poetry>=2.4 ; python_full_version >= "3.10"`) has no upper bound, so 3.14
  installs Poetry fine. Nothing else pins an upper Python bound.
- `classifiers` only claim `Programming Language :: Python :: 3` — no per-version claim to keep
  in sync, so they were left alone.

### 2. Why the below-floor 3.9 legs reported `success`

Verified, not guessed: on run 30725490428, **`Install Dependencies` is `skipped` on all 15 jobs**
— every leg hit the venv cache. The 3.9 legs never re-resolved the project, so nothing ever
raised the floor violation. Three coupled defects, all present in `filings-cvm` too (so this is a
template defect, not a wwdates one):

- **The cache key hashed only `pyproject.toml`.** A `poetry.lock`-only change was therefore always
  a cache hit — and `versioning-strategy: lockfile-only` produces *exactly* lock-only diffs. Every
  Dependabot PR would have restored a stale `.venv`, skipped the install, and gone green while
  testing the pre-bump dependency set. Fixed: `hashFiles('poetry.lock', 'pyproject.toml')`.
- **`poetry.lock` was in the cache `path:`.** A restored cache overwrites the repo's committed
  lockfile, so `poetry check --lock` was validating a cache artifact rather than the tree. Fixed:
  `path: .venv` only — cache build outputs, never tracked source.
- **`poetry check --lock` lived inside the cache-guarded step**, so the fail-loud lock-sync gate
  never ran on a warm cache — disabled by the very condition that makes it cheap. Fixed: promoted
  to its own unconditional step, before the cache restore. Verified locally: `poetry check --lock`
  exits 0 against the unmodified `pyproject.toml`.

Moving the check before the win32-stripping transform also makes it check what a developer checks
locally, rather than a rewritten `pyproject.toml`.

## Deferred (tracked here, not in this PR)

- **The win32-stripping `python -c` transform in `Install Dependencies` is dead code here** —
  wwdates has no `pywin32` dependency (`grep` finds zero matches in `pyproject.toml`), so the
  transform is a template leftover that copies, rewrites and restores `pyproject.toml` to no
  effect. Deleting it is a separate simplification, not a dependency-automation change.
- **`actions/cache@v3`** is two majors behind (`filings-cvm` is on `@v6`). Left alone on purpose:
  the `github-actions` group added in this PR is exactly what should propose that bump, and
  letting it do so is the first end-to-end proof the config works.

## Not done, on purpose

- Auto-merge for grouped patch PRs. Worth considering once the first few land and the grouping
  proves stable — not before there is any evidence about PR volume.
