# **Contributing**

Everything you need to develop, test, and release `wwdates`.

> **See also:** [Usage](usage.md) · [API Reference](api.md) · the repository's
> [`CONTRIBUTING.md`](https://github.com/guilhermegor/wwdates/blob/main/CONTRIBUTING.md) holds
> the authoritative branch/PR policy.

---

## Setting up for development

Clone the repo and bootstrap the environment. The project ships both a `Makefile` and a
parallel `tasks.sh`, so use whichever suits your machine — **`make init`**, or **`bash
tasks.sh init`** when `make` is unavailable (e.g. a stock Windows shell).

**With `make` (preferred):**

```bash
git clone https://github.com/guilhermegor/wwdates.git
cd wwdates
make init        # seed .env, create the Poetry venv + install deps, install pre-commit hooks
```

**Without `make`** — the identical steps run through `tasks.sh`:

```bash
bash tasks.sh init
```

`init` composes three steps you can also run individually: `ensure_env` (seed `.env` from
`.env.example`), `venv` (create the Poetry virtualenv and install **all** dependencies,
including the dev tools), and `precommit` (install the git hooks). Poetry is auto-installed if
missing.

Then install the Playwright browser used by the US federal-holidays provider's tests:

```bash
make fix_playwright        # or: bash tasks.sh fix_playwright
```

Every command below also has a `bash tasks.sh <name>` equivalent. Run `make help` (or
`bash tasks.sh help`) to list them all.

---

## Pre-commit hooks

`make init` installs the pre-commit hooks, which run automatically on every `git commit` and
**must pass before a commit is created**. They mirror the CI gate (see below), so a clean
local commit is a clean CI run. Run them on demand:

```bash
poetry run pre-commit run --all-files     # run every hook against the whole tree
```

If a formatting hook (e.g. `ruff format`) rewrites a file, the commit is aborted so you can
review and re-stage the change — that is expected, just `git add` and commit again.

The shell linters (`shellcheck`, `shfmt`) install automatically with the dev dependencies —
no extra step. `make install_shell_linters` exists only as an **optional** fallback for hosts
where the pip-vendored binaries can't execute; you normally never need it.

---

## Running tests

```bash
make unit_tests         # unit tests only
make integration_tests  # integration tests only
make test_cov           # unit tests + coverage report + badge
```

Unit tests mock all network I/O at the boundary (`requests`, Playwright) — they never touch a
real network, DB, or filesystem.

---

## Linting and formatting

```bash
make lint          # ruff check + ruff format + codespell + pydocstyle
```

Ruff config lives in `ruff.toml` (line-length 99, tab indent, double quotes, NumPy
docstrings). Docstring parameter/return types **must match** the type hints textually
(`int | float`, not `Union[int, float]`) — the `check-docstrings` gate enforces this.

---

## Caching internals

Fetched calendars are cached to disk so repeated runs avoid re-downloading. The cache lives at
`~/.cache/wwdates_calendar_cache/` (or `%APPDATA%\wwdates_calendar_cache` on Windows). Every
provider accepts the same cache controls (also documented in the [API Reference](api.md)):

```python
from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3(
    bool_persist_cache=True,        # write cache to disk
    bool_reuse_cache=True,          # reuse in-memory cache within a run
    int_days_cache_expiration=1,    # re-fetch after N days
    int_cache_ttl_days=30,          # prune cache files older than N days
    path_cache_dir=None,            # override the default cache directory
)
```

Pass `bool_persist_cache=False` to run fully in-memory — useful in tests so a run never writes
to the shared cache directory.

---

## Building and verifying the wheel

**Run this before your final commit / opening a PR.** It builds the wheel, installs it into
the Poetry environment, and smoke-imports the package — catching packaging mistakes (a missing
`__init__`, an unshipped `_internal/` subpackage, a broken public import) that source-tree
tests never surface:

```bash
make install_dist_locally     # or: bash tasks.sh install_dist_locally
```

A successful run prints `Package import works` followed by the version. If it fails, the wheel
is broken even when `make unit_tests` is green — fix it before pushing.

---

## Opening a branch and pull request

1. **Branch off the default branch** — `main` is protected, so never commit to it directly.
   Use a descriptive `feat/…`, `fix/…`, `docs/…`, `chore/…` name:

    ```bash
    git checkout -b feat/my-change
    ```

2. **Bump the version** when the change warrants a release
   (`patch` \| `minor` \| `major`):

    ```bash
    make bump_version LEVEL=minor
    ```

3. **Verify locally** before pushing — the same gates CI runs:

    ```bash
    make unit_tests && make lint && make install_dist_locally
    ```

4. **Open the PR.** GitHub pre-fills the
   [pull-request template](https://github.com/guilhermegor/wwdates/blob/main/.github/PULL_REQUEST_TEMPLATE.md);
   fill in every section — **Description** (what / why / how), **Changes Made**
   (added / updated / fixed), **Testing** (manual + automated evidence), **Documentation**, and
   **Reviewer Focus**. Link the issue the work addresses.

### The CI gate — must be green before review

Every push and pull request triggers the **Run Tests** workflow
(`.github/workflows/tests.yaml`). A PR is only considered once **all** of these pass:

| Gate | What it checks |
|------|----------------|
| codespell | Spelling across the repo. |
| docstring consistency | `pydocstyle` (D412/D417) + `check_docstrings.py` — docstring types/raises match the signatures. |
| ruff | Lint + format (`ruff check src/ tests/`). |
| mypy | Static type check (`cd src && mypy .`). |
| shell / sql / yaml lint | Non-Python lint gates (mirrors `make lint`). |
| unit + integration tests | The full pytest suites. |

Because pre-commit mirrors these gates, a commit that passed your local hooks will pass CI.

---

## Publishing to PyPI (maintainers)

Two GitHub Actions workflows handle releases:

- **`release_test_pypi.yaml`** — publish to [Test PyPI](https://test.pypi.org) first.
- **`release_pypi.yaml`** — publish to [PyPI](https://pypi.org) and cut a GitHub release.

Trigger either from the **Actions** tab (`workflow_dispatch`) with the version to release. Both
gate on the new version being greater than the latest already published, build with Poetry, and
upload via [OIDC **trusted publishing**](https://docs.pypi.org/trusted-publishers/) — no API
token is stored in the repo.

Configure once:

- A GitHub **Environment** named `release` (repository settings).
- A **trusted publisher** on each index (PyPI and Test PyPI), matching this repo exactly:
  owner `guilhermegor`, repo `wwdates`, workflow filename `release_pypi.yaml` (and
  `release_test_pypi.yaml` for Test PyPI), environment `release`. On a first-ever release use a
  [**pending publisher**](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
  (register it before the project exists). No `PYPI_TOKEN` / `TEST_PYPI_TOKEN` secret is needed.

Documentation is published separately — every push to `main` runs
`.github/workflows/docs.yaml`, which builds this site and deploys it to GitHub Pages.

## Changelog automation (maintainers)

`CHANGELOG.md` is regenerated on every merge to `main` by `.github/workflows/changelog.yaml`
(runs `cz changelog`, commits the result with `[skip ci]`). Because `main` is **protected**, the
workflow's push must come from an identity allowed to bypass the "require a pull request" rule:

- Create a fine-grained **PAT** with **Contents: write** on this repo and add it as the
  `CHANGELOG_TOKEN` repository secret.
- Add that token's account (or a GitHub App) to the branch-protection **bypass** list.

Without `CHANGELOG_TOKEN` the workflow falls back to `GITHUB_TOKEN`, which can push only if branch
protection permits Actions to do so. Preview locally any time with `make changelog`.
