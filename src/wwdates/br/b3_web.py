"""B3 Brazilian exchange calendar — live scrape of B3's own trading calendar.

Unlike the offline :class:`wwdates.br.b3.DatesBRB3`, which computes the national holidays and
derives B3's extras from them, this class reads the exchange's published trading calendar
directly.

**Coverage is limited to whatever B3 currently publishes** — at the time of writing, 2021
through 2026, one accordion section per year and one table per month. For a calendar spanning
2001–2099, use the offline class.

The page is an **event feed**, not a holiday table: alongside B3's own closures it lists US
holidays for reference, FX-chamber (``Câmara de Câmbio``) settlement notes, and reduced-hours
sessions such as Ash Wednesday — on all of which the exchange trades. Rows are therefore
classified by B3's own wording in the description column ("não haverá negociação" marks a
closure) rather than by guessing from the event name.

Two consequences of reading the exchange directly are worth knowing:

- B3 omits holidays that fall on a weekend, since there is no session to cancel. Working-day
  math is unaffected — weekends are already non-working days.
- Christmas Eve appears as a genuine closure in the years it falls on a weekday, and 2021 also
  carries São Paulo's municipal and state holidays, which B3 stopped observing afterwards.
"""

from datetime import date
from logging import Logger
import re

from lxml.html import HtmlElement
import pandas as pd
import requests
from requests.exceptions import RequestException

from wwdates._internal.utils.cache.cache_manager import CacheManager
from wwdates._internal.utils.calendars.abc_calendar_operations import ABCCalendarOperations
from wwdates._internal.utils.parsers.html import HtmlHandler
from wwdates._internal.utils.parsers.str import StrHandler


# B3's wording for "the exchange is closed". Rows whose description does not carry it are
# sessions that happen — reduced hours, settlement notes, or foreign holidays listed for
# reference — and must not become holidays.
STR_MARKER_CLOSED = "nao havera negociacao"

