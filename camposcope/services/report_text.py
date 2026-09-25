"""The report's explanatory text — deterministic templates, pt and en.

doc/13 §3a and the shared contract (doc/13 §2.8): pure functions
``(rows…, lang) -> str`` returning one to three sentences, fed from the same
rows the chart or table beside them is drawn from. **Nothing is recomputed
here beyond sums and shares of those rows**, and nothing is judged: the
sentences state quantities, changes over the period and comparisons with the
rings — never a cause, never a legal, compliance or valuation term.
``tests/test_report_c4.py`` scans every string this module can produce.

Portuguese is the reference language; a key missing from English falls back
to it (``_t``), the same rule as ``translations/``. Numbers go through
``report_kit.text`` so a pt report reads "1.234,5 ha" and an en one
"1,234.5 ha".
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from ..report_kit.text import fmt_date, fmt_ha, fmt_int, fmt_num, fmt_pct, fmt_signed

TEMPLATES: Dict[str, Dict[str, str]] = {
    "pt": {
        # --- report & section titles -------------------------------------
        "report_title": "Relatório do imóvel",
        "report_title_square": "Relatório da área de referência",
        "sec_identification": "Identificação",
        "sec_zones": "Zonas analisadas",
        "sec_overlaps": "Sobreposições com outros registros do CAR",
        "sec_about": "Sobre este relatório",
        "sec_maps": "Mapas",
        "sec_cobertura": "Cobertura e uso da terra",
        "sec_transicoes": "Transições",
        "sec_floresta": "Floresta (Hansen)",
        "sec_biomassa": "Biomassa",
        "sec_paisagem": "Paisagem",
        "sec_fogo": "Fogo",
        "sec_validacao": "Validação IBGE × MapBiomas",
        "sec_spot": "SPOT 2008",
        "sec_gbif": "Biodiversidade (GBIF)",
        "sec_provenance": "Métodos e proveniência",
        "sec_sources": "Fontes, citação e atribuições",
        "sec_appendix": "Apêndice",
        # --- identification keys -----------------------------------------
        "kv_cod_imovel": "Código do imóvel (CAR)",
        "kv_uf": "UF",
        "kv_municipio": "Município (código IBGE)",
        "kv_tipo": "Tipo de imóvel",
        "kv_status": "Situação no CAR (status_imovel)",
        "kv_condicao": "Condição no CAR (condicao)",
        "kv_dat_criacao": "Data de criação do registro",
        "kv_data_atualizacao": "Data da última atualização",
        "kv_m_fiscal": "Módulos fiscais",
        "kv_area_declarada": "Área declarada",
        "kv_area_calculada": "Área calculada do polígono",
        "kv_area_delta": "Diferença (calculada - declarada)",
        "kv_queried_at": "Cadastro lido em",
        "kv_coordinates": "Ponto central",
        "kv_kind_square": "Tipo de área",
        "kv_kind_square_value": "Quadrado sintético de 500 ha (sem registro no CAR)",
        "locator_label": "Localização no Brasil",
        # --- sentences ----------------------------------------------------
        "area": ("A área declarada é {declared}; a área calculada a partir do "
                 "polígono é {computed} ({delta})."),
        "area_square": ("Área de referência de {computed}, desenhada ao redor do "
                        "ponto {coords}; não corresponde a registro algum."),
        "zones": ("A análise cobre o imóvel e {n} anéis de vizinhança "
                  "({radii}), medidos a partir do limite declarado."),
        "zones_one": ("A análise cobre o imóvel e 1 anel de vizinhança "
                      "({radii}), medido a partir do limite declarado."),
        "overlaps_some": ("O polígono deste registro se sobrepõe a {n} outros "
                          "registros do CAR (tabela abaixo). As sobreposições "
                          "são listadas como constam no cadastro, sem "
                          "interpretação."),
        "overlaps_one": ("O polígono deste registro se sobrepõe a 1 outro "
                         "registro do CAR (tabela abaixo). A sobreposição é "
                         "listada como consta no cadastro, sem interpretação."),
        "overlaps_none": ("Nenhum outro registro do CAR sobreposto a este "
                          "polígono foi encontrado na consulta ao cadastro."),
        "overlaps_unchecked": ("As sobreposições com outros registros não "
                               "puderam ser consultadas para este relatório "
                               "({reason})."),
        "overlaps_square": ("A área de referência não é um registro do CAR; "
                            "sobreposições não se aplicam."),
        "about": ("Período: MapBiomas {mb_start}–{mb_end}, Hansen "
                  "{hansen_start}–{hansen_end}. Zonas: {zones}. Cada seção "
                  "traz o conjunto de dados, o gráfico, uma tabela-resumo e um "
                  "parágrafo com os números. Este documento descreve medições "
                  "de sensoriamento remoto; não emite juízo sobre o imóvel."),
        "about_focus": ("Os gráficos por zona mostram a zona «{zone}», a que "
                        "estava ativa na tela."),
        "not_run_reason": "não calculado nesta sessão (botão Calcular da aba)",
        "excluded_reason": "desmarcado na janela de exportação",
        "validacao_mode_reason": ("calculado só no modo IBGE 2022 da aba "
                                  "Validação"),
        "maps_failed_reason": "o Earth Engine não respondeu: {detail}",
        "no_data": "Sem dados para esta zona.",
        "figure_capture_failed": "o navegador não gerou a imagem ({detail})",
        # intros (what the dataset is)
        "intro_cobertura": ("MapBiomas Coleção 10.1: classificação anual da "
                            "cobertura e do uso da terra, 30 m, {start}–{end}."),
        "intro_transicoes": ("Área que passou de cada classe MapBiomas em "
                             "{year_a} para cada classe em {year_b}, na zona "
                             "«{zone}»."),
        "intro_floresta": ("Hansen Global Forest Change: perda de cobertura "
                           "arbórea datada por ano ({start}–{end}), em pixels "
                           "com pelo menos {threshold} % de copa em 2000, dividida em "
                           "três períodos: até 2008, de 2008 até o registro no "
                           "CAR e depois do registro."),
        "intro_biomassa": ("ESA CCI Biomass v6.0: biomassa acima do solo "
                           "(Mg/ha), 100 m, anos 2007, 2010 e 2015–2022."),
        "intro_paisagem": ("Métricas de paisagem sobre as manchas de vegetação "
                           "nativa do MapBiomas: número de fragmentos, maior "
                           "fragmento, densidade de borda e tamanho efetivo de "
                           "malha (Meff)."),
        "intro_fogo": ("MapBiomas Fogo Coleção 5: área queimada anual, "
                       "1985–2025."),
        "intro_validacao": ("Comparação por área entre o mapa de Vegetação do "
                            "IBGE (2022) e o MapBiomas 2022, agrupados em "
                            "classes comuns, na zona «{zone}»."),
        "intro_spot": ("Mosaico SPOT de aproximadamente 2008 (Google LLC), só "
                       "sobre áreas florestais; a data de aquisição varia por "
                       "pixel e é informada abaixo."),
        "intro_gbif": ("Registros de ocorrência do GBIF por zona, cumulativos "
                       "(cada zona inclui o imóvel e os anéis internos)."),
        # readings
        "cobertura_zone": ("Na zona «{zone}», {cls_a} ocupava {ha_a} "
                           "({pct_a}) em {year_a}; em {year_b}, {cls_b} ocupa "
                           "{ha_b} ({pct_b})."),
        "cobertura_ring": (" No anel «{zone}», {cls} passou de {pct_a} para "
                           "{pct_b} no mesmo período."),
        "transicoes": ("De {total} mapeados na zona, {stable} ({stable_pct}) "
                       "permaneceram na mesma classe entre {year_a} e "
                       "{year_b}. A maior mudança foi de {src} para {tgt}: "
                       "{area}."),
        "transicoes_stable": ("De {total} mapeados na zona, {stable} "
                              "({stable_pct}) permaneceram na mesma classe "
                              "entre {year_a} e {year_b}."),
        "floresta": ("O Hansen registra {total} de perda de cobertura arbórea "
                     "no imóvel entre {start} e {end}: {p1} até 2008, {p2} "
                     "entre 2008 e o registro no CAR ({reg}) e {p3} após o "
                     "registro."),
        "floresta_noreg": ("O Hansen registra {total} de perda de cobertura "
                           "arbórea no imóvel entre {start} e {end}: {p1} até "
                           "2008 e {p3} depois de 2008 (sem data de registro "
                           "no CAR)."),
        "floresta_none": ("O Hansen não registra perda de cobertura arbórea no "
                          "imóvel entre {start} e {end}."),
        "none_ha": "nenhuma",
        "floresta_gain": ("Ganho de cobertura arbórea no imóvel: {gain}. O "
                          "ganho do Hansen é uma camada única e sem data "
                          "(2000–2012); não é somado à perda nem colocado na "
                          "linha do tempo."),
        "biomassa": ("Na zona «{zone}», a biomassa média acima do solo era "
                     "{v_a} Mg/ha em {year_a} e {v_b} Mg/ha em {year_b}."),
        "paisagem": ("O imóvel tem {patches} fragmentos de vegetação nativa, "
                     "com Meff de {meff}; no anel «{ring}», o Meff é "
                     "{meff_ring}."),
        "paisagem_one": ("A zona «{zone}» tem {patches} fragmentos de "
                         "vegetação nativa, com Meff de {meff}."),
        "fogo": ("Na zona «{zone}», {hist} da área queimou ao menos uma vez "
                 "entre 1985 e 2025; a frequência máxima é de {freq} "
                 "ocorrências e o último ano com fogo é {last}."),
        "fogo_nolast": ("Na zona «{zone}», {hist} da área queimou ao menos uma "
                        "vez entre 1985 e 2025; a frequência máxima é de {freq} "
                        "ocorrências."),
        "fogo_never": ("Na zona «{zone}», o MapBiomas Fogo não registra área "
                       "queimada entre 1985 e 2025."),
        "fogo_ring": (" No anel «{ring}», a parcela queimada ao menos uma vez é "
                      "{hist}."),
        "validacao": ("O IBGE classifica {forest_ibge} da zona como floresta e "
                      "o MapBiomas {forest_mb}; vegetação natural: "
                      "{natural_ibge} no IBGE e {natural_mb} no MapBiomas."),
        "spot": ("O mosaico SPOT cobre {covered} do imóvel; {pre} dessa área "
                 "foi imageada antes de {cutoff} (imagens de {d_min} a "
                 "{d_max})."),
        "spot_pre_unknown": ("O mosaico SPOT cobre {covered} do imóvel "
                             "(imagens de {d_min} a {d_max}); a parcela "
                             "imageada antes de {cutoff} não está "
                             "disponível."),
        "spot_none": ("O mosaico SPOT não cobre este imóvel: o conjunto só "
                      "abrange áreas florestais do Brasil."),
        "gbif": ("Na zona «{zone}» há {records} registros de ocorrência, de "
                 "{species} espécies."),
        # captions
        "cap_cobertura": "Cobertura e uso da terra por ano (MapBiomas) — {zone}.",
        "cap_cobertura_table": ("Classes MapBiomas em {year_a} e {year_b} — "
                                "{zone}."),
        "cap_zones": "Zonas analisadas: o imóvel e seus anéis de vizinhança.",
        "cap_overlaps": "Registros do CAR que se sobrepõem a este polígono.",
        "cap_transicoes": "Transições {year_a}–{year_b} — {zone}.",
        "cap_transicoes_table": ("As 10 maiores transições entre classes "
                                 "diferentes, {year_a}–{year_b} — {zone}."),
        "cap_floresta": "Perda de cobertura arbórea por ano e período (Hansen) — {zone}.",
        "cap_floresta_table": "Perda de cobertura arbórea por período e zona (ha).",
        "cap_biomassa": "Biomassa média acima do solo (ESA CCI) — {zone}.",
        "cap_biomassa_table": "Biomassa acima do solo por ano — {zone}.",
        "cap_paisagem": "Tamanho efetivo de malha (Meff) por zona.",
        "cap_paisagem_table": "Métricas de paisagem por zona.",
        "cap_conectividade_table": ("Conectividade entre fragmentos florestais "
                                    "(distância ao vizinho mais próximo)."),
        "cap_fogo": "Área queimada por ano (MapBiomas Fogo) — {zone}.",
        "cap_fogo_table": "Fogo por zona, 1985–2025.",
        "cap_validacao_table": ("IBGE (linhas) × MapBiomas (colunas), % da área "
                                "— {zone}."),
        "cap_gbif_table": "Registros e espécies no GBIF por zona (cumulativo).",
        "cap_appendix_cobertura": "Cobertura MapBiomas por zona, classe e ano (ha).",
        "cap_appendix_fogo": "Área queimada por zona e ano (%).",
        "cap_map_s2": ("Imagem Sentinel-2 ({year}, estação seca) com o limite "
                       "declarado e o anel de 500 m."),
        "cap_map_spot": ("Mosaico SPOT, imagens de {d_min} a {d_max}; {pre} "
                         "da área coberta foi imageada antes de {cutoff}. "
                         "Limite declarado e anel de 500 m."),
        "cap_map_spot_pre_unknown": ("Mosaico SPOT, imagens de {d_min} a "
                                     "{d_max}; parcela imageada antes de "
                                     "{cutoff} indisponível. Limite declarado "
                                     "e anel de 500 m."),
        "cap_map_mapbiomas": ("MapBiomas {year} com o limite declarado e os "
                              "anéis até {radius}."),
        "cap_map_hansen": ("Cobertura arbórea em 2000 (verde) e perda Hansen "
                           "de {from_year} a {end} (vermelho), com o limite "
                           "declarado e os anéis até {radius}."),
        "legend_property": "Limite declarado",
        "legend_property_square": "Área de referência",
        "legend_rings": "Anéis de vizinhança",
        "legend_treecover": "Cobertura arbórea em 2000",
        "legend_loss": "Perda {from_year}–{end}",
        "legend_gain": "Ganho (sem data, 2000–2012)",
        # table headers
        "h_zone": "Zona", "h_kind": "Tipo", "h_radius": "Raio (m)",
        "h_area_ha": "Área (ha)", "h_class": "Classe", "h_pct": "%",
        "h_from": "De", "h_to": "Para", "h_cod": "Código do imóvel",
        "h_overlap_ha": "Sobreposição (ha)", "h_overlap_pct": "% do imóvel",
        "h_up_to_2008": "Até 2008", "h_to_reg": "2008 até o registro",
        "h_after_reg": "Após o registro", "h_total": "Total",
        "h_year": "Ano", "h_agb": "Mg/ha", "h_agb_total": "Total (Mg)",
        "h_patches": "Fragmentos", "h_largest_pct": "Maior (%)",
        "h_edge_density": "Borda (m/ha)", "h_meff": "Meff (ha)",
        "h_shannon": "Shannon", "h_n_frag": "Fragmentos",
        "h_enn_mean": "Dist. média (m)", "h_enn_median": "Mediana (m)",
        "h_fire_hist": "Queimada 1+ vez (%)", "h_fire_freq": "Frequência máx.",
        "h_fire_last": "Último ano", "h_fire_pct": "Queimada (%)",
        "h_records": "Registros", "h_species": "Espécies",
        "kind_property": "imóvel", "kind_ring": "anel",
        "kind_square": "área de referência",
        "spot_row": "Cobertura SPOT 2008",
    },
    "en": {
        "report_title": "Property report",
        "report_title_square": "Reference-area report",
        "sec_identification": "Identification",
        "sec_zones": "Zones analysed",
        "sec_overlaps": "Overlaps with other CAR registrations",
        "sec_about": "About this report",
        "sec_maps": "Maps",
        "sec_cobertura": "Land use and cover",
        "sec_transicoes": "Transitions",
        "sec_floresta": "Forest (Hansen)",
        "sec_biomassa": "Biomass",
        "sec_paisagem": "Landscape",
        "sec_fogo": "Fire",
        "sec_validacao": "IBGE × MapBiomas validation",
        "sec_spot": "SPOT 2008",
        "sec_gbif": "Biodiversity (GBIF)",
        "sec_provenance": "Methods and provenance",
        "sec_sources": "Sources, citation and attributions",
        "sec_appendix": "Appendix",
        "kv_cod_imovel": "Property code (CAR)",
        "kv_uf": "State (UF)",
        "kv_municipio": "Municipality (IBGE code)",
        "kv_tipo": "Property type",
        "kv_status": "CAR status (status_imovel, verbatim)",
        "kv_condicao": "CAR condition (condicao, verbatim)",
        "kv_dat_criacao": "Registration created",
        "kv_data_atualizacao": "Last updated",
        "kv_m_fiscal": "Fiscal modules",
        "kv_area_declarada": "Declared area",
        "kv_area_calculada": "Area computed from the polygon",
        "kv_area_delta": "Difference (computed - declared)",
        "kv_queried_at": "Registry read on",
        "kv_coordinates": "Centre point",
        "kv_kind_square": "Area type",
        "kv_kind_square_value": "Synthetic 500 ha square (no CAR registration)",
        "locator_label": "Location in Brazil",
        "area": ("The declared area is {declared}; the area computed from the "
                 "polygon is {computed} ({delta})."),
        "area_square": ("Reference area of {computed}, drawn around the point "
                        "{coords}; it matches no registration."),
        "zones": ("The analysis covers the property and {n} neighbourhood "
                  "rings ({radii}), measured from the declared boundary."),
        "zones_one": ("The analysis covers the property and 1 neighbourhood "
                      "ring ({radii}), measured from the declared boundary."),
        "overlaps_some": ("This registration's polygon overlaps {n} other CAR "
                          "registrations (table below). Overlaps are listed as "
                          "they appear in the cadastre, without "
                          "interpretation."),
        "overlaps_one": ("This registration's polygon overlaps 1 other CAR "
                         "registration (table below). The overlap is listed "
                         "as it appears in the cadastre, without "
                         "interpretation."),
        "overlaps_none": ("No other CAR registration overlapping this polygon "
                          "was found when the cadastre was queried."),
        "overlaps_unchecked": ("Overlaps with other registrations could not be "
                               "queried for this report ({reason})."),
        "overlaps_square": ("The reference area is not a CAR registration; "
                            "overlaps do not apply."),
        "about": ("Period: MapBiomas {mb_start}–{mb_end}, Hansen "
                  "{hansen_start}–{hansen_end}. Zones: {zones}. Each section "
                  "gives the dataset, the chart, a summary table and a "
                  "paragraph with the numbers. This document describes "
                  "remote-sensing measurements; it passes no judgement on the "
                  "property."),
        "about_focus": ("Per-zone charts show the zone «{zone}», the one active "
                        "on screen."),
        "not_run_reason": "not run in this session (the tab's Calcular button)",
        "excluded_reason": "unticked in the export dialog",
        "validacao_mode_reason": ("computed only in the Validação tab's IBGE "
                                  "2022 mode"),
        "maps_failed_reason": "Earth Engine did not respond: {detail}",
        "no_data": "No data for this zone.",
        "figure_capture_failed": "the browser did not produce the image ({detail})",
        "intro_cobertura": ("MapBiomas Collection 10.1: annual land use and "
                            "cover classification, 30 m, {start}–{end}."),
        "intro_transicoes": ("Area that went from each MapBiomas class in "
                             "{year_a} to each class in {year_b}, in the zone "
                             "«{zone}»."),
        "intro_floresta": ("Hansen Global Forest Change: tree-cover loss dated "
                           "by year ({start}–{end}), in pixels with at least "
                           "{threshold}% canopy in 2000, split into three "
                           "periods: up to 2008, from 2008 to the CAR "
                           "registration, and after registration."),
        "intro_biomassa": ("ESA CCI Biomass v6.0: above-ground biomass "
                           "(Mg/ha), 100 m, years 2007, 2010 and 2015–2022."),
        "intro_paisagem": ("Landscape metrics over MapBiomas native-vegetation "
                           "patches: number of patches, largest patch, edge "
                           "density and effective mesh size (Meff)."),
        "intro_fogo": ("MapBiomas Fire Collection 5: annual burned area, "
                       "1985–2025."),
        "intro_validacao": ("Area-weighted comparison between IBGE's "
                            "Vegetation map (2022) and MapBiomas 2022, grouped "
                            "into shared classes, in the zone «{zone}»."),
        "intro_spot": ("Circa-2008 SPOT mosaic (Google LLC), over forest areas "
                       "only; the acquisition date varies per pixel and is "
                       "given below."),
        "intro_gbif": ("GBIF occurrence records per zone, cumulative (each "
                       "zone includes the property and the inner rings)."),
        "cobertura_zone": ("Within the zone «{zone}», {cls_a} covered {ha_a} "
                           "({pct_a}) in {year_a}; in {year_b}, {cls_b} covers "
                           "{ha_b} ({pct_b})."),
        "cobertura_ring": (" In the ring «{zone}», {cls} went from {pct_a} to "
                           "{pct_b} over the same period."),
        "transicoes": ("Of {total} mapped in the zone, {stable} ({stable_pct}) "
                       "stayed in the same class between {year_a} and "
                       "{year_b}. The largest change was from {src} to {tgt}: "
                       "{area}."),
        "transicoes_stable": ("Of {total} mapped in the zone, {stable} "
                              "({stable_pct}) stayed in the same class between "
                              "{year_a} and {year_b}."),
        "floresta": ("Hansen records {total} of tree-cover loss within the "
                     "property between {start} and {end}: {p1} up to 2008, "
                     "{p2} between 2008 and the CAR registration ({reg}), and "
                     "{p3} after registration."),
        "floresta_noreg": ("Hansen records {total} of tree-cover loss within "
                           "the property between {start} and {end}: {p1} up to "
                           "2008 and {p3} after 2008 (no CAR registration "
                           "date)."),
        "floresta_none": ("Hansen records no tree-cover loss within the "
                          "property between {start} and {end}."),
        "none_ha": "none",
        "floresta_gain": ("Tree-cover gain within the property: {gain}. Hansen "
                          "gain is a single undated layer (2000–2012); it is "
                          "never added to loss or placed on the timeline."),
        "biomassa": ("Within the zone «{zone}», mean above-ground biomass was "
                     "{v_a} Mg/ha in {year_a} and {v_b} Mg/ha in {year_b}."),
        "paisagem": ("The property has {patches} native-vegetation patches, "
                     "with a Meff of {meff}; in the ring «{ring}», Meff is "
                     "{meff_ring}."),
        "paisagem_one": ("The zone «{zone}» has {patches} native-vegetation "
                         "patches, with a Meff of {meff}."),
        "fogo": ("Within the zone «{zone}», {hist} of the area burned at least "
                 "once between 1985 and 2025; the highest frequency is {freq} "
                 "fires and the last year with fire is {last}."),
        "fogo_nolast": ("Within the zone «{zone}», {hist} of the area burned at "
                        "least once between 1985 and 2025; the highest frequency "
                        "is {freq} fires."),
        "fogo_never": ("Within the zone «{zone}», MapBiomas Fire records no "
                       "burned area between 1985 and 2025."),
        "fogo_ring": (" In the ring «{ring}», the share burned at least once is "
                      "{hist}."),
        "validacao": ("IBGE classifies {forest_ibge} of the zone as forest and "
                      "MapBiomas {forest_mb}; natural vegetation: "
                      "{natural_ibge} in IBGE and {natural_mb} in MapBiomas."),
        "spot": ("The SPOT mosaic covers {covered} of the property; {pre} of "
                 "that area was imaged before {cutoff} (images from {d_min} "
                 "to {d_max})."),
        "spot_pre_unknown": ("The SPOT mosaic covers {covered} of the property "
                             "(images from {d_min} to {d_max}); the share "
                             "imaged before {cutoff} is unavailable."),
        "spot_none": ("The SPOT mosaic does not cover this property: the "
                      "dataset spans only Brazil's forest areas."),
        "gbif": ("Within the zone «{zone}» there are {records} occurrence "
                 "records of {species} species."),
        "cap_cobertura": "Land use and cover per year (MapBiomas) — {zone}.",
        "cap_cobertura_table": ("MapBiomas classes in {year_a} and {year_b} — "
                                "{zone}."),
        "cap_zones": "Zones analysed: the property and its neighbourhood rings.",
        "cap_overlaps": "CAR registrations that overlap this polygon.",
        "cap_transicoes": "Transitions {year_a}–{year_b} — {zone}.",
        "cap_transicoes_table": ("The 10 largest transitions between different "
                                 "classes, {year_a}–{year_b} — {zone}."),
        "cap_floresta": "Tree-cover loss per year and period (Hansen) — {zone}.",
        "cap_floresta_table": "Tree-cover loss per period and zone (ha).",
        "cap_biomassa": "Mean above-ground biomass (ESA CCI) — {zone}.",
        "cap_biomassa_table": "Above-ground biomass per year — {zone}.",
        "cap_paisagem": "Effective mesh size (Meff) per zone.",
        "cap_paisagem_table": "Landscape metrics per zone.",
        "cap_conectividade_table": ("Connectivity between forest patches "
                                    "(nearest-neighbour distance)."),
        "cap_fogo": "Burned area per year (MapBiomas Fire) — {zone}.",
        "cap_fogo_table": "Fire per zone, 1985–2025.",
        "cap_validacao_table": ("IBGE (rows) × MapBiomas (columns), % of area "
                                "— {zone}."),
        "cap_gbif_table": "GBIF records and species per zone (cumulative).",
        "cap_appendix_cobertura": "MapBiomas cover per zone, class and year (ha).",
        "cap_appendix_fogo": "Burned area per zone and year (%).",
        "cap_map_s2": ("Sentinel-2 image ({year}, dry season) with the declared "
                       "boundary and the 500 m ring."),
        "cap_map_spot": ("SPOT mosaic, images from {d_min} to {d_max}; {pre} of "
                         "the covered area was imaged before {cutoff}. "
                         "Declared boundary and 500 m ring."),
        "cap_map_spot_pre_unknown": ("SPOT mosaic, images from {d_min} to "
                                     "{d_max}; share imaged before {cutoff} "
                                     "unavailable. Declared boundary and "
                                     "500 m ring."),
        "cap_map_mapbiomas": ("MapBiomas {year} with the declared boundary and "
                              "the rings out to {radius}."),
        "cap_map_hansen": ("Tree cover in 2000 (green) and Hansen loss from "
                           "{from_year} to {end} (red), with the declared "
                           "boundary and the rings out to {radius}."),
        "legend_property": "Declared boundary",
        "legend_property_square": "Reference area",
        "legend_rings": "Neighbourhood rings",
        "legend_treecover": "Tree cover in 2000",
        "legend_loss": "Loss {from_year}–{end}",
        "legend_gain": "Gain (undated, 2000–2012)",
        "h_zone": "Zone", "h_kind": "Kind", "h_radius": "Radius (m)",
        "h_area_ha": "Area (ha)", "h_class": "Class", "h_pct": "%",
        "h_from": "From", "h_to": "To", "h_cod": "Property code",
        "h_overlap_ha": "Overlap (ha)", "h_overlap_pct": "% of property",
        "h_up_to_2008": "Up to 2008", "h_to_reg": "2008 to registration",
        "h_after_reg": "After registration", "h_total": "Total",
        "h_year": "Year", "h_agb": "Mg/ha", "h_agb_total": "Total (Mg)",
        "h_patches": "Patches", "h_largest_pct": "Largest (%)",
        "h_edge_density": "Edge (m/ha)", "h_meff": "Meff (ha)",
        "h_shannon": "Shannon", "h_n_frag": "Patches",
        "h_enn_mean": "Mean dist. (m)", "h_enn_median": "Median (m)",
        "h_fire_hist": "Burned 1+ times (%)", "h_fire_freq": "Max. frequency",
        "h_fire_last": "Last year", "h_fire_pct": "Burned (%)",
        "h_records": "Records", "h_species": "Species",
        "kind_property": "property", "kind_ring": "ring",
        "kind_square": "reference area",
        "spot_row": "SPOT 2008 coverage",
    },
}


def _t(key: str, lang: str, **kw) -> str:
    """A template in ``lang`` (fallback pt), filled in Python."""
    table = TEMPLATES.get(lang) or TEMPLATES["pt"]
    text = table.get(key, TEMPLATES["pt"][key])
    return text.format(**kw) if kw else text


def t(key: str, lang: str = "pt", **kw) -> str:
    return _t(key, lang, **kw)


def signed(value: Any, decimals: int = 1, lang: str = "pt") -> str:
    """``report_kit.text.fmt_signed`` with an ASCII minus: the kit's bundled
    Noto Sans subset has no U+2212 glyph, so the true minus it emits is
    silently dropped from the PDF (reported upstream; see doc/13 status)."""
    return fmt_signed(value, decimals, lang).replace("\u2212", "-")


def class_name(row: Dict[str, Any], lang: str) -> str:
    return str(row.get("class_en" if lang == "en" else "class_pt")
               or row.get("class_pt") or row.get("class_id", ""))


# --------------------------------------------------------------------------- #
# Identification
# --------------------------------------------------------------------------- #

def area_text(declared: float, computed: float, delta_pct: float,
              lang: str = "pt") -> str:
    return _t("area", lang, declared=fmt_ha(declared, 1, lang),
              computed=fmt_ha(computed, 1, lang),
              delta=f"{signed(delta_pct, 1, lang)}"
                    f"{'' if lang == 'en' else ' '}%")


def area_square_text(computed: float, coords: str, lang: str = "pt") -> str:
    return _t("area_square", lang, computed=fmt_ha(computed, 1, lang),
              coords=coords or "—")


def zones_text(zones: List[Dict[str, Any]], lang: str = "pt") -> str:
    rings = [z for z in zones if z.get("zone_kind") == "ring"]
    radii = ", ".join(_radius_label(z.get("radius_m"), lang) for z in rings)
    return _t("zones_one" if len(rings) == 1 else "zones", lang, n=len(rings),
              radii=radii or "—")


def _radius_label(radius_m: Any, lang: str) -> str:
    try:
        r = float(radius_m)
    except (TypeError, ValueError):
        return "—"
    if r >= 1000:
        return f"{fmt_num(r / 1000, 0 if r % 1000 == 0 else 1, lang)} km"
    return f"{fmt_int(r, lang)} m"


def radius_label(radius_m: Any, lang: str = "pt") -> str:
    return _radius_label(radius_m, lang)


def overlaps_text(overlaps: List[Dict[str, Any]], checked: bool, reason: str = "",
                  *, square: bool = False, lang: str = "pt") -> str:
    if square:
        return _t("overlaps_square", lang)
    if not checked:
        return _t("overlaps_unchecked", lang, reason=reason or "—")
    if not overlaps:
        return _t("overlaps_none", lang)
    if len(overlaps) == 1:
        return _t("overlaps_one", lang)
    return _t("overlaps_some", lang, n=fmt_int(len(overlaps), lang))


# --------------------------------------------------------------------------- #
# Analyses
# --------------------------------------------------------------------------- #

def _by_year(rows: Iterable[Dict[str, Any]], year: int) -> List[Dict[str, Any]]:
    return [r for r in rows if int(r.get("year", 0)) == year]


def _share(rows: List[Dict[str, Any]], class_id: Any) -> float:
    total = sum(float(r["area_ha"]) for r in rows) or 0.0
    part = sum(float(r["area_ha"]) for r in rows if r.get("class_id") == class_id)
    return 100.0 * part / total if total else 0.0


def cobertura_text(history_rows: List[Dict[str, Any]], zones: List[Dict[str, Any]],
                   focus_zone: str, lang: str = "pt") -> str:
    """Dominant class of the focus zone in the first and last year; the
    outermost ring's first-year dominant class, first→last share."""
    zone_rows = [r for r in history_rows if r.get("zone_key") == focus_zone]
    if not zone_rows:
        return _t("no_data", lang)
    years = sorted({int(r["year"]) for r in zone_rows})
    ya, yb = years[0], years[-1]
    rows_a, rows_b = _by_year(zone_rows, ya), _by_year(zone_rows, yb)
    top_a = max(rows_a, key=lambda r: r["area_ha"])
    top_b = max(rows_b, key=lambda r: r["area_ha"])
    label = _zone_label(zones, focus_zone)
    text = _t("cobertura_zone", lang, zone=label, cls_a=class_name(top_a, lang),
              ha_a=fmt_ha(top_a["area_ha"], 0, lang),
              pct_a=fmt_pct(_share(rows_a, top_a["class_id"]), 0, lang),
              year_a=ya, cls_b=class_name(top_b, lang),
              ha_b=fmt_ha(top_b["area_ha"], 0, lang),
              pct_b=fmt_pct(_share(rows_b, top_b["class_id"]), 0, lang), year_b=yb)
    rings = [z for z in zones if z.get("zone_kind") == "ring"]
    if rings and rings[-1]["zone_key"] != focus_zone:
        ring = rings[-1]
        ring_rows = [r for r in history_rows if r.get("zone_key") == ring["zone_key"]]
        ra, rb = _by_year(ring_rows, ya), _by_year(ring_rows, yb)
        if ra and rb:
            top = max(ra, key=lambda r: r["area_ha"])
            text += _t("cobertura_ring", lang, zone=ring.get("zone_label", ""),
                       cls=class_name(top, lang),
                       pct_a=fmt_pct(_share(ra, top["class_id"]), 0, lang),
                       pct_b=fmt_pct(_share(rb, top["class_id"]), 0, lang))
    return text


