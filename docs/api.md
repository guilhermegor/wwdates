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
| [`DatesUSFederalHolidays`](#datesusfederalholidays) | `wwdates.us.federal_holidays` | US **federal** public holidays (offline, default) |
| [`DatesUSFederalHolidaysWeb`](#datesusfederalholidaysweb) | `wwdates.us.federal_holidays_web` | US federal holidays via live scrape (Playwright) |

### Constructor parameters

The **network-backed** providers (`DatesBRAnbima`, `DatesBRFebraban`, `DatesBRB3`,
`DatesUSNasdaq`, `DatesUSFederalHolidaysWeb`) share these cache parameters:

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `bool_persist_cache` | `bool` | `True` | Write the fetched calendar to disk. |
| `bool_reuse_cache` | `bool` | `True` | Reuse the in-memory cache within a run. |
| `int_days_cache_expiration` | `int` | `1` | Re-fetch once the cache is older than N days. |
| `int_cache_ttl_days` | `int` | `30` | Prune cache files older than N days. |
| `path_cache_dir` | `str \| None` | `None` | Override the default cache directory. |
| `logger` | `logging.Logger \| None` | `None` | Logger for cache / fetch messages. |

The **offline** `DatesUSFederalHolidays` computes its holidays locally, so it has **no cache
parameters** — its constructor takes only `int_year_start`, `int_year_end`, and an optional
`logger`. Providers that fetch a year range (`DatesBRFebraban`, both US federal classes) also
take `int_year_start` / `int_year_end`.

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

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_holidays_raw` | `(timeout=(12.0, 21.0))` | `DataFrame` | Download and read the raw ANBIMA workbook. |
| `get_holidays_raw_cached` | `(timeout=(12.0, 21.0))` | `DataFrame` | Cached wrapper over `get_holidays_raw`. |
| `transform_holidays` | `(df_)` | `DataFrame` | Normalise the raw rows to typed `(NAME, DATE)`. |

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

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_holidays_years` | `()` | `DataFrame` | Fetch the raw FEBRABAN holidays for the configured years. |
| `transform_holidays` | `(df_)` | `DataFrame` | Normalise the raw rows to typed `(NAME, DATE)`. |

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

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_anbima_holidays` | `(timeout=(12.0, 21.0))` | `DataFrame` | Fetch the ANBIMA base holiday set. |
| `add_holidays_b3` | `(df_holidays_anbima)` | `DataFrame` | Append the B3 exchange non-trading days to the ANBIMA frame. |
| `get_holidays_transformed` | `(timeout=(12.0, 21.0))` | `DataFrame` | The full ANBIMA + B3 typed holiday frame. |
| `holidays_to_add` | `(df_)` | `list[tuple[str, date]]` | The extra `(name, date)` pairs B3 adds beyond ANBIMA. |
| `get_christmas_eve` | `(int_year)` | `date` | 24 December of `int_year` (added when `bool_add_christmas_eve` is set). |

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

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_holidays_raw` | `(timeout=(12.0, 21.0))` | `DataFrame` | Fetch the raw Nasdaq market closures. |
| `transform_holidays` | `(df_)` | `DataFrame` | Normalise the raw rows to typed `(NAME, DATE)`. |

### `DatesUSFederalHolidays`

The **default, recommended** US federal calendar — computed **offline**, no network and no
browser.

```python
from wwdates.us.federal_holidays import DatesUSFederalHolidays

DatesUSFederalHolidays(
    int_year_start=2024, int_year_end=2025,   # year range to compute
    logger=None,
)
```

**Holidays:** the eleven US **federal** public holidays for the requested year range (New
Year's, MLK, Washington's Birthday, Memorial, Juneteenth, Independence, Labor, Columbus,
Veterans, Thanksgiving, Christmas), computed from their statutory rules via the
[`holidays`](https://pypi.org/project/holidays/) package.

**Observed-day rule (5 U.S.C. §6103).** When a holiday falls on a weekend, the observed federal
closure day is **also** emitted: a Saturday holiday is observed the preceding Friday, a Sunday
holiday the following Monday. Both the statutory date **and** the observed date are returned —
e.g. for 2023, New Year's Day appears on **Sunday 1 Jan** *and* the observed closure on
**Monday 2 Jan**. Nothing is hidden or moved; the Monday is added because federal offices,
banks, and markets are genuinely closed then, which is required for correct working-day math.

**Source:** the `holidays` package (offline computation). **No cache parameters** — there is
nothing to fetch, so the constructor takes only the year range and an optional logger.

**Provider-specific methods:** none beyond the [shared surface](#shared-calendar-operations);
`holidays()` returns the computed `(name, date)` list.

### `DatesUSFederalHolidaysWeb`

The **live-scrape** variant — use only when you specifically want the dates exactly as
published on federalholidays.net.

```python
from wwdates.us.federal_holidays_web import DatesUSFederalHolidaysWeb

DatesUSFederalHolidaysWeb(
    int_year_start=2025, int_year_end=2026,   # year range to fetch
    bool_persist_cache=True, bool_reuse_cache=True,
    int_days_cache_expiration=1, int_cache_ttl_days=30,
    path_cache_dir=None, logger=None,
)
```

**Holidays:** US federal holidays as published on the site, for the requested year range.

**Source:** `federalholidays.net` — scraped with **Playwright**, so run `playwright install
chromium` once before first use. Prefer the offline `DatesUSFederalHolidays` unless you need
this site's exact published dates.

**Provider-specific methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_holidays_years` | `()` | `DataFrame` | Scrape the federal holidays for the configured years. |
| `get_holidays_raw` | `(int_year, timeout=5000)` | `DataFrame` | Scrape one year via Playwright. |
| `transform_holidays` | `(df_)` | `DataFrame` | Normalise the raw rows to typed `(NAME, DATE)`. |

---

## Shared calendar operations

**Every provider inherits all of the methods below** — they are canonical to each calendar
class. They come from a linear chain of internal capability mixins that build up the
`ABCCalendarOperations` facade every provider extends:

```
ABCCalendar → CalendarCore → DateManipulation → DateTimezoneAware
            → DatesRangeDelta → DatesCurrent → DateFormatter → ABCCalendarOperations
```

Each layer below lists the methods it contributes. Throughout, `date_` accepts either a
`date` or a `datetime`.

### Holidays & working-day predicates — `CalendarCore`

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `holidays` | `()` | `list[tuple[str, date]]` | Every holiday the provider loads, as `(name, date)` pairs — the base set all working-day logic builds on. |
| `holidays_in_year` | `(int_year)` | `list[int]` | Day-of-year ordinals that fall on a holiday in `int_year`; handy for fast membership checks. |
| `is_holiday` | `(date_)` | `bool` | Whether the date is a loaded holiday. Gate settlement / trading logic on this. |
| `is_weekend` | `(date_)` | `bool` | Whether the date is a Saturday or Sunday. |
| `is_working_day` | `(date_)` | `bool` | The core business-day test — `True` when the date is neither weekend nor holiday. |
| `date_only` | `(date_)` | `date` | Normalise a `datetime` to its `date`, dropping the time; used before day arithmetic. |
| `get_holidays_raw` | `(timeout=(12.0, 21.0))` | `DataFrame` | The untransformed upstream holiday table — for debugging or custom pipelines. |

### Date manipulation — `DateManipulation`

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add_holidays` | `(list_new_holidays)` | `None` | Inject extra `(name, date)` holidays at runtime — e.g. a one-off company closure on top of the official set. |
| `add_working_days` | `(date_, int_days_to_add)` | `date` | Advance by N business days, skipping weekends + holidays (negative N goes back). The T+N settlement primitive. |
| `add_calendar_days` | `(date_, int_days_to_add)` | `date` | Add N calendar days, ignoring weekends/holidays. |
| `add_months` | `(date_, int_months_to_add)` | `datetime` | Add N calendar months, preserving day-of-month where valid. |
| `nearest_working_day` | `(date_, bool_next=True)` | `date` | Snap a date to the nearest business day — forward by default, backward with `bool_next=False`. Rolls a due date off a holiday. |
| `build_date` | `(year, month, day)` | `date` | Construct a `date` from components. |
| `build_datetime` | `(year, month, day, hour, minute, second, str_timezone="UTC")` | `datetime` | Construct a timezone-aware `datetime` from components. |
| `str_date_to_date` | `(str_date, format_input="DD/MM/YYYY")` | `date` | Parse a date string using a format token (e.g. `"YYYY-MM-DD"`) into a `date`. |
| `timestamp_to_date` | `(timestamp_, substr_timestamp="T")` | `date` | Parse a timestamp string into a `date`, splitting on `substr_timestamp`. |
| `timestamp_to_datetime` | `(timestamp_, substr_timestamp="T")` | `datetime` | Parse a timestamp string into a `datetime`. |
| `excel_float_to_date` | `(numeric_excel_date)` | `date` | Convert an Excel serial number to a `date` (handles the 1900 leap-year bug). |
| `to_integer` | `(date_)` | `int` | Encode a date as a `YYYYMMDD` integer — a compact sortable key for storage/comparison. |

### Timezone & timestamp conversion — `DateTimezoneAware`

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `change_timezone` | `(date_, target_tz="UTC", source_tz=None)` | `datetime` | Re-express a date/datetime in `target_tz`; pass `source_tz` for naive inputs. |
| `date_to_datetime` | `(date_, str_timezone="UTC")` | `datetime` | Promote a `date` to a midnight `datetime` in the given timezone. |
| `str_date_to_datetime` | `(str_date, format_input="DD/MM/YYYY", str_timezone="UTC")` | `datetime` | Parse a date string to a timezone-aware `datetime`. |
| `to_unix_timestamp` | `(date_, str_timezone="UTC")` | `int` | Convert a date / datetime / time to Unix epoch seconds. |
| `iso_to_unix_timestamp` | `(iso_timestamp, str_timezone="UTC")` | `int` | Convert an ISO-8601 string to Unix epoch seconds. |
| `unix_timestamp_to_date` | `(unix_timestamp, str_timezone="UTC")` | `date` | Convert Unix epoch seconds back to a `date` in the given timezone. |
| `unix_timestamp_to_datetime` | `(unix_timestamp, str_timezone="UTC")` | `datetime` | Convert Unix epoch seconds back to a `datetime`. |
| `excel_float_to_datetime` | `(float_date, str_timezone="UTC")` | `datetime` | Convert an Excel serial number to a timezone-aware `datetime`, including the fractional-day time. |

### Ranges & deltas — `DatesRangeDelta`

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `working_days_range` | `(date_start, date_end)` | `set[date]` | All business days within `[start, end]` inclusive. |
| `calendar_days_range` | `(date_start, date_end)` | `set[date]` | All calendar days within `[start, end]` inclusive. |
| `delta_working_days` | `(date_start, date_end)` | `int` | Count of business days between two dates — e.g. SLA / aging in business days. |
| `delta_calendar_days` | `(date_start, date_end)` | `int` | Count of calendar days between two dates. |
| `delta_working_hours` | `(timestamp_start, timestamp_end, …office/lunch hours…)` | `int` | Business hours between two timestamps, honouring configurable office + lunch windows and holidays. |
| `get_dates_weekday_month` | `(year, month, weekday)` | `list[date]` | Every occurrence of a given weekday in a month (e.g. all Mondays). |
| `get_last_working_day_years` | `(list_years)` | `list[date]` | The last business day of each requested year — for year-end processing. |
| `get_nth_weekday_month` | `(year, month, weekday, n, bool_working_days=True, bool_next_working_day=True)` | `date` | The n-th given weekday of a month (e.g. 3rd Wednesday — options expiry), optionally rolled to a working day. |
| `get_start_end_day_month` | `(date_, bool_working_days=False)` | `tuple[date, date]` | The first and last day of a date's month, optionally as working days. |
| `years_between_dates` | `(date_start, date_end)` | `set[int]` | The set of calendar years a range spans. |

### Current date & time — `DatesCurrent`

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `curr_date` | `()` | `date` | Today's date. |
| `curr_datetime` | `(str_timezone="UTC")` | `datetime` | The current datetime in the given timezone. |
| `curr_time` | `(str_timezone="UTC")` | `time` | The current time-of-day in the given timezone. |
| `current_timestamp_string` | `(format_output="%Y%m%d_%H%M%S", str_timezone="UTC")` | `str` | The current timestamp formatted as a string — handy for filenames / log keys. |

### Formatting & components — `DateFormatter`

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `day_number` | `(date_)` | `int` | Day of month (1–31). |
| `week_number` | `(date_)` | `str` | ISO week number. |
| `month_number` | `(date_, bool_month_mm=False)` | `int \| str` | Month as an `int`, or a zero-padded `"MM"` string when `bool_month_mm=True`. |
| `month_name` | `(date_, bool_abbreviation=False, str_timezone="UTC")` | `str` | Locale-aware month name (full, or abbreviated when `bool_abbreviation=True`). |
| `month_str` | `(date_)` | `str` | Month rendered as a string. |
| `year_number` | `(date_)` | `int` | Four-digit year. |
| `weekday_name` | `(date_, bool_abbreviation=False, str_timezone="UTC")` | `str` | Locale-aware weekday name (full, or abbreviated when `bool_abbreviation=True`). |
| `get_platform_locale` | `(str_locale=None, str_timezone=None)` | `str` | Resolve a platform-appropriate locale string backing the name methods above. |
| `utc_log_ts` | `()` | `datetime` | A UTC datetime intended for log timestamps. |

---

## Conventions

| Convention | Rule |
|------------|------|
| Public API | Country providers under `wwdates.<cc>.<provider>`; one class per module. |
| Private code | Everything under `wwdates._internal` is off-limits — internal, may change. |
| Type hints | Required on all public methods, including `-> None` returns. |
| Docstrings | NumPy style; explain *why*, not *what*. |
