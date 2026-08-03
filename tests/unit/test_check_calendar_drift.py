"""Unit tests for ``bin/check_calendar_drift.py``.

The drift script is the only thing that re-checks offline↔web calendar parity, since
``tests/conftest.py`` blocks sockets and no test may reach the wire. These tests therefore
exercise the script's **pure** halves — span clamping, the date comparison, the allowlist
rules, and the issue-upsert helpers — against synthetic date sets, with the network guard
fully intact (no ``allow_network`` marker anywhere in this module).

``bin/`` is not an importable package, so the module is loaded by path via ``importlib``
(the convention documented in ``tests/CLAUDE.md`` for ``bin/`` scripts).
"""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


# --------------------------
# Module Utilities
# --------------------------


def _load_drift_module() -> ModuleType:
	"""Load ``bin/check_calendar_drift.py`` by path.

	Returns
	-------
	ModuleType
		The imported module object.
	"""
	path_script = Path(__file__).resolve().parents[2] / "bin" / "check_calendar_drift.py"
	cls_spec = importlib.util.spec_from_file_location("check_calendar_drift", path_script)
	if cls_spec is None or cls_spec.loader is None:  # pragma: no cover - defensive
		raise ImportError(f"cannot load {path_script}")
	cls_module = importlib.util.module_from_spec(cls_spec)
	sys.modules["check_calendar_drift"] = cls_module
	cls_spec.loader.exec_module(cls_module)
	return cls_module


@pytest.fixture(scope="module")
def drift() -> ModuleType:
	"""Provide the loaded drift module.

	Returns
	-------
	ModuleType
		The imported ``check_calendar_drift`` module.
	"""
	return _load_drift_module()


# --------------------------
# Span clamping
# --------------------------


def test_clamp_to_web_span_drops_offline_years_the_web_never_publishes(drift: ModuleType) -> None:
	"""Offline years outside the web side's span are not drift.

	B3 publishes roughly 2021–2026 while the offline class spans 2001–2099; without clamping,
	every unpublished year would be reported as a missing holiday.
	"""
	set_offline = {date(2019, 1, 1), date(2021, 1, 1), date(2026, 1, 1), date(2030, 1, 1)}
	set_web = {date(2021, 1, 1), date(2026, 1, 1)}
	assert drift.clamp_to_web_span(set_offline, set_web) == {date(2021, 1, 1), date(2026, 1, 1)}


def test_clamp_to_web_span_keeps_a_gap_year_inside_the_span(drift: ModuleType) -> None:
	"""A year inside the span with no web dates is kept — that is real drift, not absence."""
	set_offline = {date(2021, 1, 1), date(2023, 9, 7), date(2026, 1, 1)}
	set_web = {date(2021, 1, 1), date(2026, 1, 1)}
	assert date(2023, 9, 7) in drift.clamp_to_web_span(set_offline, set_web)


def test_clamp_to_web_span_returns_nothing_when_the_web_side_is_empty(drift: ModuleType) -> None:
	"""An empty web set has no span, so nothing can be compared against it."""
	assert drift.clamp_to_web_span({date(2021, 1, 1)}, set()) == set()


# --------------------------
# Comparison
# --------------------------


def test_identical_sets_report_no_problems(drift: ModuleType) -> None:
	"""The happy path: the offline default agrees with what the publisher serves."""
	set_dates = {date(2026, 1, 1), date(2026, 4, 21)}
	assert drift.compare_dates("b3", set_dates, set_dates) == []


def test_a_web_only_date_is_reported(drift: ModuleType) -> None:
	"""The publisher closed on a day the offline calendar calls a working day."""
	list_problems = drift.compare_dates(
		"b3", {date(2026, 1, 1)}, {date(2026, 1, 1), date(2026, 11, 20)}
	)
	assert len(list_problems) == 1
	assert "2026-11-20" in list_problems[0]
	assert "b3" in list_problems[0]


