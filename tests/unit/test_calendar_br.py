"""Unit tests for the offline Brazilian holiday calendars.

These need no mocking: the providers are computed from the ``holidays`` package, so the
autouse network guard in ``tests/conftest.py`` doubles as the proof that they are offline —
any accidental fetch would raise ``NetworkAccessError`` here.
"""

from datetime import date, timedelta

import pytest

from wwdates.br import DatesBRAnbima, DatesBRB3, DatesBRFebraban


# The 2026 ANBIMA table, as published in feriados_nacionais.xls. Carnaval (Feb 16-17) and
# Corpus Christi (Jun 4) are the entries `holidays.Brazil` omits and `holidays.B3` carries —
# the reason the offline source is the financial calendar, not the statutory one.
LIST_DATES_ANBIMA_2026 = [
	date(2026, 1, 1),
	date(2026, 2, 16),
	date(2026, 2, 17),
	date(2026, 4, 3),
	date(2026, 4, 21),
	date(2026, 5, 1),
	date(2026, 6, 4),
	date(2026, 9, 7),
	date(2026, 10, 12),
	date(2026, 11, 2),
	date(2026, 11, 15),
	date(2026, 11, 20),
	date(2026, 12, 25),
]


@pytest.fixture
def anbima_instance() -> DatesBRAnbima:
	"""Provide an offline ANBIMA calendar restricted to 2026.

	Returns
	-------
	DatesBRAnbima
		Instance covering 2026 only.
	"""
	return DatesBRAnbima(int_year_start=2026, int_year_end=2026)


@pytest.fixture
def b3_instance() -> DatesBRB3:
	"""Provide an offline B3 calendar restricted to 2026.

	Returns
	-------
	DatesBRB3
		Instance covering 2026 only.
	"""
	return DatesBRB3(int_year_start=2026, int_year_end=2026)


def test_anbima_matches_published_table() -> None:
	"""The offline ANBIMA calendar reproduces the published 2026 table exactly.

	Returns
	-------
	None
	"""
	cls_cal = DatesBRAnbima(int_year_start=2026, int_year_end=2026)
	assert [date_ for _, date_ in cls_cal._source_holidays()] == LIST_DATES_ANBIMA_2026


def test_anbima_carnival_and_corpus_christi_are_not_working_days(
	anbima_instance: DatesBRAnbima,
) -> None:
	"""Carnival and Corpus Christi close the banks, so they are not working days.

	Parameters
	----------
	anbima_instance : DatesBRAnbima
		Offline ANBIMA calendar covering 2026.

	Returns
	-------
	None
	"""
	for date_ in (date(2026, 2, 16), date(2026, 2, 17), date(2026, 6, 4)):
		assert anbima_instance.is_working_day(date_) is False


def test_anbima_default_range_covers_the_published_span() -> None:
	"""The default year range matches the span ANBIMA publishes, so it is a drop-in.

	Returns
	-------
	None
	"""
	list_dates = [date_ for _, date_ in DatesBRAnbima()._source_holidays()]
	assert min(list_dates).year == 2001
	assert max(list_dates).year == 2099


def test_febraban_matches_anbima_for_the_same_years() -> None:
	"""FEBRABAN's bank holidays are the same national set ANBIMA publishes.

	Returns
	-------
	None
	"""
	cls_febraban = DatesBRFebraban(int_year_start=2026, int_year_end=2026)
	assert [date_ for _, date_ in cls_febraban._source_holidays()] == LIST_DATES_ANBIMA_2026


def test_b3_adds_the_last_working_day_of_the_year(b3_instance: DatesBRB3) -> None:
	"""B3 does not trade on the last working day of the year, unlike the banks.

	Returns
	-------
	None
	"""
	set_dates = {date_ for _, date_ in b3_instance._source_holidays()}
	assert date(2026, 12, 31) in set_dates
	assert date(2026, 12, 31) not in set(LIST_DATES_ANBIMA_2026)


