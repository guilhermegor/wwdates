"""wwdates — worldwide holiday calendars and date operations.

Import the country subpackages for the concrete providers, e.g.
``from wwdates.br.b3 import DatesBRB3`` or ``from wwdates.us.nasdaq import DatesUSNasdaq``.
"""

from importlib.metadata import PackageNotFoundError, version


try:
	__version__ = version("wwdates")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed dist
	__version__ = "0.0.0"


__all__ = ["__version__"]
