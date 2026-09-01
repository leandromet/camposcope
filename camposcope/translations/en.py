"""English — overrides only. Missing keys fall back to Portuguese
(``translations/__init__.py::get_translations``); this file does not need to
mirror ``pt.py`` key-for-key while coverage is still being built out, but
``python -m camposcope.translations`` should reach parity as it grows.
"""

from __future__ import annotations

TRANSLATIONS_EN: dict[str, str] = {
    # --- header --------------------------------------------------------- #
    "app_name": "Camposcope - Earth Engine for the CAR",
    "go_to_canada": "Canada",
    "start_hint": "Click anywhere in Brazil to start",

    # --- search panel ----------------------------------------------------- #
    "search_title": "Search",
    "search_placeholder": "CAR code, coordinate, município or place…",
    "search_read_as": "read as:",
    "search_button": "Search",
    "search_button_busy": "Searching…",
    "search_municipios_heading": "Municipalities",
    "search_places_heading": "Places",
    "search_places_note": (
        "A place only frames the map. Click on a property to analyse it."
    ),
    "search_places_attribution": (
        "Place search © OpenStreetMap contributors (ODbL)"
    ),
    "search_candidates_note": (
        "More than one registered property covers this point. Overlaps are "
        "common in the CAR — choose which one to analyse:"
    ),
    "echo_codigo": "CAR code",
    "echo_coordenada": "coordinate",
    "echo_municipio": "municipality",
    "echo_lugar": "place",
    "municipio_browser_title": "Properties in this municipality",
    "municipio_browser_total": "records",
    "municipio_browser_prev": "‹ previous",
    "municipio_browser_next": "next ›",

    # --- cadastral card ----------------------------------------------------- #
    "cadastro_title": "Rural Property",
    "cadastro_codigo": "Code",
    "cadastro_municipio": "Município",
    "cadastro_area_declarada": "Declared area",
    "cadastro_area_calculada": "Computed area (geometry)",
    "cadastro_area_disagreement_prefix": (
        "The declared area and the geometry's area differ by"
    ),
    "cadastro_area_disagreement_suffix": "Both are shown as they are.",
    "cadastro_modulos_fiscais": "Módulos fiscais",
    "cadastro_tipo": "Type",
    "cadastro_status": "Status",
    "cadastro_condicao": "Condição",
    "cadastro_registrado_em": "Registered on",
    "cadastro_atualizado_em": "Updated on",
    "cadastro_nao_informada": "not informed",
    "cadastro_sobreposicoes": "Overlaps with other registrations",
    "cadastro_details_toggle": "Registration details",
    "zonas_title": "Zones",
    "zonas_note": "Rings measured outward from the property's boundary, not from a centroid.",

    # --- synthetic 500 ha fallback card -------------------------------- #
    "square_title": "Analysis area",
    "square_note": (
        "No CAR registration at this point — this is a synthetic 500 ha "
        "square centred on where you clicked, so the land-cover, forest, "
        "biomass and fire tabs still have something to analyse."
    ),
    "square_coordinate": "Centre point",
    "square_disclosure": (
        "This boundary is not a CAR record or any kind of official record "
        "— it is a fixed-size square drawn around a coordinate, so analysis "
        "stays possible even with no registration."
    ),

    # --- results: shared --------------------------------------------------- #
    "calcular": "Calculate",
    "calculando": "Calculating…",
    "map_layer_note": (
        "The matching layer appears on the map — use the legend in the "
        "map's corner to turn it on/off or change the year."
    ),
    "tab_cobertura": "Cover",
    "tab_cobertura_hint": (
        "Land-use and land-cover history, 1985–2024, by MapBiomas class — "
        "the same series as the main chart."
    ),
    "tab_transicoes": "Transitions",
    "tab_transicoes_hint": (
        "Where one class went between two chosen years — what turned to "
        "pasture, what regrew, and so on."
    ),
    "tab_floresta": "Forest",
    "tab_floresta_hint": (
        "Forest loss (Hansen), split into three periods relative to 2008 "
        "and the property's own CAR registration date."
    ),
    "tab_biomassa": "Biomass",
    "tab_biomassa_hint": (
        "Above-ground biomass (ESA CCI) over time, for the selected area."
    ),
    "tab_paisagem": "Landscape",
    "tab_paisagem_hint": (
        "Fragmentation metrics for the natural vegetation — patch count, "
        "edge, effective mesh size — for the property and its zones."
    ),
    "tab_fogo": "Fire",
    "tab_fogo_hint": "Fire scar history for the selected area.",
    "tab_validacao": "Validation",
    "tab_validacao_hint": (
        "Checks MapBiomas' classification against SPOT 2008 imagery or "
        "IBGE's vegetation map, to spot-check the 2008 classification."
    ),

    # --- Cover tab ------------------------------------------------------- #
    "cobertura_ano": "Year",
    "cobertura_classe": "Class",
    "cobertura_hectares": "hectares",
    "cobertura_percentual": "percentage",
    "cobertura_degraded": (
        "Result computed at reduced resolution after a temporary Earth "
        "Engine failure."
    ),
    "cobertura_running": "Computing MapBiomas trajectory…",
    "cobertura_empty": "Select a property to see its land-cover trajectory.",
    "cobertura_attribution": (
        "MapBiomas Collection 10.1 (CC BY-SA 4.0) · 30 m scale · batched "
        "reduceRegions per zone."
    ),

    # --- Forest tab ------------------------------------------------------- #
    "floresta_intro": (
        "Forest cover loss by period: up to 2008 (the Forest Code's cutoff "
        "date), 2008 to CAR registration, and after registration. Gain is a "
        "single undated layer (2000–2012), never summed with loss."
    ),
    "floresta_ate_2008": "Up to 2008",
    "floresta_2008_ate_registro": "2008 to registration",
    "floresta_depois_registro": "After registration",
    "floresta_ganho_sem_data": "Gain (undated)",
    "floresta_col_ano": "Year",
    "floresta_col_perda": "Loss (ha)",
    "floresta_col_periodo": "Period",
    "floresta_attribution": "Hansen/UMD/Google/USGS/NASA — Global Forest Change · 30 m scale.",

    # --- Biomass tab ------------------------------------------------------- #
    "biomassa_intro": (
        "Above-ground biomass, ten years: 2007, 2010, then annual from 2015. "
        "The gap between them is a real gap in the source, not missing data "
        "— not interpolated."
    ),
    "biomassa_col_ano": "Year",
    "biomassa_col_mg_ha": "Mg/ha",
    "biomassa_col_total_mg": "Total (Mg)",
    "biomassa_attribution": "ESA CCI Biomass v6.0 — Santoro & Cartus (2025) · 100 m scale.",

    # --- Landscape tab ------------------------------------------------------ #
    "paisagem_ano": "Year",
    "paisagem_col_zona": "Zone",
    "paisagem_col_area": "Area (ha)",
    "paisagem_col_fragmentos": "Patches",
    "paisagem_col_densidade": "Density",
    "paisagem_col_maior": "Largest patch (%)",
    "paisagem_col_borda": "Edge density",
    "paisagem_col_meff": "Meff (ha)",
    "paisagem_col_shannon": "Shannon",
    "paisagem_col_simpson": "Simpson",
    "paisagem_col_evenness": "Evenness",
    "paisagem_empty": "Metrics not computed yet.",
    "paisagem_attribution": (
        "MapBiomas Collection 10.1 — fragmentation metrics (NP, PD, LPI, ED, "
        "Meff) per zone, 30 m scale."
    ),
    "connectivity_hint": (
        "Distance to the nearest forest patch — slower (vectorising + local "
        "search), computed only on request."
    ),
    "connectivity_run_button": "Compute connectivity (slower)",
    "connectivity_empty": "Not computed yet — click to run.",
    "connectivity_n_fragments": "Fragments",
    "connectivity_enn_mean": "Mean nearest-neighbour dist. (m)",
    "connectivity_enn_median": "Median (m)",
    "connectivity_degraded": (
        "One or more zones had more forest patches than the processed "
        "limit; the distance considered only the first ones Earth Engine "
        "returned, not the full set."
    ),

    # --- Transitions tab ---------------------------------------------------- #
    "transicoes_intro": (
        "Pixel-level land-cover transitions — soybean that became forest is "
        "still counted as soybean at both ends of the comparison."
    ),
    "transicoes_multi_stage_title": "Before · CAR registration · today",
    "transicoes_multi_stage_running": "Computing transitions…",
    "transicoes_de": "From",
    "transicoes_para": "To",
    "transicoes_maiores": "Largest transitions",
    "transicoes_min_gap_note_prefix": "MapBiomas Collection 10.1 · year pairs less than",
    "transicoes_min_gap_note_suffix": (
        "years apart are refused — at that interval most \"transitions\" "
        "are classification noise, not real change."
    ),

    # --- Validation tab ------------------------------------------------------ #
    "validacao_mode_spot": "SPOT × MapBiomas 2008",
    "validacao_mode_ibge": "IBGE × MapBiomas 2022",
    "validacao_spot_mosaic": "SPOT mosaic",
    "validacao_spot_visual": "Visual",
    "validacao_spot_analytic": "False colour (NIR)",
    "validacao_spot_analytic_short": "False colour",
    "validacao_spot_note": (
        "Circa-2008 SPOT imagery next to the MapBiomas classification for "
        "the same year — the closest visual reference to the Forest Code's "
        "cutoff date (22 July 2008)."
    ),
    "validacao_no_verdict": "Does not classify consolidated area or assess compliance.",
    "validacao_no_verdict_short": "Does not classify consolidated area.",
    "validacao_floresta": "Forest",
    "validacao_natural": "Natural",
    "validacao_col_ibge": "IBGE (left)",
    "validacao_col_mapbiomas": "MapBiomas (right)",
    "validacao_ibge_intro": (
        "IBGE Vegetação (1:250,000, 2022) against the same year's MapBiomas "
        "classification, both reduced to a shared 6-group taxonomy — the "
        "two maps share no classes."
    ),
    "validacao_ibge_caveat": (
        "IBGE's 'Vegetação Secundária' has no direct MapBiomas equivalent by "
        "definition; the table shows what MapBiomas currently reads those "
        "polygons as."
    ),
    "validacao_attribution": (
        "IBGE — Mapa de Vegetação do Brasil 1:250,000 (2022) · Google Brazil "
        "Forest Imagery Dataset 2008."
    ),

    # --- on-map legend -------------------------------------------------------- #
    "legend_mapbiomas": "MapBiomas",
    "legend_mapbiomas_palette": "Colours: official MapBiomas palette",
    "legend_floresta_hansen": "Forest — Hansen",
    "legend_hansen_since_2008": "since 2008",
    "legend_hansen_since_registro": "since registration",
    "legend_perda": "Loss",
    "legend_ganho_sem_data": "Gain (undated)",
    "legend_spot_2008": "SPOT 2008 imagery",
    "legend_loading": "Loading…",
    "legend_verifying": "Checking…",
    "legend_verify_coverage": "Check coverage",
    "legend_no_coverage": "No SPOT coverage in this zone.",
    "legend_spot_before_cutoff": "before 22 July 2008",
    "legend_biomassa_esa": "Biomass — ESA CCI",
    "legend_paisagem_fragmentos": "Landscape patches",
    "legend_fogo_frequencia": "Fire — Frequency",
    "legend_fogo_ocorrencias": "occurrences (1985–2025)",
    "legend_mapbiomas_comparacao": "MapBiomas — comparison",
    "legend_choose_years": "Choose the years on the Transitions tab.",
    "legend_drag_to_compare": "Drag the bar on the map to compare.",
    "legend_choose_mode": "Choose the mode on the Validation tab.",
    "legend_run_calcular": "Click Calculate on the Validation tab to see the classes.",
    "legend_run_cobertura": "Run the Cover tab (year 2008) to see the classes.",
    "legend_visual": "Visual",
    "legend_falsa_cor": "False colour",

    # --- layers panel --------------------------------------------------------- #
    "layers_title": "Layers",
    "layers_loading": "Loading layer…",
    "layers_spot_hint": "Coverage and date check: Forest tab.",
    "layers_car_wms": "CAR properties (WMS)",
    "layers_car_wms_note": "Appears from zoom 8 onward.",
    "layers_biomes": "Biomes and domains (IBGE)",
    "layers_biomes_note": (
        "Approximate boundaries (~1 km) — orientation only, does not "
        "decide a specific property's biome."
    ),
    "sidebar_hide_aria": "Hide panel",
    "sidebar_show_aria": "Show panel",
    "sheet_handle_aria": "Resize panel — drag or use the arrow keys",
    "mobile_options_toggle": "Search options",
    "mobile_panel_toggle": "Data & options",
    "mobile_cadastro_zonas_toggle": "Registration & zones",

    # --- runtime errors --------------------------------------------------- #
    "erro_fora_brasil": (
        "This point is outside the Brazilian territory covered by CAR."
    ),
    "erro_lugar_nao_encontrado": (
        "No place found for “{query}”. Try a município, a "
        "coordinate, or a CAR code."
    ),
    "erro_zonas": "Could not build the zones: {detail}",
    "erro_camada_aba": "Could not load this tab's map layer.",
    "erro_camadas_comparacao": "Could not load the comparison layers.",
    "erro_camadas_comparacao_spot": (
        "Could not load the comparison layers. SPOT may require "
        "CS_SPOT_ENABLED=true."
    ),
    "erro_basemap": (
        "Could not load the '{name}' layer. It may require a licence this "
        "installation does not have (CS_SPOT_ENABLED)."
    ),
    "erro_transicao": "Could not compute the transition: {detail}",
    "erro_transicoes_multi": "Could not compute the transitions: {detail}",
    "erro_transicao_dados_insuficientes": (
        "Not enough transition data for the diagram."
    ),
    "erro_trajetoria_mapbiomas": (
        "Could not compute the MapBiomas trajectory: {detail}"
    ),
    "erro_mapbiomas_sem_classes": (
        "The MapBiomas query returned no classes for this geometry."
    ),
    "erro_perda_florestal": "Could not compute forest loss: {detail}",
    "erro_biomassa": "Could not compute biomass: {detail}",
    "erro_paisagem": "Could not compute landscape metrics: {detail}",
    "erro_connectivity": "Could not compute connectivity: {detail}",
    "erro_fogo": "Could not compute fire analysis: {detail}",
    "erro_spot_cobertura": "Could not check SPOT coverage: {detail}",
    "erro_comparacao_ibge": "Could not compute the comparison: {detail}",

    # --- Fire tab (components/fogo.py) -------------------------------------- #
    "fogo_intro": (
        "Fire history analysis (% of years with detected fire), fire frequency, "
        "and year of last fire occurrence."
    ),
    "fogo_col_ano": "Year",
    "fogo_col_cicatrizes": "Fire Scars (%)",
    "fogo_col_frequencia": "Frequency",
    "fogo_historio_anos": "Years with fire",
    "fogo_frequencia_ocorrencias": "Frequency (occurrences)",
    "fogo_ultima_queimada": "Last fire",
    "fogo_attribution": "MapBiomas Fire Collection 5 (CC BY-SA 4.0) · 30 m scale · Landsat classification (NBR) with deep learning.",

    # --- export dialog (components/exports.py) ------------------------------ #
    "download_button": "Download data",
    "export_dialog_title": "Download data",
    "export_dialog_desc": (
        "A spreadsheet with everything already computed for this property, "
        "or an HTML report ready for reading or printing."
    ),
    "export_choose_imovel_first": "Select a property first.",
    "export_stage_waiting": "Waiting for the MapBiomas trajectory to finish…",
    "export_stage_building": "Building the file…",
    "export_workbook_failed": "Failed to build the spreadsheet: {exc}",
    "export_report_failed": "Failed to build the report: {exc}",
    "download_workbook_button": "Download spreadsheet (.ods)",
    "download_workbook_hint": "Select a property on the map or search to enable this.",
    "workbook_desc": (
        "A spreadsheet with land cover per zone and year, forest loss, "
        "biomass, transitions and fire already computed, the IBGE "
        "validation (if computed), the MapBiomas class dictionary, and a "
        "metadata tab with the provenance of every query."
    ),
    "report_section_title": "HTML report (paper-friendly layout)",
    "report_section_desc": (
        "One self-contained HTML file with the figures and/or tables "
        "already computed, laid out for reading or printing to PDF — "
        "complements the spreadsheet above, not a replacement for it."
    ),
    "check_report_figures_label": "Figures",
    "check_report_figures_detail": (
        "Land cover, forest change, biomass and fire — one chart per zone "
        "— plus transitions, if already computed."
    ),
    "check_report_tables_label": "Tables",
    "check_report_tables_detail": (
        "Latest land cover, forest loss, biomass, transitions, fire, IBGE "
        "validation (if already computed) and the provenance of every "
        "query."
    ),
    "download_report_button": "Download report (HTML)",
    "export_close_button": "Close",

    # --- per-chart/per-table export icons (components/export_widgets.py) --- #
    "export_chart_aria": "Download this chart (PNG)",
    "export_table_aria": "Download this table (CSV)",
    "export_chart_label": "Export figure",
    "export_table_label": "Export table",
}
