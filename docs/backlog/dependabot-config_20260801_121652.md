# Ledger — #13 dependabot-config

Branch: `chore/13-dependabot-config` · Issue: #13 · Class: **ci** (no `src/` diff → no release)

## Goal

Give the repo dependency automation it currently lacks — there is no `.github/dependabot.yml`.
Both `filings-cvm` and `filings-b3` already converged on one tested configuration; porting it
yields grouped, predictable PRs instead of manual bumps nobody remembers.

## Work

- [ ] `.github/dependabot.yml`, ported from `filings-cvm/.github/dependabot.yml`:
      - `pip` / `/` / weekly · `versioning-strategy: lockfile-only` (this repo commits
        `poetry.lock` and CI refuses to re-lock) · group `python-minor-patch` (`*`, minor+patch) ·
        `ignore` pandas major bumps · `open-pull-requests-limit: 5` ·
        `commit-message.prefix: chore(deps)`.
      - `github-actions` / `/` / weekly · group `github-actions` (`*`) ·
        `commit-message.prefix: chore(ci)`.
- [ ] **No `labels:` key** — Dependabot posts an error comment when a referenced label does not
      exist (the reason filings-cvm dropped it; see its PR #79/#80).
- [ ] Carry over the explanatory header comments verbatim in spirit — they are why the settings
      survive review instead of being "simplified" away later.
- [ ] Check the version floors first: `tests.yaml` runs a 3.9→3.13 × 3-OS matrix, so a grouped
      minor bump must not silently drop 3.9 support. Record the constraint here once confirmed.
- [ ] Verify: Dependabot parsed the file (repo → Insights → Dependency graph → Dependabot), and
      the first PR it opens is grouped and carries the `chore(deps)` / `chore(ci)` prefix.

## Deferred (tracked here, not in this PR)

- Nothing.

## Not done, on purpose

- Auto-merge for grouped patch PRs. Worth considering once the first few land and the grouping
  proves stable — not before there is any evidence about PR volume.
