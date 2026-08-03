# Ledger — #30 explicit-release-assets

Branch: `fix/30-explicit-release-assets` · Issue: #30 · Class: **ci** (no `src/` diff → no release)

## Goal

Name the release artifacts explicitly instead of globbing `dist/*`, **before** merging Dependabot's
#23, which bumps `softprops/action-gh-release` from `@v1` to `@v3`.

## Work

- [x] `files: dist/*` → `dist/*.whl` + `dist/*.tar.gz` in `release_pypi.yaml`.
- [x] Comment recording *why*, including that this step exists only in `release_pypi.yaml` so the
      Test PyPI rehearsal cannot catch a regression in it.
- [x] Left `dist/.keep` in place — it keeps the directory tracked, and `install_dist_locally`
      cleans `dist/*` rather than `dist/` precisely to preserve it.

## Why this is urgent rather than tidy-up

`dist/.keep` is tracked and **0 bytes**; GitHub rejects a 0-byte asset. `@v1` tolerated it —
proven by releases 1.0.0 and 1.0.1, both with exactly 2 assets and `draft=false`. **`@v3` uses a
different flow**: it creates the release as a *draft*, uploads, then promotes. A rejected asset
leaves `draft=true`, and **GitHub creates no tag for a draft**.

The failure order is what makes it expensive:

1. the `pypi` job publishes first — the version becomes public and **cannot be un-published**;
2. `Create GitHub Release` fails after that;
3. the run is red, with no tag and a draft release;
4. re-dispatching does **not** recover: the index rejects the duplicate version, so the run reddens
   again and the tag is still missing.

A missing tag is not cosmetic — `poetry-dynamic-versioning` derives the version from it, and the
next release's `git diff <tag>..HEAD` gate uses it as the base.

## Verification

- [x] Confirmed the trap is armed and not hypothetical: `files: dist/*` present at
      `release_pypi.yaml:226`, and `git cat-file -s HEAD:dist/.keep` → **0**.
- [x] Confirmed #23 is the trigger: its diff contains
      `softprops/action-gh-release@v1` → `@v3`.
- [x] Confirmed the rehearsal blind spot: `release_test_pypi.yaml` has no
      `Create GitHub Release` step, so `@v3` would run for the first time ever in production.
- [ ] Next real release: confirm the GitHub release carries exactly the wheel + tarball, is not a
      draft, and the tag exists.

## Deferred (tracked here, not in this PR)

- Nothing.

## Not done, on purpose

- **Did not delete `dist/.keep`.** It is what keeps `dist/` tracked; removing it would break
  `install_dist_locally`'s `rm -rf dist/*` idiom and is a bigger change than naming two globs.
- **Did not hold back #23.** Bumping the actions is wanted; the fix is to make the workflow correct
  under `@v3`, not to pin away from it.
