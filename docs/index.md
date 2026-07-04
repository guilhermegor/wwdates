# **wwdates**

Worldwide holiday calendars and business-day date operations for Python.

`wwdates` fetches official holiday calendars for Brazil (ANBIMA, FEBRABAN, B3) and the United
States (Nasdaq, Federal Holidays), then layers a rich set of working-day / date helpers on top
— `is_working_day`, `add_working_days`, `working_days_range`, `delta_working_days`,
timezone-aware conversions, and more. Fetched calendars are cached locally so repeated calls
stay fast and offline-friendly.

---

## Contents

| Section | Description |
|---------|-------------|
| [Usage](usage.md) | Installation, choosing a provider, and basic examples |
| [Examples](examples.md) | Task-oriented recipes (settlement dates, expiry, cross-market) |
| [API Reference](api.md) | Public providers and every shared calendar operation |
| [FAQ](faq.md) | Common questions and troubleshooting |
| [Contributing](contributing.md) | Dev setup, testing, wheel build, PR workflow, releasing |
| [Changelog](changelog.md) | Per-version release history |

---

## Quick start

```bash
pip install wwdates
```

```python
from datetime import date

from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3()
cls_cal.is_working_day(date(2024, 12, 25))          # False — Christmas
cls_cal.add_working_days(date(2024, 12, 24), 3)     # skips holidays + weekends
cls_cal.holidays()                                  # [(name, date), ...]
```

The US Federal Holidays provider scrapes with Playwright, so install its browser once:

```bash
playwright install chromium
```

---

## Providers at a glance

| Country | Import | Source |
|---------|--------|--------|
| 🇧🇷 Brazil | `from wwdates.br.anbima import DatesBRAnbima` | ANBIMA national holidays |
| 🇧🇷 Brazil | `from wwdates.br.febraban import DatesBRFebraban` | FEBRABAN bank holidays |
| 🇧🇷 Brazil | `from wwdates.br.b3 import DatesBRB3` | ANBIMA + B3 exchange extras |
| 🇺🇸 USA | `from wwdates.us.nasdaq import DatesUSNasdaq` | Nasdaq trading calendar |
| 🇺🇸 USA | `from wwdates.us.federal_holidays import DatesUSFederalHolidays` | US federal holidays |

---

Generated from the **lib-minimal** template via [BlueprintX](https://github.com/guilhermegor/BlueprintX).
