#!/usr/bin/env python
"""Enforce one shape for ``docs/backlog/`` work ledgers, deterministically.

Every non-trivial branch keeps a ledger at
``docs/backlog/<kebab-topic>_YYYYMMDD_HHMMSS.md`` (timestamped at creation, never renamed).
The shape is fixed so a ledger stays scannable across branches and sessions::

    # Ledger — #<issue> <slug>

    Branch: `<branch>` · Issue: #<issue> · Class: **<src|ci|docs>**

    ## Goal
    ## Work        (at least one `- [ ]` / `- [x]` checkbox)
    ## Deferred (tracked here, not in this PR)     (optional)
    ## Not done, on purpose                        (optional)

**This gate checks the shape of the ledgers it is given — it never demands that a ledger
exist.** That is a deliberate divergence from ``filings-cvm``'s port of this script, which
derives a mandatory-ledger rule from ``bin/pr_gate.py``'s path-risk classes. wwdates has no
``pr_gate.py``, and issue #15 explicitly rejected mandatory existence ("making one mandatory
would block trivial fix branches for no gain"). Dropping that half removes the only dependency
and the whole git-diff machinery: pre-commit already passes the changed ledger paths in argv.

Failures (each a hard error, exit 1):

- the filename does not match ``<kebab-topic>_YYYYMMDD_HHMMSS.md``;
- the H1 is not ``# Ledger — #<issue> <slug>``;
- no ``Branch: … · Issue: #<n> · Class: **<src|ci|docs>**`` metadata line;
- the H1's issue number disagrees with the metadata line's;
- the H1's slug disagrees with the filename's topic;
- ``## Goal`` or ``## Work`` is missing;
- ``## Work`` carries no ``- [ ]`` / ``- [x]`` checkbox item.
"""

from __future__ import annotations

from collections.abc import Callable
import pathlib
import re
import sys


# ``<kebab-topic>_YYYYMMDD_HHMMSS.md`` — kebab topic (no underscores of its own), then an
# 8-digit date and a 6-digit time. Fixed at creation, never renamed.
_NAME_RE = re.compile(r"^(?P<slug>[a-z0-9-]+)_\d{8}_\d{6}\.md$")

# ``# Ledger — #13 dependabot-config``. The separator is an em dash, matching every existing
# ledger; a hyphen here is a real difference and is meant to fail.
_H1_RE = re.compile(r"^#\s+Ledger\s+—\s+#(?P<issue>\d+)\s+(?P<slug>[a-z0-9-]+)\s*$", re.MULTILINE)

# ``Branch: `x` · Issue: #13 · Class: **ci** (trailing prose allowed)``. Separated by the middle
# dot the existing ledgers use. Trailing commentary after the class is free-form on purpose.
_META_RE = re.compile(
	r"^Branch:\s*.+?·\s*Issue:\s*#(?P<issue>\d+)\s*·\s*Class:\s*\*\*(?P<cls>src|ci|docs)\*\*",
	re.MULTILINE,
)

# A Markdown task checkbox: ``- [ ]`` open, ``- [x]`` / ``- [X]`` done. A bare ``-`` bullet does
# not count — ledger to-dos must be trackable.
_CHECKBOX_RE = re.compile(r"^\s*[-*] \[[ xX]\]", re.MULTILINE)

# Sections every ledger must carry. `Deferred` / `Not done, on purpose` are optional: a branch
# with nothing deferred should not be forced to write a section saying so.
_REQUIRED_SECTIONS: tuple[str, ...] = ("## Goal", "## Work")

LEDGER_DIR = "docs/backlog"


def is_ledger_path(str_path: str) -> bool:
	"""Say whether a path is a ledger this gate should judge.

	Matches on the parent **directory segment**, not a string prefix. A prefix test
	(``startswith("docs/backlog/")``) silently returns False for an absolute path, which would
	turn the whole gate into a no-op the moment a caller passes one — the failure mode where a
	check reports success because it examined nothing.

	Parameters
	----------
	str_path : str
		A path, absolute or repo-relative.

	Returns
	-------
	bool
		True when the file sits directly in a ``docs/backlog`` directory and ends in ``.md``.
	"""
	cls_path = pathlib.PurePath(str_path)
	if cls_path.suffix != ".md":
		return False
	return cls_path.parent.as_posix().endswith(LEDGER_DIR)


