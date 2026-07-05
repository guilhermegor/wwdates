"""US federal holiday calendar — offline, computed via the ``holidays`` package.

No network and no browser: the eleven US federal holidays are computed from their statutory
rules. When a holiday falls on a weekend, the observed federal closure day is also emitted per
5 U.S.C. §6103 (a Saturday holiday is observed the preceding Friday; a Sunday holiday the
following Monday) — both the statutory date and the observed date are returned, so a Sunday
holiday still appears on that Sunday *and* the closed Monday is marked too. This is required for
correct working-day math, since federal offices, banks, and markets close on the observed day.

For the dates exactly as published on federalholidays.net (a live scrape), use
:class:`wwdates.us.federal_holidays_web.DatesUSFederalHolidaysWeb` instead.
"""

from datetime import date
from logging import Logger

import holidays

from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations


class DatesUSFederalHolidays(ABCCalendarOperations):
	"""US federal holiday calendar computed offline from the ``holidays`` package.

	Emits both the statutory holiday date and, when it falls on a weekend, the observed federal
	closure day (5 U.S.C. §6103). No network or browser is used, so no cache is needed.

	References
	----------
	[1] 5 U.S.C. §6103 — Holidays (observed-day rule).
	"""

	def __init__(
		self,
		int_year_start: int = date.today().year - 1,
		int_year_end: int = date.today().year,
		logger: Logger | None = None,
	) -> None:
		"""Initialize the offline US federal holidays calendar.

		Parameters
		----------
		int_year_start : int
			First year to include (default: last year).
		int_year_end : int
			Last year to include (default: current year).
		logger : Optional[Logger]
			Logger object for logging (default: None).

		Returns
		-------
		None
		"""
		self.int_year_start = int_year_start
		self.int_year_end = int_year_end
		self._logger = logger

	def _source_holidays(self) -> list[tuple[str, date]]:
		"""Return US federal holidays for the configured year range.

		Both the statutory date and the observed closure day (when a holiday falls on a
		weekend) are returned, per 5 U.S.C. §6103.

		Returns
		-------
		list[tuple[str, date]]
			Tuples of ``(name, date)``, sorted by date.
		"""
		self._validate_year_range(self.int_year_start, self.int_year_end)
		dict_holidays = holidays.UnitedStates(
			years=range(self.int_year_start, self.int_year_end + 1),
			observed=True,
		)
		return [(str_name, date_) for date_, str_name in sorted(dict_holidays.items())]

	def _validate_year_range(self, int_year_start: int, int_year_end: int) -> None:
		"""Validate the year-range parameters.

		Parameters
		----------
		int_year_start : int
			Starting year.
		int_year_end : int
			Ending year.

		Raises
		------
		ValueError
			If either year is not positive, or the range is inverted.
		"""
		if int_year_start <= 0 or int_year_end <= 0:
			raise ValueError("Year must be a positive integer")
		if int_year_start > int_year_end:
			raise ValueError("Start year must be less than or equal to end year")
