"""English — canonical key set for the Canada page. Every other language falls
back to this."""

from __future__ import annotations

TRANSLATIONS_EN: dict[str, str] = {
    # --- header ----------------------------------------------------------- #
    "app_name": "Camposcope — Earth Engine for Rural Properties",
    "nav_title_suffix": "Canada",
    "nav_subtitle": "Rural property analysis from the ParcelMap BC parcel fabric",
    "go_to_brazil": "Brazil",
    "language_label": "Language",
    "nav_toggle_layers_aria": "Show layers",
    "drawer_title": "Layers",
    "drawer_close_aria": "Close",
    "sidebar_show_aria": "Show sidebar",
    "sidebar_hide_aria": "Hide sidebar",
    "sheet_handle_aria": "Resize panel — drag or use the arrow keys",
    "close_button": "Close",
    "calcular": "Calculate",
    "calculando": "Calculating…",

    # --- search panel ------------------------------------------------------ #
    "search_title": "Search",
    "search_placeholder": "PID, coordinate, municipality, or place…",
    "search_read_as": "read as:",
    "search_button": "Search",
    "search_button_busy": "Searching…",
    "search_areas_heading": "Municipalities & regional districts",
    "search_places_heading": "Places",
    "search_places_note": "A place only frames the map. Click a parcel to "
        "analyse it.",
    "search_places_attribution": "Place search © OpenStreetMap contributors "
        "(ODbL)",
    "search_candidates_note": "More than one parcel covers this point — pick "
        "which to analyse:",
    "echo_pid": "PID",
    "echo_coordenada": "coordinate",
    "echo_area": "area",
    "echo_lugar": "place",
    "area_browser_title": "Parcels in this area",
    "area_browser_total": "parcels",
    "area_browser_prev": "‹ previous",
    "area_browser_next": "next ›",
    "bc_only_note": "Parcel search covers British Columbia only.",

    # --- parcel card -------------------------------------------------------- #
    "parcel_title": "Parcel",
    "parcel_identifier": "Identifier",
    "parcel_area_registered": "Registered area",
    "parcel_area_calculated": "Calculated area (geometry)",
    "parcel_area_disagreement_prefix": "The registered and geometric areas "
        "differ by",
    "parcel_area_disagreement_suffix": "Both are shown as reported.",
    "parcel_class": "Parcel class",
    "parcel_status": "Status",
    "parcel_owner_type": "Owner type",
    "parcel_plan_number": "Plan number",
    "parcel_start_date": "Start date",
    "parcel_start_date_none": "not on record",
    "parcel_municipality": "Municipality",
    "parcel_regional_district": "Regional district",
    "parcel_updated": "Last updated",
    "parcel_not_reported": "not reported",
    "parcel_non_land_prefix": "This parcel class (",
    "parcel_non_land_suffix": ") has no land cover of its own — it is a "
        "legal or infrastructure parcel, not a piece of ground.",
    "parcel_neighbours": "Overlapping parcels",
    "parcel_neighbours_note": "Rare on a surveyed fabric — usually an "
        "air-space or strata parcel stacked over the same ground.",
    "zones_title": "Zones",
    "zones_note": "Rings measured outward from the parcel boundary.",
    "zona_park": "Protected area",
    "zona_square": "Analysis area",

    # --- protected-area card (no parcel here, but a park) ------------------ #
    "park_title": "Protected area",
    "park_no_parcel_note": "No parcel here — this point falls inside a "
        "protected area instead, so that boundary is the analysis area.",
    "park_name": "Name",
    "park_designation": "Designation",
    "park_designation_type": "Designation level",
    "park_iucn_category": "IUCN category",
    "park_status": "Status",
    "park_status_year": "Status since",
    "park_managing_authority": "Managing authority",
    "park_area_reported": "Reported area (WDPA)",
    "park_area_calculated": "Calculated area (geometry)",
    "park_area_disagreement_prefix": "The reported and geometric areas "
        "differ by",
    "park_area_disagreement_suffix": "Both are shown as reported.",
    "park_disclosure": "From the World Database on Protected Areas "
        "(WDPA), UNEP-WCMC/IUCN. A conservation register, not a land title: "
        "it carries no owner names and says nothing about public access.",

    # --- synthetic-square card (no parcel, no park) ------------------------ #
    "square_title": "Analysis area",
    "square_note": "No parcel or protected area here — this is a synthetic "
        "500 ha square centred on where you clicked, so the land-cover, "
        "forest, biomass and fire tabs still have something to analyse.",
    "square_coordinate": "Centre point",
    "coord_clicked": "Clicked at",
    "coord_centroid": "Centroid",
    "square_disclosure": "This boundary is not a legal or administrative "
        "record of any kind — it is a fixed-size square drawn around a "
        "coordinate, for consistent monitoring of land with no registered "
        "or protected boundary of its own.",

    # --- layers panel / legend ---------------------------------------------- #
    "layers_title": "Basemap",
    "layers_loading": "Loading…",
    "layers_landsat_hint": "Annual composite — pick the year below.",
    "layers_parcel_wms": "Parcel fabric (context)",
    "layers_parcel_wms_note": "Every ParcelMap BC parcel, drawn by the "
        "server — visible from zoom 12.",
    "layers_ecozones": "Ecological framework",
    "layers_ecozone_level_ecozone": "Ecozone",
    "layers_ecozone_level_ecoregion": "Ecoregion",
    "layers_ecozone_level_ecodistrict": "Ecodistrict",
    "layers_ecozones_note": "Orientation only — boundaries are approximate "
        "and decide nothing. Ecozones are coarse (fifteen cover all of "
        "Canada); ecoregion and ecodistrict are finer tiers of the same "
        "framework — ecodistrict carries no name of its own, only the "
        "ecoregion and ecozone it sits inside.",
    "legend_aci": "AAFC Crop Inventory",
    "legend_aci_palette": "Official AAFC legend colours.",
    "legend_landsat": "Landsat composite",
    "legend_landsat_error": "Could not load this year's Landsat composite.",
    "legend_verifying": "Checking…",
    "legend_floresta_hansen": "Forest change (Hansen)",
    "legend_hansen_split_start_date": "Split at parcel start date",
    "legend_hansen_split_undivided": "Undivided series",
    "legend_perda": "Loss",
    "legend_ganho": "Gain (undated)",
    "legend_choose_years": "Choose the years on the Transitions tab.",
    "legend_drag_to_compare": "Drag the bar on the map to compare.",
    "map_layer_note": "This tab's map layer can be turned on or off from "
        "the legend in the map corner.",

    # --- Cobertura (ACI) ----------------------------------------------------- #
    "tab_cobertura": "Cover",
    "cobertura_ano": "Year",
    "cobertura_classe": "Class",
    "cobertura_hectares": "Hectares",
    "cobertura_percentual": "Percent",
    "cobertura_running": "Fetching the crop-inventory trajectory…",
    "cobertura_empty": "No data yet — select a parcel.",
    "cobertura_degraded": "This result was retried at a coarser scale after "
        "an Earth Engine failure. It is usable, but see the provenance "
        "record for what changed.",
    "cobertura_out_of_range": "The Annual Crop Inventory has no coverage "
        "this far north — this is expected above roughly 54–58°N, not a "
        "failure. The Floresta, Biomassa and Fogo tabs still answer.",
    "cobertura_attribution": "Agriculture and Agri-Food Canada — Annual "
        "Crop Inventory · 30 m",

    # --- Transições ----------------------------------------------------------- #
    "tab_transicoes": "Transitions",
    "transicoes_intro": "How land cover changed between two years, for the "
        "active zone.",
    "transicoes_de": "From",
    "transicoes_para": "To",
    "transicoes_maiores": "Largest transitions",
    "transicoes_min_gap_note_prefix": "Years closer than",
    "transicoes_min_gap_note_suffix": "apart are refused — between "
        "consecutive years most inventory 'transitions' are crop rotation, "
        "not a land-use change.",

    # --- Floresta -------------------------------------------------------------- #
    "tab_floresta": "Forest",
    "floresta_split_start_date": "Split at parcel start date",
    "floresta_split_undivided": "Undivided",
    "floresta_before_parcel": "Before the parcel existed",
    "floresta_after_parcel": "After the parcel was created",
    "floresta_undivided_total": "Total loss (undivided)",
    "floresta_ganho_sem_data": "Gain (undated)",
    "floresta_no_start_date_note": "This parcel's fabric record carries no "
        "start date, so loss is shown as one undivided series rather than "
        "split at an invented anchor.",
    "floresta_col_ano": "Year",
    "floresta_col_perda": "Loss (ha)",
    "floresta_col_periodo": "Period",
    "floresta_attribution": "Hansen/UMD/Google/USGS/NASA — Global Forest "
        "Change · 30 m",
    "floresta_age_title": "Stand age (NTEMS, 2019)",
    "floresta_age_run_button": "Get stand age",
    "floresta_age_mean": "Mean age",
    "floresta_age_median": "Median age",
    "floresta_age_unit": "yr",
    "floresta_age_forested_pct": "Forested share of zone",
    "floresta_age_note": "Ages are as published, as of 2019 — not aged "
        "forward to today. Masked to forested pixels: a low forested share "
        "means the age figures describe only a small part of this zone.",
    "floresta_age_attribution": "NRCan / NFIS — NTEMS Canada forest age "
        "(2019) · 30 m",

    # --- Biomassa --------------------------------------------------------------- #
    "tab_biomassa": "Biomass",
    "biomassa_col_ano": "Year",
    "biomassa_col_mg_ha": "Mg/ha",
    "biomassa_col_total_mg": "Total (Mg)",
    "biomassa_attribution": "ESA CCI Biomass v6.0 — Santoro & Cartus "
        "(2025) · 100 m",
    "biomassa_canada_note": "Retrieval is weaker over terrain with "
        "persistent snow cover and sparse northern woodland than over "
        "closed temperate forest.",

    # --- Paisagem ----------------------------------------------------------------- #
    "tab_paisagem": "Landscape",
    "paisagem_ano": "Year",
    "paisagem_empty": "No data yet.",
    "paisagem_legend_note": "Patch counts follow the ACI's own class "
        "distinctions, which resolve crops finely and forest coarsely — "
        "comparable between this parcel and its rings, not between a farmed "
        "landscape and a forested one.",
    "paisagem_col_zona": "Zone",
    "paisagem_col_area": "Area (ha)",
    "paisagem_col_fragmentos": "Patches",
    "paisagem_col_densidade": "Density",
    "paisagem_col_maior": "Largest (%)",
    "paisagem_col_borda": "Edge density",
    "paisagem_col_meff": "Meff (ha)",
    "paisagem_col_shannon": "Shannon",
    "paisagem_col_simpson": "Simpson",
    "paisagem_col_evenness": "Evenness",
    "paisagem_attribution": "AAFC Annual Crop Inventory · 30 m",
    "connectivity_hint": "Mean distance between forest fragments — a "
        "second Earth Engine call plus a local search, so it runs on request.",
    "connectivity_run_button": "Get fragment distance",
    "connectivity_degraded": "More fragments than the cap in one or more "
        "zones — the distance considers only the first ones returned.",
    "connectivity_empty": "No result yet.",
    "connectivity_n_fragments": "Fragments",
    "connectivity_enn_mean": "Mean distance (m)",
    "connectivity_enn_median": "Median distance (m)",

    # --- Fogo --------------------------------------------------------------------- #
    "tab_fogo": "Fire",
    "fogo_historio_anos": "Years with any burn",
    "fogo_frequencia_ocorrencias": "Mean burn frequency",
    "fogo_ultima_queimada": "Last burn year",
    "fogo_below_resolution_prefix": "This zone is smaller than roughly ",
    "fogo_below_resolution_suffix": " ha — MODIS pixels are ~21 ha, so these "
        "numbers are dominated by pixel-edge effects rather than resolving "
        "the zone.",
    "fogo_attribution": "MODIS MCD64A1 v6.1 Burned Area — NASA LP DAAC · "
        "463 m",
    "fogo_current_year_prefix": "The year ",
    "fogo_current_year_suffix": " is still in progress — MODIS keeps "
        "publishing new months through the year, so this bar (hatched on "
        "the chart) is a running total, not a finished season.",
    "fogo_source_modis": "MODIS · 500 m",
    "fogo_source_aci": "AAFC · 30 m",
    "fogo_modis_layer_note_prefix": "Map shows every year on record combined "
        "(2001–",
    "fogo_modis_layer_note_suffix": ") — darker red burned more often. The "
        "final year is still in progress.",
    "fogo_aci_layer_note": "Map shows every year on record combined "
        "(2009–2025) — darker red burned more often.",
    "fogo_aci_years_detected": "Years with burn detected",
    "fogo_aci_last_year": "Most recent burnt year",
    "fogo_aci_empty": "No Cobertura data yet for this zone — visit the "
        "Cobertura tab, or wait for it to finish loading. The burnt-area "
        "class comes from that same fetch, at no extra cost.",
    "fogo_aci_note": "The crop inventory's own burnt-area class (2009–2025, "
        "national from 2011), 30 m — seven times finer than MODIS, but a "
        "land-cover class rather than a dedicated burn product: it can miss "
        "a fire MODIS catches if the scar had already regreened by that "
        "year's satellite pass, the same way it can resolve a burn's shape "
        "MODIS only sees as a blur. The two are never merged into one "
        "number.",
    "fogo_aci_attribution": "Agriculture and Agri-Food Canada — Annual Crop "
        "Inventory, class 60 \"Forest Fire and Burnt Area\" · 30 m",

    # --- Validação -------------------------------------------------------------------- #
    "tab_validacao": "Validation",
    "validacao_intro": "The Annual Crop Inventory checked against NTEMS "
        "VLCE2, an independent national land-cover product, for the same "
        "year. Compared at a coarse group level only — see the note below.",
    "validacao_ano": "Year",
    "validacao_agreement_label": "Group-level agreement",
    "validacao_area_label": "Area compared",
    "validacao_no_verdict": "Disagreement between two independent products "
        "is not error in either — this reports where they differ and says "
        "nothing about which is right.",
    "validacao_group_note": "Compared at group level, not class level: the "
        "ACI resolves crops and has no forest-type detail, VLCE2 the "
        "reverse. A class-level agreement rate would be meaningless.",
    "validacao_col_aci": "ACI group",
    "validacao_col_vlce2": "VLCE2 group",
    "validacao_col_area": "Area (ha)",
    "validacao_col_agreement": "Agree?",
    "validacao_attribution": "AAFC Annual Crop Inventory · NTEMS VLCE2 "
        "(Hermosilla et al., Canadian Forest Service)",

    # --- errors --------------------------------------------------------------------------- #
    "erro_fora_canada": "That point is outside Canada. This page covers "
        "Canada; use the Brazil page for South American coordinates.",
    "erro_coordenada_invertida": "That looks like a transposed coordinate — "
        "swapping latitude and longitude would land inside Canada, but this "
        "order does not. Latitude comes first.",
    "erro_zonas": "Could not build the zones: {detail}",
    "erro_camada_aba": "This tab's map layer could not be loaded.",
    "erro_trajetoria_aci": "The crop-inventory trajectory failed: {detail}",
    "erro_aci_sem_classes": "No crop-inventory data over this zone — this "
        "is expected north of the inventory's coverage.",
    "erro_lugar_nao_encontrado": "No place found for “{query}”.",
    "erro_transicao": "The transitions failed: {detail}",
    "erro_perda_florestal": "Forest change failed: {detail}",
    "erro_idade_floresta": "Stand age failed: {detail}",
    "erro_biomassa": "Biomass failed: {detail}",
    "erro_fogo": "Burned-area analysis failed: {detail}",
    "erro_paisagem": "Landscape metrics failed: {detail}",
    "erro_connectivity": "Fragment connectivity failed: {detail}",
    "erro_validacao": "The validation comparison failed: {detail}",

    # --- misc ------------------------------------------------------------------------------- #
    "zona_parcela": "Parcel",
    "export_chart_aria": "Download this chart",
    "export_chart_label": "Download chart (PNG)",
    "export_table_aria": "Download this table",
    "export_table_label": "Download table (CSV)",

    # --- how-to-use dialog -------------------------------------------------------------------- #
    "help_trigger": "How to use",
    "help_dialog_title": "How to use this page",
    "help_dialog_desc": "Seven steps from a parcel to an analysis, and what "
        "this page cannot tell you.",
    "help_step1_title": "1. Find a parcel",
    "help_step1_body": "Type a Parcel Identifier (PID, e.g. 010-322-060), "
        "click the map, or search a municipality — the search box reads "
        "what you typed and shows it back before acting.",
    "help_step2_title": "2. Read the parcel card",
    "help_step2_body": "Every fabric field is shown verbatim — status, "
        "class, owner type, plan number. ParcelMap BC is a boundary record, "
        "not an ownership one: it carries no owner names.",
    "help_step3_title": "3. Check the zones",
    "help_step3_body": "The parcel plus concentric rings out to 5 km, "
        "measured outward from the boundary — every analysis below runs "
        "over all of them at once.",
    "help_step4_title": "4. Cover, Transitions, Floresta, Biomassa",
    "help_step4_body": "The Annual Crop Inventory trajectory, its "
        "year-to-year transitions, Hansen forest loss/gain plus NTEMS stand "
        "age, and ESA CCI biomass — each tab computes on request.",
    "help_step5_title": "5. Paisagem and Fogo",
    "help_step5_body": "Fragmentation metrics for every zone at once, plus "
        "an opt-in fragment-distance metric; MODIS burned-area history — "
        "coarse at 463 m, flagged when a zone is too small for it to "
        "resolve.",
    "help_step6_title": "6. Validação",
    "help_step6_body": "The crop inventory checked against an independent "
        "land-cover product for the same year, at a coarse group level. "
        "Disagreement is not a verdict either way.",
    "help_step7_title": "7. Export",
    "help_step7_body": "Every chart downloads as a PNG, every table as a "
        "CSV, from the icon beside it — for a paper's own reprocessing "
        "rather than a screenshot.",
    "help_limitations_title": "What this page cannot tell you",
    "help_limit_1": "ParcelMap BC shows legal boundaries, never ownership — "
        "no owner names appear anywhere in this app.",
    "help_limit_2": "Parcel search covers British Columbia only; the "
        "land-cover, forest, biomass and fire layers cover all of Canada.",
    "help_limit_3": "The Annual Crop Inventory has no data north of "
        "roughly 54–58°N — an empty Cobertura tab up there is the dataset, "
        "not a failure.",
    "help_limit_4": "This page issues no verdict about compliance, land "
        "use, or which of two disagreeing datasets is correct.",

    # --- citation dialog ---------------------------------------------------------------------- #
    "cite_trigger": "Cite",
    "cite_dialog_title": "How to cite",
    "cite_dialog_desc": "Camposcope Canada and the datasets it draws on.",
    "cite_sources_title": "Data sources",
    "cite_sources_desc": "Every source this page draws on, whether or not "
        "the current parcel happens to use all of them.",
    "cite_example_title": "Suggested citation",
    "cite_example_body": "",     # filled at runtime from config/citation.py

    # --- export dialog ------------------------------------------------------------------------ #
    "download_button": "Export",
    "export_dialog_title": "Export",
    "export_dialog_desc": "Per-chart PNGs and per-table CSVs are available "
        "from the icon next to each one. A combined workbook and report are "
        "not yet available on this page.",
}