def transitions_text(rows: List[tuple], year_a: int, year_b: int,
                     lang: str = "pt") -> str:
    """``rows``: (src_label, tgt_label, area_ha, same_class) tuples."""
    total = sum(r[2] for r in rows)
    if not total:
        return _t("no_data", lang)
    stable = sum(r[2] for r in rows if r[3])
    changes = sorted((r for r in rows if not r[3]), key=lambda r: -r[2])
    kw = dict(total=fmt_ha(total, 0, lang), stable=fmt_ha(stable, 0, lang),
              stable_pct=fmt_pct(100.0 * stable / total, 0, lang),
              year_a=year_a, year_b=year_b)
    if not changes:
        return _t("transicoes_stable", lang, **kw)
    src, tgt, area, _ = changes[0]
    return _t("transicoes", lang, src=src, tgt=tgt, area=fmt_ha(area, 1, lang), **kw)


def hansen_period_totals(loss_rows: List[Dict[str, Any]], zone_key: str) -> Dict[str, float]:
    out = {"ate_2008": 0.0, "2008_ate_registro": 0.0, "apos_registro": 0.0}
    for r in loss_rows:
        if r.get("zone_key") == zone_key and r.get("period") in out:
            out[r["period"]] += float(r["area_ha"])
    return out


def floresta_text(loss_rows: List[Dict[str, Any]], registration_year: Optional[int],
                  start: int, end: int, lang: str = "pt") -> str:
    p = hansen_period_totals(loss_rows, "imovel")
    total = sum(p.values())
    if total <= 0:
        return _t("floresta_none", lang, start=start, end=end)

    def ha(v: float) -> str:
        return fmt_ha(v, 1, lang) if v > 0.05 else _t("none_ha", lang)

    if registration_year:
        return _t("floresta", lang, total=fmt_ha(total, 1, lang), start=start,
                  end=end, p1=ha(p["ate_2008"]), p2=ha(p["2008_ate_registro"]),
                  p3=ha(p["apos_registro"]), reg=registration_year)
    return _t("floresta_noreg", lang, total=fmt_ha(total, 1, lang), start=start,
              end=end, p1=ha(p["ate_2008"]),
              p3=ha(p["2008_ate_registro"] + p["apos_registro"]))


