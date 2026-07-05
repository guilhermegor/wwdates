# **Examples & Recipes**

Task-oriented snippets for common date/holiday problems. Each is self-contained.

> **See also:** [Usage](usage.md) for the basics · [API Reference](api.md) for every method.

---

## Compute a T+N settlement date

Advance a trade date by N business days on the B3 exchange calendar:

```python
from datetime import date

from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3()
trade_date = date(2024, 12, 20)
settlement = cls_cal.add_working_days(trade_date, 2)   # T+2, skipping weekends + holidays
print(settlement)
```

---

## Roll a due date off a holiday/weekend

Snap a nominal due date to the next (or previous) business day:

```python
from datetime import date

from wwdates.br.anbima import DatesBRAnbima

cls_cal = DatesBRAnbima()
due = date(2025, 1, 1)                                  # New Year — a holiday
print(cls_cal.nearest_working_day(due, bool_next=True))  # first business day on/after
print(cls_cal.nearest_working_day(due, bool_next=False)) # last business day on/before
```

---

## Count business days between two dates

E.g. an SLA or aging metric in working days:

```python
from datetime import date

from wwdates.us.nasdaq import DatesUSNasdaq

cls_cal = DatesUSNasdaq()
opened = date(2024, 12, 20)
closed = date(2025, 1, 6)
print(cls_cal.delta_working_days(opened, closed))   # business days elapsed
```

---

## Find options expiry (3rd Friday of a month)

```python
from wwdates.us.nasdaq import DatesUSNasdaq

cls_cal = DatesUSNasdaq()
# weekday: Monday=0 … Friday=4; n=3 → the third Friday, rolled to a working day if needed.
expiry = cls_cal.get_nth_weekday_month(2025, 3, weekday=4, n=3)
print(expiry)
```

---

## List every holiday in a year

```python
from wwdates.br.b3 import DatesBRB3

cls_cal = DatesBRB3()
for name, day in sorted(cls_cal.holidays(), key=lambda pair: pair[1]):
    if day.year == 2025:
        print(day, name)
```

---

## Build a working-day set for fast membership tests

```python
from datetime import date

from wwdates.br.febraban import DatesBRFebraban

cls_cal = DatesBRFebraban()
business_days = cls_cal.working_days_range(date(2025, 1, 1), date(2025, 3, 31))
print(date(2025, 2, 17) in business_days)   # O(1) lookup against the quarter
```

---

## Cross-market: is it a working day in both BR and the US?

```python
from datetime import date

from wwdates.br.b3 import DatesBRB3
from wwdates.us.nasdaq import DatesUSNasdaq

cls_br = DatesBRB3()
cls_us = DatesUSNasdaq()

def is_dual_working_day(day: date) -> bool:
    """True only when both the B3 and Nasdaq calendars are open."""
    return cls_br.is_working_day(day) and cls_us.is_working_day(day)

print(is_dual_working_day(date(2025, 7, 4)))   # US Independence Day → False
```
