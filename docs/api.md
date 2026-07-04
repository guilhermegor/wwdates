# **API Reference**

Complete public interface for `wwdates`.

> **See also:** [Usage](usage.md)

The public API is the set of **country providers**, one class per module under a two-letter
country package (`wwdates.<country>.<provider>`). Every provider **loads a different holiday
calendar** but **shares the same date-operations surface** — the [shared calendar
operations](#shared-calendar-operations) documented at the bottom of this page.

| Provider | Import | Holidays it loads |
|----------|--------|-------------------|
| [`DatesBRAnbima`](#datesbranbima) | `wwdates.br.anbima` | Brazilian **national** holidays (ANBIMA) |
| [`DatesBRFebraban`](#datesbrfebraban) | `wwdates.br.febraban` | Brazilian **bank** holidays (FEBRABAN) |
| [`DatesBRB3`](#datesbrb3) | `wwdates.br.b3` | ANBIMA national **+ B3 exchange** non-trading days |
| [`DatesUSNasdaq`](#datesusnasdaq) | `wwdates.us.nasdaq` | US **Nasdaq** market-closure days |
| [`DatesUSFederalHolidays`](#datesusfederalholidays) | `wwdates.us.federal_holidays` | US **federal** public holidays |

### Constructor parameters

All providers share these constructor parameters:

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `bool_persist_cache` | `bool` | `True` | Write the fetched calendar to disk. |
| `bool_reuse_cache` | `bool` | `True` | Reuse the in-memory cache within a run. |
| `int_days_cache_expiration` | `int` | `1` | Re-fetch once the cache is older than N days. |
| `int_cache_ttl_days` | `int` | `30` | Prune cache files older than N days. |
| `path_cache_dir` | `str \| None` | `None` | Override the default cache directory. |
| `logger` | `logging.Logger \| None` | `None` | Logger for cache / fetch messages. |

---

## Brazil — `wwdates.br`

### `DatesBRAnbima`

```python
from wwdates.br.anbima import DatesBRAnbima

DatesBRAnbima(
    bool_persist_cache=True, bool_reuse_cache=True,
    int_days_cache_expiration=1, int_cache_ttl_days=30,
    path_cache_dir=None, logger=None,
)
```

**Holidays:** the Brazilian **national** holiday set published by ANBIMA — e.g. Confraternização
Universal (New Year), Carnaval, Sexta-feira Santa (Good Friday), Tiradentes, Dia do Trabalho,
Corpus Christi, Independência, Nossa Senhora Aparecida, Finados, Proclamação da República, Natal.
The authoritative list is fetched live from ANBIMA's workbook.

**Source:** `anbima.com.br/feriados/arqs/feriados_nacionais.xls` (read through a schema contract).

**Provider-specific methods** (in addition to the [shared surface](#shared-calendar-operations)):

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_holidays_raw` | `(timeout=(12.0, 21.0)) -> DataFrame` | Download + read the raw ANBIMA workbook. |
| `get_holidays_raw_cached` | `(timeout=(12.0, 21.0)) -> DataFrame` | Cached wrapper over `get_holidays_raw`. |
| `transform_holidays` | `(df_) -> DataFrame` | Normalise raw rows to typed `(NAME, DATE)`. |

### `DatesBRFebraban`

```python
from wwdates.br.febraban import DatesBRFebraban

DatesBRFebraban(
    int_year_start=2025, int_year_end=2026,   # year range to fetch
    bool_persist_cache=True, bool_reuse_cache=True,
    int_days_cache_expiration=1, int_cache_ttl_days=30,
    path_cache_dir=None, logger=None,
)
```

**Holidays:** Brazilian **bank** holidays (bank non-working days) as published by FEBRABAN for the
requested `int_year_start`…`int_year_end` range. Overlaps the national set but is the
banking-sector authority (what settles / clears).

**Source:** the FEBRABAN bank-holidays JSON API.

**Provider-specific methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_holidays_years` | `() -> DataFrame` | Fetch raw FEBRABAN holidays for the configured years. |
| `transform_holidays` | `(df_) -> DataFrame` | Normalise raw rows to typed `(NAME, DATE)`. |

### `DatesBRB3`

```python
from wwdates.br.b3 import DatesBRB3

DatesBRB3(
    bool_add_christmas_eve=False,   # also treat 24 Dec as a holiday
    bool_persist_cache=True, bool_reuse_cache=True,
    int_days_cache_expiration=1, int_cache_ttl_days=30,
    path_cache_dir=None, logger=None,
)
```

**Holidays:** the ANBIMA **national** set **plus** the B3 exchange's own non-trading days. Pass
`bool_add_christmas_eve=True` to additionally treat **24 December** (Christmas Eve) as a holiday,
matching B3's partial/closed-session convention. Use this provider for **trading-day** logic on
the Brazilian exchange.

**Source:** ANBIMA workbook + B3 exchange rules.

**Provider-specific methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_anbima_holidays` | `(timeout=(12.0, 21.0)) -> DataFrame` | Fetch the ANBIMA base set. |
| `add_holidays_b3` | `(df_holidays_anbima) -> DataFrame` | Append B3 exchange non-trading days. |
| `get_holidays_transformed` | `(timeout=(12.0, 21.0)) -> DataFrame` | Full ANBIMA+B3 typed frame. |
| `holidays_to_add` | `(df_) -> list[tuple[str, date]]` | The extra `(name, date)` pairs B3 adds. |
| `get_christmas_eve` | `(int_year) -> date` | 24 December of `int_year` (added when enabled). |

---

## United States — `wwdates.us`

### `DatesUSNasdaq`

```python
from wwdates.us.nasdaq import DatesUSNasdaq

DatesUSNasdaq(
    bool_persist_cache=True, bool_reuse_cache=True,
    int_days_cache_expiration=1, int_cache_ttl_days=30,
    path_cache_dir=None, logger=None,
)
```

**Holidays:** the days the **Nasdaq** stock market is closed — e.g. New Year's Day, Martin Luther
King Jr. Day, Presidents' Day, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day,
Thanksgiving, Christmas. Use this provider for **US market trading-day** logic.

**Source:** `nasdaqtrader.com` (requests-based scrape).

**Provider-specific methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_holidays_raw` | `(timeout=(12.0, 21.0)) -> DataFrame` | Fetch the raw Nasdaq closures. |
| `transform_holidays` | `(df_) -> DataFrame` | Normalise raw rows to typed `(NAME, DATE)`. |

### `DatesUSFederalHolidays`

```python
from wwdates.us.federal_holidays import DatesUSFederalHolidays

DatesUSFederalHolidays(
    int_year_start=2025, int_year_end=2026,   # year range to fetch
    bool_persist_cache=True, bool_reuse_cache=True,
    int_days_cache_expiration=1, int_cache_ttl_days=30,
    path_cache_dir=None, logger=None,
)
```

**Holidays:** US **federal** public holidays for the requested year range (the eleven federal
holidays — New Year's, MLK, Washington's Birthday, Memorial, Juneteenth, Independence, Labor,
Columbus, Veterans, Thanksgiving, Christmas). Distinct from Nasdaq market closures.

**Source:** `federalholidays.net` — scraped with **Playwright**, so run `playwright install
chromium` once before first use.

**Provider-specific methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_holidays_years` | `() -> DataFrame` | Scrape federal holidays for the configured years. |
| `transform_holidays` | `(df_) -> DataFrame` | Normalise raw rows to typed `(NAME, DATE)`. |

---

## Shared calendar operations

Every provider inherits the full surface below (from the internal `ABCCalendarOperations`
facade). `date_` accepts either a `date` or a `datetime`.

### Holidays & day predicates

| Method | Signature | Returns / purpose |
|--------|-----------|-------------------|
| `holidays` | `()` | `list[tuple[str, date]]` — every `(name, date)` the provider loads. |
| `holidays_in_year` | `(int_year)` | `list[int]` — ordinal days of the year that are holidays. |
| `is_holiday` | `(date_)` | `bool` |
| `is_weekend` | `(date_)` | `bool` |
| `is_working_day` | `(date_)` | `bool` — not weekend and not holiday. |
| `add_holidays` | `(list_new_holidays)` | `None` — inject extra `(name, date)` pairs at runtime. |
| `get_holidays_raw` | `(timeout=(12.0, 21.0))` | `DataFrame` — the raw upstream table. |

### Business-day & calendar arithmetic

| Method | Signature | Returns / purpose |
|--------|-----------|-------------------|
| `add_working_days` | `(date_, int_days_to_add)` | `date` — skips weekends + holidays (negative goes back). |
| `add_calendar_days` | `(date_, int_days_to_add)` | `date` — plain day arithmetic. |
| `add_months` | `(date_, int_months_to_add)` | `datetime` |
| `nearest_working_day` | `(date_, bool_next=True)` | `date` — nearest business day forward (or back). |
| `get_last_working_day_years` | `(list_years)` | `list[date]` — last business day of each year. |
| `get_nth_weekday_month` | `(year, month, weekday, n, bool_working_days=True, bool_next_working_day=True)` | `date` — the n-th given weekday of a month. |
| `get_dates_weekday_month` | `(year, month, weekday)` | `list[date]` — all of one weekday in a month. |
| `get_start_end_day_month` | `(date_, bool_working_days=False)` | `tuple[date, date]` — first/last day of the month. |

### Ranges & deltas

| Method | Signature | Returns / purpose |
|--------|-----------|-------------------|
| `working_days_range` | `(date_start, date_end)` | `set[date]` — business days in `[start, end]`. |
| `calendar_days_range` | `(date_start, date_end)` | `set[date]` — all days in `[start, end]`. |
| `delta_working_days` | `(date_start, date_end)` | `int` — count of business days between. |
| `delta_calendar_days` | `(date_start, date_end)` | `int` — count of calendar days between. |
| `delta_working_hours` | `(timestamp_start, timestamp_end, …office/lunch hours…)` | `int` — business hours between two timestamps. |
| `years_between_dates` | `(date_start, date_end)` | `set[int]` — the years spanned. |

### Current date & time

| Method | Signature | Returns / purpose |
|--------|-----------|-------------------|
| `curr_date` | `()` | `date` |
| `curr_datetime` | `(str_timezone="UTC")` | `datetime` |
| `curr_time` | `(str_timezone="UTC")` | `time` |
| `current_timestamp_string` | `(format_output="%Y%m%d_%H%M%S", str_timezone="UTC")` | `str` |
| `utc_log_ts` | `()` | `datetime` — UTC timestamp for logging. |

### Construction & conversion

| Method | Signature | Returns / purpose |
|--------|-----------|-------------------|
| `build_date` | `(year, month, day)` | `date` |
| `build_datetime` | `(year, month, day, hour, minute, second, str_timezone="UTC")` | `datetime` |
| `date_only` | `(date_)` | `date` — drop the time component. |
| `date_to_datetime` | `(date_, str_timezone="UTC")` | `datetime` |
| `str_date_to_date` | `(str_date, format_input="DD/MM/YYYY")` | `date` |
| `str_date_to_datetime` | `(str_date, format_input="DD/MM/YYYY", str_timezone="UTC")` | `datetime` |
| `timestamp_to_date` | `(timestamp_, substr_timestamp="T")` | `date` |
| `timestamp_to_datetime` | `(timestamp_, substr_timestamp="T")` | `datetime` |
| `to_unix_timestamp` | `(date_, str_timezone="UTC")` | `int` |
| `iso_to_unix_timestamp` | `(iso_timestamp, str_timezone="UTC")` | `int` |
| `unix_timestamp_to_date` | `(unix_timestamp, str_timezone="UTC")` | `date` |
| `unix_timestamp_to_datetime` | `(unix_timestamp, str_timezone="UTC")` | `datetime` |
| `excel_float_to_date` | `(numeric_excel_date)` | `date` — Excel serial → date. |
| `excel_float_to_datetime` | `(float_date, str_timezone="UTC")` | `datetime` |
| `to_integer` | `(date_)` | `int` — `YYYYMMDD` form. |
| `change_timezone` | `(date_, target_tz="UTC", source_tz=None)` | `datetime` |

### Components & naming

| Method | Signature | Returns / purpose |
|--------|-----------|-------------------|
| `day_number` | `(date_)` | `int` — day of month. |
| `week_number` | `(date_)` | `str` — ISO week. |
| `month_number` | `(date_, bool_month_mm=False)` | `int \| str` |
| `month_name` | `(date_, bool_abbreviation=False, str_timezone="UTC")` | `str` — locale-aware. |
| `month_str` | `(date_)` | `str` |
| `year_number` | `(date_)` | `int` |
| `weekday_name` | `(date_, bool_abbreviation=False, str_timezone="UTC")` | `str` — locale-aware. |
| `get_platform_locale` | `(str_locale=None, str_timezone=None)` | `str` |

---

## Conventions

| Convention | Rule |
|------------|------|
| Public API | Country providers under `wwdates.<cc>.<provider>`; one class per module. |
| Private code | Everything under `wwdates._internal` is off-limits — internal, may change. |
| Type hints | Required on all public methods, including `-> None` returns. |
| Docstrings | NumPy style; explain *why*, not *what*. |
