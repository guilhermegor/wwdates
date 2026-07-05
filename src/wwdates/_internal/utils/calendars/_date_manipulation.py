"""CalendarCore-derived — calendar mixin."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.relativedelta import relativedelta

from wwdates._internal.utils.calendars._abc_calendar import (
	TypeDatetimeDate,
)
from wwdates._internal.utils.calendars._calendar_core import CalendarCore


class DateManipulation(CalendarCore):
	"""Abstract class for date manipulation operations."""

	def _get_added_holidays(self) -> list[tuple[str, date]]:
		"""Return the runtime-added holidays, initialising the store on first access.

		Lazily initialised rather than set in ``__init__`` so it works even for concrete
		providers that do not chain ``super().__init__()`` — accessing the store never
		raises ``AttributeError``.

		Returns
		-------
		list[tuple[str, date]]
			The list of ``(name, date)`` holidays injected via ``add_holidays``.
		"""
		if not hasattr(self, "_added_holidays"):
			self._added_holidays: list[tuple[str, date]] = []
		return self._added_holidays

	def holidays(self) -> list[tuple[str, date]]:
		"""Return the provider's holidays plus any injected at runtime.

		Concrete providers supply their source calendar via ``_source_holidays``; this
		single, non-overridden method appends the runtime additions, so ``add_holidays``
		works uniformly across every provider.

		Returns
		-------
		list[tuple[str, date]]
			List of tuples containing holiday names and dates
		"""
		return self._source_holidays() + self._get_added_holidays()

	def add_holidays(self, list_new_holidays: list[tuple[str, date]]) -> None:
		"""Add new holidays to the existing holiday cache.

		Parameters
		----------
		list_new_holidays : list[tuple[str, date]]
			A list of tuples containing holiday names and dates to add.

		Raises
		------
		TypeError
			If list_new_holidays is not a list of tuples or if any tuple does not contain
			a string and a date object.
		ValueError
			If list_new_holidays is empty or contains invalid date objects.
		"""
		if not isinstance(list_new_holidays, list):
			raise TypeError("list_new_holidays must be a list")
		if not list_new_holidays:
			raise ValueError("list_new_holidays list cannot be empty")

		for holiday in list_new_holidays:
			if not isinstance(holiday, tuple) or len(holiday) != 2:
				raise TypeError("Each holiday must be a tuple of (str, date)")
			name, date_ = holiday
			if not isinstance(name, str):
				raise TypeError(f"Holiday name must be a string, got {type(name).__name__}")
			if not isinstance(date_, date) or isinstance(date_, datetime):
				raise TypeError(f"Holiday date must be a date object, got {type(date_).__name__}")

		self._get_added_holidays().extend(list_new_holidays)

		# Rebuild the date-set cache eagerly, unioning the current holidays with the new
		# ones. The current holiday accessor may be patched or overridden to exclude the
		# additions, so the new dates are unioned in explicitly rather than assumed present.
		set_current = {tup_holiday[1] for tup_holiday in self.holidays()}
		set_new = {tup_holiday[1] for tup_holiday in list_new_holidays}
		self._holidays_cache = set_current | set_new

	def add_working_days(self, date_: TypeDatetimeDate, int_days_to_add: int) -> date:
		"""Add the specified number of working days to the given date.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.
		int_days_to_add : int
			The number of working days to add.

		Returns
		-------
		date
			The resulting date after adding the specified number of working days.
		"""
		date_current = self.date_only(date_)
		int_days_left = abs(int_days_to_add)
		int_step = 1 if int_days_to_add >= 0 else -1

		while int_days_left > 0:
			date_current += timedelta(days=int_step)
			if self.is_working_day(date_current):
				int_days_left -= 1

		return date_current

	def add_calendar_days(self, date_: TypeDatetimeDate, int_days_to_add: int) -> date:
		"""Add the specified number of calendar days to the given date.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.
		int_days_to_add : int
			The number of calendar days to add.

		Returns
		-------
		date
			The resulting date after adding the specified number of calendar days.
		"""
		date_ = self.date_only(date_)
		return date_ + timedelta(days=int_days_to_add)

	def add_months(self, date_: datetime, int_months_to_add: int) -> datetime:
		"""Add the specified number of months to the given date.

		Parameters
		----------
		date_ : datetime
			A datetime object.
		int_months_to_add : int
			The number of months to add.

		Returns
		-------
		datetime
			The resulting datetime after adding the specified number of months.
		"""
		return date_ + relativedelta(months=int_months_to_add)

	def build_date(self, year: int, month: int, day: int) -> date:
		"""Build a date object from the given year, month, and day.

		Parameters
		----------
		year : int
			The year component of the date.
		month : int
			The month component of the date.
		day : int
			The day component of the date.

		Returns
		-------
		date
			The built date object.
		"""
		return date(year=year, month=month, day=day)

	def build_datetime(
		self,
		year: int,
		month: int,
		day: int,
		hour: int,
		minute: int,
		second: int,
		str_timezone: str | None = "UTC",
	) -> datetime:
		"""Build a datetime object from the given year, month, day, hour, minute, and second.

		Parameters
		----------
		year : int
			The year component of the datetime.
		month : int
			The month component of the datetime.
		day : int
			The day component of the datetime.
		hour : int
			The hour component of the datetime.
		minute : int
			The minute component of the datetime.
		second : int
			The second component of the datetime.
		str_timezone : Optional[str]
			The timezone component of the datetime, by default "UTC".

		Returns
		-------
		datetime
			The built datetime object.

		Raises
		------
		ZoneInfoNotFoundError
			If the timezone is empty or None
		ValueError
			If the date components are invalid
		"""
		if str_timezone == "" or str_timezone is None:
			raise ZoneInfoNotFoundError("Timezone cannot be empty or None")
		try:
			return datetime(
				year=year,
				month=month,
				day=day,
				hour=hour,
				minute=minute,
				second=second,
				tzinfo=ZoneInfo(str_timezone),
			)
		except ValueError as err:
			raise ValueError(f"Invalid date components: {err}") from err

	def nearest_working_day(self, date_: TypeDatetimeDate, bool_next: bool = True) -> date:
		"""Find the nearest working day to the given date.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.
		bool_next : bool
			If True, returns the nearest working day after the given date; if False,
			returns the nearest working day before the given date, by default True

		Returns
		-------
		date
			The nearest working day to the given date.
		"""
		date_ = self.date_only(date_)
		date_ref = self.add_working_days(self.add_working_days(date_, -1), 1)
		if bool_next:
			return date_ref
		else:
			return self.add_working_days(date_ref, -1) if date_ref > date_ else date_ref

	def str_date_to_date(self, str_date: str, format_input: str | None = "DD/MM/YYYY") -> date:
		"""Convert a string representation of a date to a date object.

		Parameters
		----------
		str_date : str
			The string representation of the date.
		format_input : str | None
			The format of the input date string, by default "DD/MM/YYYY"

		Returns
		-------
		date
			The date object corresponding to the input string.

		Raises
		------
		ValueError
			If the input date string is not in the specified format.
		"""
		format_map = {
			"DD/MM/YYYY": "%d/%m/%Y",
			"D/M/YYYY": "%d/%m/%Y",
			"YYYY-MM-DD": "%Y-%m-%d",
			"YYYY-MM-DDTHH:MM:SS": "%Y-%m-%dT%H:%M:%S",
			"YYMMDD": "%y%m%d",
			"DDMMYY": "%d%m%y",
			"DDMMYYYY": "%d%m%Y",
			"DMMYYY": "%d%m%Y",
			"YYYYMMDD": "%Y%m%d",
			"MM-DD-YYYY": "%m-%d-%Y",
			"DD/MM/YY": "%d/%m/%y",
			"DD.MM.YY": "%d.%m.%y",
			"YYYY/MM/DD": "%Y/%m/%d",
		}

		if format_input not in format_map or format_input is None:
			raise ValueError(f"Not a valid date format: {format_input}")

		try:
			dt = datetime.strptime(str_date, format_map[format_input])
			return dt.date()
		except ValueError as err:
			raise ValueError(
				f"Invalid date string '{str_date}' for format {format_input}: {err}"
			) from err

	def timestamp_to_date(
		self,
		timestamp_: str,
		substr_timestamp: str = "T",
	) -> date:
		"""Convert a string representation of a timestamp to a date object.

		Parameters
		----------
		timestamp_ : str
			The string representation of the timestamp.
		substr_timestamp : str
			The substring to split the timestamp on, by default "T"

		Returns
		-------
		date
			The date object corresponding to the input timestamp string.
		"""
		return self.str_date_to_date(timestamp_.split(substr_timestamp)[0], "YYYY-MM-DD")

	def timestamp_to_datetime(
		self,
		timestamp_: str,
		substr_timestamp: str = "T",
	) -> datetime:
		"""Convert a string representation of a timestamp to a datetime object.

		Parameters
		----------
		timestamp_ : str
			The string representation of the timestamp.
		substr_timestamp : str
			The substring to split the timestamp on, by default "T"

		Returns
		-------
		datetime
			The datetime object corresponding to the input timestamp string.

		Raises
		------
		ValueError
			If the input timestamp string is not in the expected format.
		"""
		try:
			return datetime.fromisoformat(timestamp_.replace("Z", "+00:00"))
		except ValueError:
			try:
				return datetime.strptime(timestamp_, f"%Y-%m-%d{substr_timestamp}%H:%M:%S")
			except ValueError as err:
				raise ValueError(
					f"Failed to parse timestamp '{timestamp_}' in format "
					f"'YYYY-MM-DD{substr_timestamp}HH:MM:SS' or ISO 8601: {str(err)}"
				) from err

	def to_integer(self, date_: TypeDatetimeDate) -> int:
		"""Convert a date object to an integer.

		Parameters
		----------
		date_ : TypeDatetimeDate
			A datetime or date object.

		Returns
		-------
		int
			The integer representation of the date.
		"""
		date_ = self.date_only(date_)
		return 10000 * date_.year + 100 * date_.month + date_.day

	def excel_float_to_date(self, numeric_excel_date: int | float) -> date:
		"""Convert an Excel float to a date object.

		Parameters
		----------
		numeric_excel_date : int | float
			The Excel float to convert.

		Returns
		-------
		date
			The date object corresponding to the Excel float.

		Raises
		------
		ValueError
			If numeric_excel_date is None or negative
		"""
		if numeric_excel_date is None:
			raise ValueError("numeric_excel_date cannot be None")
		if numeric_excel_date < 0:
			raise ValueError("numeric_excel_date cannot be negative")

		# Excel's epoch starts at January 1, 1900, but there's a bug where
		# Excel treats 1900 as a leap year, so we use December 30, 1899 as base
		base_date = date(1899, 12, 30)

		# Excel has a leap year bug for 1900, so dates >= 60 need adjustment  # noqa: ERA001
		if numeric_excel_date >= 60:
			numeric_excel_date -= 1

		return base_date + timedelta(days=int(numeric_excel_date))
