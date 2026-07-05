"""Data contract for the ANBIMA national-holidays workbook.

The ANBIMA ``.xls`` is headerless with a title banner on the first row, so it is read
``skiprows=1`` with the three columns assigned positionally (``DATE``, ``WEEKDAY``, ``NAME``)
via ``tabular_reader.read_table``; this contract asserts those columns are present before the
provider transforms them.
"""

from __future__ import annotations

from wwdates._internal.utils.tabular_reader import FileContract


# str_name, str_source_key, tuple_required, tuple_cnpj_cols (none — holidays carry no CNPJ).
ANBIMA_HOLIDAYS = FileContract(
	"ANBIMA National Holidays",
	"anbima_holidays",
	("DATE", "WEEKDAY", "NAME"),
	(),
)
