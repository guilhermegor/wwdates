"""Unit tests for the backlog-ledger shape gate.

``check`` takes its reader as an argument, so every case here runs on in-memory text with no
filesystem and no git working tree.
"""

from __future__ import annotations

from collections.abc import Callable
import importlib.util
import pathlib
import sys
from types import ModuleType

import pytest


def _load_checker() -> ModuleType:
	"""Import ``bin/check_backlog_ledger.py``, which is a script rather than a package module.

	Returns
	-------
	ModuleType
		The loaded module.
	"""
	path_script = pathlib.Path(__file__).resolve().parents[2] / "bin" / "check_backlog_ledger.py"
	cls_spec = importlib.util.spec_from_file_location("check_backlog_ledger", path_script)
	assert cls_spec is not None and cls_spec.loader is not None
	cls_module = importlib.util.module_from_spec(cls_spec)
	sys.modules["check_backlog_ledger"] = cls_module
	cls_spec.loader.exec_module(cls_module)
	return cls_module


checker = _load_checker()

VALID_PATH = "docs/backlog/dependabot-config_20260801_121652.md"

VALID_LEDGER = """# Ledger — #13 dependabot-config

Branch: `chore/13-dependabot-config` · Issue: #13 · Class: **ci** (no `src/` diff → no release)

## Goal

Give the repo dependency automation it currently lacks.

## Work

- [x] Added `.github/dependabot.yml`.
- [ ] Verify the first grouped PR.

## Deferred (tracked here, not in this PR)

- Nothing.
"""


def _reader(dict_files: dict[str, str]) -> Callable[[str], str | None]:
	"""Build a ``read_text`` callable over an in-memory file map.

	Parameters
	----------
	dict_files : dict[str, str]
		Maps path to text; a missing key reads as ``None``.

	Returns
	-------
	callable
		A function suitable as ``check``'s ``read_text`` argument.
	"""

	def read_text(str_path: str) -> str | None:
		"""Return the mapped text, or ``None`` when the path is absent.

		Parameters
		----------
		str_path : str
			Path to read.

		Returns
		-------
		str or None
			The text, or ``None``.
		"""
		return dict_files.get(str_path)

	return read_text


def test_a_conforming_ledger_reports_no_errors() -> None:
	"""The shape the repo's own ledgers use must pass."""
	assert checker.check([VALID_PATH], _reader({VALID_PATH: VALID_LEDGER})) == []


def test_filename_must_be_timestamped() -> None:
	"""A ledger without the ``_YYYYMMDD_HHMMSS`` stamp is rejected."""
	str_path = "docs/backlog/dependabot-config.md"
	list_errors = checker.check([str_path], _reader({str_path: VALID_LEDGER}))

	assert any("filename must match" in e for e in list_errors)


def test_heading_must_use_the_ledger_form() -> None:
	"""The old ``# Work ledger — branch`` shape is rejected."""
	str_text = VALID_LEDGER.replace(
		"# Ledger — #13 dependabot-config", "# Work ledger — `chore/13`"
	)
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("first heading must be" in e for e in list_errors)


def test_metadata_line_is_required() -> None:
	"""Dropping the ``Branch: … · Issue: … · Class: …`` line is an error."""
	str_text = "\n".join(
		line for line in VALID_LEDGER.splitlines() if not line.startswith("Branch:")
	)
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("missing the metadata line" in e for e in list_errors)


def test_class_must_be_one_of_the_known_values() -> None:
	"""An invented class such as ``**feature**`` does not satisfy the metadata line."""
	str_text = VALID_LEDGER.replace("Class: **ci**", "Class: **feature**")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("missing the metadata line" in e for e in list_errors)


def test_issue_number_must_agree_between_heading_and_metadata() -> None:
	"""A heading and metadata line naming different issues is a real inconsistency."""
	str_text = VALID_LEDGER.replace("Issue: #13", "Issue: #14")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("but the metadata line says" in e for e in list_errors)


def test_slug_must_agree_with_the_filename() -> None:
	"""A heading slug that drifted from the filename topic is caught."""
	str_text = VALID_LEDGER.replace("#13 dependabot-config", "#13 something-else")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("does not match the filename topic" in e for e in list_errors)


@pytest.mark.parametrize("str_section", ["## Goal", "## Work"])
def test_required_sections_are_enforced(str_section: str) -> None:
	"""Both mandatory sections are checked.

	Parameters
	----------
	str_section : str
		The heading removed from an otherwise valid ledger.
	"""
	str_text = VALID_LEDGER.replace(str_section + "\n", "")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any(f"missing the `{str_section}` section" in e for e in list_errors)