def test_an_offline_only_date_is_reported(drift: ModuleType) -> None:
	"""The offline calendar claims a closure the publisher does not list."""
	list_problems = drift.compare_dates(
		"anbima", {date(2026, 1, 1), date(2026, 5, 1)}, {date(2026, 1, 1)}
	)
	assert len(list_problems) == 1
	assert "2026-05-01" in list_problems[0]


def test_both_directions_are_reported_together(drift: ModuleType) -> None:
	"""A set that differs both ways yields one problem per date, not one per direction."""
	list_problems = drift.compare_dates("b3", {date(2026, 5, 1)}, {date(2026, 11, 20)})
	assert len(list_problems) == 2


# --------------------------
# Known-exception rules (seeded from PR #10)
# --------------------------


def test_an_offline_only_weekend_date_is_not_drift_when_the_rule_is_on(drift: ModuleType) -> None:
	"""B3 omits weekend holidays — there is no session to cancel, so it is not drift.

	2026-01-01 is a Thursday; 2026-11-15 is a Sunday.
	"""
	list_problems = drift.compare_dates(
		"b3",
		{date(2026, 1, 1), date(2026, 11, 15)},
		{date(2026, 1, 1)},
		bool_offline_only_weekend_ok=True,
	)
	assert list_problems == []


def test_an_offline_only_weekday_date_is_still_drift_under_the_weekend_rule(
	drift: ModuleType,
) -> None:
	"""The weekend rule must not swallow a genuine weekday divergence.

	2026-05-01 is a Friday, so the weekend allowance does not apply to it.
	"""
	list_problems = drift.compare_dates(
		"b3",
		{date(2026, 1, 1), date(2026, 5, 1)},
		{date(2026, 1, 1)},
		bool_offline_only_weekend_ok=True,
	)
	assert len(list_problems) == 1
	assert "2026-05-01" in list_problems[0]


def test_the_weekend_rule_never_excuses_a_web_only_date(drift: ModuleType) -> None:
	"""A publisher-listed closure on a weekend is still reported.

	The allowance is one-directional by design: it explains dates the *publisher* omits, and
	must not hide something the publisher actually published. 2026-11-15 is a Sunday.
	"""
	list_problems = drift.compare_dates(
		"b3", set(), {date(2026, 11, 15)}, bool_offline_only_weekend_ok=True
	)
	assert len(list_problems) == 1


def test_an_allowlisted_web_only_date_is_not_drift(drift: ModuleType) -> None:
	"""B3's 2021 São Paulo municipal/state closures are scrape-only and expected."""
	list_problems = drift.compare_dates(
		"b3",
		set(),
		{date(2021, 1, 25)},
		frozenset_known_web_only=frozenset({date(2021, 1, 25)}),
	)
	assert list_problems == []


def test_an_allowlisted_offline_only_date_is_not_drift(drift: ModuleType) -> None:
	"""An explicitly excused offline-only date is suppressed."""
	list_problems = drift.compare_dates(
		"b3",
		{date(2026, 12, 24)},
		set(),
		frozenset_known_offline_only=frozenset({date(2026, 12, 24)}),
	)
	assert list_problems == []


def test_the_allowlist_does_not_suppress_the_opposite_direction(drift: ModuleType) -> None:
	"""A date excused as web-only is still drift if it shows up offline-only.

	Widening the allowlist must stay narrow: it excuses one direction on one date.
	"""
	list_problems = drift.compare_dates(
		"b3",
		{date(2021, 1, 25)},
		set(),
		frozenset_known_web_only=frozenset({date(2021, 1, 25)}),
	)
	assert len(list_problems) == 1


# --------------------------
# B3 known-exception builder
# --------------------------


def test_b3_known_web_only_no_longer_excuses_christmas_eve(drift: ModuleType) -> None:
	"""24 December must NOT be excused any more (issue #35).

	The excuse existed only because the offline default omitted the date while B3 publishes it.
	Now that ``bool_add_christmas_eve`` defaults to True, both sides agree and there is nothing to
	excuse — and keeping the excuse would actively **suppress signal**: if B3 ever stopped
	publishing 24 December on a weekday while the offline calendar still added it, that is exactly
	what the job should report.
	"""
	frozenset_excused = drift.b3_known_web_only({date(2024, 1, 1), date(2026, 5, 1)})
	assert date(2024, 12, 24) not in frozenset_excused
	assert date(2026, 12, 24) not in frozenset_excused


