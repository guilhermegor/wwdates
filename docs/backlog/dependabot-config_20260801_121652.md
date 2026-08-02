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

## Deferred (tracked here, not in this PR)

- **`tests.yaml` advertises a Python version the package rejects.** The matrix runs
  `["3.9", "3.10", ..., "3.13"]` while `pyproject.toml` requires `>=3.10`. The 3.9 jobs report
  `success` (run 30725490428, all 15 green), so the matrix leg is not actually exercising the
  package on 3.9 — either the install silently no-ops or `poetry` resolves a different
  interpreter. Not a dependency-automation bug and out of this PR's scope, but it means CI
  publishes a support claim the metadata contradicts. Needs its own issue.

## Not done, on purpose

- Auto-merge for grouped patch PRs. Worth considering once the first few land and the grouping
  proves stable — not before there is any evidence about PR volume.
