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

The gate has **two halves**, and they answer different questions:

1. **Shape** — every ledger in the diff must match the template above. Pure, no git needed.
2. **Existence** — a branch whose cumulative diff touches any ``src``/``ci`` path must add or edit
   at least one ledger. ``docs``, ``tests``, ``deps`` and ``other`` are exempt.

**"Non-trivial" is made deterministic by PATH**, reusing ``bin/pr_gate.py``'s ``classify_risk``
rather than re-listing the risk paths here, so the two can never drift on what ``src`` or ``ci``
means — the same axis the sibling repos classify by.

``classify_risk`` is applied **per path** (set-membership), never to the whole list: the
whole-list call collapses a diff to its *single most dangerous* class and ranks ``tests`` above
``ci``, so a branch touching both ``bin/`` and ``tests/`` would collapse to ``tests`` and wrongly
escape the requirement. The question here is "does *any* changed path fall in a ledger class?",
not "what is this diff's worst class".

**History of the existence half (issue #26 reversed issue #15).** #15 shipped shape-only and
recorded, under "Not done, on purpose": *"Requiring a ledger to exist for every branch … would
block trivial fix branches for no gain."* #26 reversed that deliberately, with the trigger
narrowed to ``src``/``ci``: a docs-only or tests-only branch stays free (the trivial case #15
actually cared about — PR #28, a one-line docs fix, needs no ledger), while a change to shipped
code or to the CI that guards it must record its reasoning. A one-line ``src/`` fix **does** now
owe a ledger; that is the accepted cost, chosen over an opt-out flag that erodes once it becomes
habitual.

The check is **diff-based, not per-commit**: a ledger is a per-*branch* artifact, so a later
source-only commit on a branch that already carries one must pass. It compares the branch against
its merge-base with ``main``. On ``main`` itself the merge-base is ``HEAD``, the diff is empty, and
the whole check is a no-op — so it only ever fires on a feature branch, which is where a ledger is
owed.

Failures (each a hard error, exit 1):

- the branch touches a ``src``/``ci`` path but its diff adds no ledger at all;
- the filename does not match ``<kebab-topic>_YYYYMMDD_HHMMSS.md``;
- the H1 is not ``# Ledger — #<issue> <slug>``;
- no ``Branch: … · Issue: #<n> · Class: **<src|ci|docs>**`` metadata line;
- the H1's issue number disagrees with the metadata line's;
- the H1's slug disagrees with the filename's topic;
- ``## Goal`` or ``## Work`` is missing;
- ``## Work`` carries no ``- [ ]`` / ``- [x]`` checkbox item.

Bots are exempt from the **existence** half — see :func:`is_bot_actor`.
"""

from __future__ import annotations

from collections.abc import Callable
import os
import pathlib
import re
import shutil
import subprocess
import sys


# Reuse the PR gate's path->risk classifier instead of re-listing the risk paths here, so the two
# can never drift on what "src" or "ci" means. `bin/` is this file's own directory; put it on the
# path first so the sibling import resolves regardless of the caller's cwd (pre-commit and a manual
# run both invoke this as `python bin/check_backlog_ledger.py`).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pr_gate  # noqa: E402  (deliberate: import follows the sys.path bootstrap above)


# Risk classes whose changes are "non-trivial" enough to demand a work ledger — the same path axis
# `pr_gate` computes: `src` = shipped source, `ci` = bin/CI/workflows/build config. `deps` / `docs`
# / `tests` / `other` are exempt (a lockfile bump, a docs typo, a test-only tweak).
LEDGER_CLASSES: frozenset[str] = frozenset({"src", "ci"})


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
		if re.search(rf"^{re.escape(str_section)}\s*$", str_text, re.MULTILINE):
			continue
		# A required heading carrying a trailing qualifier is the common near-miss, and calling it
		# "missing" is actively misleading, because the section is right there on the page — the
		# reader then goes hunting for a different problem. Name what is actually wrong instead.
		# It is worded this way because the original phrasing cost two real debug cycles.
		cls_near_miss = re.search(rf"^{re.escape(str_section)}\s+\S.*$", str_text, re.MULTILINE)
		if cls_near_miss:
			list_errors.append(
				f"❌ {str_path}: the heading `{cls_near_miss.group(0).strip()}` must be exactly "
				f"`{str_section}` — move the qualifier into a `###` subsection below it."
			)
		else:
			list_errors.append(f"❌ {str_path}: missing the `{str_section}` section.")

	if not _CHECKBOX_RE.search(work_section(str_text)):
		list_errors.append(
			f"❌ {str_path}: the `## Work` section has no `- [ ]`/`- [x]` checkbox item — "
			"ledger to-dos must be checkboxes, not bare `-` bullets."
		)

	return list_errors


def requires_ledger(list_paths: list[str]) -> bool:
	"""Say whether a diff's paths oblige the branch to carry a work ledger.

	Reuses :func:`pr_gate.classify_risk` **per path** (set-membership), not on the whole list: the
	whole-list call returns only the single most-dangerous class and ranks ``tests`` above ``ci``,
	so a branch touching both ``bin/`` and ``tests/`` would collapse to ``tests`` and wrongly
	escape the requirement. Asking each path keeps "any src/ci path present?" honest.

	Parameters
	----------
	list_paths : list of str
		Repo-relative paths in the branch's cumulative diff.

	Returns
	-------
	bool
		True when at least one path classifies as a ledger class (``src`` or ``ci``).
	"""
	return any(pr_gate.classify_risk([str_path]) in LEDGER_CLASSES for str_path in list_paths)


def check(
	list_paths: list[str],
	read_text: Callable[[str], str | None],
	*,
	bool_require_existence: bool = False,
) -> list[str]:
	"""Return every violation across the given paths (empty list = clean).

	Pure: all filesystem and git access is injected via ``read_text`` and the caller's path list,
	so both halves are unit-testable without a working tree.

	Parameters
	----------
	list_paths : list of str
		Paths to check, absolute or repo-relative. For the shape half, anything that is not a
		``.md`` file directly inside a ``docs/backlog`` directory is ignored, so the hook can be
		handed a broad file list. For the existence half, this must be the branch's **cumulative**
		diff — a per-commit list would demand a ledger on every later commit of a branch that
		already carries one.
	read_text : callable
		Maps a repo-relative path to its text, or ``None`` when the file is absent (e.g. a
		deleted ledger, which has no content to judge).
	bool_require_existence : bool, optional
		When True, also require that a ``src``/``ci`` diff carries at least one ledger. Defaults
		to False so an explicit, ad-hoc invocation stays shape-only.

	Returns
	-------
	list of str
		Human-readable error lines; empty when the branch satisfies the rule.
	"""
	list_errors: list[str] = []

	if (
		bool_require_existence
		and requires_ledger(list_paths)
		and not any(is_ledger_path(str_path) for str_path in list_paths)
	):
		list_errors.append(
			"❌ branch touches a src/ci path but its diff adds no "
			"docs/backlog/<kebab-topic>_YYYYMMDD_HHMMSS.md work ledger — a change to shipped "
			"code or to the CI guarding it must record its reasoning (issue #26). Create one, "
			"tracking each to-do as a `- [ ]` box."
		)

	for str_path in list_paths:
		if not is_ledger_path(str_path):
			continue
		str_text = read_text(str_path)
		if str_text is None:
			continue
		list_errors.extend(check_one(str_path, str_text))
	return list_errors


def is_bot_actor(str_actor: str | None) -> bool:
	"""Say whether a branch's author is a bot, and so exempt from the existence rule.

	GitHub names bot actors with a ``[bot]`` suffix — ``dependabot[bot]``,
	``github-actions[bot]``. That suffix is the whole test: it is GitHub's own marker, so no
	allow-list of bot names has to be maintained (and none can go stale).

	⚠️ **Feed this the PR's author, not ``GITHUB_ACTOR``.** ``GITHUB_ACTOR`` names whoever
	*triggered the run*, so the moment a human touches a bot's PR — a manual re-run, a
	maintainer's fixup — it becomes that human and the exemption evaporates, which is exactly when
	it is needed. :func:`_ledger_author` resolves the right value.

	**Why bots are exempt.** A work ledger records a *human's* reasoning — what was done, what is
	still open, why a shortcut was taken. An automated dependency bump has none to record: the
	diff is the entire message and the upstream changelog is the justification. Dependabot's
	``github-actions`` group edits ``.github/`` (risk class ``ci``), so without this exemption
	every one of those PRs would be permanently red — which only teaches people to reach for
	``--no-verify``, a worse habit than the gate prevents.

	The exemption keys on the **author**, never on the path: a *human* branch touching a workflow
	still owes a ledger, and only the actor changes the answer.

	Parameters
	----------
	str_actor : str or None
		The acting user. ``None`` or empty (a local run) is **not** a bot — a developer's machine
		must still satisfy the rule.

	Returns
	-------
	bool
		True when the actor is a GitHub bot.
	"""
	if not str_actor:
		return False
	return str_actor.strip().lower().endswith("[bot]")


def _ledger_author() -> str | None:
	"""Resolve whose branch this is: the PR's author, falling back to the run's actor.

	``LEDGER_PR_AUTHOR`` is supplied by CI from ``github.event.pull_request.user.login`` — the
	PR's **author**, which never changes no matter who re-runs or updates the branch. It is the
	value the bot exemption actually needs.

	``GITHUB_ACTOR`` is the fallback for contexts with no pull-request payload (a push to
	``main``, a local run). There the actor *is* the right answer, and it is a human, so the gate
	applies — which is the safe direction to fall back in.

	Returns
	-------
	str or None
		The PR author when CI provides one, else the triggering actor, else ``None``.
	"""
	return os.environ.get("LEDGER_PR_AUTHOR") or os.environ.get("GITHUB_ACTOR")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
	"""Run a git command with a trusted, constant argv and capture its output.

	Parameters
	----------
	*args : str
		Arguments after the ``git`` executable.

	Returns
	-------
	subprocess.CompletedProcess of str
		The completed process (``check=False``; callers inspect ``returncode``).
	"""
	str_git = shutil.which("git") or "git"
	# Trusted, constant argv, with an absolute git path resolved beforehand — bandit S603.
	return subprocess.run([str_git, *args], capture_output=True, text=True, check=False)  # noqa: S603


def _base_ref() -> str | None:
	"""Resolve the commit to diff the branch against (its merge-base with main).

	Honours a ``LEDGER_BASE_REF`` override first (CI passes the PR's base SHA), then the
	merge-base with ``origin/main`` and finally with ``main``. Returns ``None`` when none
	resolves — e.g. on ``main`` itself, where there is no branch to enforce.

	Returns
	-------
	str or None
		A commit-ish to diff against, or ``None`` when the check should be a no-op.
	"""
	str_override = os.environ.get("LEDGER_BASE_REF")
	if str_override:
		return str_override
	for str_ref in ("origin/main", "main"):
		cls_proc = _git("merge-base", "HEAD", str_ref)
		if cls_proc.returncode == 0 and cls_proc.stdout.strip():
			return cls_proc.stdout.strip()
	return None


def _changed_paths() -> list[str]:
	"""Return the branch's cumulative changed paths (merge-base with main -> the index).

	Diffs the **index** (``--cached``), not the working tree: pre-commit runs against *staged*
	content, and ``git diff`` ignores untracked files — a brand-new ledger not yet staged would
	be invisible, so the gate would demand a ledger that is right there but not added. The index
	holds the branch's earlier commits and the files staged for this commit, so ``--cached``
	captures exactly what the branch is about to contribute.

	Diffing from the merge-base (not two-dot against the branch tip) yields exactly the branch's
	own changes and excludes commits that landed on ``main`` in the meantime, matching three-dot
	semantics without needing them.

	Returns
	-------
	list of str
		Repo-relative changed paths; empty when there is no base to compare against.
	"""
	str_base = _base_ref()
	if str_base is None:
		return []
	cls_proc = _git("diff", "--cached", "--name-only", str_base)
	if cls_proc.returncode != 0:
		return []
	return [line for line in cls_proc.stdout.splitlines() if line]


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
	# Force UTF-8 on the output streams. Windows defaults stdout to cp1252, which cannot encode
	# the status glyphs printed below, so the first write raises UnicodeEncodeError and the gate
	# CRASHES instead of reporting. That is not cosmetic — the pre-commit hook is `always_run`, so
	# no commit could be made at all from a Windows checkout.
	#
	# It stayed invisible because the hook is normally run on Linux, and the CI step that
	# calls this script is Linux-gated. The integration test added in #39 is the first thing
	# that ever ran it on Windows, and all five of its cases failed at once.
	for cls_stream in (sys.stdout, sys.stderr):
		if hasattr(cls_stream, "reconfigure"):
			cls_stream.reconfigure(encoding="utf-8", errors="replace")

	# The bot exemption lives here, in the I/O seam, so `check` stays pure and unit-testable
	# without an environment. See `is_bot_actor` for why bots are exempt, and `_ledger_author` for
	# why the PR's author — not the run's actor — is the value that decides it.
	if is_bot_actor(_ledger_author()):
		print("ℹ️  bot-authored branch — work ledger not required (see is_bot_actor).")
		sys.exit(0)

	# There are two invocation modes, deliberately.
	#
	# With explicit path arguments — a manual run naming one ledger — only the SHAPE is checked,
	# which is handy when there is no branch context. With no arguments, which is how pre-commit
	# and CI call it, the branch's cumulative diff drives BOTH halves.
	#
	# The existence half must NOT work from a handed-in file list. Pre-commit would only ever pass
	# the ledgers that changed, so the one case this exists to catch — a branch carrying no ledger
	# whatsoever — would arrive as nothing to look at, and pass in silence.
	list_argv = sys.argv[1:]
	if list_argv:
		list_found = check(list_argv, _read_text)
	else:
		list_changed = _changed_paths()
		# Say what was examined, ALWAYS. A silent pass is indistinguishable from a gate that looked
		# at nothing, and there are two ways to end up with an empty list that do not mean clean —
		# a base ref that never resolved, such as under a shallow CI clone with no merge-base, and
		# a diff command that failed. Printing the count turns a vacuous pass into a visible one in
		# the CI log. See the `every-gate-needs-a-should-fail-test` lesson.
		if not list_changed:
			print(
				"ℹ️  work ledger: no changed paths resolved against the base — "
				"nothing to check. On a feature branch this means the base ref did not resolve "
				"(a shallow clone has no merge-base; CI needs fetch-depth: 0), NOT that the "
				"branch is clean."
			)
		else:
			print(f"ℹ️  work ledger: examined {len(list_changed)} changed path(s).")
		list_found = check(list_changed, _read_text, bool_require_existence=True)

	for str_line in list_found:
		print(str_line)
	sys.exit(1 if list_found else 0)