def test_work_items_must_be_checkboxes() -> None:
	"""Bare ``-`` bullets under ``## Work`` are rejected."""
	str_text = VALID_LEDGER.replace("- [x] Added", "- Added").replace("- [ ] Verify", "- Verify")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("no `- [ ]`/`- [x]` checkbox item" in e for e in list_errors)


def test_a_checkbox_outside_the_work_section_does_not_satisfy_the_rule() -> None:
	"""The checkbox must be in ``## Work``, not merely somewhere in the file.

	Guards the difference between this gate and a naive whole-file search.
	"""
	str_text = VALID_LEDGER.replace("- [x] Added `.github/dependabot.yml`.\n", "").replace(
		"- [ ] Verify the first grouped PR.\n", ""
	)
	str_text = str_text.replace("- Nothing.", "- [x] Nothing.")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("no `- [ ]`/`- [x]` checkbox item" in e for e in list_errors)


def test_non_ledger_paths_are_ignored() -> None:
	"""The gate judges ledgers only, so it can be handed a broad file list."""
	dict_files = {"src/wwdates/main.py": "print('x')", "README.md": "# readme"}

	assert checker.check(list(dict_files), _reader(dict_files)) == []


def test_a_deleted_ledger_is_not_an_error() -> None:
	"""A path whose file is gone has no content to judge."""
	assert checker.check([VALID_PATH], _reader({})) == []


def test_absolute_paths_are_still_checked() -> None:
	"""Regression: a prefix match on ``docs/backlog/`` silently skips absolute paths.

	That turned the whole gate into a no-op — it reported success because it examined
	nothing. Caught by a negative test during implementation.
	"""
	str_path = "/home/user/repo/docs/backlog/bad-name.md"
	list_errors = checker.check([str_path], _reader({str_path: VALID_LEDGER}))

	assert any("filename must match" in e for e in list_errors)


def test_is_ledger_path_rejects_a_lookalike_directory() -> None:
	"""``docs/backlog`` must be the file's own parent, not merely part of the path."""
	assert checker.is_ledger_path("docs/backlog/x_20260101_010101.md") is True
	assert checker.is_ledger_path("docs/backlog/nested/x_20260101_010101.md") is False
	assert checker.is_ledger_path("docs/backlog/notes.txt") is False


# --------------------------------------------------------------------------------------------
# Existence half (issue #26). `check` takes the path list, so these run with no git working tree.
# --------------------------------------------------------------------------------------------


def test_src_diff_without_a_ledger_is_an_error() -> None:
	"""THE should-fail case: touching shipped source with no ledger must fail, by message.

	This is the whole point of the existence half. If this test ever passes trivially, the gate
	has become a no-op (see the `every-gate-needs-a-should-fail-test` lesson).
	"""
	list_paths = ["src/wwdates/us/federal_holidays.py"]
	list_errors = checker.check(list_paths, _reader({}), bool_require_existence=True)

	assert any("adds no" in e and "work ledger" in e for e in list_errors)


def test_src_diff_with_a_ledger_is_clean() -> None:
	"""The same diff satisfies the rule once a ledger rides along."""
	list_paths = ["src/wwdates/us/federal_holidays.py", VALID_PATH]

	list_errors = checker.check(
		list_paths, _reader({VALID_PATH: VALID_LEDGER}), bool_require_existence=True
	)

	assert list_errors == []


def test_ci_diff_without_a_ledger_is_an_error() -> None:
	"""A workflow change is `ci`, which also owes a ledger."""
	list_errors = checker.check(
		[".github/workflows/tests.yaml"], _reader({}), bool_require_existence=True
	)

	assert any("work ledger" in e for e in list_errors)


@pytest.mark.parametrize(
	"str_path",
	["docs/usage.md", "README.md", "tests/unit/test_x.py", "poetry.lock", "pyproject.toml"],
)
def test_exempt_classes_never_demand_a_ledger(str_path: str) -> None:
	"""Docs / tests / deps stay free — the trivial-branch case #15 actually cared about.

	PR #28 (a one-line docs fix) is the live example: it needed no ledger.

	Parameters
	----------
	str_path : str
		A changed path whose class is exempt.
	"""
	assert checker.check([str_path], _reader({}), bool_require_existence=True) == []


