"""Portuguese — canonical key set. Every other language falls back to this.

Values are the exact strings the UI already showed before this table existed
— PT text moved here verbatim from each component, not rewritten, so porting
a component to ``AppState.tr`` never changes what a Portuguese-reading user
sees.
"""

from __future__ import annotations

TRANSLATIONS_PT: dict[str, str] = {
    # --- header --------------------------------------------------------- #
    "app_name": "Camposcope - Earth Engine para o CAR",

    # --- search panel (components/search.py) ---------------------------- #
    "search_title": "Busca",
    "search_placeholder": "código CAR, coordenada, município ou lugar…",
    "search_read_as": "lido como:",
    "search_button": "Buscar",
    "search_button_busy": "Buscando…",
    "search_municipios_heading": "Municípios",
    "search_places_heading": "Lugares",
    "search_places_note": (
        "Um lugar apenas enquadra o mapa. Clique sobre um imóvel para "
        "analisá-lo."
    ),
    "search_places_attribution": (
        "Busca de lugares © colaboradores do OpenStreetMap (ODbL)"
    ),
    "search_candidates_note": (
        "Mais de um imóvel registrado cobre este ponto. Sobreposições são "
        "comuns no CAR — escolha qual analisar:"
    ),
    "echo_codigo": "código CAR",
    "echo_coordenada": "coordenada",
    "echo_municipio": "município",
    "echo_lugar": "lugar",
    "municipio_browser_title": "Imóveis no município",
    "municipio_browser_total": "registros",
    "municipio_browser_prev": "‹ anterior",
    "municipio_browser_next": "próxima ›",

    # --- cadastral card (components/cadastro.py) ------------------------ #
    "cadastro_title": "Imóvel",
    "cadastro_codigo": "Código",
    "cadastro_municipio": "Município",
    "cadastro_area_declarada": "Área declarada",
    "cadastro_area_calculada": "Área calculada (geometria)",
    "cadastro_area_disagreement_prefix": (
        "A área declarada e a área da geometria diferem em"
    ),
    "cadastro_area_disagreement_suffix": "Ambas são exibidas como estão.",
    "cadastro_modulos_fiscais": "Módulos fiscais",
    "cadastro_tipo": "Tipo",
    "cadastro_status": "Status",
    "cadastro_condicao": "Condição",
    "cadastro_registrado_em": "Registrado em",
    "cadastro_atualizado_em": "Atualizado em",
    "cadastro_nao_informada": "não informada",
    "cadastro_sobreposicoes": "Sobreposições com outros registros",
    "zonas_title": "Zonas",
    "zonas_note": "Anéis medidos a partir do limite do imóvel, não do centroide.",

    # --- results: shared (components/results.py) ------------------------ #
    "calcular": "Calcular",
    "calculando": "Calculando…",
    "map_layer_note": (
        "A camada correspondente aparece no mapa — use a legenda no canto do "
        "mapa para ligar/desligar ou trocar o ano."
    ),
    "tab_cobertura": "Cobertura",
    "tab_transicoes": "Transições",
    "tab_floresta": "Floresta",
    "tab_biomassa": "Biomassa",
    "tab_fogo": "Fogo",
    "tab_validacao": "Validação",

    # --- Cobertura tab ---------------------------------------------------- #
    "cobertura_ano": "Ano",
    "cobertura_classe": "Classe",
    "cobertura_hectares": "hectares",
    "cobertura_percentual": "percentual",
    "cobertura_degraded": (
        "Resultado calculado em resolução reduzida após uma falha temporária "
        "do Earth Engine."
    ),
    "cobertura_running": "Calculando trajetória MapBiomas…",
    "cobertura_empty": "Selecione um imóvel para ver a trajetória de uso da terra.",
    "cobertura_attribution": (
        "MapBiomas Coleção 10.1 (CC BY-SA 4.0) · escala 30 m · reduceRegions "
        "em lote por zona."
    ),

    # --- Floresta tab ----------------------------------------------------- #
    "floresta_intro": (
        "Perda de cobertura florestal por período: até 2008 (data de corte "
        "do Código Florestal), de 2008 até o registro no CAR, e depois do "
        "registro. Ganho é uma camada única, sem data (2000–2012), nunca "
        "somado à perda."
    ),
    "floresta_ate_2008": "Até 2008",
    "floresta_2008_ate_registro": "2008 até o registro",
    "floresta_depois_registro": "Depois do registro",
    "floresta_ganho_sem_data": "Ganho (sem data)",
    "floresta_col_ano": "Ano",
    "floresta_col_perda": "Perda (ha)",
    "floresta_col_periodo": "Período",
    "floresta_attribution": "Hansen/UMD/Google/USGS/NASA — Global Forest Change · escala 30 m.",

    # --- Biomassa tab ------------------------------------------------------ #
    "biomassa_intro": (
        "Biomassa acima do solo, dez anos: 2007, 2010 e anual a partir de "
        "2015. O intervalo entre eles é uma lacuna real da fonte, não um "
        "dado ausente — não interpolado."
    ),
    "biomassa_col_ano": "Ano",
    "biomassa_col_mg_ha": "Mg/ha",
    "biomassa_col_total_mg": "Total (Mg)",
    "biomassa_attribution": "ESA CCI Biomass v6.0 — Santoro & Cartus (2025) · escala 100 m.",

    # --- Fogo tab --------------------------------------------------------------- #
    "fogo_intro": (
        "Análise de histórico de fogo (% de anos com fogo detectado), frequência de "
        "ocorrências de queimadas e ano da última queimada."
    ),
    "fogo_col_ano": "Ano",
    "fogo_col_cicatrizes": "Cicatrizes (%)",
    "fogo_col_frequencia": "Frequência",
    "fogo_historio_anos": "Anos com fogo",
    "fogo_frequencia_ocorrencias": "Frequência (ocorrências)",
    "fogo_ultima_queimada": "Última queimada",
    "fogo_attribution": "MapBiomas Fogo Coleção 5 (CC BY-SA 4.0) · escala 30 m · classificação Landsat (NBR) com aprendizado profundo.",

    # --- Transições tab (components/sankey.py) ---------------------------- #
    "transicoes_intro": (
        "Transições de cobertura da terra pixel a pixel — a soja que virou "
        "floresta continua contada como soja em ambos os pontos da "
        "comparação."
    ),
    "transicoes_multi_stage_title": "Antes · registro do CAR · hoje",
    "transicoes_multi_stage_running": "Calculando transições…",
    "transicoes_de": "De",
    "transicoes_para": "Para",
    "transicoes_maiores": "Maiores transições",
    "transicoes_min_gap_note_prefix": "MapBiomas Coleção 10.1 · pares de anos com menos de",
    "transicoes_min_gap_note_suffix": (
        "anos de diferença são recusados — nesse intervalo, a maior parte "
        "das \"transições\" é ruído de classificação, não mudança real."
    ),

    # --- Validação tab (components/validacao.py) -------------------------- #
    "validacao_mode_spot": "SPOT × MapBiomas 2008",
    "validacao_mode_ibge": "IBGE × MapBiomas 2022",
    "validacao_spot_mosaic": "Mosaico SPOT",
    "validacao_spot_visual": "Visual",
    "validacao_spot_analytic": "Falsa-cor (NIR)",
    "validacao_spot_analytic_short": "Falsa-cor",
    "validacao_spot_note": (
        "Imagens SPOT de aproximadamente 2008 ao lado da classificação "
        "MapBiomas para o mesmo ano — a referência visual mais próxima da "
        "data de corte do Código Florestal (22/07/2008)."
    ),
    "validacao_no_verdict": "Não classifica área consolidada nem avalia regularidade.",
    "validacao_no_verdict_short": "Não classifica área consolidada.",
    "validacao_floresta": "Floresta",
    "validacao_natural": "Natural",
    "validacao_col_ibge": "IBGE (esquerda)",
    "validacao_col_mapbiomas": "MapBiomas (direita)",
    "validacao_ibge_intro": (
        "IBGE Vegetação (1:250.000, 2022) contra a classificação MapBiomas "
        "do mesmo ano, reduzidas a uma taxonomia comum de 6 grupos — os "
        "dois mapas não compartilham classes."
    ),
    "validacao_ibge_caveat": (
        "'Vegetação Secundária' do IBGE não tem equivalente direto no "
        "MapBiomas por definição; a tabela mostra o que o MapBiomas lê hoje "
        "nesses polígonos."
    ),
    "validacao_attribution": (
        "IBGE — Mapa de Vegetação do Brasil 1:250.000 (2022) · Google Brazil "
        "Forest Imagery Dataset 2008."
    ),

    # --- on-map legend (components/map_legend.py) -------------------------- #
    "legend_mapbiomas": "MapBiomas",
    "legend_mapbiomas_palette": "Cores: paleta oficial MapBiomas",
    "legend_floresta_hansen": "Floresta — Hansen",
    "legend_hansen_since_2008": "desde 2008",
    "legend_hansen_since_registro": "desde o registro",
    "legend_perda": "Perda",
    "legend_ganho_sem_data": "Ganho (sem data)",
    "legend_spot_2008": "Imagem SPOT 2008",
    "legend_loading": "Carregando…",
    "legend_verifying": "Verificando…",
    "legend_verify_coverage": "Verificar cobertura",
    "legend_no_coverage": "Sem cobertura SPOT nesta zona.",
    "legend_spot_before_cutoff": "antes de 22/07/2008",
    "legend_biomassa_esa": "Biomassa — ESA CCI",
    "legend_fogo_frequencia": "Fogo — Frequência",
    "legend_fogo_ocorrencias": "ocorrências (1985–2025)",
    "legend_mapbiomas_comparacao": "MapBiomas — comparação",
    "legend_choose_years": "Escolha os anos na aba Transições.",
    "legend_drag_to_compare": "Arraste a barra no mapa para comparar.",
    "legend_choose_mode": "Escolha o modo na aba Validação.",
    "legend_visual": "Visual",
    "legend_falsa_cor": "Falsa-cor",

    # --- layers panel (pages/index.py) -------------------------------------- #
    "layers_title": "Camadas",
    "layers_loading": "Carregando camada…",
    "layers_spot_hint": "Verificação de cobertura e datas: aba Floresta.",
    "layers_car_wms": "Imóveis do CAR (WMS)",
    "layers_car_wms_note": "Aparece a partir do zoom 8.",
    "layers_biomes": "Biomas e domínios (IBGE)",
    "layers_biomes_note": (
        "Limites aproximados (~1 km) — orientação, não decide o bioma de um "
        "imóvel específico."
    ),
    "sidebar_hide_aria": "Esconder painel",
    "sidebar_show_aria": "Mostrar painel",

    # --- runtime errors (state/*.py — set from background event handlers,
    # not JSX, so they read through get_translations() directly rather
    # than the AppState.tr computed var) ------------------------------- #
    "erro_fora_brasil": (
        "Este ponto está fora do território brasileiro coberto pelo CAR."
    ),
    "erro_sem_imovel_ponto": "Nenhum imóvel registrado no CAR neste ponto ({uf}).",
    "erro_lugar_nao_encontrado": (
        "Nenhum lugar encontrado para “{query}”. Tente um "
        "município, uma coordenada ou um código CAR."
    ),
    "erro_zonas": "Não foi possível construir as zonas: {detail}",
    "erro_camada_aba": "Não foi possível carregar a camada desta aba no mapa.",
    "erro_camadas_comparacao": "Não foi possível carregar as camadas de comparação.",
    "erro_camadas_comparacao_spot": (
        "Não foi possível carregar as camadas de comparação. SPOT pode "
        "exigir CS_SPOT_ENABLED=true."
    ),
    "erro_basemap": (
        "Não foi possível carregar a camada '{name}'. Ela pode exigir uma "
        "licença que esta instalação não tem (CS_SPOT_ENABLED)."
    ),
    "erro_transicao": "Não foi possível calcular a transição: {detail}",
    "erro_transicoes_multi": "Não foi possível calcular as transições: {detail}",
    "erro_transicao_dados_insuficientes": (
        "Sem dados de transição suficientes para o diagrama."
    ),
    "erro_trajetoria_mapbiomas": (
        "Não foi possível calcular a trajetória MapBiomas: {detail}"
    ),
    "erro_mapbiomas_sem_classes": (
        "A consulta ao MapBiomas não retornou classes para esta geometria."
    ),
    "erro_perda_florestal": "Não foi possível calcular a perda florestal: {detail}",
    "erro_biomassa": "Não foi possível calcular a biomassa: {detail}",
    "erro_fogo": "Não foi possível calcular a análise de fogo: {detail}",
    "erro_spot_cobertura": "Não foi possível verificar a cobertura SPOT: {detail}",
    "erro_comparacao_ibge": "Não foi possível calcular a comparação: {detail}",

    # --- disclosure (constraint C4, config/sicar.py DISCLOSURE_PT mirror) -- #
    # Not read from here — AppState.disclosure reads config/sicar.py's own
    # DISCLOSURE_PT/DISCLOSURE_EN constants directly (one canonical legal
    # statement, not duplicated into this table).

    # --- citation dialog (components/citation.py) --------------------------- #
    # Already bilingual via its own rx.cond(lang==...) pairs; not migrated
    # here to avoid a second source of truth for the same strings.

    # --- export dialog (components/exports.py) ------------------------------ #
    "download_button": "Baixar dados",
    "export_dialog_title": "Baixar dados",
    "export_dialog_desc": (
        "Uma planilha com tudo o que já foi calculado para este imóvel, ou um "
        "relatório em HTML pronto para leitura ou impressão."
    ),
    "export_choose_imovel_first": "Selecione um imóvel primeiro.",
    "export_stage_waiting": "Aguardando a trajetória MapBiomas terminar…",
    "export_stage_building": "Montando o arquivo…",
    "export_workbook_failed": "Falha ao gerar a planilha: {exc}",
    "export_report_failed": "Falha ao gerar o relatório: {exc}",
    "download_workbook_button": "Baixar planilha (.ods)",
    "download_workbook_hint": "Selecione um imóvel no mapa ou na busca para habilitar.",
    "workbook_desc": (
        "Uma planilha com a cobertura por zona e ano, a perda florestal, a "
        "biomassa, as transições e o fogo já calculados, a validação IBGE "
        "(se calculada), o dicionário de classes do MapBiomas e uma aba de "
        "metadados com a proveniência de cada consulta."
    ),
    "report_section_title": "Relatório em HTML (formato de artigo)",
    "report_section_desc": (
        "Um único arquivo HTML autocontido com os gráficos e/ou tabelas já "
        "calculados, formatado para leitura ou impressão em PDF — "
        "complementa a planilha acima, não a substitui."
    ),
    "check_report_figures_label": "Gráficos",
    "check_report_figures_detail": (
        "Cobertura, floresta, biomassa e fogo — um gráfico por zona — mais "
        "as transições, se já calculadas."
    ),
    "check_report_tables_label": "Tabelas",
    "check_report_tables_detail": (
        "Cobertura mais recente, perda florestal, biomassa, transições, "
        "fogo, validação IBGE (se já calculada) e a proveniência de cada "
        "consulta."
    ),
    "download_report_button": "Baixar relatório (HTML)",
    "export_close_button": "Fechar",

    # --- per-chart/per-table export icons (components/export_widgets.py) --- #
    "export_chart_aria": "Baixar este gráfico (PNG)",
    "export_table_aria": "Baixar esta tabela (CSV)",
    "export_chart_label": "Exportar figura",
    "export_table_label": "Exportar tabela",
}
