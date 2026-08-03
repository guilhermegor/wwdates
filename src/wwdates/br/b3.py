"""B3 Brazilian exchange calendar — offline, computed via the ``holidays`` package.

No network and no cache: the national holidays come from ``holidays.B3`` (verified identical
to ANBIMA's published table) and the exchange's own non-trading days — the last working day
of each year, and optionally Christmas Eve — are derived from them.

For the calendar built from the live ANBIMA fetch, use
:class:`wwdates.br.b3_web.DatesBRB3Web` instead.
"""

from datetime import date, timedelta
from logging import Logger

from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations
from wwdates.br._offline_holidays import (
	INT_YEAR_END_DEFAULT,
	INT_YEAR_START_DEFAULT,
	national_holidays,
)


class DatesBRB3(ABCCalendarOperations):
	"""B3 exchange calendar computed offline.

	The national holidays plus B3's own non-trading days: the last working day of each year
	(the exchange does not trade on it) and, optionally, Christmas Eve.

	References
	----------
	.. [1] https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/calendario-de-negociacao/feriados/
	"""

	def __init__(
		self,
		bool_add_christmas_eve: bool = True,
		int_year_start: int = INT_YEAR_START_DEFAULT,
		int_year_end: int = INT_YEAR_END_DEFAULT,
		logger: Logger | None = None,
	) -> None:
		"""Initialize the offline B3 calendar.

		Parameters
		----------
		bool_add_christmas_eve : bool
			If True, 24 December is a non-trading day (default: True). This matches B3, whose
			published calendar carries 24 December as a closure ("não haverá negociação") in
			every year it falls on a weekday — verified live for 2021, 2024, 2025 and 2026.
			Pass False for the pre-2.0 behaviour, in which the offline calendar omitted it and
			therefore disagreed with the exchange. Note that the date is added unconditionally,
			so in a year where 24 December falls on a weekend it appears in the holiday list
			even though B3 omits it (harmless for working-day arithmetic — a weekend is already
			non-working — and excused by the drift job's offline-only weekend rule).
		int_year_start : int
			First year to include (default: 2001).
		int_year_end : int
			Last year to include (default: 2099).
		logger : Optional[Logger]
			Logger object for logging (default: None).

		Returns
		-------
		None
		"""
		self.bool_add_christmas_eve = bool_add_christmas_eve
		self.int_year_start = int_year_start
		self.int_year_end = int_year_end
		self._logger = logger

	def _source_holidays(self) -> list[tuple[str, date]]:
		"""Return the B3 non-trading days for the configured year range.

		Returns
		-------
		list[tuple[str, date]]
			Tuples of ``(name, date)``, sorted by date.
		"""
		list_national = national_holidays(self.int_year_start, self.int_year_end)
		list_all = list_national + self.holidays_to_add({date_ for _, date_ in list_national})
		return sorted(list_all, key=lambda tup: tup[1])

	def holidays_to_add(self, set_dates_national: set[date]) -> list[tuple[str, date]]:
		"""Return the B3-specific non-trading days for the configured year range.

		Parameters
		----------
		set_dates_national : set[date]
			The national holiday dates, needed to skip them when walking back to the last
			working day of the year.

		Returns
		-------
		list[tuple[str, date]]
			Tuples of ``(name, date)``.
		"""
		list_: list[tuple[str, date]] = []
		for int_year in range(self.int_year_start, self.int_year_end + 1):
			list_.append(
				("Ultimo Dia Util do Ano", self.get_last_working_day(int_year, set_dates_national))
			)
			if self.bool_add_christmas_eve:
				list_.append(("Vespera de Natal", self.get_christmas_eve(int_year)))
		return list_

	def get_last_working_day(self, int_year: int, set_dates_national: set[date]) -> date:
		"""Get the last working day of a given year.

		Parameters
		----------
		int_year : int
			Year for which to retrieve the last working day.
		set_dates_national : set[date]
			The national holiday dates to skip.

		Returns
		-------
		date
			The last day of the year that is neither a weekend nor a national holiday.
		"""
		date_ = date(int_year, 12, 31)
		while self.is_weekend(date_) or date_ in set_dates_national:
			date_ -= timedelta(days=1)
		return date_

	def get_christmas_eve(self, int_year: int) -> date:
		"""Get Christmas Eve for a given year.

		Parameters
		----------
		int_year : int
			Year for which to retrieve Christmas Eve.

		Returns
		-------
		date
			Christmas Eve for the given year.
		"""
		return date(int_year, 12, 24)
