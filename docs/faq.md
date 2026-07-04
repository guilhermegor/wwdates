# **FAQ & Troubleshooting**

Common questions and fixes when using `wwdates`.

> **See also:** [Usage](usage.md) · [API Reference](api.md)

---

## `DatesUSFederalHolidays` raises a Playwright / browser error

That provider scrapes with a headless browser, which needs the Chromium binary installed
once (separate from the pip package):

```bash
playwright install chromium
```

If you deploy in a container, run this in the image build so the browser ships with it. The
other four providers (`DatesBRAnbima`, `DatesBRFebraban`, `DatesBRB3`, `DatesUSNasdaq`) use
plain HTTP and need no browser.

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