def floresta_gain_text(gain_ha: float, lang: str = "pt") -> str:
    return _t("floresta_gain", lang, gain=fmt_ha(gain_ha, 1, lang))


def biomass_text(rows: List[Dict[str, Any]], zone_label: str, lang: str = "pt") -> str:
    ordered = sorted((r for r in rows if r.get("agb_mean_mgha") is not None),
                     key=lambda r: r["year"])
    if not ordered:
        return _t("no_data", lang)
    a, b = ordered[0], ordered[-1]
    return _t("biomassa", lang, zone=zone_label,
              v_a=fmt_num(a["agb_mean_mgha"], 1, lang), year_a=a["year"],
              v_b=fmt_num(b["agb_mean_mgha"], 1, lang), year_b=b["year"])


def landscape_text(rows: List[Dict[str, Any]], lang: str = "pt") -> str:
    if not rows:
        return _t("no_data", lang)
    first = rows[0]
    if len(rows) == 1:
        return _t("paisagem_one", lang, zone=first.get("zone_label", ""),
                  patches=fmt_int(first.get("patches"), lang),
                  meff=fmt_ha(first.get("meff_ha"), 1, lang))
    last = rows[-1]
    return _t("paisagem", lang, patches=fmt_int(first.get("patches"), lang),
              meff=fmt_ha(first.get("meff_ha"), 1, lang),
              ring=last.get("zone_label", ""),
              meff_ring=fmt_ha(last.get("meff_ha"), 1, lang))


