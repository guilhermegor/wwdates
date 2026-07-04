"""B3 Brazilian holiday calendar."""

from datetime import date, timedelta
from logging import Logger

import pandas as pd

from wwdates._internal.utils.cache.cache_manager import CacheManager
from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations
from wwdates._internal.utils.parsers.str import StrHandler
from wwdates._internal.utils.typing import type_checker
from wwdates.br.anbima import DatesBRAnbima


class DatesBRB3(ABCCalendarOperations):
	"""B3 calendar class."""

	def __init__(
		self,
		bool_add_christmas_eve: bool = False,
		bool_persist_cache: bool = True,
		bool_reuse_cache: bool = True,
		int_days_cache_expiration: int = 1,
		int_cache_ttl_days: int = 30,
		path_cache_dir: str | None = None,
		logger: Logger | None = None,
	) -> None:
		"""Initialize the DatesBRB3 class.

		Parameters
		----------
		bool_add_christmas_eve : bool
			If True, adds Christmas Eve to the list of holidays (default: False)
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
		self.bool_add_christmas_eve = bool_add_christmas_eve
		self.cls_cache_manager = CacheManager(
			bool_persist_cache=bool_persist_cache,
			bool_reuse_cache=bool_reuse_cache,
			int_days_cache_expiration=int_days_cache_expiration,
			int_cache_ttl_days=int_cache_ttl_days,
			path_cache_dir=path_cache_dir,
			logger=logger,
		)
		self.cls_dates_br_anbima = DatesBRAnbima(
			bool_persist_cache=bool_persist_cache,
			bool_reuse_cache=bool_reuse_cache,
			int_days_cache_expiration=int_days_cache_expiration,
			int_cache_ttl_days=int_cache_ttl_days,
			path_cache_dir=path_cache_dir,
			logger=logger,
		)
		self.cls_str_handler = StrHandler()

	def holidays(self) -> list[tuple[str, date]]:
		"""Return a list of tuples containing holiday names and dates.

		Returns
		-------
		list[tuple[str, date]]
			List of tuples containing holiday names and dates
		"""
		df_ = self.get_holidays_transformed()
		return [(row["NAME"], row["DATE"]) for _, row in df_.iterrows()]

	@CacheManager.cache_df(key="br_b3_holidays_raw")
	def get_holidays_transformed(
		self, timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0)
	) -> pd.DataFrame:
		"""Fetch raw holiday data from ANBIMA Excel file, transform it and add B3 holidays.

		Parameters
		----------
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			DataFrame containing raw holiday data
		"""
		df_ = self.get_anbima_holidays(timeout=timeout)
		return self.add_holidays_b3(df_)

	def get_anbima_holidays(
		self, timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0)
	) -> pd.DataFrame:
		"""Fetch raw holiday data from ANBIMA Excel file and transform it.

		Parameters
		----------
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			DataFrame containing raw holiday data
		"""
		df_ = self.cls_dates_br_anbima.get_holidays_raw(timeout=timeout)
		return self.cls_dates_br_anbima.transform_holidays(df_)

	def add_holidays_b3(self, df_holidays_anbima: pd.DataFrame) -> pd.DataFrame:
		"""Add additional holidays to the DataFrame.

		Parameters
		----------
		df_holidays_anbima : pd.DataFrame
			DataFrame containing raw holiday data

		Returns
		-------
		pd.DataFrame
			DataFrame containing raw holiday data with additional holidays
		"""
		df_holidays_to_add = pd.DataFrame(
			self.holidays_to_add(df_holidays_anbima), columns=["NAME", "DATE"]
		)
		df_holidays_to_add["WEEKDAY"] = [
			self.weekday_name(date_, bool_abbreviation=False, str_timezone="America/Sao_Paulo")
			for date_ in df_holidays_to_add["DATE"].tolist()
		]
		df_holidays_to_add = df_holidays_to_add[["DATE", "WEEKDAY", "NAME"]]
		df_ = pd.concat([df_holidays_anbima, df_holidays_to_add], ignore_index=True).reset_index(
			drop=True
		)
		return df_.sort_values(by=["DATE"])

	def holidays_to_add(self, df_: pd.DataFrame) -> list[tuple[str, date]]:
		"""Add additional holidays to the DataFrame.

		Parameters
		----------
		df_ : pd.DataFrame
			DataFrame containing raw holiday data

		Returns
		-------
		list[tuple[str, date]]
			List of tuples containing holiday names and dates
		"""
		list_: list[tuple[str, date]] = []
		set_anbima_holidays = {row["DATE"] for _, row in df_.iterrows()}

		@type_checker
		def temp_is_working_day(date_current: date) -> bool:
			"""Temporary is working day function to avoid recursion.

			Parameters
			----------
			date_current : date
				The date to check.

			Returns
			-------
			bool
				True if the date is a working day, False otherwise.
			"""
			return not self.is_weekend(date_current) and date_current not in set_anbima_holidays

		@type_checker
		def temp_add_working_days(date_: date, int_days_to_add: int) -> date:
			"""Temporary add working days function to avoid recursion.

			Parameters
			----------
			date_ : date
				The date to start from.
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
				if temp_is_working_day(date_current):
					int_days_left -= 1
			return date_current

		set_years = {self.year_number(date_) for date_ in df_["DATE"].tolist()}
		for int_year in set_years:
			last_working_day = temp_add_working_days(date(int_year + 1, 1, 1), -1)
			list_.append(("Último Dia Útil do Ano", last_working_day))
			if self.bool_add_christmas_eve:
				list_.append(("Véspera de Natal", self.get_christmas_eve(int_year)))
		return list_

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
