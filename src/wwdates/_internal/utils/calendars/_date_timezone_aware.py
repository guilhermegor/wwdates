"""DateManipulation-derived — calendar mixin."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from wwdates._internal.utils.calendars._abc_calendar import (
	TypeDatetimeDate,
)
from wwdates._internal.utils.calendars._date_manipulation import DateManipulation


class DateTimezoneAware(DateManipulation):
	"""Abstract class for date manipulation with timezone support."""

	def str_date_to_datetime(
		self,
		str_date: str,
		format_input: str | None = "DD/MM/YYYY",
		str_timezone: str | None = "UTC",
	) -> datetime:
		"""Convert a string representation of a date to a datetime object.

		Parameters
		----------
		str_date : str
			The string representation of the date.
		format_input : str | None
			The format of the input date string, by default "DD/MM/YYYY"
		str_timezone : Optional[str]
			The timezone to use for the resulting datetime object, by default "UTC"

		Returns
		-------
		datetime
			The datetime object corresponding to the input string.
		"""
		date_obj = self.str_date_to_date(str_date, format_input)
		return datetime.combine(date_obj, time(0, 0), tzinfo=ZoneInfo(str_timezone or "UTC"))

	def change_timezone(
		self, date_: TypeDatetimeDate, target_tz: str = "UTC", source_tz: str | None = None
	) -> datetime:
		"""Change the timezone of a datetime or date object.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The datetime or date object to change the timezone of.
		target_tz : str
			The target timezone, by default "UTC"
		source_tz : Optional[str]
			The source timezone, by default None

		Returns
		-------
		datetime
			The datetime object with the changed timezone.

		Raises
		------
		ValueError
			If date_ is a date object and source_tz is None
		"""
		if isinstance(date_, date) and not isinstance(date_, datetime):
			date_ = self.date_to_datetime(date_, str_timezone=target_tz)
		elif date_.tzinfo is None:
			if source_tz is None:
				raise ValueError("Cannot change timezone of naive datetime without source_tz")
			date_ = date_.replace(tzinfo=ZoneInfo(source_tz))
		return date_.astimezone(ZoneInfo(target_tz))

	def date_to_datetime(self, date_: date, str_timezone: str | None = "UTC") -> datetime:
		"""Convert a date object to a datetime object.

		Parameters
		----------
		date_ : date
			The date object to convert.
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		datetime
			The datetime object corresponding to the input date.
		"""
		return datetime.combine(date_, time(0, 0), tzinfo=ZoneInfo(str_timezone or "UTC"))

	def to_unix_timestamp(
		self, date_: TypeDatetimeDate | time, str_timezone: str | None = "UTC"
	) -> int:
		"""Convert date to unix timestamp (seconds since January 1, 1970, 00:00:00 UTC).

		Parameters
		----------
		date_ : TypeDatetimeDate | time
			Date to convert.
		str_timezone : Optional[str]
			Timezone to use, defaults to UTC.

		Returns
		-------
		int
			Unix timestamp.
		"""
		if isinstance(date_, time):
			today = date.today()
			date_ = datetime.combine(today, date_)
			date_ = date_.replace(tzinfo=ZoneInfo(str_timezone or "UTC"))
		elif isinstance(date_, date) and not isinstance(date_, datetime):
			date_ = self.date_to_datetime(date_, str_timezone=str_timezone)
		elif isinstance(date_, datetime) and date_.tzinfo is None:
			date_ = date_.replace(tzinfo=ZoneInfo(str_timezone or "UTC"))

		return int(date_.timestamp())

	def unix_timestamp_to_datetime(
		self, unix_timestamp: float | int, str_timezone: str | None = "UTC"
	) -> datetime:
		"""Convert unix timestamp to datetime object.

		Parameters
		----------
		unix_timestamp : float | int
			The unix timestamp to convert.
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		datetime
			The datetime object corresponding to the input unix timestamp.
		"""
		return datetime.fromtimestamp(unix_timestamp, tz=ZoneInfo(str_timezone or "UTC"))

	def unix_timestamp_to_date(
		self, unix_timestamp: float | int, str_timezone: str | None = "UTC"
	) -> date:
		"""Convert unix timestamp to date object.

		Parameters
		----------
		unix_timestamp : float | int
			The unix timestamp to convert.
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		date
			The date object corresponding to the input unix timestamp.
		"""
		return self.unix_timestamp_to_datetime(unix_timestamp, str_timezone=str_timezone).date()

	def iso_to_unix_timestamp(self, iso_timestamp: str, str_timezone: str | None = "UTC") -> int:
		"""Convert ISO timestamp to unix timestamp (seconds since January 1, 1970, 00:00:00 UTC).

		Parameters
		----------
		iso_timestamp : str
			The ISO timestamp to convert.
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		int
			The unix timestamp corresponding to the input ISO timestamp.
		"""
		date_ = datetime.fromisoformat(iso_timestamp)
		if date_.tzinfo is None:
			date_ = date_.replace(tzinfo=ZoneInfo(str_timezone or "UTC"))
		return int(date_.timestamp())

	def excel_float_to_datetime(
		self, float_date: float, str_timezone: str | None = "UTC"
	) -> datetime:
		"""Convert Excel float date to datetime object.

		Parameters
		----------
		float_date : float
			The Excel float date to convert.
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		datetime
			The datetime object corresponding to the input Excel float date.

		Raises
		------
		ValueError
			If float_date is negative
		"""
		if float_date < 0:
			raise ValueError("float_date cannot be negative")

		# excel's epoch starts at January 1, 1900, but we adjust for the leap year bug
		base_date = datetime(1899, 12, 31, tzinfo=ZoneInfo(str_timezone or "UTC"))

		int_days = int(float_date)
		float_fractional_days = float_date - int_days

		# adjust for Excel's leap year bug (1900 is not a leap year, but Excel treats it as one)  # noqa: ERA001,E501
		if float_date >= 60:
			int_days -= 1

		# calculate the date and time components
		result_date = base_date + timedelta(days=int_days)
		# convert fractional days to seconds (1 day = 86400 seconds)  # noqa: ERA001
		seconds = float_fractional_days * 86400
		result_datetime = result_date + timedelta(seconds=seconds)

		return result_datetime