DICT_MONTHS = {
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


class DatesBRB3Web(ABCCalendarOperations):
	"""B3 exchange calendar scraped from B3's published trading calendar.

	References
	----------
	.. [1] https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/calendario-de-negociacao/feriados/
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
		"""Initialize the DatesBRB3Web class.

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
			Logger object for logging (default: None)

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
		self.cls_html_handler = HtmlHandler()
		self.cls_str_handler = StrHandler()

	def _source_holidays(self) -> list[tuple[str, date]]:
		"""Get the days B3 does not trade, as published by the exchange.

		Returns
		-------
		list[tuple[str, date]]
			List of holiday tuples containing (name, date), sorted by date.
		"""
		df_ = self.get_holidays_raw()
		df_ = self.transform_holidays(df_)
		return [(row["NAME"], row["DATE"]) for _, row in df_.iterrows()]

	@CacheManager.cache_df(key="br_b3_web_holidays_raw")
	def get_holidays_raw(
		self, timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0)
	) -> pd.DataFrame:
		"""Fetch and flatten B3's trading calendar into one row per published event.

		The year comes from the outer accordion heading ("Calendário do mercado YYYY") and the
		month from the inner one, so each row can be dated without parsing free text.

		Parameters
		----------
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			Raw event data with YEAR, MONTH, DAY, NAME, DESCRIPTION columns.

		Raises
		------
		RequestException
			If the HTTP request fails or returns a non-200 status.
		ValueError
			If the page yields no parseable event rows.
		"""
		url = (
			"https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/"
			"para-participantes-e-traders/calendario-de-negociacao/feriados/"
		)
		dict_headers = {
			"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
			"accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
			"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",  # noqa E501: line too long
		}

		try:
			resp_req = requests.get(url, headers=dict_headers, timeout=timeout)
			resp_req.raise_for_status()
			root_html = self.cls_html_handler.lxml_parser(resp_req)
		except RequestException as err:
			raise RequestException(f"Failed to fetch B3 holidays: {str(err)}") from err

		list_rows = []
		for html_table in self.cls_html_handler.lxml_xpath(root_html, "//table"):
			tuple_labels = self._accordion_labels(html_table)
			if tuple_labels is None:
				continue
			int_year, int_month = tuple_labels
			for html_row in html_table.xpath(".//tr"):
				list_cells = [self._cell_text(x) for x in html_row.xpath("./td")]
				if len(list_cells) < 4 or not list_cells[0].isdigit():
					continue
				list_rows.append(
					{
						"YEAR": int_year,
						"MONTH": int_month,
						"DAY": int(list_cells[0]),
						"NAME": list_cells[1],
						"DESCRIPTION": list_cells[3],
					}
				)

		if not list_rows:
			raise ValueError("B3 calendar page yielded no parseable event rows")
		return pd.DataFrame(list_rows)

	def transform_holidays(self, df_: pd.DataFrame) -> pd.DataFrame:
		"""Keep only the days B3 is closed and give them a typed date.

		Parameters
		----------
		df_ : pd.DataFrame
			Raw event data from :meth:`get_holidays_raw`.

		Returns
		-------
		pd.DataFrame
			Standardized holiday data with DATE and NAME columns, sorted by date.

		Raises
		------
		ValueError
			If the frame is empty or missing the expected columns.
		"""
		self._validate_dataframe(df_)

		df_ = df_.astype({"YEAR": int, "MONTH": int, "DAY": int, "NAME": str, "DESCRIPTION": str})
		df_ = df_[
			[STR_MARKER_CLOSED in self._normalize(x) for x in df_["DESCRIPTION"].tolist()]
		].copy()
		if df_.empty:
			raise ValueError("No B3 closure rows found — the page wording may have changed")

		df_["DATE"] = [date(row["YEAR"], row["MONTH"], row["DAY"]) for _, row in df_.iterrows()]
		df_["NAME"] = [
			self.cls_str_handler.remove_diacritics(self.cls_str_handler.latin_characters(x))
			for x in df_["NAME"].tolist()
		]
		return df_.sort_values(by=["DATE"]).drop_duplicates(subset=["DATE"]).reset_index(drop=True)

	def _accordion_labels(self, html_table: HtmlElement) -> tuple[int, int] | None:
		"""Resolve the year and month a table sits under, from its accordion headings.

		Parameters
		----------
		html_table : HtmlElement
			The ``<table>`` element to locate.

		Returns
		-------
		tuple[int, int] | None
			``(year, month)``, or None when the table is not inside a year/month pair.
		"""
		list_labels = []
		for html_ancestor in html_table.iterancestors():
			if html_ancestor.tag != "li":
				continue
			if "accordion-navigation" not in (html_ancestor.get("class") or ""):
				continue
			list_anchors = html_ancestor.xpath("./a")
			if list_anchors:
				list_labels.append(self._cell_text(list_anchors[0]))
		list_labels.reverse()

		if len(list_labels) != 2:
			return None
		match_year = re.search(r"(\d{4})", list_labels[0])
		int_month = DICT_MONTHS.get(self._normalize(list_labels[1]))
		if match_year is None or int_month is None:
			return None
		return int(match_year.group(1)), int_month

	def _cell_text(self, html_element: HtmlElement) -> str:
		"""Return an element's text with whitespace collapsed.

		Parameters
		----------
		html_element : HtmlElement
			The element to read.

		Returns
		-------
		str
			The collapsed, stripped text content.
		"""
		return re.sub(r"\s+", " ", html_element.text_content() or "").strip()

	def _normalize(self, str_: str) -> str:
		"""Lower-case and strip diacritics, so wording matches survive accent changes.

		Parameters
		----------
		str_ : str
			Text to normalize.

		Returns
		-------
		str
			The normalized text.
		"""
		return self.cls_str_handler.remove_diacritics(
			self.cls_str_handler.latin_characters(str_)
		).lower()

	def _validate_dataframe(self, df_: pd.DataFrame) -> None:
		"""Validate the raw event frame before transforming it.

		Parameters
		----------
		df_ : pd.DataFrame
			DataFrame to validate.

		Raises
		------
		ValueError
			If the frame is empty or missing an expected column. A non-DataFrame input is
			already rejected by the annotation-driven type checker.
		"""
		if df_.empty:
			raise ValueError("df_holidays_raw cannot be empty")
		set_missing = {"YEAR", "MONTH", "DAY", "NAME", "DESCRIPTION"} - set(df_.columns)
		if set_missing:
			raise ValueError(f"df_holidays_raw is missing columns: {sorted(set_missing)}")