def test_b3_known_web_only_excuses_the_2021_sao_paulo_closures(drift: ModuleType) -> None:
	"""B3 observed the São Paulo municipal/state holidays in 2021 and stopped afterwards."""
	frozenset_excused = drift.b3_known_web_only({date(2021, 5, 1)})
	assert date(2021, 1, 25) in frozenset_excused
	assert date(2021, 7, 9) in frozenset_excused


def test_b3_known_web_only_excuses_nothing_else(drift: ModuleType) -> None:
	"""A narrow allowlist is the whole point — anything broader hides real drift."""
	frozenset_excused = drift.b3_known_web_only({date(2021, 5, 1)})
	assert date(2021, 11, 20) not in frozenset_excused
	assert date(2021, 5, 1) not in frozenset_excused


# --------------------------
# Pair registry
# --------------------------


def test_calendar_pairs_covers_the_four_pairs_and_excludes_nasdaq(drift: ModuleType) -> None:
	"""``DatesUSNasdaq`` is web-only — it has no offline twin to diff against."""
	tuple_names = tuple(cls_pair.str_name for cls_pair in drift.calendar_pairs())
	assert tuple_names == ("br.b3", "br.anbima", "br.febraban", "us.federal_holidays")


def test_every_web_side_is_built_with_caching_disabled(drift: ModuleType) -> None:
	"""A drift detector that reads a cache cannot detect drift.

	The ``*Web`` classes default to ``bool_persist_cache=True`` / ``bool_reuse_cache=True`` with
	a one-day expiry, so the sweep would happily diff against a stale copy — and, worse, against
	a *partial* one left behind by an earlier failed fetch, reporting it as drift. Found exactly
	that way: a local run served 2 of 22 US dates from a stale cache and reported 9 false
	positives. Constructing the ``*Web`` classes touches no network, so this is assertable here.
	"""
	for cls_pair in drift.calendar_pairs():
		cls_web = cls_pair.callable_web()
		assert cls_web.cls_cache_manager.bool_persist_cache is False, cls_pair.str_name
		assert cls_web.cls_cache_manager.bool_reuse_cache is False, cls_pair.str_name


# --------------------------
# Sweep behaviour (with fakes — still no network)
# --------------------------


class _FakeCalendar:
	"""Stand-in for a calendar whose ``holidays()`` returns a fixed list."""

	def __init__(self, list_holidays: list[tuple[str, date]]) -> None:
		"""Store the holidays this fake will return.

		Parameters
		----------
		list_holidays : list of tuple
			The ``(name, date)`` pairs to return.
		"""
		self._list_holidays = list_holidays

	def holidays(self) -> list[tuple[str, date]]:
		"""Return the fixed holiday list.

		Returns
		-------
		list of tuple
			The ``(name, date)`` pairs given at construction.
		"""
		return self._list_holidays


def _pair(drift: ModuleType, str_name: str, list_offline: list, list_web: list):  # noqa: ANN202
	"""Build a CalendarPair backed by fakes.

	Parameters
	----------
	drift : ModuleType
		The loaded drift module.
	str_name : str
		Pair label.
	list_offline : list
		Offline ``(name, date)`` pairs.
	list_web : list
		Web ``(name, date)`` pairs.

	Returns
	-------
	CalendarPair
		A pair whose factories return the fakes.
	"""
	return drift.CalendarPair(
		str_name=str_name,
		callable_offline=lambda: _FakeCalendar(list_offline),
		callable_web=lambda: _FakeCalendar(list_web),
	)


def test_check_pair_clamps_the_offline_side_to_the_web_span(drift: ModuleType) -> None:
	"""An offline holiday in a year the source never publishes is not drift."""
	cls_pair = _pair(
		drift,
		"br.b3",
		[("Confraternização", date(2019, 1, 1)), ("Confraternização", date(2026, 1, 1))],
		[("Confraternização", date(2026, 1, 1))],
	)
	assert drift.check_pair(cls_pair) == []


