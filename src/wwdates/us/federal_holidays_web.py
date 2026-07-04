"""US federal holiday calendar — live web-scrape variant.

Scrapes federalholidays.net with Playwright. Prefer the offline
:class:`wwdates.us.federal_holidays.DatesUSFederalHolidays` (computed via the ``holidays``
package, no browser); use this variant only when you specifically want the dates as published
on that site. Requires a Playwright browser binary: run ``playwright install chromium`` once.
"""

from datetime import date, timedelta
from logging import Logger

import pandas as pd

from wwdates._internal.utils.cache.cache_manager import CacheManager
from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations
from wwdates._internal.utils.parsers.dicts import HandlingDicts
from wwdates._internal.utils.parsers.html import HtmlHandler
from wwdates._internal.utils.webdriver_tools.playwright_wd import PlaywrightScraper


class DatesUSFederalHolidaysWeb(ABCCalendarOperations):
	"""US federal holiday calendar scraped live from federalholidays.net (Playwright).

	Reflects the dates as published on that site. For an offline, browser-free calendar that
	applies the statutory observed-day rule (5 U.S.C. §6103), prefer
	:class:`wwdates.us.federal_holidays.DatesUSFederalHolidays`.

	References
	----------
	[1] https://www.federalholidays.net
	"""

	def __init__(
		self,
		int_year_start: int = (date.today() - timedelta(days=22)).year - 1,
		int_year_end: int = (date.today() - timedelta(days=22)).year,
		bool_persist_cache: bool = True,
		bool_reuse_cache: bool = True,
		int_days_cache_expiration: int = 1,
		int_cache_ttl_days: int = 30,
		path_cache_dir: str | None = None,
		logger: Logger | None = None,
	) -> None:
		"""Initialize Federal holidays handler with HTML and dict utilities.

		Parameters
		----------
		int_year_start : int
			Starting year for holidays (default: (date.today() - timedelta(days=22)).year - 1)
		int_year_end : int
			Ending year for holidays (default: (date.today() - timedelta(days=22)).year)
		bool_persist_cache : bool
			If True, saves cache to disk; if False, uses in-memory cache only (default: True)
		bool_reuse_cache : bool
			If True, caches in-memory; if False, does not cache in-memory (default: True)
		int_days_cache_expiration : int
			Number of days after which the cache expires (default: 1)
		int_cache_ttl_days : int
			Number of days after which the cache is considered expired (default: 30)
		path_cache_dir : Optional[str]
			Path to the cache directory (default: None)
		logger : Optional[Logger]
			Logger object for logging (default: None)

		Returns
		-------
		None
		"""
		self.int_year_start = int_year_start
		self.int_year_end = int_year_end
		self.cls_cache_manager = CacheManager(
			bool_persist_cache=bool_persist_cache,
			bool_reuse_cache=bool_reuse_cache,
			int_days_cache_expiration=int_days_cache_expiration,
			int_cache_ttl_days=int_cache_ttl_days,
			path_cache_dir=path_cache_dir,
			logger=logger,
		)
		self.cls_html_handler = HtmlHandler()
		self.cls_dict_handler = HandlingDicts()

	def holidays(self) -> list[tuple[str, date]]:
		"""Get list of US Federal holidays with names and dates.

		Returns
		-------
		list[tuple[str, date]]
			list of tuples containing holiday name and date
		"""
		df_ = self.get_holidays_years()
		df_ = self.transform_holidays(df_)
		return [(row["NAME"], row["DATE_WINS"]) for _, row in df_.iterrows()]

	@CacheManager.cache_df(key="usa_federal_holidays_web")
	def get_holidays_years(self) -> pd.DataFrame:
		"""Fetch Federal holidays for multiple years.

		Returns
		-------
		pd.DataFrame
			Combined holiday data for all specified years
		"""
		self._validate_year_range(self.int_year_start, self.int_year_end)
		list_ser = []
		for int_year in range(self.int_year_start, self.int_year_end + 1):
			list_ser.extend(self.get_holidays_raw(int_year).to_dict(orient="records"))
		return pd.DataFrame(list_ser)

	def get_holidays_raw(  # type: ignore[override]  # federalholidays.net is scraped per-year: int_year is required, unlike the base's optional-arg contract
		self, int_year: int, timeout: int | None = 5000
	) -> pd.DataFrame:
		"""Fetch raw Federal holiday data for specific year.

		Parameters
		----------
		int_year : int
			Year to fetch holidays for
		timeout : Optional[int]
			Playwright timeout in milliseconds (default: 5000)

		Returns
		-------
		pd.DataFrame
			Raw holiday data with DATE, WEEKDAY, NAME, YEAR columns

		Raises
		------
		RuntimeError
			If Playwright navigation or data extraction fails
		"""
		self._validate_year(int_year)
		url = f"https://www.federalholidays.net/usa/federal-holidays-{int_year}.html"
		scraper = PlaywrightScraper(
			bool_headless=True, int_default_timeout=timeout if timeout is not None else 5000
		)
		try:
			with scraper.launch():
				if not scraper.navigate(url):
					raise RuntimeError(f"Failed to navigate to URL: {url}")
				list_td = [
					x.replace(r"\n", "").strip()
					for x in scraper.get_list_data("//table/tbody/tr/td", selector_type="xpath")
				]
			list_ser = self.cls_dict_handler.pair_headers_with_data(
				["DATE", "WEEKDAY", "NAME"], list_td
			)
			df_ = pd.DataFrame(list_ser)
			df_["YEAR"] = int_year
			return df_
		except Exception as err:
			raise RuntimeError(
				f"Failed to fetch Federal holidays for {int_year}: {str(err)}"
			) from err

	def transform_holidays(self, df_: pd.DataFrame) -> pd.DataFrame:
		"""Transform raw Federal holiday data into structured format.

		Parameters
		----------
		df_ : pd.DataFrame
			Raw holiday data from get_holidays_raw

		Returns
		-------
		pd.DataFrame
			Transformed data with DATE_WINS as date objects
		"""
		self._validate_federal_holidays_dataframe(df_)
		df_ = df_.astype({"DATE": str, "WEEKDAY": str, "NAME": str, "YEAR": int})
		df_["DATE_WINS"] = [
			self._parse_dates(str_dt=row["DATE"], int_year=row["YEAR"])
			for _, row in df_.iterrows()
		]
		return df_

	def _parse_dates(self, str_dt: str, int_year: int) -> date:
		"""Parse date string into date object using provided year.

		Parameters
		----------
		str_dt : str
			Date string in format "Month Day"
		int_year : int
			Year to use for date construction

		Returns
		-------
		date
			Parsed date object

		Raises
		------
		ValueError
			If date string format is invalid or month is unrecognized
		"""
		self._validate_date_string(str_dt)
		dict_mappings = {
			"January": 1,
			"February": 2,
			"March": 3,
			"April": 4,
			"May": 5,
			"June": 6,
			"July": 7,
			"August": 8,
			"September": 9,
			"October": 10,
			"November": 11,
			"December": 12,
		}
		list_parts_dt = [x.replace(",", "") for x in str_dt.split(" ") if x]
		if list_parts_dt[0] in dict_mappings:
			month = dict_mappings[list_parts_dt[0]]
			day = int(list_parts_dt[1])
		else:
			try:
				day = int(list_parts_dt[0])
				month = dict_mappings[list_parts_dt[1]]
			except (IndexError, KeyError, ValueError) as err:
				raise ValueError(
					f"Invalid date format: {str_dt}. Expected 'Month Day' "
					f"or 'Day Month'. Error: {err}"
				) from err

		return date(int_year, month, day)

	def _validate_year_range(self, int_year_start: int, int_year_end: int) -> None:
		"""Validate year range parameters.

		Parameters
		----------
		int_year_start : int
			Starting year
		int_year_end : int
			Ending year

		Raises
		------
		ValueError
			If years are not positive integers or range is invalid
		"""
		self._validate_year(int_year_start)
		self._validate_year(int_year_end)
		if int_year_start > int_year_end:
			raise ValueError("Start year must be less than or equal to end year")

	def _validate_year(self, int_year: int) -> None:
		"""Validate year parameter.

		Parameters
		----------
		int_year : int
			Year to validate

		Raises
		------
		ValueError
			If year is not a positive integer
		"""
		if int_year <= 0:
			raise ValueError("Year must be a positive integer")

	def _validate_federal_holidays_dataframe(self, df_: pd.DataFrame) -> None:
		"""Validate Federal holidays DataFrame structure and content.

		Parameters
		----------
		df_ : pd.DataFrame
			DataFrame to validate

		Raises
		------
		ValueError
			If DataFrame is empty or missing required columns
		"""
		if df_.empty:
			raise ValueError("Federal holidays DataFrame cannot be empty")
		required_columns = {"DATE", "WEEKDAY", "NAME", "YEAR"}
		if not required_columns.issubset(df_.columns):
			raise ValueError(f"DataFrame must contain columns: {required_columns}")

	def _validate_date_string(self, str_dt: str) -> None:
		"""Validate date string format.

		Parameters
		----------
		str_dt : str
			Date string to validate

		Raises
		------
		ValueError
			If date string is empty, not a string, or has invalid format
		"""
		if not str_dt:
			raise ValueError("Date string cannot be empty")
		if len(str_dt.split(" ")) < 2:
			raise ValueError("Date string must contain month and day components")
