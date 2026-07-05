"""DatesCurrent-derived — calendar mixin."""

from datetime import datetime, timezone
import locale
import platform

from wwdates._internal.utils.calendars._abc_calendar import (
	TypeDatetimeDate,
)
from wwdates._internal.utils.calendars._dates_current import DatesCurrent


class DateFormatter(DatesCurrent):
	"""Abstract class for date formatting."""

	def get_platform_locale(
		self, str_locale: str | None = None, str_timezone: str | None = None
	) -> str:
		"""Return the platform locale.

		Parameters
		----------
		str_locale : Optional[str]
			The locale to use, by default None
		str_timezone : Optional[str]
			The timezone to use, by default None

		Returns
		-------
		str
			The platform locale.

		Raises
		------
		ValueError
			If the locale is not found
		"""
		dict_tz_to_locale_map = {
			"America/Sao_Paulo": "pt-BR",
			"America/New_York": "en-US",
			"America/Chicago": "en-US",
			"America/Los_Angeles": "en-US",
			"Europe/Madrid": "es-ES",
			"Europe/Paris": "fr-FR",
			"Europe/London": "en-GB",
			"Asia/Tokyo": "ja-JP",
			"Asia/Shanghai": "zh-CN",
			"Asia/Seoul": "ko-KR",
			"UTC": "en-GB",
		}
		if (
			str_locale is None
			and str_timezone is not None
			and str_timezone in dict_tz_to_locale_map
		):
			str_locale = dict_tz_to_locale_map[str_timezone]
		if str_locale is None:
			str_locale = "en-GB"
		base_locale = str_locale.replace("_", "-").replace(".UTF-8", "")
		normalized_locale = (
			base_locale
			if platform.system() == "Windows"
			else f"{base_locale.replace('-', '_')}.UTF-8"
		)
		try:
			locale.setlocale(locale.LC_TIME, normalized_locale)
			return normalized_locale
		except locale.Error:
			normalized_locale = "en_GB.UTF-8" if platform.system() != "Windows" else "en-GB"
			try:
				locale.setlocale(locale.LC_TIME, normalized_locale)
				return normalized_locale
			except locale.Error as err:
				raise ValueError(
					f"Invalid or unsupported locale: {str_locale}. Error: {err}"
				) from err

	def year_number(self, date_: TypeDatetimeDate) -> int:
		"""Return the year number.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The date to get the year number from.

		Returns
		-------
		int
			The year number.
		"""
		date_ = self.date_only(date_)
		return int(date_.strftime("%Y"))

	def month_str(self, date_: TypeDatetimeDate) -> str:
		"""Return the month name.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The date to get the month name from.

		Returns
		-------
		str
			The month name.
		"""
		date_ = self.date_only(date_)
		return date_.strftime("%B")

	def month_number(self, date_: TypeDatetimeDate, bool_month_mm: bool = False) -> int | str:
		"""Return the month number.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The date to get the month number from.
		bool_month_mm : bool
			Whether to return the month number or the month name, by default False

		Returns
		-------
		int | str
			The month number or the month name.
		"""
		date_ = self.date_only(date_)
		if not bool_month_mm:
			return int(date_.strftime("%m"))
		else:
			return date_.strftime("%m")

	def week_number(self, date_: TypeDatetimeDate) -> str:
		"""Return the week number.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The date to get the week number from.

		Returns
		-------
		str
			The week number.
		"""
		date_ = self.date_only(date_)
		return date_.strftime("%w")

	def day_number(self, date_: TypeDatetimeDate) -> int:
		"""Return the day number.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The date to get the day number from.

		Returns
		-------
		int
			The day number.
		"""
		date_ = self.date_only(date_)
		return int(date_.strftime("%d"))

	def month_name(
		self,
		date_: TypeDatetimeDate,
		bool_abbreviation: bool = False,
		str_timezone: str | None = "UTC",
	) -> str:
		"""Return the month name.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The date to get the month name from.
		bool_abbreviation : bool
			Whether to return the month name or the month abbreviation, by default False
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		str
			The month name or the month abbreviation.
		"""
		date_ = self.date_only(date_)
		str_locale = self.get_platform_locale(str_timezone=str_timezone)
		locale.setlocale(locale.LC_TIME, str_locale)
		return date_.strftime("%b" if bool_abbreviation else "%B")

	def weekday_name(
		self,
		date_: TypeDatetimeDate,
		bool_abbreviation: bool = False,
		str_timezone: str | None = "UTC",
	) -> str:
		"""Return the week name.

		Parameters
		----------
		date_ : TypeDatetimeDate
			The date to get the week name from.
		bool_abbreviation : bool
			Whether to return the week name or the week abbreviation, by default False
		str_timezone : Optional[str]
			The timezone to use, by default "UTC"

		Returns
		-------
		str
			The week name or the week abbreviation.
		"""
		date_ = self.date_only(date_)
		str_locale = self.get_platform_locale(str_timezone=str_timezone)
		locale.setlocale(locale.LC_TIME, str_locale)
		return date_.strftime("%a" if bool_abbreviation else "%A")

	def utc_log_ts(self) -> datetime:
		"""Return the current UTC datetime.

		Returns
		-------
		datetime
			The current UTC datetime.
		"""
		return datetime.now(timezone.utc)