@pytest.mark.parametrize(
	("int_year", "date_expected"),
	[(2023, date(2023, 12, 29)), (2026, date(2026, 12, 31)), (2028, date(2028, 12, 29))],
)
def test_last_working_day_skips_weekends(
	b3_instance: DatesBRB3, int_year: int, date_expected: date
) -> None:
	"""The last working day walks back past weekends and holidays.

	Parameters
	----------
	b3_instance : DatesBRB3
		Offline B3 calendar.
	int_year : int
		Year under test.
	date_expected : date
		The last working day published by B3 for that year.

	Returns
	-------
	None
	"""
	cls_cal = DatesBRB3(int_year_start=int_year, int_year_end=int_year)
	set_dates = {date_ for _, date_ in DatesBRAnbima(int_year, int_year)._source_holidays()}
	assert cls_cal.get_last_working_day(int_year, set_dates) == date_expected


def test_b3_christmas_eve_is_opt_in() -> None:
	"""Christmas Eve is only a non-trading day when explicitly requested.

	Returns
	-------
	None
	"""
	kwargs = {"int_year_start": 2026, "int_year_end": 2026}
	set_without = {date_ for _, date_ in DatesBRB3(**kwargs)._source_holidays()}
	set_with = {
		date_ for _, date_ in DatesBRB3(bool_add_christmas_eve=True, **kwargs)._source_holidays()
	}
	assert date(2026, 12, 24) not in set_without
	assert set_with - set_without == {date(2026, 12, 24)}


def test_b3_holidays_are_sorted(b3_instance: DatesBRB3) -> None:
	"""The B3 extras are merged in date order, not appended at the end.

	Parameters
	----------
	b3_instance : DatesBRB3
		Offline B3 calendar.

	Returns
	-------
	None
	"""
	list_dates = [date_ for _, date_ in b3_instance._source_holidays()]
	assert list_dates == sorted(list_dates)


def test_working_day_arithmetic_crosses_carnival(anbima_instance: DatesBRAnbima) -> None:
	"""Adding a working day over the Carnival block lands after it, not inside.

	Parameters
	----------
	anbima_instance : DatesBRAnbima
		Offline ANBIMA calendar covering 2026.

	Returns
	-------
	None
	"""
	assert anbima_instance.add_working_days(date(2026, 2, 13), 1) == date(2026, 2, 18)


@pytest.mark.parametrize(
	("int_year_start", "int_year_end"),
	[(2026, 2025), (1800, 1900), (2000, 2200)],
)
def test_invalid_year_range_raises(int_year_start: int, int_year_end: int) -> None:
	"""An inverted or out-of-bounds year range fails fast.

	Parameters
	----------
	int_year_start : int
		Starting year under test.
	int_year_end : int
		Ending year under test.

	Returns
	-------
	None
	"""
	cls_cal = DatesBRAnbima(int_year_start=int_year_start, int_year_end=int_year_end)
	with pytest.raises(ValueError):
		cls_cal._source_holidays()


def test_add_holidays_merges_into_the_offline_provider(anbima_instance: DatesBRAnbima) -> None:
	"""A runtime-injected holiday reaches both `holidays()` and the working-day set.

	Parameters
	----------
	anbima_instance : DatesBRAnbima
		Offline ANBIMA calendar covering 2026.

	Returns
	-------
	None
	"""
	date_custom = date(2026, 3, 10)
	assert anbima_instance.is_working_day(date_custom) is True
	anbima_instance.add_holidays([("Feriado Interno", date_custom)])
	assert date_custom in {date_ for _, date_ in anbima_instance.holidays()}
	assert anbima_instance.is_working_day(date_custom) is False


def test_febraban_default_range_is_recent_years() -> None:
	"""FEBRABAN keeps its narrow rolling default rather than the full ANBIMA span.

	Returns
	-------
	None
	"""
	int_year_reference = (date.today() - timedelta(days=22)).year
	cls_febraban = DatesBRFebraban()
	assert cls_febraban.int_year_start == int_year_reference - 1
	assert cls_febraban.int_year_end == int_year_reference
