"""Brazilian holiday calendars (ANBIMA, FEBRABAN, B3).

Each provider comes in two flavours: an **offline** class (the default, computed from the
``holidays`` package — no network, no cache) and a ``*Web`` class that fetches the publisher's
live table. The two were verified to agree; see :mod:`wwdates.br._offline_holidays`.
"""

from wwdates.br.anbima import DatesBRAnbima
from wwdates.br.anbima_web import DatesBRAnbimaWeb
from wwdates.br.b3 import DatesBRB3
from wwdates.br.b3_web import DatesBRB3Web
from wwdates.br.febraban import DatesBRFebraban
from wwdates.br.febraban_web import DatesBRFebrabanWeb


__all__ = [
	"DatesBRAnbima",
	"DatesBRAnbimaWeb",
	"DatesBRB3",
	"DatesBRB3Web",
	"DatesBRFebraban",
	"DatesBRFebrabanWeb",
]