def year_or_none(value: Any) -> Optional[int]:
    """A year cell that may be None, NaN (pandas) or a float — as an int."""
    try:
        year = int(float(value))
    except (TypeError, ValueError):
        return None
    return year if year > 0 else None


def fire_text(fire_rows: List[Dict[str, Any]], zones: List[Dict[str, Any]],
              focus_zone: str, lang: str = "pt") -> str:
    row = next((r for r in fire_rows if r.get("zone_key") == focus_zone), None)
    if row is None:
        return _t("no_data", lang)
    label = _zone_label(zones, focus_zone)
    hist = float(row.get("fire_history_pct") or 0.0)
    if hist <= 0:
        text = _t("fogo_never", lang, zone=label)
    else:
        last = year_or_none(row.get("fire_last_year"))
        kw = dict(zone=label, hist=fmt_pct(hist, 1, lang),
                  freq=fmt_int(row.get("fire_frequency") or 0, lang))
        text = (_t("fogo", lang, last=last, **kw) if last
                else _t("fogo_nolast", lang, **kw))
    rings = [z for z in zones if z.get("zone_kind") == "ring"]
    if rings and rings[-1]["zone_key"] != focus_zone:
        ring_row = next((r for r in fire_rows
                         if r.get("zone_key") == rings[-1]["zone_key"]), None)
        if ring_row is not None:
            text += _t("fogo_ring", lang, ring=rings[-1].get("zone_label", ""),
                       hist=fmt_pct(ring_row.get("fire_history_pct") or 0.0, 1, lang))
    return text


