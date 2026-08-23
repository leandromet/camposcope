"""Build ``data/uf_boundaries.simplified.geojson``.

Offline prep, run rarely, never imported by the app.

Why this file exists: the CAR GeoServer publishes **one layer per UF and no
national layer** (doc/05-sicar-geoserver.md §2), so a map click has to be routed
to one of 27 layers before it can be queried. Doing that locally against a
simplified boundary file is decision **D5** — it is deterministic, costs no
network call, and cannot be wrong in a way that looks like "no property here".

Accuracy is deliberately low. The file only has to answer *which state*, and near
a state line the property query itself is the arbiter (services/uf_lookup.py
falls back to the neighbouring UF once).

Source: IBGE malhas territoriais API, ``qualidade=minima``.

    python scripts/fetch_uf_boundaries.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import requests

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "uf_boundaries.simplified.geojson"

IBGE_MALHAS = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=minima"
)
IBGE_UFS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"


def main() -> int:
    print("fetching UF geometries …")
    geo = requests.get(IBGE_MALHAS, timeout=(10, 120)).json()

    print("fetching UF codes → siglas …")
    ufs = requests.get(IBGE_UFS, timeout=(10, 60)).json()
    # The malhas API identifies each polygon by `codarea`, which is the UF's
    # two-digit IBGE code — not its sigla. The localidades endpoint is the join.
    by_code = {str(u["id"]): u for u in ufs}

    features = []
    for feat in geo["features"]:
        code = str(feat["properties"].get("codarea", "")).strip()
        uf = by_code.get(code)
        if uf is None:
            print(f"  ! no UF for codarea={code!r}, skipping", file=sys.stderr)
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "uf": uf["sigla"],
                "nome": uf["nome"],
                "codigo_ibge": int(code),
            },
            "geometry": feat["geometry"],
        })

    features.sort(key=lambda f: f["properties"]["uf"])
    out = {"type": "FeatureCollection", "features": features}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Separators without spaces: this file is committed, and the whitespace is
    # a third of its size.
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")

    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} — {len(features)} UFs, {size_kb:.0f} kB")
    if len(features) != 27:
        print(f"  ! expected 27 UFs, got {len(features)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
