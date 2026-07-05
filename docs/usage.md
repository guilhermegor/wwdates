# **Usage**

Installing and using `wwdates`.

> **See also:** [API Reference](api.md) for the full method list · [Contributing](contributing.md)
> to develop or release the library.

---

## Installation

```bash
pip install wwdates
```

Or with Poetry:

```bash
poetry add wwdates
```

Everything above works offline after install — **no browser needed**. The recommended
`DatesUSFederalHolidays` computes federal holidays locally.

### Optional: the browser-scrape provider (`[web]` extra)

**Only** `DatesUSFederalHolidaysWeb` needs a browser — it scrapes federalholidays.net with
Playwright, which the base package does **not** install. It is **vital only when you
specifically want that provider's live-scraped dates**; otherwise use the offline
`DatesUSFederalHolidays` and skip this.

Install the optional `web` extra (quote the brackets so the shell does not glob them), then
download the browser binary:

```bash
pip install "wwdates[web]"   # adds Playwright
playwright install chromium  # one-time browser download (pip cannot do this)
```

Without both, constructing/using `DatesUSFederalHolidaysWeb` raises a clear `ImportError` with
these instructions.

---

## Choosing a provider

Every provider exposes the same calendar-operations surface (see [API Reference](api.md)); they
differ only in **which** holidays they load.

```python
from wwdates.br.anbima import DatesBRAnbima      # ANBIMA national holidays
from wwdates.br.febraban import DatesBRFebraban  # FEBRABAN bank holidays
from wwdates.br.b3 import DatesBRB3              # ANBIMA + B3 exchange extras
from wwdates.us.nasdaq import DatesUSNasdaq      # Nasdaq trading calendar
from wwdates.us.federal_holidays import DatesUSFederalHolidays  # offline, recommended
from wwdates.us.federal_holidays_web import DatesUSFederalHolidaysWeb  # live scrape (Playwright)
```

You can also import from the country package:

```python
from wwdates.br import DatesBRAnbima, DatesBRB3, DatesBRFebraban
from wwdates.us import DatesUSNasdaq, DatesUSFederalHolidays, DatesUSFederalHolidaysWeb
```

Fetched calendars are cached locally so repeated calls stay fast and offline-friendly; the
cache controls are documented in the [API Reference](api.md#constructor-parameters) and their
internals in [Contributing](contributing.md#caching-internals).

---

## Working with business days

```python
from datetime import date

from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3()

cls_cal.is_working_day(date(2024, 12, 25))   # False — Christmas
cls_cal.is_holiday(date(2024, 12, 25))       # True
cls_cal.is_weekend(date(2024, 12, 28))       # True — Saturday

# Add three business days, skipping weekends and holidays.
cls_cal.add_working_days(date(2024, 12, 24), 3)     # -> date(2024, 12, 30)

# Nearest business day on or after (or before) a given date.
cls_cal.nearest_working_day(date(2024, 12, 25), bool_next=True)

# Count / list business days in a range.
cls_cal.delta_working_days(date(2024, 12, 1), date(2024, 12, 31))
cls_cal.working_days_range(date(2024, 12, 1), date(2024, 12, 31))
```

`DatesBRB3` here is just an example — the same methods work on every provider
(`DatesBRAnbima`, `DatesBRFebraban`, `DatesUSNasdaq`, `DatesUSFederalHolidays`,
`DatesUSFederalHolidaysWeb`); only the
loaded holiday set differs. See the [API Reference](api.md) for the full list of classes and
their shared methods.

---

## Listing holidays

Every provider returns `(name, date)` tuples:

```python
from wwdates.us.nasdaq import DatesUSNasdaq

for name, day in DatesUSNasdaq().holidays():
    print(day, name)
```