def validacao_text(matrix: Dict[str, Any], lang: str = "pt") -> str:
    if not matrix.get("matrix"):
        return _t("no_data", lang)
    return _t("validacao", lang,
              forest_ibge=fmt_pct(matrix.get("forest_ibge"), 1, lang),
              forest_mb=fmt_pct(matrix.get("forest_mb"), 1, lang),
              natural_ibge=fmt_pct(matrix.get("natural_ibge"), 1, lang),
              natural_mb=fmt_pct(matrix.get("natural_mb"), 1, lang))


def spot_text(summary: Dict[str, Any], lang: str = "pt") -> str:
    """doc/12 §4: dates and the share imaged before the cutoff — never
    "0 %" for an unknown share, never a label derived from the imagery."""
    if not summary.get("has_coverage"):
        return _t("spot_none", lang)
    kw = dict(covered=fmt_pct(summary.get("covered_pct"), 0, lang),
              cutoff=fmt_date(summary.get("cutoff", "2008-07-22"), lang),
              d_min=fmt_date(summary.get("date_min"), lang),
              d_max=fmt_date(summary.get("date_max"), lang))
    pre = summary.get("pre_cutoff_pct")
    if pre is None:
        return _t("spot_pre_unknown", lang, **kw)
    return _t("spot", lang, pre=fmt_pct(pre, 0, lang), **kw)