def test_a_ci_path_beside_a_tests_path_still_demands_a_ledger() -> None:
	"""Regression for the per-path design.

	`classify_risk` on the WHOLE list returns only the most-dangerous class and ranks `tests`
	above `ci`, so this diff collapses to `tests` and would escape. Asking per path keeps it
	honest — verified here against the collapsing call itself.
	"""
	list_paths = ["bin/lint_yaml.sh", "tests/unit/test_x.py"]

	assert checker.pr_gate.classify_risk(list_paths) == "tests"
	assert checker.requires_ledger(list_paths) is True
	assert checker.check(list_paths, _reader({}), bool_require_existence=True) != []


def test_existence_is_off_by_default() -> None:
	"""An explicit ad-hoc run stays shape-only, so it never demands a branch context."""
	assert checker.check(["src/wwdates/main.py"], _reader({})) == []


def test_a_ledger_alone_satisfies_nothing_but_also_demands_nothing() -> None:
	"""A ledger-only diff is `docs`, so it is exempt — and its shape is still checked."""
	list_errors = checker.check(
		[VALID_PATH], _reader({VALID_PATH: VALID_LEDGER}), bool_require_existence=True
	)

	assert list_errors == []


def test_shape_errors_still_surface_alongside_the_existence_check() -> None:
	"""Both halves report together — a malformed ledger is not masked by a satisfied existence."""
	str_bad = VALID_LEDGER.replace("## Goal\n", "")
	list_paths = ["src/wwdates/main.py", VALID_PATH]
	list_errors = checker.check(
		list_paths, _reader({VALID_PATH: str_bad}), bool_require_existence=True
	)

	assert any("missing the `## Goal` section" in e for e in list_errors)


@pytest.mark.parametrize(
	("str_actor", "bool_expected"),
	[
		("dependabot[bot]", True),
		("github-actions[bot]", True),
		("DependaBot[Bot]", True),
		("guilhermegor", False),
		("", False),
		(None, False),
	],
)
def test_is_bot_actor(str_actor: str | None, bool_expected: bool) -> None:
	"""The `[bot]` suffix is the whole test — no allow-list to go stale.

	`None`/empty is deliberately NOT a bot: a local run must still satisfy the rule.

	Parameters
	----------
	str_actor : str or None
		The acting user.
	bool_expected : bool
		Whether it should be treated as a bot.
	"""
	assert checker.is_bot_actor(str_actor) is bool_expected


def test_ledger_author_prefers_the_pr_author_over_the_run_actor(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""GITHUB_ACTOR becomes whoever re-ran the job, which would cancel a bot's exemption.

	Parameters
	----------
	monkeypatch : pytest.MonkeyPatch
		Fixture used to set the environment.
	"""
	monkeypatch.setenv("GITHUB_ACTOR", "guilhermegor")
	monkeypatch.setenv("LEDGER_PR_AUTHOR", "dependabot[bot]")

	assert checker._ledger_author() == "dependabot[bot]"
	assert checker.is_bot_actor(checker._ledger_author()) is True


def test_ledger_author_falls_back_to_the_actor_when_there_is_no_pr(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""No PR payload (a push, a local run) -> the actor is the right answer, and it is human.

	Parameters
	----------
	monkeypatch : pytest.MonkeyPatch
		Fixture used to set the environment.
	"""
	monkeypatch.delenv("LEDGER_PR_AUTHOR", raising=False)
	monkeypatch.setenv("GITHUB_ACTOR", "guilhermegor")

	assert checker._ledger_author() == "guilhermegor"
	assert checker.is_bot_actor(checker._ledger_author()) is False


def test_a_heading_with_a_trailing_qualifier_says_so_instead_of_missing() -> None:
	"""`## Work — suffix` must be reported as a wrong heading, not as a missing section.

	Reporting "missing" for a heading that is visibly on the page sends the reader hunting for the
	wrong problem — measured twice while authoring ledgers for this very gate.
	"""
	str_text = VALID_LEDGER.replace("## Work\n", "## Work — the release workflows\n")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("must be exactly" in e and "## Work" in e for e in list_errors)
	assert not any("missing the `## Work` section" in e for e in list_errors)


def test_a_genuinely_absent_section_still_says_missing() -> None:
	"""The near-miss hint must not swallow the plain case."""
	str_text = VALID_LEDGER.replace("## Goal\n", "")
	list_errors = checker.check([VALID_PATH], _reader({VALID_PATH: str_text}))

	assert any("missing the `## Goal` section" in e for e in list_errors)
