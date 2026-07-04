# wwdates <img src="assets/logo_wwdates.png" align="right" width="200" style="border-radius: 15px;" alt="wwdates">

[![Project Status: Active](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
[![Linting](https://img.shields.io/badge/linting-ruff_|_codespell-blue)](https://github.com/astral-sh/ruff)
[![Type-checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue)](https://mypy-lang.org/)
![Test Coverage](./coverage.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Open Issues](https://img.shields.io/github/issues/guilhermegor/wwdates)
![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-darkgreen.svg)

Global calendar system. Python package.

`wwdates` fetches official holiday calendars for Brazil (ANBIMA, FEBRABAN, B3) and the United
States (Nasdaq, Federal Holidays), then layers a rich set of working-day / date helpers on top —
`is_working_day`, `add_working_days`, `working_days_range`, `delta_working_days`, timezone-aware
conversions, and more. Fetched calendars are cached locally so repeated calls stay fast and
offline-friendly.

📖 **Full documentation:** <https://guilhermegor.github.io/wwdates/>

## ✨ Key Features

### 🗓️ Holiday providers

One class per calendar source; all share the same date-operations surface — they differ only in
**which** holidays they load.

| Provider | Import | Holidays |
|----------|--------|----------|
| `DatesBRAnbima` | `wwdates.br.anbima` | 🇧🇷 ANBIMA national holidays |
| `DatesBRFebraban` | `wwdates.br.febraban` | 🇧🇷 FEBRABAN bank holidays |
| `DatesBRB3` | `wwdates.br.b3` | 🇧🇷 ANBIMA + B3 exchange non-trading days |
| `DatesUSNasdaq` | `wwdates.us.nasdaq` | 🇺🇸 Nasdaq market closures |
| `DatesUSFederalHolidays` | `wwdates.us.federal_holidays` | 🇺🇸 US federal holidays (offline, recommended) |
| `DatesUSFederalHolidaysWeb` | `wwdates.us.federal_holidays_web` | 🇺🇸 US federal holidays via live scrape |

### ⚙️ Shared calendar operations

Every provider inherits the full surface: working-day predicates (`is_working_day`, `is_holiday`,
`is_weekend`), business-day arithmetic (`add_working_days`, `nearest_working_day`,
`get_nth_weekday_month`), ranges & deltas (`working_days_range`, `delta_working_days`,
`delta_working_hours`), timezone/timestamp conversions, and locale-aware formatting. See the
[API Reference](https://guilhermegor.github.io/wwdates/api/) for the complete list.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Poetry (recommended)

### Installation

```bash
pip install wwdates
```

Or with Poetry:

```bash
poetry add wwdates
```

Everything works offline after install — **no browser needed**. The one exception is the optional
`DatesUSFederalHolidaysWeb` provider (a live scrape); if you use it, install its Playwright browser
once:

```bash
playwright install chromium
```

The recommended `DatesUSFederalHolidays` computes federal holidays offline and needs no browser.

### Quick start

```python
from datetime import date

from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3()
cls_cal.is_working_day(date(2024, 12, 25))       # False — Christmas
cls_cal.add_working_days(date(2024, 12, 24), 3)  # skips holidays + weekends
cls_cal.holidays()                               # [(name, date), ...]
```

`DatesBRB3` here is just an example — the same methods work on every provider; only the loaded
holiday set differs. More recipes in the
[Examples](https://guilhermegor.github.io/wwdates/examples/) guide.

## 📚 Documentation

- [Usage](https://guilhermegor.github.io/wwdates/usage/) — install, providers, basics
- [Examples](https://guilhermegor.github.io/wwdates/examples/) — task-oriented recipes
- [API Reference](https://guilhermegor.github.io/wwdates/api/) — every class and method
- [FAQ](https://guilhermegor.github.io/wwdates/faq/) — common questions & troubleshooting
- [Contributing](https://guilhermegor.github.io/wwdates/contributing/) — dev setup, tests, releasing
- [Changelog](https://guilhermegor.github.io/wwdates/changelog/) — release history

## 🛠️ Development

```bash
git clone https://github.com/guilhermegor/wwdates.git
cd wwdates
make init                  # or: bash tasks.sh init  (venv + deps + pre-commit hooks)
make unit_tests            # run the test suite
make install_dist_locally  # build the wheel and smoke-import it
```

See [Contributing](https://guilhermegor.github.io/wwdates/contributing/) for the full branch/PR
workflow and CI gate.

## 👨‍💻 Authors

- guilhermegor — [GitHub](https://github.com/guilhermegor)

## 📜 License

This project is licensed under the **MIT** License — see [`LICENSE`](LICENSE) for details.

## 🔗 Useful Links

- [Documentation](https://guilhermegor.github.io/wwdates/)
- [GitHub Repository](https://github.com/guilhermegor/wwdates)
- [Issue Tracker](https://github.com/guilhermegor/wwdates/issues)