def spot_map_caption(summary: Dict[str, Any], lang: str = "pt") -> str:
    kw = dict(cutoff=fmt_date(summary.get("cutoff", "2008-07-22"), lang),
              d_min=fmt_date(summary.get("date_min"), lang),
              d_max=fmt_date(summary.get("date_max"), lang))
    pre = summary.get("pre_cutoff_pct")
    if pre is None:
        return _t("cap_map_spot_pre_unknown", lang, **kw)
    return _t("cap_map_spot", lang, pre=fmt_pct(pre, 0, lang), **kw)


def gbif_text(zone_label: str, records: Any, species: Any, lang: str = "pt") -> str:
    return _t("gbif", lang, zone=zone_label, records=fmt_int(records, lang),
              species=fmt_int(species, lang))


def about_text(zones: List[Dict[str, Any]], mb_start: int, mb_end: int,
               hansen_start: int, hansen_end: int, lang: str = "pt") -> str:
    labels = ", ".join(str(z.get("zone_label", "")) for z in zones) or "—"
    return _t("about", lang, mb_start=mb_start, mb_end=mb_end,
              hansen_start=hansen_start, hansen_end=hansen_end, zones=labels)


def _zone_label(zones: List[Dict[str, Any]], key: str) -> str:
    return next((str(z.get("zone_label", key)) for z in zones
                 if z.get("zone_key") == key), key)


def zone_label(zones: List[Dict[str, Any]], key: str) -> str:
    return _zone_label(zones, key)


__all__ = ["TEMPLATES", "t", "area_text", "area_square_text", "zones_text",
           "overlaps_text", "cobertura_text", "transitions_text", "floresta_text",
           "floresta_gain_text", "biomass_text", "landscape_text", "fire_text",
           "validacao_text", "spot_text", "spot_map_caption", "gbif_text",
           "about_text", "hansen_period_totals", "zone_label", "radius_label",
           "class_name"]
