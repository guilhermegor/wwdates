"""Offline Brazilian banking-holiday source, computed via the ``holidays`` package.

Shared by the three offline BR providers. The source is ``holidays.B3`` (Brasil, Bolsa,
Balcão) — the Brazilian *financial market* calendar, not ``holidays.Brazil``. The latter is
the statutory-only national set and omits Carnaval (Monday and Tuesday) and Corpus Christi,
neither of which is a statutory national holiday but on both of which banks and markets close.

Verified equivalence against the live sources (see ``docs/backlog/``):

- ANBIMA (``feriados_nacionais.xls``, 2001–2099): identical to ``holidays.B3``, empty
  symmetric difference across all 99 published years.
- FEBRABAN (JSON endpoint, 2025–2026): identical to ``holidays.B3``.
- B3: ``holidays.B3`` plus the last working day of each year, which
  :class:`wwdates.br.b3.DatesBRB3` computes itself.
"""

from datetime import date

import holidays

from wwdates._internal.utils.parsers.str import StrHandler


# ANBIMA publishes its national holiday table over exactly this span; matching it keeps the
# offline providers a drop-in replacement for the web ones rather than a narrower calendar.
INT_YEAR_START_DEFAULT = 2001
INT_YEAR_END_DEFAULT = 2099


def national_holidays(
	int_year_start: int = INT_YEAR_START_DEFAULT,
	int_year_end: int = INT_YEAR_END_DEFAULT,
) -> list[tuple[str, date]]:
	"""Return the Brazilian banking holidays for a year range, computed offline.

	Parameters
	----------
	int_year_start : int
		First year to include (default: 2001).
	int_year_end : int
		Last year to include (default: 2099).

	Returns
	-------
	list[tuple[str, date]]
		Tuples of ``(name, date)``, sorted by date. Names are diacritic-stripped to match
		the normalisation the web providers apply.
	"""
	validate_year_range(int_year_start, int_year_end)
	cls_str_handler = StrHandler()
	dict_holidays = holidays.B3(years=range(int_year_start, int_year_end + 1))
	return [
		(
			cls_str_handler.remove_diacritics(cls_str_handler.latin_characters(str_name)),
			date_,
		)
		for date_, str_name in sorted(dict_holidays.items())
	]


def validate_year_range(int_year_start: int, int_year_end: int) -> None:
	"""Validate a year-range pair.

	Parameters
	----------
	int_year_start : int
		Starting year.
	int_year_end : int
		Ending year.

	Raises
	------
	ValueError
		If either year is outside 1900–2100, or the range is inverted.
	"""
	for int_year in (int_year_start, int_year_end):
		if not isinstance(int_year, int) or isinstance(int_year, bool):
			raise ValueError("Year must be an integer")
		if int_year < 1900 or int_year > 2100:
			raise ValueError(f"Year must be between 1900 and 2100, got {int_year}")
	if int_year_start > int_year_end:
		raise ValueError(f"Start year {int_year_start} cannot be after end year {int_year_end}")
