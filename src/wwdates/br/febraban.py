"""FEBRABAN Brazilian bank-holiday calendar — offline, computed via the ``holidays`` package.

No network and no cache. FEBRABAN has no dedicated entry in the ``holidays`` package, but its
published federal bank holidays were verified identical to ``holidays.B3`` — the Brazilian
financial-market calendar — so that is the offline source. The equivalence was checked against
the live endpoint for 2025 and 2026; years outside that window are computed from the same
statutory rules but have not been diffed against FEBRABAN's own publication.

For the table fetched live from feriadosbancarios.febraban.org.br, use
:class:`wwdates.br.febraban_web.DatesBRFebrabanWeb` instead.
"""

from datetime import date, timedelta
from logging import Logger

from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations
from wwdates.br._offline_holidays import national_holidays


class DatesBRFebraban(ABCCalendarOperations):
	"""FEBRABAN Brazilian bank holiday calendar computed offline.

	References
	----------
	.. [1] https://feriadosbancarios.febraban.org.br/
	"""

	def __init__(
		self,
		int_year_start: int = (date.today() - timedelta(days=22)).year - 1,
		int_year_end: int = (date.today() - timedelta(days=22)).year,
		logger: Logger | None = None,
	) -> None:
		"""Initialize the offline FEBRABAN holiday calendar.

		Parameters
		----------
		int_year_start : int
			Starting year for holidays (default: (date.today() - timedelta(days=22)).year - 1)
		int_year_end : int
			Ending year for holidays (default: (date.today() - timedelta(days=22)).year)
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
		"""Return the FEBRABAN bank holidays for the configured year range.

		Returns
		-------
		list[tuple[str, date]]
			Tuples of ``(name, date)``, sorted by date.
		"""
		return national_holidays(self.int_year_start, self.int_year_end)
