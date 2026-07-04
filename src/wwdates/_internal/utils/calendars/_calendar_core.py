"""ABCCalendar-derived — calendar mixin."""

from datetime import date, datetime

import pandas as pd

from wwdates._internal.utils.calendars._abc_calendar import (
	ABCCalendar,
	TypeDatetimeDate,
)


class CalendarCore(ABCCalendar):
	"""Abstract base class for calendar operations."""

	def get_holidays_raw(
		self, timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0)
	) -> pd.DataFrame:
		"""Return an empty DataFrame as a default implementation.

		Parameters
		----------
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			An empty DataFrame.
		"""
		return pd.DataFrame(columns=["name", "date"])

	def holidays(self) -> list[tuple[str, date]]:
		"""Return an empty list of holidays as a default implementation.

		Returns
		-------
		list[tuple[str, date]]
			An empty list.
		"""
		return []

	@property
	def _holidays(self) -> set[date]:
		"""Return a set of holiday dates.

		Returns
		-------
		set[date]
			Set of holiday dates
		"""
		if not hasattr(self, "_holidays_cache"):
			self._holidays_cache = {tup_holiday[1] for tup_holiday in self.holidays()}
		return self._holidays_cache

	def date_only(self, date_: TypeDatetimeDate) -> date:
		"""Return the date component of a datetime or date object.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.

		Returns
		-------
		date
			The date component of the input object.

		Raises
		------
		TypeError
			If the input object is not of type datetime or date
		"""
		if not isinstance(date_, datetime | date):
			raise TypeError(f"date_ must be of type datetime or date, got {type(date_).__name__}")
		return (
			date_ if isinstance(date_, date) and not isinstance(date_, datetime) else date_.date()
		)

	def is_weekend(self, date_: TypeDatetimeDate) -> bool:
		"""Return True if the given date is a weekend day, False otherwise.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.

		Returns
		-------
		bool
			True if the given date is a weekend day, False otherwise.
		"""
		date_ = self.date_only(date_)
		return date_.weekday() >= 5

	def is_working_day(self, date_: TypeDatetimeDate) -> bool:
		"""Return True if the given date is a working day, False otherwise.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.

		Returns
		-------
		bool
			True if the given date is a working day, False otherwise.
		"""
		date_ = self.date_only(date_)
		return not self.is_weekend(date_) and date_ not in self._holidays

	def is_holiday(self, date_: TypeDatetimeDate) -> bool:
		"""Return True if the given date is a holiday, False otherwise.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.

		Returns
		-------
		bool
			True if the given date is a holiday, False otherwise.
		"""
		date_ = self.date_only(date_)
		return date_ in self._holidays

	def holidays_in_year(self, int_year: int) -> list[int]:
		"""Return a list of holiday days in the given year.

		Parameters
		----------
		int_year : int
			The year for which to retrieve holiday days.

		Returns
		-------
		list[int]
			A list of holiday days in the given year.
		"""
		holidays = [date_ for date_ in self._holidays if int(date_.strftime("%Y")) == int_year]
		return sorted([int(date_.strftime("%d")) for date_ in holidays])
