"""Minimal dict/tabular helpers used by the calendar providers.

Exposes only ``pair_headers_with_data``, which the US calendars use to zip a flat scraped
value list back into row dicts. Stdlib-only.
"""

from typing import Any

from wwdates._internal.utils.typing import TypeChecker


class HandlingDicts(metaclass=TypeChecker):
	"""Small, dependency-free dict helpers for the calendar providers."""

	def pair_headers_with_data(
		self, list_headers: list[str], list_data: list[Any]
	) -> list[dict[str, Any]]:
		"""Pair headers with a flat data list to build a list of row dicts.

		Parameters
		----------
		list_headers : list[str]
			List of header / field names.
		list_data : list[Any]
			Flat list of data values, row-major.

		Returns
		-------
		list[dict[str, Any]]
			One dict per row, mapping each header to its value.

		Raises
		------
		ValueError
			If ``list_data`` length is not a multiple of ``list_headers`` length.
		"""
		if len(list_data) % len(list_headers) != 0:
			raise ValueError(
				f"Data length {len(list_data)} not multiple of headers {len(list_headers)}"
			)

		return [
			{list_headers[j]: list_data[i + j] for j in range(len(list_headers))}
			for i in range(0, len(list_data), len(list_headers))
		]
