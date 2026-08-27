"""Is this point in Canada, and which analysis-area tier answers it?

Originally scoped to "is this worth asking the parcel cadastre" — the
Canadian counterpart to :mod:`camposcope.services.uf_lookup`. That question
still matters (ParcelMap BC is provincial; nothing outside BC has a parcel
fabric to query), but it is no longer the whole answer: a click outside BC, or
inside BC on unsurveyed land, is not necessarily a click on nothing. It falls
through to the protected-area lookup (``protected_areas.py``, national) and
then to a synthetic analysis square (``zones.py::synthetic_square_geojson``,
also national) before the page gives up on it — see
``canada/state/_parcel.py::CanadaParcelMixin.select_at_point`` for the three-
tier chain this module's :func:`classify` result drives.

**Three different "no parcel" reasons, and conflating any two of them is a
bug.** A parcel query can come back empty for reasons that call for entirely
different next steps:

* **Outside Canada.** Nothing on this page answers here at all — refused
  before any request leaves the machine, with a note pointing at the Brazil
  page if the coordinate looks South American.
* **Inside Canada, outside BC.** No parcel fabric exists here — expected, not
  a failure — so the chain moves straight to the protected-area tier rather
  than trying (and failing) a BC-only query against a point it was never going
  to answer for.
* **Inside BC, on unsurveyed land.** Much of the province is Crown land with
  no parcel in the fabric — sampled during development, several ordinary
  forested points in the Kootenays and the Okanagan highlands returned
  nothing. Also expected, and the chain falls through the same way.

The bbox is deliberately generous and the module never claims a point is *in*
BC or *in* Canada — only that it is not obviously outside either. The parcel
query and the WDPA lookup are the actual arbiters, the same posture
``uf_lookup`` takes toward Brazilian state lines.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from ..config.settings import BC_BBOX, CANADA_BBOX

logger = logging.getLogger(__name__)

BC_MIN_LON, BC_MIN_LAT, BC_MAX_LON, BC_MAX_LAT = BC_BBOX
CA_MIN_LON, CA_MIN_LAT, CA_MAX_LON, CA_MAX_LAT = CANADA_BBOX


def in_bc(lat: float, lon: float) -> bool:
    """Whether the point is inside the British Columbia bounding box.

    A box, not the province's outline: the outline would reject valid clicks
    near the ragged coast and the Alaska panhandle boundary for no gain, since
    the parcel query answers definitively either way. What this buys is
    knowing to try ParcelMap BC at all before falling through to the
    national-scope tiers.
    """
    return BC_MIN_LON <= lon <= BC_MAX_LON and BC_MIN_LAT <= lat <= BC_MAX_LAT


def in_canada(lat: float, lon: float) -> bool:
    """Whether the point is anywhere in Canada.

    The protected-area lookup and the synthetic-square fallback both answer
    nationally — a click in Ontario or Alberta gets no parcel, but the WDPA
    tier and, failing that, a 500 ha square around the click both still
    apply, the same as everywhere else in the country.
    """
    return CA_MIN_LON <= lon <= CA_MAX_LON and CA_MIN_LAT <= lat <= CA_MAX_LAT


def looks_swapped(lat: float, lon: float) -> bool:
    """True if this pair is not a valid Canadian coordinate, but swapping it
    would be.

    Checked only once :func:`classify` has already ruled out both ``in_bc``
    and ``in_canada`` on the pair *as given* — a coordinate that is already a
    valid unswapped point is never "probably swapped" just because its mirror
    also happens to land in Canada, which a version of this check that ran
    unconditionally would occasionally do near the same latitude/longitude
    range as its own longitude/latitude range (rare for Canada's real extent,
    but a needless trap to leave in).
    """
    return in_canada(lon, lat)


def classify(lat: float, lon: float) -> str:
    """``"bc"`` | ``"canada"`` | ``"swapped"`` | ``"outside"``.

    One function returning one of four answers, rather than three booleans a
    caller has to combine in the right order — getting that order wrong is how
    a genuine transposition ends up reported as "outside Canada" instead of
    naming the actual problem. Order matters: a pair already valid (in BC, or
    in the wider country) is accepted before the swap check ever runs.
    """
    if in_bc(lat, lon):
        return "bc"
    if in_canada(lat, lon):
        return "canada"
    if looks_swapped(lat, lon):
        return "swapped"
    return "outside"


def flipped(lat: float, lon: float) -> Tuple[float, float]:
    """The transposed pair, for a message that can offer the correction."""
    return lon, lat


def bc_bounds() -> Optional[list]:
    """``[[south, west], [north, east]]`` — BC's framing box for the map."""
    return [[BC_MIN_LAT, BC_MIN_LON], [BC_MAX_LAT, BC_MAX_LON]]


__all__ = ["in_bc", "in_canada", "looks_swapped", "classify", "flipped",
           "bc_bounds"]
