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
