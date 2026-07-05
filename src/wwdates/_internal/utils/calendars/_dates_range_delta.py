"""DateTimezoneAware-derived — calendar mixin."""

from datetime import date, time, timedelta

import businesstimedelta

from wwdates._internal.utils.calendars._abc_calendar import (
	TypeDatetimeDate,
)
from wwdates._internal.utils.calendars._date_timezone_aware import DateTimezoneAware


class DatesRangeDelta(DateTimezoneAware):
	"""Abstract class for range dates and delta operations."""

	def working_days_range(
		self, date_start: TypeDatetimeDate, date_end: TypeDatetimeDate
	) -> set[date]:
		"""Return a set of working days between two dates.

		Parameters
		----------
		date_start : TypeDatetimeDate
			Start date.
		date_end : TypeDatetimeDate
			End date.

		Returns
		-------
		set[date]
			Set of working days between two dates.

		Raises
		------
		ValueError
			If date_end is less than date_start
		"""
		date_start = self.date_only(date_start)
		date_end = self.date_only(date_end)
		if date_end < date_start:
			raise ValueError("date_end must be greater than date_start")

		return {
			date_
			for date_ in (
				date_start + timedelta(days=i) for i in range((date_end - date_start).days + 1)
			)
			if self.is_working_day(date_)
		}

	def calendar_days_range(
		self, date_start: TypeDatetimeDate, date_end: TypeDatetimeDate
	) -> set[date]:
		"""Return a set of calendar days between two dates.

		Parameters
		----------
		date_start : TypeDatetimeDate
			Start date.
		date_end : TypeDatetimeDate
			End date.

		Returns
		-------
		set[date]
			Set of calendar days between two dates.

		Raises
		------
		ValueError
			If date_end is less than date_start
		"""
		date_start = self.date_only(date_start)
		date_end = self.date_only(date_end)
		if date_end < date_start:
			raise ValueError("date_end must be greater than date_start")

		return {date_start + timedelta(days=i) for i in range((date_end - date_start).days + 1)}

	def years_between_dates(
		self, date_start: TypeDatetimeDate, date_end: TypeDatetimeDate
	) -> set[int]:
		"""Return a set of years between two dates.

		Parameters
		----------
		date_start : TypeDatetimeDate
			Start date.
		date_end : TypeDatetimeDate
			End date.

		Returns
		-------
		set[int]
			Set of years between two dates.

		Raises
		------
		ValueError
			If date_end is less than date_start
		"""
		date_start = self.date_only(date_start)
		date_end = self.date_only(date_end)
		if date_end < date_start:
			raise ValueError("date_end must be greater than date_start")

		list_ = self.calendar_days_range(date_start, date_end)
		return set(int(date_.strftime("%Y")) for date_ in list_)

	def delta_working_days(self, date_start: TypeDatetimeDate, date_end: TypeDatetimeDate) -> int:
		"""Return the number of working days between two dates.

		Parameters
		----------
		date_start : TypeDatetimeDate
			Start date.
		date_end : TypeDatetimeDate
			End date.

		Returns
		-------
		int
			Number of working days between two dates.

		Raises
		------
		ValueError
			If date_end is less than date_start
		"""
		date_start = self.date_only(date_start)
		date_end = self.date_only(date_end)
		if date_end < date_start:
			raise ValueError("date_end must be greater than date_start")

		return (
			len(self.working_days_range(date_start, date_end)) - 1
			if self.is_working_day(date_start)
			else len(self.working_days_range(date_start, date_end))
		)

	def delta_calendar_days(self, date_start: TypeDatetimeDate, date_end: TypeDatetimeDate) -> int:
		"""Return the number of calendar days between two dates.

		Parameters
		----------
		date_start : TypeDatetimeDate
			Start date.
		date_end : TypeDatetimeDate
			End date.

		Returns
		-------
		int
			Number of calendar days between two dates.

		Raises
		------
		ValueError
			If date_end is less than date_start
		"""
		date_start = self.date_only(date_start)
		date_end = self.date_only(date_end)
		if date_end < date_start:
			raise ValueError("date_end must be greater than date_start")

		return (date_end - date_start).days

	def get_start_end_day_month(
		self, date_: TypeDatetimeDate, bool_working_days: bool = False
	) -> tuple[date, date]:
		"""Return the start and end date of the month of the given date.

		Parameters
		----------
		date_ : TypeDatetimeDate
			Date.
		bool_working_days : bool
			If True, the start and end date will be the nearest working day.
			Default is False.

		Returns
		-------
		tuple[date, date]
			Start and end date of the month of the given date.
		"""
		date_ = self.date_only(date_)

		date_start = date(date_.year, date_.month, 1)
		date_start = (
			self.nearest_working_day(date_start, bool_next=True)
			if bool_working_days
			else date_start
		)

		next_month = date_.month + 1 if date_.month < 12 else 1
		next_year = date_.year + 1 if date_.month == 12 else date_.year
		date_end = date(next_year, next_month, 1) - timedelta(days=1)
		date_end = (
			self.nearest_working_day(date_end, bool_next=False) if bool_working_days else date_end
		)

		return date_start, date_end

	def get_dates_weekday_month(
		self,
		year: int,
		month: int,
		weekday: int,
	) -> list[date]:
		"""Return a list of dates for the given year, month, and weekday.

		Parameters
		----------
		year : int
			Year.
		month : int
			Month.
		weekday : int
			Weekday.

		Returns
		-------
		list[date]
			List of dates for the given year, month, and weekday.

		Raises
		------
		ValueError
			If month is not between 1 and 12
			If weekday is not between 0 (Monday) and 6 (Sunday)
		"""
		if not 1 <= month <= 12:
			raise ValueError("Month must be between 1 and 12")
		if not 0 <= weekday <= 6:
			raise ValueError("Weekday must be between 0 (Monday) and 6 (Sunday)")

		list_ = []
		start_date = date(year, month, 1)

		current_date = start_date
		while current_date.weekday() != weekday:
			current_date += timedelta(days=1)

		while current_date.month == month:
			list_.append(current_date)
			current_date += timedelta(days=7)

		return list_

	def get_nth_weekday_month(
		self,
		year: int,
		month: int,
		weekday: int,
		n: int,
		bool_working_days: bool = True,
		bool_next_working_day: bool = True,
	) -> date:
		"""Return the nth weekday of the month.

		Parameters
		----------
		year : int
			Year.
		month : int
			Month.
		weekday : int
			Weekday.
		n : int
			Nth.
		bool_working_days : bool
			If True, the date will be the nearest working day.
			Default is True.
		bool_next_working_day : bool
			If True, the date will be the next working day.
			Default is True.

		Returns
		-------
		date
			Nth weekday of the month.

		Raises
		------
		ValueError
			If month is not between 1 and 12
			If weekday is not between 0 (Monday) and 6 (Sunday)
			If n is 0
			If n is greater than the number of weekdays in the month
		"""
		if not 1 <= month <= 12:
			raise ValueError("Month must be between 1 and 12")
		if not 0 <= weekday <= 6:
			raise ValueError("Weekday must be between 0 (Monday) and 6 (Sunday)")
		if n < 1:
			raise ValueError("n must be positive")
		if n == 0:
			raise ValueError("n must be non-zero")

		dates = self.get_dates_weekday_month(year, month, weekday)
		if n > len(dates):
			raise ValueError(f"n must be less than or equal to {len(dates)}")

		date_ref = dates[n - 1]
		return (
			self.nearest_working_day(date_ref, bool_next=bool_next_working_day)
			if bool_working_days
			else date_ref
		)

	def get_last_working_day_years(self, list_years: list[int]) -> list[date]:
		"""Return a list of last working days in the given years.

		Parameters
		----------
		list_years : list[int]
			List of years.

		Returns
		-------
		list[date]
			List of last working days in the given years.
		"""
		return [self.add_working_days(date(y + 1, 1, 1), -1) for y in list_years]

	def delta_working_hours(
		self,
		timestamp_start: str,
		timestamp_end: str,
		int_hour_start_office: int = 8,
		int_minute_start_office: int = 0,
		int_hour_end_office: int = 18,
		int_minute_end_office: int = 0,
		int_hour_start_lunch: int = 12,
		int_minute_start_lunch: int = 0,
		int_hour_end_lunch: int = 13,
		int_minute_end_lunch: int = 0,
		list_working_days_range: list[int] | None = None,
		substr_timestamp: str = "T",
	) -> int:
		"""Return the number of working hours between two timestamps.

		Parameters
		----------
		timestamp_start : str
			Start timestamp.
		timestamp_end : str
			End timestamp.
		int_hour_start_office : int
			Start hour of office.
			Default is 8.
		int_minute_start_office : int
			Start minute of office.
			Default is 0.
		int_hour_end_office : int
			End hour of office.
			Default is 18.
		int_minute_end_office : int
			End minute of office.
			Default is 0.
		int_hour_start_lunch : int
			Start hour of lunch.
			Default is 12.
		int_minute_start_lunch : int
			Start minute of lunch.
			Default is 0.
		int_hour_end_lunch : int
			End hour of lunch.
			Default is 13.
		int_minute_end_lunch : int
			End minute of lunch.
			Default is 0.
		list_working_days_range : Optional[list[int]]
			List of working days.
			Default is [0, 1, 2, 3, 4] (monday to friday).
		substr_timestamp : str
			Substring to remove from the timestamp.
			Default is "T".

		Returns
		-------
		int
			Number of working hours between two timestamps.
		"""
		dt_start = self.timestamp_to_datetime(timestamp_start, substr_timestamp)
		dt_end = self.timestamp_to_datetime(timestamp_end, substr_timestamp)

		if list_working_days_range is None:
			list_working_days_range = [0, 1, 2, 3, 4]  # monday to friday

		# get holidays for the relevant years
		holidays_dict = {}
		for year in range(dt_start.year, dt_end.year + 1):
			for holiday_name, holiday_date in self.holidays():
				if holiday_date.year == year:
					holidays_dict[holiday_date] = holiday_name

		# create business time rules
		workday = businesstimedelta.WorkDayRule(
			start_time=time(int_hour_start_office, int_minute_start_office),
			end_time=time(int_hour_end_office, int_minute_end_office),
			working_days=list_working_days_range,
		)

		lunchbreak = businesstimedelta.LunchTimeRule(
			start_time=time(int_hour_start_lunch, int_minute_start_lunch),
			end_time=time(int_hour_end_lunch, int_minute_end_lunch),
			working_days=list_working_days_range,
		)

		rules = [workday, lunchbreak]

		if holidays_dict:
			holidays_rule = businesstimedelta.HolidayRule(holidays_dict)
			rules.append(holidays_rule)

		businesshrs = businesstimedelta.Rules(rules)
		delta = businesshrs.difference(dt_start, dt_end)

		# convert timedelta to hours
		return int(delta.hours)
