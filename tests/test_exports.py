"""services/exports.py — the property ODS workbook.

Mirrors Naturametrics' tests/test_exports.py: the writer is exercised via an
independent reader (odfpy, through pandas) rather than trusting that what
was written is what was meant. Skipped without odfpy installed, same as
upstream — it is not a runtime dependency of the app itself.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from camposcope.services import exports  # noqa: E402

ZONES = [
    {"zone_key": "imovel", "zone_label": "Imóvel", "zone_kind": "property",
     "radius_m": None, "area_ha": 120.0},
    {"zone_key": "ring_500", "zone_label": "0 – 500 m", "zone_kind": "ring",
     "radius_m": 500, "area_ha": 340.0},
]

IMOVEL = {"cod_imovel": "MT-5107925-ABCD1234", "uf": "MT", "municipio": "Sinop",
         "area_declarada_ha": 120.0, "condicao": "Ativo",
         "status_imovel": "Aguardando análise", "dat_criacao": "2015-03-01",
         "ano_criacao": 2015}


def _read_back(data: bytes, tmp_path: Path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("odf", reason="odfpy is the independent reader")
    path = tmp_path / "out.ods"
    path.write_bytes(data)
    return pd.read_excel(path, sheet_name=None, engine="odf")


def _history_rows():
    rows = []
    for z in ZONES:
        for year in (1985, 2024):
            rows.append({"zone_key": z["zone_key"], "zone_label": z["zone_label"],
                        "year": year, "class_id": 3, "class_pt": "Formação Florestal",
                        "class_en": "Forest", "pixels": 100, "area_ha": 90.0,
                        "color": "#1f8d49"})
    return rows


def _prov():
    return {"name": "landuse_history", "dataset_id": "asset", "bands": ["b1"],
           "scale_m": 30, "reducer": "frequencyHistogram", "pixel_area_basis": "",
           "max_pixels": 1e9, "tile_scale": 4, "geometry": None, "degraded": False,
           "notes": [], "computed_at": "2026-01-01T00:00:00+00:00", "extra": {}}


def test_workbook_has_one_tab_per_dataset_and_its_provenance(tmp_path):
    data, name = exports.imovel_workbook(
        IMOVEL, ZONES, _history_rows(), history_provenance=_prov())

    assert name.endswith(".ods")
    back = _read_back(data, tmp_path)

    for sheet in ("metadados", "zonas", "cobertura", "floresta_perda",
                 "floresta_ganho", "biomassa", "transicoes", "fogo_resumo",
                 "fogo_anual", "classes_mapbiomas"):
        assert sheet in back, f"missing sheet {sheet!r}"

    # C6: the numbers never travel without the record of how they were made.
    joined = " ".join(str(v) for v in back["metadados"].to_numpy().ravel())
    assert "frequencyHistogram" in joined
    assert "asset" in joined


def test_workbook_carries_the_car_identity_verbatim(tmp_path):
    """Constraint C4: cadastral fields travel unmodified, no verdict derived
    from them."""
    data, _ = exports.imovel_workbook(IMOVEL, ZONES, _history_rows())
    back = _read_back(data, tmp_path)
    joined = " ".join(str(v) for v in back["metadados"].to_numpy().ravel())
    assert IMOVEL["cod_imovel"] in joined
    assert "Aguardando análise" in joined


def test_workbook_survives_nothing_computed_yet(tmp_path):
    """A workbook downloaded before any of the on-demand tabs (Floresta,
    Biomassa, Transições, Fogo, Validação) have run must still produce a
    valid file with an honest note, not a crash or a blank sheet with no
    explanation."""
    data, name = exports.imovel_workbook(IMOVEL, ZONES, [])
    assert name.endswith(".ods")
    back = _read_back(data, tmp_path)
    assert back["cobertura"].empty
    joined = " ".join(str(v) for v in back["metadados"].to_numpy().ravel())
    assert "Ainda não calculada" in joined


def test_provenance_with_a_still_proxied_geometry_does_not_crash_to_dict():
    """Regression: every services/*.py analysis sets
    ``Provenance(geometry=zones[0].geojson)``, and that geometry is read out
    of ``AppState.zones_geojson`` through a *shallow* ``dict(...)``/``list``
    copy in every ``run_*`` handler — which leaves the nested "features"
    list, and each feature's own "geometry" dict, still wrapped in Reflex's
    ``MutableProxy``. That is invisible right up until something recurses
    all the way through it: ``Provenance.to_dict()`` (``dataclasses.asdict``)
    does, reconstructing each nested dict/list via ``type(obj)(...)`` — so a
    still-proxied inner container becomes a call to ``MutableProxy(items)``
    with no ``state``/``field_name``, and raises. Only a real ``AppState``
    instance reproduces this (a plain dict/list literal is never wrapped),
    same reasoning as Naturametrics'
    ``test_state_values_survive_the_trip_into_a_workbook``.
    """
    from camposcope.services.provenance import Provenance
    from camposcope.state import AppState
    from camposcope.state._proxy import plain

    state = AppState(_reflex_internal_init=True)
    state.zones_geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "properties": {"zone_key": "imovel"},
            "geometry": {"type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        }],
    }

    # The bug in miniature: proxied on the way out.
    assert type(dict(state.zones_geojson)["features"]).__name__ == "MutableProxy"

    zones_geojson = plain(state.zones_geojson) or {}
    geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                  for f in zones_geojson["features"]}
    prov = Provenance(name="mapbiomas_history", dataset_id="asset",
                      geometry=geom_by_key["imovel"])

    # The operation that actually failed (state/_analysis.py run_history and
    # every sibling run_* handler now call this on the way into export).
    d = prov.to_dict()
    assert d["geometry"]["type"] == "Polygon"
