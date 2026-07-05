"""DatesRangeDelta-derived — calendar mixin."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from wwdates._internal.utils.calendars._dates_range_delta import DatesRangeDelta


class DatesCurrent(DatesRangeDelta):
	"""Abstract class for getting current date and time."""

	def curr_date(self) -> date:
		"""Return the current date.

		Returns
		-------
		date
			Current date.
		"""
		return date.today()

	def curr_datetime(self, str_timezone: str | None = "UTC") -> datetime:
		"""Return the current datetime.

		Parameters
		----------
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		datetime
			Current datetime.
		"""
		return datetime.now(tz=ZoneInfo(str_timezone or "UTC"))

	def curr_time(self, str_timezone: str | None = "UTC") -> time:
		"""Return the current time.

		Parameters
		----------
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		time
			Current time.
		"""
		return self.curr_datetime(str_timezone=str_timezone).time()

	def current_timestamp_string(
		self, format_output: str = "%Y%m%d_%H%M%S", str_timezone: str | None = "UTC"
	) -> str:
		"""Return the current timestamp as a string.

		Parameters
		----------
		format_output : str
			The format to use, by default "%Y%m%d_%H%M%S"
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		str
			Current timestamp as a string.
		"""
		return self.curr_datetime(str_timezone=str_timezone).strftime(format_output)
