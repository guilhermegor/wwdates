"""Weekly, NON-BLOCKING offline↔web calendar drift detector — issue #12.

Compares each offline calendar against the live page its publisher maintains and, on any
divergence, opens or updates ONE tracking issue. It is deliberately kept OUT of the PR gate and
the release path:

* ``tests/conftest.py`` blocks the network on purpose, so this can never run at test time; and
* a B3/ANBIMA outage and a real drift are indistinguishable in a red check, so a red check must
  never gate a PR.

Failure here is an OPENED ISSUE, never a failed required check: ``main`` always exits 0, and only
an unhandled crash reddens the run — a reddened *scheduled* run blocks nothing.

Why a scheduled job at all: the whole library is offline-first, and parity between each offline
class and its ``*Web`` twin was verified **once, by hand**, in PR #10 (over ANBIMA's full
2001–2099 span: empty symmetric difference). Nothing at PR time can see B3 adding a closure
*after* we shipped. This is the job that goes back and looks again.

Comparison is on **dates only, never names** — B3 publishes an event feed whose free-text wording
is not a stable key.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
import json
import os
import sys
import traceback
from typing import Any
import urllib.request

from wwdates.br.anbima import DatesBRAnbima
from wwdates.br.anbima_web import DatesBRAnbimaWeb
from wwdates.br.b3 import DatesBRB3
from wwdates.br.b3_web import DatesBRB3Web
from wwdates.br.febraban import DatesBRFebraban
from wwdates.br.febraban_web import DatesBRFebrabanWeb
from wwdates.us.federal_holidays import DatesUSFederalHolidays
from wwdates.us.federal_holidays_web import DatesUSFederalHolidaysWeb


# ---------------------------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------------------------

_GH_API = "https://api.github.com"
_ISSUE_LABEL = "calendar-drift"
_ISSUE_TITLE = "Calendar drift: offline calendars disagree with their live sources"

# Hidden HTML comment used to find this job's own issue again on the next run, so it updates one
# issue instead of opening a new one every week. The label alone is not enough — a human may add
# it to something else.
_ISSUE_MARKER = "<!-- wwdates:calendar-drift-tracker -->"

# B3's 2021 São Paulo municipal/state closures. B3 observed them that year and stopped afterwards,
# so they appear on the scrape and never in the offline (national) set. Established in PR #10.
# ⚠ Seeded from that PR's findings — confirm against the first live run before trusting it, and
# treat any addition here as a deliberate narrowing of what the job can still catch.
_B3_KNOWN_WEB_ONLY_2021 = frozenset(
	{
		date(2021, 1, 25),  # Aniversário da cidade de São Paulo
		date(2021, 7, 9),  # Revolução Constitucionalista
	}
)


# ---------------------------------------------------------------------------------------------
# Comparison (pure — no network, fully unit-tested)
# ---------------------------------------------------------------------------------------------


def clamp_to_web_span(set_offline: set[date], set_web: set[date]) -> set[date]:
	"""Restrict the offline dates to the year span the web source actually publishes.

	The offline classes span far more years than the live pages do — ``DatesBRB3`` covers
	2001–2099 while B3 publishes roughly 2021–2026 — so without clamping every unpublished year
	would be reported as a missing holiday. The span is derived from the web side at runtime
	rather than hard-coded, so it follows the publisher when it adds a year.

	Parameters
	----------
	set_offline : set of datetime.date
		Dates from the offline calendar.
	set_web : set of datetime.date
		Dates from the live source.

	Returns
	-------
	set of datetime.date
		The offline dates whose year falls inside the web source's span; empty when the web
		source returned nothing (there is no span to compare against).
	"""
	if not set_web:
		return set()
	int_year_min = min(date_.year for date_ in set_web)
	int_year_max = max(date_.year for date_ in set_web)
	return {date_ for date_ in set_offline if int_year_min <= date_.year <= int_year_max}


def compare_dates(
	str_pair: str,
	set_offline: set[date],
	set_web: set[date],
	bool_offline_only_weekend_ok: bool = False,
	frozenset_known_web_only: frozenset[date] = frozenset(),
	frozenset_known_offline_only: frozenset[date] = frozenset(),
) -> list[str]:
	"""Diff the two date sets and render one message per unexplained divergence.

	Parameters
	----------
	str_pair : str
		Pair label used to prefix each message, e.g. ``"br.b3"``.
	set_offline : set of datetime.date
		Dates from the offline calendar, already clamped to the web span.
	set_web : set of datetime.date
		Dates from the live source.
	bool_offline_only_weekend_ok : bool
		When True, an offline-only date landing on a Saturday or Sunday is not drift. B3 omits
		weekend holidays because there is no session to cancel, and the US offline class emits
		the statutory date *and* the §6103 observed weekday while the scrape lists only the
		latter. Deliberately one-directional: it never excuses a date the publisher listed.
	frozenset_known_web_only : frozenset of datetime.date
		Dates the source is expected to list and the offline calendar is expected to omit.
	frozenset_known_offline_only : frozenset of datetime.date
		Dates the offline calendar is expected to hold and the source is expected to omit.

	Returns
	-------
	list of str
		One message per divergence, web-only first, then offline-only; empty when they agree.
	"""
	list_problems = []
	for date_ in sorted(set_web - set_offline):
		if date_ in frozenset_known_web_only:
			continue
		list_problems.append(
			f"{str_pair}: {date_:%Y-%m-%d} is published as a closure by the source, but the "
			f"offline calendar treats it as a working day"
		)
	for date_ in sorted(set_offline - set_web):
		if date_ in frozenset_known_offline_only:
			continue
		if bool_offline_only_weekend_ok and date_.weekday() >= 5:
			continue
		list_problems.append(
			f"{str_pair}: {date_:%Y-%m-%d} is a holiday in the offline calendar, but the source "
			f"does not list it"
		)
	return list_problems


# ---------------------------------------------------------------------------------------------
# Pair registry + sweep (network)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CalendarPair:
	"""One offline calendar and the live source it is supposed to reproduce.

	Attributes
	----------
	str_name : str
		Pair label used in messages.
	callable_offline : Callable
		Zero-argument factory returning the offline calendar instance.
	callable_web : Callable
		Zero-argument factory returning the live-source instance.
	bool_offline_only_weekend_ok : bool
		Passed through to :func:`compare_dates`.
	callable_known_web_only : Callable or None
		Given the web date set, returns the dates excused in the web-only direction. A callable
		rather than a constant because some exceptions depend on the span being compared.
	"""

	str_name: str
	callable_offline: Callable[[], Any]
	callable_web: Callable[[], Any]
	bool_offline_only_weekend_ok: bool = False
	callable_known_web_only: Callable[[set[date]], frozenset[date]] | None = field(default=None)


def b3_known_web_only(set_web: set[date]) -> frozenset[date]:
	"""Return the B3 dates expected on the scrape but not in the offline calendar.

	One group now: the 2021 São Paulo closures B3 stopped observing afterwards.

	**Christmas Eve used to be excused here and deliberately is not any more** (issue #35). The
	excuse existed only because ``DatesBRB3`` defaulted to ``bool_add_christmas_eve=False`` while
	B3 publishes 24 December as a closure in every year it falls on a weekday — so the divergence
	was real, known, and would have been restated weekly. That default is now ``True``, so both
	sides agree and there is nothing to excuse. Keeping the excuse would be worse than dead code:
	it would **suppress real signal** — if B3 ever stops publishing 24 December on a weekday while
	the offline calendar still adds it, that is exactly what this job should report.

	A year where 24 December falls on a weekend needs no entry either: the date is then
	offline-only, and the pair's ``bool_offline_only_weekend_ok`` already covers it, because B3
	omits weekends (there is no session to cancel).

	Parameters
	----------
	set_web : set of datetime.date
		The dates the live source returned. Unused now that the span-dependent Christmas Eve group
		is gone, but kept so the ``callable_known_web_only`` signature stays uniform across pairs.

	Returns
	-------
	frozenset of datetime.date
		The excused web-only dates.
	"""
	del set_web  # signature kept uniform across pairs; see the note above
	return _B3_KNOWN_WEB_ONLY_2021


def _uncached(cls_web: Callable[..., Any]) -> Callable[[], Any]:
	"""Wrap a ``*Web`` class so the sweep always constructs it with caching off.

	The ``*Web`` classes default to persisting and reusing a cache with a one-day expiry, which
	is right for a library consumer and wrong for this job twice over: a drift detector that
	reads a cache cannot detect drift, and a *partial* cache left behind by an earlier failed
	fetch is reported as drift. Measured during the first local run — 2 of 22 US dates came back
	from a stale cache and produced 9 false positives.

	Parameters
	----------
	cls_web : Callable
		The ``*Web`` class to wrap.

	Returns
	-------
	Callable
		A zero-argument factory building the class with both cache flags off.
	"""
	return lambda: cls_web(bool_persist_cache=False, bool_reuse_cache=False)


def calendar_pairs() -> tuple[CalendarPair, ...]:
	"""Return the offline↔web pairs to sweep.

	``DatesUSNasdaq`` is deliberately absent: it is web-only and has no offline twin, so there
	is nothing to compare it against.

	Returns
	-------
	tuple of CalendarPair
		The four pairs, BR first.
	"""
	return (
		CalendarPair(
			str_name="br.b3",
			callable_offline=DatesBRB3,
			callable_web=_uncached(DatesBRB3Web),
			# B3 lists no weekend closures — there is no session to cancel.
			bool_offline_only_weekend_ok=True,
			callable_known_web_only=b3_known_web_only,
		),
		CalendarPair(
			str_name="br.anbima",
			callable_offline=DatesBRAnbima,
			callable_web=_uncached(DatesBRAnbimaWeb),
		),
		CalendarPair(
			str_name="br.febraban",
			callable_offline=DatesBRFebraban,
			callable_web=_uncached(DatesBRFebrabanWeb),
		),
		CalendarPair(
			str_name="us.federal_holidays",
			callable_offline=DatesUSFederalHolidays,
			callable_web=_uncached(DatesUSFederalHolidaysWeb),
			# The offline class emits the statutory date AND the §6103 observed weekday; the
			# scrape publishes only the observed one, so the weekend statutory date is expected
			# to be offline-only.
			bool_offline_only_weekend_ok=True,
		),
	)


def check_pair(cls_pair: CalendarPair) -> list[str]:
	"""Fetch both sides of one pair and diff them.

	Parameters
	----------
	cls_pair : CalendarPair
		The pair to check.

	Returns
	-------
	list of str
		The divergence messages for this pair.
	"""
	set_web = {date_ for _, date_ in cls_pair.callable_web().holidays()}
	set_offline = {date_ for _, date_ in cls_pair.callable_offline().holidays()}
	set_offline = clamp_to_web_span(set_offline, set_web)
	frozenset_web_only = (
		frozenset()
		if cls_pair.callable_known_web_only is None
		else cls_pair.callable_known_web_only(set_web)
	)
	return compare_dates(
		cls_pair.str_name,
		set_offline,
		set_web,
		bool_offline_only_weekend_ok=cls_pair.bool_offline_only_weekend_ok,
		frozenset_known_web_only=frozenset_web_only,
	)


def collect_drift() -> tuple[list[str], list[str]]:
	"""Sweep every pair, collecting divergences and per-pair read failures **separately**.

	A pair that cannot be read is recorded and the sweep continues, so one flaky publisher never
	hides the other three. The two lists are kept apart because they mean different things and
	get different treatment: divergences open the tracking issue, read failures never do. A
	source being down is common and outside this repo's control, and filing "calendar drift" for
	it is the cry-wolf that makes a drift job worse than nothing.

	Returns
	-------
	tuple of (list of str, list of str)
		The divergence messages, and the "could not check" messages.
	"""
	list_problems = []
	list_errors = []
	for cls_pair in calendar_pairs():
		try:
			list_problems.extend(check_pair(cls_pair))
		except Exception as cls_error:  # noqa: BLE001 - one bad source must not stop the sweep
			list_errors.append(
				f"{cls_pair.str_name}: could not check the live source ({cls_error!r})"
			)
			traceback.print_exc()
	return list_problems, list_errors


# ---------------------------------------------------------------------------------------------
# Issue upsert (network) — one tracking issue, found again by label + marker.
# ---------------------------------------------------------------------------------------------


def build_issue_body(list_problems: list[str], list_errors: list[str]) -> str:
	"""Render the drift messages into the tracking issue's body (with the dedupe marker).

	Parameters
	----------
	list_problems : list of str
		The drift messages.
	list_errors : list of str
		The "could not check" messages. These never open the issue on their own, but they are
		surfaced here when one is opened anyway — otherwise a reader would mistake a partial
		sweep for a complete one.

	Returns
	-------
	str
		Markdown body carrying the hidden marker used to find this issue again.
	"""
	str_lines = "\n".join(f"- {str_problem}" for str_problem in list_problems)
	str_errors = (
		""
		if not list_errors
		else "\n**Not checked this run** (the source could not be read — not drift):\n"
		+ "\n".join(f"- {str_error}" for str_error in list_errors)
		+ "\n"
	)
	return (
		f"{_ISSUE_MARKER}\n\n"
		f"The weekly calendar-drift sweep found **{len(list_problems)}** divergence(s) between "
		f"the offline calendars and the pages their publishers serve today.\n\n"
		f"{str_lines}\n"
		f"{str_errors}\n"
		f"Dates are compared **on dates only, never names** — B3 publishes an event feed whose "
		f"wording is not a stable key. Fix the affected calendar (or widen the known-exceptions "
		f"allowlist in `bin/check_calendar_drift.py` if the divergence is expected) and close "
		f"this issue — the job reopens it if the drift persists.\n"
	)


def _api(str_method: str, str_url: str, dict_body: dict | None = None) -> Any:  # noqa: ANN401
	"""Call the GitHub API with the workflow token and decode the JSON reply.

	Parameters
	----------
	str_method : str
		HTTP method.
	str_url : str
		Absolute API URL.
	dict_body : dict, optional
		JSON payload, when the method takes one.

	Returns
	-------
	Any
		The decoded JSON (an object or an array, per the endpoint).
	"""
	bytes_body = None if dict_body is None else json.dumps(dict_body).encode()
	cls_request = urllib.request.Request(str_url, data=bytes_body, method=str_method)  # noqa: S310
	cls_request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
	cls_request.add_header("Accept", "application/vnd.github+json")
	cls_request.add_header("Content-Type", "application/json")
	with urllib.request.urlopen(cls_request) as cls_response:  # noqa: S310
		return json.loads(cls_response.read() or "null")


def find_open_drift_issue(list_issues: list[dict]) -> int | None:
	"""Return the number of the existing open drift issue, if any.

	Parameters
	----------
	list_issues : list of dict
		Open issues carrying the drift label, each ``{"number": int, "body": str, ...}``.

	Returns
	-------
	int or None
		The first issue whose body carries the marker, or ``None``.
	"""
	for dict_issue in list_issues:
		if _ISSUE_MARKER in (dict_issue.get("body") or ""):
			return dict_issue["number"]
	return None


def upsert_issue(str_api: str, list_problems: list[str], list_errors: list[str]) -> None:
	"""Open the tracking issue, or update it in place if it already exists.

	Parameters
	----------
	str_api : str
		The ``.../repos/{owner}/{name}`` API base.
	list_problems : list of str
		The drift messages to report.
	list_errors : list of str
		The "could not check" messages to surface alongside them.
	"""
	str_body = build_issue_body(list_problems, list_errors)
	list_open = _api("GET", f"{str_api}/issues?state=open&labels={_ISSUE_LABEL}&per_page=100")
	int_existing = find_open_drift_issue(list_open)
	if int_existing is not None:
		_api("PATCH", f"{str_api}/issues/{int_existing}", {"body": str_body})
		print(f"updated drift issue #{int_existing}", file=sys.stderr)
		return
	_api(
		"POST",
		f"{str_api}/issues",
		{"title": _ISSUE_TITLE, "body": str_body, "labels": [_ISSUE_LABEL]},
	)
	print("opened a new drift issue", file=sys.stderr)


def main() -> int:
	"""Run the sweep; open/update the tracking issue on drift. Always exits 0 (non-blocking).

	Returns
	-------
	int
		Always ``0`` — drift is reported as an issue, never as a failed check.
	"""
	list_problems, list_errors = collect_drift()

	for str_error in list_errors:
		print(f"  ! {str_error}", file=sys.stderr)

	if not list_problems:
		print(f"no calendar drift detected ({len(list_errors)} source(s) could not be checked)")
		return 0

	print(f"calendar drift detected: {len(list_problems)} problem(s)")
	for str_problem in list_problems:
		print(f"  - {str_problem}")

	# Only real drift files the issue. An unreadable source is printed above and carried into the
	# body when an issue is opened anyway, but it never opens one by itself.
	str_repo = os.environ.get("GITHUB_REPOSITORY")
	if str_repo:
		upsert_issue(f"{_GH_API}/repos/{str_repo}", list_problems, list_errors)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
