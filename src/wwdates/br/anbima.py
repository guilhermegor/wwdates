"""ANBIMA Brazilian holiday calendar."""

from datetime import date
from logging import Logger
from pathlib import Path
import tempfile

import pandas as pd
import requests

from wwdates._internal.config.contracts import ANBIMA_HOLIDAYS
from wwdates._internal.utils.cache.cache_manager import CacheManager
from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations
from wwdates._internal.utils.parsers.str import StrHandler
from wwdates._internal.utils.tabular_reader import read_table


class DatesBRAnbima(ABCCalendarOperations):
	"""ANBIMA Brazilian holiday calendar implementation.

	This class fetches and processes holiday data from ANBIMA's Excel format,
	providing standardized holiday information for financial operations.

	References
	----------
	.. [1] https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls
	"""

	def __init__(
		self,
		bool_persist_cache: bool = True,
		bool_reuse_cache: bool = True,
		int_days_cache_expiration: int = 1,
		int_cache_ttl_days: int = 30,
		path_cache_dir: str | None = None,
		logger: Logger | None = None,
	) -> None:
		"""Initialize the DatesBRAnbima class.

		Parameters
		----------
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
		self.cls_cache_manager = CacheManager(
			bool_persist_cache=bool_persist_cache,
			bool_reuse_cache=bool_reuse_cache,
			int_days_cache_expiration=int_days_cache_expiration,
			int_cache_ttl_days=int_cache_ttl_days,
			path_cache_dir=path_cache_dir,
			logger=logger,
		)
		self.cls_str_handler = StrHandler()

	def holidays(self) -> list[tuple[str, date]]:
		"""Get list of Brazilian holidays from ANBIMA.

		Returns
		-------
		list[tuple[str, date]]
			List of holiday tuples containing (name, date)
		"""
		df_ = self.get_holidays_raw_cached()
		df_ = self.transform_holidays(df_)
		return [(row["NAME"], row["DATE"]) for _, row in df_.iterrows()]

	@CacheManager.cache_df(key="br_anbima_holidays_raw")
	def get_holidays_raw_cached(
		self, timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0)
	) -> pd.DataFrame:
		"""Fetch raw holiday data from ANBIMA Excel file and cache it.

		Parameters
		----------
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			Raw holiday data with DATE, WEEKDAY, NAME columns
		"""
		return self.get_holidays_raw(timeout=timeout)

	def get_holidays_raw(
		self, timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0)
	) -> pd.DataFrame:
		"""Fetch raw holiday data from ANBIMA Excel file.

		Parameters
		----------
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			Raw holiday data with DATE, WEEKDAY, NAME columns
		"""
		url = "https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls"

		dict_headers = {
			"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa E501: line too long
			"accept-language": "en-US,en;q=0.9,pt;q=0.8,es;q=0.7",
			"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",  # noqa E501: line too long
		}

		resp_req = requests.get(url, headers=dict_headers, timeout=timeout)
		resp_req.raise_for_status()
		self._validate_response_content(resp_req.content)

		# ANBIMA serves a headerless workbook with a title banner on the first row. The reader
		# dispatches by file extension and needs a path, so the downloaded bytes are staged to a
		# temporary file and read through the contract rather than parsed inline.
		with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
			tmp.write(resp_req.content)
			path_tmp = Path(tmp.name)
		try:
			return read_table(
				path_file=path_tmp,
				str_sheet="",
				dict_dtypes={"DATE": "str", "WEEKDAY": "str", "NAME": "str"},
				cls_contract=ANBIMA_HOLIDAYS,
				list_columns=["DATE", "WEEKDAY", "NAME"],
				int_skip_rows=1,
			)
		finally:
			path_tmp.unlink(missing_ok=True)

	def transform_holidays(self, df_: pd.DataFrame) -> pd.DataFrame:
		"""Transform raw holiday data into standardized format.

		Parameters
		----------
		df_ : pd.DataFrame
			Raw holiday data from ANBIMA

		Returns
		-------
		pd.DataFrame
			Standardized holiday data with proper types
		"""
		self._validate_dataframe(df_, "df_holidays_raw")

		df_ = df_.astype({"DATE": str, "WEEKDAY": str, "NAME": str})
		df_ = self._remove_footer(df_)
		df_["DATE"] = [
			self.timestamp_to_date(d, substr_timestamp=" ") for d in df_["DATE"].tolist()
		]
		df_["NAME"] = [
			self.cls_str_handler.remove_diacritics(self.cls_str_handler.latin_characters(x))
			for x in df_["NAME"].tolist()
		]

		self._validate_dataframe(df_, "df_holidays_standardized")
		return df_

	def _remove_footer(self, df_: pd.DataFrame) -> pd.DataFrame:
		"""Remove footer content from ANBIMA DataFrame.

		Parameters
		----------
		df_ : pd.DataFrame
			Raw holiday DataFrame

		Returns
		-------
		pd.DataFrame
			DataFrame with footer rows removed
		"""
		self._validate_dataframe(df_, "df_to_remove_footer")
		footer_index = None

		for idx, row in df_.iterrows():
			if any("fonte: anbima" in str(cell).lower() for cell in row if pd.notna(cell)):
				footer_index = idx
				break

		if footer_index is not None:
			df_ = df_.iloc[:footer_index]

		self._validate_dataframe(df_, "df_removed_footer")
		return df_

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

	def _validate_response_content(self, content: bytes) -> None:
		"""Validate HTTP response content.

		Parameters
		----------
		content : bytes
			Response content to validate

		Raises
		------
		ValueError
			If content is empty or None
		"""
		if content is None:
			raise ValueError("Response content cannot be None")
		if len(content) == 0:
			raise ValueError("Response content cannot be empty")
