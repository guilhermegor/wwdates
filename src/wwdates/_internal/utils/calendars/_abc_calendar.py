"""ABCCalendar — abstract base of the calendar mixin chain."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal, TypeVar

import pandas as pd

from wwdates._internal.utils.typing import ABCTypeCheckerMeta


# A bounded TypeVar over the accepted date-format strings. Kept a TypeVar (not a plain Literal
# alias) on purpose: the runtime TypeChecker enforces Literal membership eagerly, which would
# raise TypeError for an unknown format before each method's own ValueError validation runs —
# changing the public error contract. The TypeVar keeps that validation in the methods.
TypeDateFormatInput = TypeVar(
	"TypeDateFormatInput",
	bound=Literal[
		"DD/MM/YYYY",
		"D/M/YYYY",
		"YYYY-MM-DD",
		"YYYY-MM-DDTHH:MM:SS",
		"YYMMDD",
		"DDMMYY",
		"DDMMYYYY",
		"DMMYYY",
		"YYYYMMDD",
		"MM-DD-YYYY",
		"DD/MM/YY",
		"DD.MM.YY",
	],
)

# A "date-like" input annotation, not a generic: methods accept either a date or a datetime
# and normalise internally. A plain union alias (not a TypeVar) lets mypy narrow the value to
# the concrete type after normalisation, which a bounded TypeVar cannot.
TypeDatetimeDate = datetime | date


class ABCCalendar(ABC, metaclass=ABCTypeCheckerMeta):
	"""Abstract base class for calendar operations."""

	@abstractmethod
	def get_holidays_raw(
		self, timeout: int | float | tuple[float, float] | tuple[int, int] = (12.0, 21.0)
	) -> pd.DataFrame:
		"""Return a DataFrame containing raw holiday data.

		Parameters
		----------
		timeout : int | float | tuple[float, float] | tuple[int, int]
			Timeout for HTTP request, by default (12.0, 21.0)

		Returns
		-------
		pd.DataFrame
			DataFrame containing raw holiday data
		"""
		pass

	@abstractmethod
	def holidays(self) -> list[tuple[str, date]]:
		"""Return a list of tuples containing holiday names and dates.

		Returns
		-------
		list[tuple[str, date]]
			List of tuples containing holiday names and dates
		"""
		pass