def test_collect_drift_reports_a_pair_that_cannot_be_read_without_calling_it_drift(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""A source being down and a calendar having changed must not look alike."""

	def _explode() -> None:
		raise RuntimeError("B3 timed out")

	cls_broken = drift.CalendarPair(
		str_name="br.b3",
		callable_offline=lambda: _FakeCalendar([]),
		callable_web=_explode,
	)
	monkeypatch.setattr(drift, "calendar_pairs", lambda: (cls_broken,))
	list_problems, list_errors = drift.collect_drift()
	assert list_problems == []
	assert len(list_errors) == 1
	assert "could not check" in list_errors[0]


def test_collect_drift_keeps_sweeping_after_one_pair_fails(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""One flaky publisher must not hide the other three pairs' findings."""

	def _explode() -> None:
		raise RuntimeError("B3 timed out")

	cls_broken = drift.CalendarPair(
		str_name="br.b3",
		callable_offline=lambda: _FakeCalendar([]),
		callable_web=_explode,
	)
	cls_drifting = _pair(drift, "br.anbima", [], [("Novo feriado", date(2026, 11, 20))])
	monkeypatch.setattr(drift, "calendar_pairs", lambda: (cls_broken, cls_drifting))
	list_problems, list_errors = drift.collect_drift()
	assert any("2026-11-20" in str_problem for str_problem in list_problems)
	assert len(list_errors) == 1


# --------------------------
# Issue upsert helpers
# --------------------------


def test_find_open_drift_issue_matches_on_the_hidden_marker(drift: ModuleType) -> None:
	"""The tracking issue is found again by its marker, so the job updates instead of piling up."""
	list_issues = [
		{"number": 41, "body": "some unrelated issue"},
		{"number": 42, "body": f"{drift._ISSUE_MARKER}\n\nprevious run"},
	]
	assert drift.find_open_drift_issue(list_issues) == 42


def test_find_open_drift_issue_returns_none_without_the_marker(drift: ModuleType) -> None:
	"""No marker means no prior tracking issue — a new one must be opened."""
	assert drift.find_open_drift_issue([{"number": 41, "body": "unrelated"}]) is None


def test_find_open_drift_issue_tolerates_a_null_body(drift: ModuleType) -> None:
	"""GitHub returns ``body: null`` for a bodyless issue; that must not raise."""
	assert drift.find_open_drift_issue([{"number": 41, "body": None}]) is None


def test_build_issue_body_carries_the_marker_and_every_problem(drift: ModuleType) -> None:
	"""The body must be self-identifying and must not silently truncate findings."""
	list_problems = ["b3: alpha", "anbima: beta"]
	str_body = drift.build_issue_body(list_problems, [])
	assert drift._ISSUE_MARKER in str_body
	for str_problem in list_problems:
		assert str_problem in str_body


def test_build_issue_body_surfaces_unreadable_sources_when_an_issue_is_opened_anyway(
	drift: ModuleType,
) -> None:
	"""A pair that could not be read is visible in the issue, so partial blindness is not silent.

	Errors never *open* the issue, but when one is opened for real drift they ride along —
	otherwise a reader would take the finding list for a full sweep.
	"""
	str_body = drift.build_issue_body(["b3: alpha"], ["us.federal_holidays: could not check"])
	assert "could not check" in str_body


# --------------------------
# Non-blocking contract
# --------------------------


def test_main_returns_zero_when_drift_is_found(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""Drift is reported as an issue, never as a failed check.

	A red required check cannot distinguish "B3 is down" from "the calendar changed", so the
	script must stay non-blocking. This is the load-bearing test of the whole design.
	"""
	monkeypatch.setattr(drift, "collect_drift", lambda: (["b3: something diverged"], []))
	monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
	assert drift.main() == 0


def test_main_returns_zero_when_there_is_no_drift(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""The clean path also exits 0."""
	monkeypatch.setattr(drift, "collect_drift", lambda: ([], []))
	monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
	assert drift.main() == 0


def test_main_returns_zero_when_a_source_is_unreadable(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""An unreachable publisher is not a failure of this repo."""
	monkeypatch.setattr(drift, "collect_drift", lambda: ([], ["b3: could not check"]))
	monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
	assert drift.main() == 0


def test_main_does_not_touch_the_network_without_a_repo_env(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""Off CI there is no repo to file against, so the upsert must be skipped, not attempted.

	If it were attempted, the autouse socket guard in ``tests/conftest.py`` would raise
	``NetworkAccessError`` and this test would fail — which is exactly the assertion.
	"""
	monkeypatch.setattr(drift, "collect_drift", lambda: (["b3: something diverged"], []))
	monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
	assert drift.main() == 0


# --------------------------
# An outage must not open an issue
# --------------------------


def test_main_does_not_open_an_issue_when_only_sources_were_unreadable(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""An outage must never file a "calendar drift" issue.

	A source being down and a calendar having changed are different events, and the first is
	both common and outside this repo's control. Filing for it is the cry-wolf failure that
	makes a drift job worse than nothing — measured elsewhere at ~122 false positives to 1 real
	finding. Found by the first live run: federalholidays.net timed out and the sweep would have
	opened a drift issue naming no drift at all.
	"""
	list_calls = []
	monkeypatch.setattr(drift, "collect_drift", lambda: ([], ["us: could not check"]))
	monkeypatch.setattr(drift, "upsert_issue", lambda *args: list_calls.append(args))
	monkeypatch.setenv("GITHUB_REPOSITORY", "guilhermegor/wwdates")
	assert drift.main() == 0
	assert list_calls == []


def test_main_opens_an_issue_when_there_is_real_drift(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""The converse of the outage rule — real drift must still be filed."""
	list_calls = []
	monkeypatch.setattr(drift, "collect_drift", lambda: (["b3: diverged"], []))
	monkeypatch.setattr(drift, "upsert_issue", lambda *args: list_calls.append(args))
	monkeypatch.setenv("GITHUB_REPOSITORY", "guilhermegor/wwdates")
	assert drift.main() == 0
	assert len(list_calls) == 1


# --------------------------------------------------------------------------------------------
# upsert_issue — the WRITE half (issue #33).
#
# Every pre-existing test here monkeypatches `upsert_issue` ITSELF, which tests whether `main`
# decides to call it — never what it does. So its body (GET -> PATCH-or-POST) had never executed
# in any test, and never in production either, because there has never been real drift. These
# cases drive it with `_api` stubbed, so nothing touches the network and the conftest socket
# guard stays intact.
# --------------------------------------------------------------------------------------------


def _record_api(list_calls: list[tuple], object_get_result: object) -> object:
	"""Build an ``_api`` stub that records calls and answers the GET with a fixture.

	Parameters
	----------
	list_calls : list of tuple
		Sink receiving ``(method, url, body)`` for every call.
	object_get_result : object
		What the ``GET`` should return (the open-issues list).

	Returns
	-------
	object
		A callable with ``_api``'s signature.
	"""

	def _api(str_method: str, str_url: str, dict_body: dict | None = None) -> object:
		"""Record one call and return the fixture for a GET.

		Parameters
		----------
		str_method : str
			HTTP method.
		str_url : str
			Request URL.
		dict_body : dict, optional
			Request body.

		Returns
		-------
		object
			The GET fixture, or an empty dict for writes.
		"""
		list_calls.append((str_method, str_url, dict_body))
		return object_get_result if str_method == "GET" else {}

	return _api


def test_upsert_issue_opens_one_issue_when_none_exists(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""No open tracker -> exactly one POST carrying title, body and label.

	Parameters
	----------
	drift : ModuleType
		The loaded drift module.
	monkeypatch : pytest.MonkeyPatch
		Fixture used to stub the API seam.
	"""
	list_calls: list[tuple] = []
	monkeypatch.setattr(drift, "_api", _record_api(list_calls, []))

	drift.upsert_issue("https://api.github.com/repos/o/r", ["b3: drifted"], [])

	list_posts = [c for c in list_calls if c[0] == "POST"]
	list_patches = [c for c in list_calls if c[0] == "PATCH"]
	assert len(list_posts) == 1
	assert not list_patches
	assert list_posts[0][1].endswith("/issues")
	assert list_posts[0][2]["title"] == drift._ISSUE_TITLE
	assert list_posts[0][2]["labels"] == [drift._ISSUE_LABEL]
	assert "b3: drifted" in list_posts[0][2]["body"]


def test_upsert_issue_updates_in_place_when_one_exists(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""An existing tracker -> one PATCH to that issue, and NO second issue opened.

	This is the dedupe the ledger flagged as most likely to be wrong: a broken marker match
	would open a fresh issue on every weekly run.

	Parameters
	----------
	drift : ModuleType
		The loaded drift module.
	monkeypatch : pytest.MonkeyPatch
		Fixture used to stub the API seam.
	"""
	list_calls: list[tuple] = []
	list_open = [{"number": 77, "body": f"stale text\n{drift._ISSUE_MARKER}\nmore"}]
	monkeypatch.setattr(drift, "_api", _record_api(list_calls, list_open))

	drift.upsert_issue("https://api.github.com/repos/o/r", ["b3: drifted"], [])

	list_patches = [c for c in list_calls if c[0] == "PATCH"]
	assert len(list_patches) == 1
	assert list_patches[0][1].endswith("/issues/77")
	assert not [c for c in list_calls if c[0] == "POST"]


def test_upsert_issue_queries_only_open_issues_with_the_label(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""The GET must filter by state=open AND the label, or it dedupes against the wrong set.

	Parameters
	----------
	drift : ModuleType
		The loaded drift module.
	monkeypatch : pytest.MonkeyPatch
		Fixture used to stub the API seam.
	"""
	list_calls: list[tuple] = []
	monkeypatch.setattr(drift, "_api", _record_api(list_calls, []))

	drift.upsert_issue("https://api.github.com/repos/o/r", ["b3: drifted"], [])

	str_get_url = next(c[1] for c in list_calls if c[0] == "GET")
	assert "state=open" in str_get_url
	assert f"labels={drift._ISSUE_LABEL}" in str_get_url


def test_upsert_issue_body_carries_the_marker_it_later_matches_on(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""The written body must contain the marker `find_open_drift_issue` searches for.

	Closes the loop between the two halves: if the writer stopped emitting the marker, the
	reader would never find the issue again and would open a duplicate every run — with both
	halves passing their own tests.

	Parameters
	----------
	drift : ModuleType
		The loaded drift module.
	monkeypatch : pytest.MonkeyPatch
		Fixture used to stub the API seam.
	"""
	list_calls: list[tuple] = []
	monkeypatch.setattr(drift, "_api", _record_api(list_calls, []))

	drift.upsert_issue("https://api.github.com/repos/o/r", ["b3: drifted"], ["us: unreachable"])

	str_body = next(c[2]["body"] for c in list_calls if c[0] == "POST")
	assert drift._ISSUE_MARKER in str_body
	assert drift.find_open_drift_issue([{"number": 5, "body": str_body}]) == 5


def test_upsert_issue_surfaces_errors_alongside_problems(
	drift: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
	"""A source that could not be checked must still reach the issue body.

	Parameters
	----------
	drift : ModuleType
		The loaded drift module.
	monkeypatch : pytest.MonkeyPatch
		Fixture used to stub the API seam.
	"""
	list_calls: list[tuple] = []
	monkeypatch.setattr(drift, "_api", _record_api(list_calls, []))

	drift.upsert_issue("https://api.github.com/repos/o/r", ["b3: drifted"], ["us: unreachable"])

	str_body = next(c[2]["body"] for c in list_calls if c[0] == "POST")
	assert "us: unreachable" in str_body
