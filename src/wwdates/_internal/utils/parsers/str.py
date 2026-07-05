"""Minimal string helpers used by the calendar providers.

Exposes only the members the calendars call (``latin_characters``, ``remove_diacritics``,
``convert_case``). Stdlib-only by design — no third-party text dependencies.
"""

import re
from unicodedata import combining, normalize

from wwdates._internal.utils.typing import TypeChecker


class StrHandler(metaclass=TypeChecker):
	"""Small, dependency-free string helpers for the calendar providers."""

	def latin_characters(self, str_: str) -> str:
		"""Re-decode a latin1-mis-decoded string as UTF-8.

		Parameters
		----------
		str_ : str
			The string to convert.

		Returns
		-------
		str
			The converted string, or the original if it cannot be re-decoded.
		"""
		try:
			return str_.encode("latin1").decode("utf-8")
		except (UnicodeEncodeError, UnicodeDecodeError):
			return str_

	def remove_diacritics(self, str_: str) -> str:
		"""Remove all diacritics (accents, cedillas, …) from a string.

		Parameters
		----------
		str_ : str
			The string with diacritics.

		Returns
		-------
		str
			The string with diacritics removed.
		"""
		norm_txt = normalize("NFD", str_)
		shaved = "".join(c for c in norm_txt if not combining(c))
		return normalize("NFC", shaved)

	def convert_case(self, str_: str, from_case: str, to_case: str) -> str:
		"""Convert a string between naming conventions.

		Supported cases: ``camel``, ``pascal``, ``kebab``, ``upper_constant``,
		``lower_constant``, ``snake``, ``upper_first`` and ``default`` (words separated by
		spaces, hyphens or underscores).

		Parameters
		----------
		str_ : str
			The string to convert.
		from_case : str
			Current case of the string.
		to_case : str
			Desired case of the string.

		Returns
		-------
		str
			The converted string.

		Raises
		------
		ValueError
			If ``from_case`` or ``to_case`` are invalid.
		"""
		if not str_:
			return ""

		# from case
		list_words: list[str]
		if from_case == "camel":
			str_camel = re.sub(r"([a-z])([A-Z])", r"\1_\2", str_)
			str_camel = re.sub(r"([a-zA-Z])(\d)", r"\1_\2", str_camel)
			str_camel = re.sub(r"(\d)([a-zA-Z])", r"\1_\2", str_camel)
			list_words = str_camel.lower().split("_")
		elif from_case == "pascal":
			list_words = re.sub(r"([a-z])([A-Z])", r"\1_\2", str_).lower().split("_")
		elif from_case == "kebab":
			list_words = str_.lower().split("-")
		elif from_case in ("upper_constant", "lower_constant", "snake"):
			list_words = str_.lower().split("_")
		elif from_case == "upper_first":
			list_words = [str_[0].upper() + str_[1:].lower()]
		elif from_case == "default":
			str_ = str_.replace(" - ", " ")
			str_ = str_.replace("-", " ")
			str_ = str_.replace("_", " ")
			str_ = str_.replace("+", " ")
			str_ = str_.replace(" (", " ")
			str_ = str_.replace(") ", " ")
			str_ = str_.replace(r"\n", " ")
			list_words = str_.lower().split()
		else:
			raise ValueError(
				"Invalid from_case. Choose from ['camel', 'pascal', 'snake', 'kebab', "
				"'upper_constant', 'lower_constant', 'upper_first']"
			)
		if not list_words:
			return ""

		# converting to case
		if to_case == "camel":
			return list_words[0] + "".join(word.capitalize() for word in list_words[1:])
		elif to_case == "pascal":
			return "".join(word.capitalize() for word in list_words)
		elif to_case in ("snake", "lower_constant"):
			return "_".join(list_words).lower()
		elif to_case == "kebab":
			return "-".join(list_words).lower()
		elif to_case == "upper_constant":
			return "_".join(list_words).upper()
		elif to_case == "upper_first":
			return list_words[0].capitalize() + " " + " ".join(word for word in list_words[1:])
		else:
			raise ValueError(
				"Invalid to_case. Choose from ['camel', 'pascal', 'snake', 'kebab', "
				"'upper_constant', 'lower_constant', 'upper_first']"
			)
