# **FAQ & Troubleshooting**

Common questions and fixes when using `wwdates`.

> **See also:** [Usage](usage.md) · [API Reference](api.md)

---

## Do I need `playwright install chromium`? / A provider raises a browser error

**Almost certainly not.** Every provider works offline after `pip install wwdates` — including
the recommended `DatesUSFederalHolidays`, which computes US federal holidays locally (no network,
no browser). Use it and you never touch Playwright.

The **only** class that needs a browser is the optional `DatesUSFederalHolidaysWeb` — a live
scrape of federalholidays.net. Playwright is **not** installed by the base package; enable it
with the `web` extra (quote the brackets so the shell does not glob them), then download the
browser binary:

```bash
pip install "wwdates[web]"   # adds Playwright
playwright install chromium  # one-time browser download (pip cannot do this)
```

Constructing or using `DatesUSFederalHolidaysWeb` without both steps raises an `ImportError`
telling you to run them. If you deploy in a container, run both in the image build so the browser
ships with it. Prefer `DatesUSFederalHolidays` (offline) unless you specifically need the scraped
site's published dates.

## Why does a US federal holiday show up on both a Sunday *and* the next Monday?

That is correct and intentional. `DatesUSFederalHolidays` follows the federal observed-day rule
(5 U.S.C. §6103): when a holiday lands on a weekend, the observed closure day is emitted **in
addition** to the statutory date — a Saturday holiday is observed the preceding Friday, a Sunday
holiday the following Monday. So for 2023, New Year's Day appears on **Sun 1 Jan** (statutory)
*and* **Mon 2 Jan** (observed). Nothing is moved or hidden; the Monday is added because federal
offices, banks, and markets are genuinely closed then — and `is_working_day(Mon 2 Jan)` must
return `False` for correct business-day math. Brazilian calendars have no such rule and keep
each holiday on its published date.

---

## Where are the cached holiday files, and how do I clear them?

Fetched calendars are cached per platform:

| OS | Default cache directory |
|----|-------------------------|
| Linux | `~/.cache/wwdates_calendar_cache/` |
| macOS | `~/.cache/wwdates_calendar_cache/` |
| Windows | `%APPDATA%\wwdates_calendar_cache\` |

Delete that directory to force a clean re-fetch:

```bash
# Linux
rm -rf ~/.cache/wwdates_calendar_cache
```

```bash
# macOS
rm -rf ~/.cache/wwdates_calendar_cache
```

```powershell
# Windows (PowerShell)
Remove-Item -Recurse -Force "$env:APPDATA\wwdates_calendar_cache"
```

Or skip disk entirely by constructing a provider with `bool_persist_cache=False`:

```python
from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3(bool_persist_cache=False)   # in-memory only
```

Point the cache elsewhere with `path_cache_dir="/some/path"`. See
[Caching internals](contributing.md#caching-internals) for the full controls.

---

## A holiday looks stale / I want fresh data now

The cache re-fetches once it is older than `int_days_cache_expiration` days (default `1`).
Force an immediate refresh by lowering it, clearing the cache directory, or disabling reuse:

```python
DatesBRAnbima(int_days_cache_expiration=0)   # always re-fetch
```

---

## `ZoneInfoNotFoundError` on a timezone lookup

`wwdates` depends on `tzdata` so the IANA timezone database is available even on systems that
ship none (notably Windows and minimal containers). If you see this error, confirm `tzdata`
installed alongside the package:

```bash
pip show tzdata
```

---

## Which provider should I use for trading-day logic?

- **Brazilian exchange (B3):** `DatesBRB3` — ANBIMA national holidays plus B3 non-trading
  days (optionally Christmas Eve).
- **Brazilian banking / settlement:** `DatesBRFebraban`.
- **US market:** `DatesUSNasdaq` (market closures) — not `DatesUSFederalHolidays`, which is
  the civil federal-holiday calendar.

See the [provider comparison table](api.md) for what each one loads.

---

## Can I add my own one-off holidays?

Yes — every provider inherits `add_holidays`:

```python
from datetime import date
from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3()
cls_cal.add_holidays([("Company offsite", date(2025, 6, 2))])
```