def work_section(str_text: str) -> str:
	"""Return the text of the ``## Work`` section, up to the next H2 (or end of file).

	Parameters
	----------
	str_text : str
		The ledger's full text.

	Returns
	-------
	str
		The section body, or an empty string when ``## Work`` is absent.
	"""
	cls_match = re.search(
		r"^## Work\s*$(?P<body>.*?)(?=^## |\Z)", str_text, re.MULTILINE | re.DOTALL
	)
	return cls_match.group("body") if cls_match else ""


def check_one(str_path: str, str_text: str) -> list[str]:
	"""Return every shape violation in a single ledger (empty list = clean).

	Pure: takes the text rather than reading it, so the rule is unit-testable with no
	filesystem.

	Parameters
	----------
	str_path : str
		Repo-relative path, used for the filename rule and in messages.
	str_text : str
		The ledger's full text.

	Returns
	-------
	list of str
		Human-readable error lines; empty when the ledger satisfies the shape.
	"""
	list_errors: list[str] = []
	str_name = str_path.rsplit("/", 1)[-1]

	cls_name = _NAME_RE.match(str_name)
	if not cls_name:
		list_errors.append(
			f"❌ {str_path}: filename must match <kebab-topic>_YYYYMMDD_HHMMSS.md "
			"(kebab topic, then an 8-digit date and a 6-digit time)."
		)

	cls_h1 = _H1_RE.search(str_text)
	if not cls_h1:
		list_errors.append(
			f"❌ {str_path}: first heading must be `# Ledger — #<issue> <slug>` "
			"(em dash, issue number, then the kebab-case slug)."
		)

	cls_meta = _META_RE.search(str_text)
	if not cls_meta:
		list_errors.append(
			f"❌ {str_path}: missing the metadata line "
			"`Branch: `<branch>` · Issue: #<n> · Class: **<src|ci|docs>**`."
		)

	# Cross-checks only run when both sides parsed — otherwise the errors above already say it.
	if cls_h1 and cls_meta and cls_h1.group("issue") != cls_meta.group("issue"):
		list_errors.append(
			f"❌ {str_path}: heading says issue #{cls_h1.group('issue')} but the metadata line "
			f"says #{cls_meta.group('issue')} — they must agree."
		)
	if cls_h1 and cls_name and cls_h1.group("slug") != cls_name.group("slug"):
		list_errors.append(
			f"❌ {str_path}: heading slug `{cls_h1.group('slug')}` does not match the filename "
			f"topic `{cls_name.group('slug')}` — they must agree."
		)

	for str_section in _REQUIRED_SECTIONS:
		if not re.search(rf"^{re.escape(str_section)}\s*$", str_text, re.MULTILINE):
			list_errors.append(f"❌ {str_path}: missing the `{str_section}` section.")

	if not _CHECKBOX_RE.search(work_section(str_text)):
		list_errors.append(
			f"❌ {str_path}: the `## Work` section has no `- [ ]`/`- [x]` checkbox item — "
			"ledger to-dos must be checkboxes, not bare `-` bullets."
		)

	return list_errors


def check(list_paths: list[str], read_text: Callable[[str], str | None]) -> list[str]:
	"""Return every violation across the given ledgers (empty list = clean).

	Pure: all filesystem access is injected via ``read_text``, so the rule is unit-testable
	without a working tree.

	Parameters
	----------
	list_paths : list of str
		Paths to check, absolute or repo-relative. Anything that is not a ``.md`` file directly
		inside a ``docs/backlog`` directory is ignored, so the hook can be handed a broad file
		list.
	read_text : callable
		Maps a repo-relative path to its text, or ``None`` when the file is absent (e.g. a
		deleted ledger, which has no content to judge).

	Returns
	-------
	list of str
		Human-readable error lines; empty when every ledger satisfies the shape.
	"""
	list_errors: list[str] = []
	for str_path in list_paths:
		if not is_ledger_path(str_path):
			continue
		str_text = read_text(str_path)
		if str_text is None:
			continue
		list_errors.extend(check_one(str_path, str_text))
	return list_errors


def _read_text(str_path: str) -> str | None:
	"""Read a repo-relative file's text, or ``None`` when it does not exist.

	Parameters
	----------
	str_path : str
		Repo-relative path.

	Returns
	-------
	str or None
		The file's text, or ``None`` when absent.
	"""
	cls_path = pathlib.Path(str_path)
	if not cls_path.is_file():
		return None
	return cls_path.read_text(encoding="utf-8")


if __name__ == "__main__":
	list_found = check(sys.argv[1:], _read_text)
	for str_line in list_found:
		print(str_line)
	sys.exit(1 if list_found else 0)
