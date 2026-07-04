"""FEBRABAN Brazilian holiday calendar."""

from datetime import date, timedelta
from logging import Logger

import pandas as pd
import requests

from wwdates._internal.utils.cache.cache_manager import CacheManager
from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations
from wwdates._internal.utils.parsers.str import StrHandler


class DatesBRFebraban(ABCCalendarOperations):
	"""FEBRABAN Brazilian holiday calendar implementation.

	This class fetches and processes holiday data from FEBRABAN's JSON API,
	providing standardized holiday information for financial operations.

	References
	----------
	.. [1] https://feriadosbancarios.febraban.org.br/
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
		"""Initialize the DatesBRFebraban class.

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
			The logger to use (default: None)

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
		self.cls_str_handler = StrHandler()

	def _source_holidays(self) -> list[tuple[str, date]]:
		"""Get list of Brazilian holidays from FEBRABAN.

		Returns
		-------
		list[tuple[str, date]]
			List of holiday tuples containing (name, date)
		"""
		df_ = self.get_holidays_years()
		df_ = self.transform_holidays(df_)
		return [(row["NOME_FERIADO"], row["DIA_MES_ANO"]) for _, row in df_.iterrows()]

	@CacheManager.cache_df(key="br_febraban_holidays_raw")
	def get_holidays_years(self) -> pd.DataFrame:
		"""Fetch holiday data for multiple years from FEBRABAN.

		Parameters
		----------
		int_year_start : int
			Starting year, by default (date.today() - timedelta(days=22)).year - 1
		int_year_end : int
			Ending year, by default (date.today() - timedelta(days=22)).year

		Returns
		-------
		pd.DataFrame
			Combined holiday data for multiple years
		"""
		self._validate_year_range(self.int_year_start, self.int_year_end)
		list_holidays = []
		for int_year in range(self.int_year_start, self.int_year_end + 1):
			raw_data = self.get_holidays_raw(int_year)
			df_ = pd.DataFrame(raw_data) if isinstance(raw_data, list) else raw_data
			df_["ANO"] = int_year
			list_holidays.extend(df_.to_dict(orient="records"))
		return pd.DataFrame(list_holidays)

	def get_holidays_raw(  # type: ignore[override]  # FEBRABAN fetches per-year: int_year is required, unlike the base's optional-arg contract
		self,
		int_year: int,
		timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0),
	) -> pd.DataFrame:
		"""Fetch raw holiday data from FEBRABAN API for specific year.

		Parameters
		----------
		int_year : int
			Year to fetch holidays for
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			Raw holiday data as a DataFrame
		"""
		self._validate_year(int_year)
		url = (
			f"https://feriadosbancarios.febraban.org.br/Home/ObterFeriadosFederais?ano={int_year}"
		)

		headers = {
			"Accept": "application/json, text/javascript, */*; q=0.01",
			"Accept-Language": "en-US,en;q=0.9,pt;q=0.8,es;q=0.7",
			"Connection": "keep-alive",
			"Referer": "https://feriadosbancarios.febraban.org.br/",
			"Sec-Fetch-Dest": "empty",
			"Sec-Fetch-Mode": "cors",
			"Sec-Fetch-Site": "same-origin",
			"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",  # noqa E501: line too long
			"X-Requested-With": "XMLHttpRequest",
			"sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
			"sec-ch-ua-mobile": "?0",
			"sec-ch-ua-platform": '"Linux"',
		}

		cookies = {
			"cookiesession1": "678A3E1BC76EE4FED06EE2AB5ECEBCA3",
			"ai_user": "mhow/6j5BLAqjymITLwhjp|2025-08-26T19:55:49.930Z",
			"_ga": "GA1.1.1869622352.1756238150",
			"ai_session": "bZbh0ZzASkZdB8vurjJhQt|1756238150270|1756238150270",
			"_ga_KJWKM4PZXY": "GS2.1.s1756238150$o1$g0$t1756238155$j55$l0$h0",
		}

		resp_req = requests.get(url, headers=headers, cookies=cookies, timeout=timeout)
		resp_req.raise_for_status()
		json_response = resp_req.json()
		self._validate_json_response(json_response, int_year)
		return pd.DataFrame(json_response)

	def transform_holidays(self, df_: pd.DataFrame) -> pd.DataFrame:
		"""Transform raw holiday data into standardized format.

		Parameters
		----------
		df_ : pd.DataFrame
			Raw holiday data from FEBRABAN

		Returns
		-------
		pd.DataFrame
			Standardized holiday data with proper types
		"""
		self._validate_dataframe(df_, "df_holidays_raw")

		df_ = df_.astype({"diaMes": str, "diaSemana": str, "nomeFeriado": str, "ANO": int})
		df_["diaMesAno"] = [
			self._parse_brazillian_date(row["diaMes"], int_year=row["ANO"])
			for _, row in df_.iterrows()
		]
		df_.columns = [
			self.cls_str_handler.convert_case(x, "camel", "upper_constant") for x in df_.columns
		]
		df_["NOME_FERIADO"] = [
			self.cls_str_handler.remove_diacritics(self.cls_str_handler.latin_characters(x))
			for x in df_["NOME_FERIADO"].tolist()
		]

		self._validate_dataframe(df_, "df_holidays_standardized")
		return df_

	def _parse_brazillian_date(self, date_str: str, int_year: int) -> date:
		"""Parse Brazilian date string into date object.

		Parameters
		----------
		date_str : str
			Brazilian date string (e.g., "1 de janeiro")
		int_year : int
			Year to use for date construction

		Returns
		-------
		date
			Parsed date object

		Raises
		------
		ValueError
			If date format is invalid or parsing fails
		"""
		self._validate_date_string(date_str)
		self._validate_year(int_year)
		dict_month_map = {
			"janeiro": 1,
			"fevereiro": 2,
			"marco": 3,
			"abril": 4,
			"maio": 5,
			"junho": 6,
			"julho": 7,
			"agosto": 8,
			"setembro": 9,
			"outubro": 10,
			"novembro": 11,
			"dezembro": 12,
		}

		try:
			list_parts_date = [part for part in date_str.split(" ") if part]
			day = int(list_parts_date[0])
			month_name = list_parts_date[2].lower()
			month_name = self.cls_str_handler.remove_diacritics(
				self.cls_str_handler.latin_characters(month_name)
			)
			month = dict_month_map[month_name]
			return date(year=int_year, month=month, day=day)
		except (ValueError, KeyError, IndexError) as err:
			raise ValueError(f"Invalid date format: {date_str}") from err

	def _validate_dataframe(self, df_: pd.DataFrame, name: str) -> None:
		"""Validate DataFrame structure and content.

		Parameters
		----------
		df_ : pd.DataFrame
			DataFrame to validate
		name : str
			Variable name for error messages

		Raises
		------
		ValueError
			If DataFrame is empty, None, or has invalid structure
		"""
		if df_ is None:
			raise ValueError(f"{name} cannot be None")
		if not isinstance(df_, pd.DataFrame):
			raise ValueError(f"{name} must be a pandas DataFrame")
		if df_.empty:
			raise ValueError(f"{name} cannot be empty")

	def _validate_year(self, year: int) -> None:
		"""Validate year value.

		Parameters
		----------
		year : int
			Year to validate

		Raises
		------
		ValueError
			If year is not positive or reasonable
		"""
		if not isinstance(year, int):
			raise ValueError("Year must be an integer")
		if year < 1900 or year > 2100:
			raise ValueError(f"Year must be between 1900 and 2100, got {year}")

	def _validate_year_range(self, start_year: int, end_year: int) -> None:
		"""Validate year range.

		Parameters
		----------
		start_year : int
			Start year of range
		end_year : int
			End year of range

		Raises
		------
		ValueError
			If range is invalid or years are unreasonable
		"""
		self._validate_year(start_year)
		self._validate_year(end_year)
		if start_year > end_year:
			raise ValueError(f"Start year {start_year} cannot be after end year {end_year}")

	def _validate_date_string(self, date_str: str) -> None:
		"""Validate Brazilian date string format.

		Parameters
		----------
		date_str : str
			Date string to validate

		Raises
		------
		ValueError
			If string is empty, None, or doesn't match expected format
		"""
		if not date_str:
			raise ValueError("Date string cannot be empty")
		if not isinstance(date_str, str):
			raise ValueError("Date string must be a string")
		if " de " not in date_str:
			raise ValueError(f"Date string must contain ' de ' separator: {date_str}")

	def _validate_json_response(self, json_response: list[dict], year: int) -> None:
		"""Validate FEBRABAN JSON response structure.

		Parameters
		----------
		json_response : list[dict]
			JSON response to validate
		year : int
			Year used for the request

		Raises
		------
		ValueError
			If response is empty, None, or has invalid structure
		"""
		if json_response is None:
			raise ValueError(f"JSON response for year {year} cannot be None")
		if not isinstance(json_response, list):
			raise ValueError(f"JSON response for year {year} must be a list")
		if not json_response:
			raise ValueError(f"JSON response for year {year} cannot be empty")
