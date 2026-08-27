"""The ``/canada`` workspace — a rural-property analysis of British Columbia.

A self-contained sibling of the Brazil app, not a fork of it. The two answer the
same question — *what has happened on and around this rural property* — over
different cadastres and different land-cover products, so what is shared is the
engineering (Earth Engine access, the tile cache, the persistent Leaflet map,
the zone abstraction, provenance, the ODS writer) and what is separate is every
dataset, every legend and every piece of cadastral vocabulary.

The substitutions, one for one:

======================  ==========================================
Brazil                  Canada / British Columbia
======================  ==========================================
CAR / SICAR             ParcelMap BC parcel fabric (LTSA)
MapBiomas Coll. 10.1    AAFC Annual Crop Inventory (2009–2025)
SPOT 2008 validation    NTEMS VLCE2 vs. the ACI, same year
MapBiomas Fogo Coll. 5  MODIS MCD64A1 burned area (2001–2025)
IBGE biomes             Ecozones of Canada (National Ecological
                        Framework, AAFC)
IBGE municípios         BC municipalities and regional districts
======================  ==========================================

Hansen Global Forest Change and ESA CCI Biomass are global and are used
unchanged — only what they are *anchored on* differs (a parcel's start date
rather than a CAR registration, and no Forest Code cutoff at all).

**British Columbia only, deliberately.** ParcelMap BC is a provincial cadastre;
there is no national Canadian parcel fabric to fall back on, and pretending
otherwise would mean a search box that silently fails everywhere east of the
Rockies. The land-cover half of the page would work Canada-wide — the property
half is what bounds it, and the UI says so rather than leaving a user to
discover it by clicking.
"""
