"""Portuguese overrides for the Canada page.

English is canonical here (see this module's package docstring); Portuguese
fills in what a Brazilian-Portuguese reader needs and falls back to English for
anything not (yet) overridden below.
"""

from __future__ import annotations

TRANSLATIONS_PT: dict[str, str] = {
    # --- header ----------------------------------------------------------- #
    "app_name": "Camposcope — Earth Engine para Propriedades Rurais",
    "nav_title_suffix": "Canadá",
    "nav_subtitle": "Análise de propriedades rurais a partir da malha "
        "ParcelMap BC",
    "go_to_brazil": "Brasil",
    "language_label": "Idioma",
    "nav_toggle_layers_aria": "Mostrar camadas",
    "drawer_title": "Camadas",
    "drawer_close_aria": "Fechar",
    "sidebar_show_aria": "Mostrar painel lateral",
    "sidebar_hide_aria": "Ocultar painel lateral",
    "close_button": "Fechar",
    "calcular": "Calcular",
    "calculando": "Calculando…",

    # --- search panel ------------------------------------------------------ #
    "search_title": "Busca",
    "search_placeholder": "PID, coordenada, município ou lugar…",
    "search_read_as": "lido como:",
    "search_button": "Buscar",
    "search_button_busy": "Buscando…",
    "search_areas_heading": "Municípios e distritos regionais",
    "search_places_heading": "Lugares",
    "search_places_note": "Um lugar apenas enquadra o mapa. Clique sobre "
        "uma parcela para analisá-la.",
    "search_places_attribution": "Busca de lugares © colaboradores do "
        "OpenStreetMap (ODbL)",
    "search_candidates_note": "Mais de uma parcela cobre este ponto — "
        "escolha qual analisar:",
    "echo_pid": "PID",
    "echo_coordenada": "coordenada",
    "echo_area": "área",
    "echo_lugar": "lugar",
    "area_browser_title": "Parcelas nesta área",
    "area_browser_total": "parcelas",
    "area_browser_prev": "‹ anterior",
    "area_browser_next": "próxima ›",
    "bc_only_note": "A busca de parcelas cobre apenas a Colúmbia Britânica.",

    # --- parcel card -------------------------------------------------------- #
    "parcel_title": "Parcela",
    "parcel_identifier": "Identificador",
    "parcel_area_registered": "Área registrada",
    "parcel_area_calculated": "Área calculada (geometria)",
    "parcel_area_disagreement_prefix": "A área registrada e a área da "
        "geometria diferem em",
    "parcel_area_disagreement_suffix": "Ambas são exibidas como informadas.",
    "parcel_class": "Classe da parcela",
    "parcel_status": "Situação",
    "parcel_owner_type": "Tipo de titular",
    "parcel_plan_number": "Número do plano",
    "parcel_start_date": "Data de início",
    "parcel_start_date_none": "não registrada",
    "parcel_municipality": "Município",
    "parcel_regional_district": "Distrito regional",
    "parcel_updated": "Última atualização",
    "parcel_not_reported": "não informado",
    "parcel_non_land_prefix": "Esta classe de parcela (",
    "parcel_non_land_suffix": ") não tem cobertura da terra própria — é "
        "uma parcela legal ou de infraestrutura, não um pedaço de terreno.",
    "parcel_neighbours": "Parcelas sobrepostas",
    "parcel_neighbours_note": "Raro numa malha agrimensada — geralmente uma "
        "parcela de espaço aéreo ou condomínio empilhada sobre o mesmo "
        "terreno.",
    "zones_title": "Zonas",
    "zones_note": "Anéis medidos para fora a partir do limite da parcela.",
    "zona_park": "Área protegida",
    "zona_square": "Área de análise",

    # --- cartão de área protegida (sem parcela, mas há um parque) --------- #
    "park_title": "Área protegida",
    "park_no_parcel_note": "Nenhuma parcela aqui — este ponto cai dentro "
        "de uma área protegida, então esse limite é a área de análise.",
    "park_name": "Nome",
    "park_designation": "Designação",
    "park_designation_type": "Nível de designação",
    "park_iucn_category": "Categoria IUCN",
    "park_status": "Situação",
    "park_status_year": "Situação desde",
    "park_managing_authority": "Órgão gestor",
    "park_area_reported": "Área informada (WDPA)",
    "park_area_calculated": "Área calculada (geometria)",
    "park_area_disagreement_prefix": "A área informada e a área da "
        "geometria diferem em",
    "park_area_disagreement_suffix": "Ambas são exibidas como informadas.",
    "park_disclosure": "Do World Database on Protected Areas (WDPA), "
        "UNEP-WCMC/IUCN. Um registro de conservação, não um título de "
        "terra: não traz nomes de proprietários e nada diz sobre acesso "
        "público.",

    # --- cartão de área sintética (sem parcela, sem parque) --------------- #
    "square_title": "Área de análise",
    "square_note": "Nenhuma parcela ou área protegida aqui — este é um "
        "quadrado sintético de 500 ha centrado onde você clicou, para que "
        "as abas de cobertura, floresta, biomassa e fogo ainda tenham algo "
        "para analisar.",
    "square_coordinate": "Ponto central",
    "coord_clicked": "Clicado em",
    "coord_centroid": "Centroide",
    "square_disclosure": "Este limite não é um registro legal ou "
        "administrativo de espécie alguma — é um quadrado de tamanho fixo "
        "desenhado ao redor de uma coordenada, para monitoramento "
        "consistente de terra sem limite registrado ou protegido próprio.",

    # --- layers panel / legend ---------------------------------------------- #
    "layers_title": "Mapa base",
    "layers_loading": "Carregando…",
    "layers_landsat_hint": "Composto anual — escolha o ano abaixo.",
    "layers_parcel_wms": "Malha de parcelas (contexto)",
    "layers_parcel_wms_note": "Todas as parcelas do ParcelMap BC, "
        "desenhadas pelo servidor — visível a partir do zoom 12.",
    "layers_ecozones": "Marco ecológico",
    "layers_ecozone_level_ecozone": "Ecozona",
    "layers_ecozone_level_ecoregion": "Ecorregião",
    "layers_ecozone_level_ecodistrict": "Ecodistrito",
    "layers_ecozones_note": "Apenas orientação — limites aproximados que "
        "não decidem nada. Ecozonas são amplas (quinze cobrem todo o "
        "Canadá); ecorregião e ecodistrito são níveis mais finos do mesmo "
        "marco — ecodistrito não tem nome próprio, apenas a ecorregião e "
        "ecozona em que se encontra.",
    "legend_aci": "Inventário de Culturas (AAFC)",
    "legend_aci_palette": "Cores da legenda oficial do AAFC.",
    "legend_landsat": "Composto Landsat",
    "legend_landsat_error": "Não foi possível carregar o composto Landsat "
        "deste ano.",
    "legend_verifying": "Verificando…",
    "legend_floresta_hansen": "Mudança florestal (Hansen)",
    "legend_hansen_split_start_date": "Dividido na data de início da "
        "parcela",
    "legend_hansen_split_undivided": "Série não dividida",
    "legend_perda": "Perda",
    "legend_ganho": "Ganho (sem data)",
    "map_layer_note": "A camada desta aba pode ser ligada ou desligada "
        "pela legenda no canto do mapa.",

    # --- Cobertura ------------------------------------------------------------ #
    "tab_cobertura": "Cobertura",
    "cobertura_ano": "Ano",
    "cobertura_classe": "Classe",
    "cobertura_hectares": "Hectares",
    "cobertura_percentual": "Percentual",
    "cobertura_running": "Buscando a trajetória do inventário de culturas…",
    "cobertura_empty": "Ainda sem dados — selecione uma parcela.",
    "cobertura_degraded": "Este resultado foi repetido em escala mais "
        "grosseira após uma falha do Earth Engine. É utilizável, mas veja o "
        "registro de proveniência para o que mudou.",
    "cobertura_out_of_range": "O Inventário Anual de Culturas não tem "
        "cobertura tão ao norte — isso é esperado acima de "
        "aproximadamente 54–58°N, não uma falha. As abas Floresta, "
        "Biomassa e Fogo continuam respondendo.",
    "cobertura_attribution": "Agriculture and Agri-Food Canada — Annual "
        "Crop Inventory · 30 m",

    # --- Transições ----------------------------------------------------------- #
    "tab_transicoes": "Transições",
    "transicoes_intro": "Como a cobertura da terra mudou entre dois anos, "
        "para a zona ativa.",
    "transicoes_de": "De",
    "transicoes_para": "Para",
    "transicoes_maiores": "Maiores transições",
    "transicoes_min_gap_note_prefix": "Anos com diferença menor que",
    "transicoes_min_gap_note_suffix": "são recusados — entre anos "
        "consecutivos, a maior parte das 'transições' do inventário é "
        "rotação de lavoura, não mudança de uso da terra.",

    # --- Floresta -------------------------------------------------------------- #
    "tab_floresta": "Floresta",
    "floresta_split_start_date": "Dividido na data de início",
    "floresta_split_undivided": "Não dividido",
    "floresta_before_parcel": "Antes da parcela existir",
    "floresta_after_parcel": "Depois da criação da parcela",
    "floresta_undivided_total": "Perda total (não dividida)",
    "floresta_ganho_sem_data": "Ganho (sem data)",
    "floresta_no_start_date_note": "O registro desta parcela não traz data "
        "de início, então a perda é mostrada como uma única série não "
        "dividida, em vez de dividida numa âncora inventada.",
    "floresta_col_ano": "Ano",
    "floresta_col_perda": "Perda (ha)",
    "floresta_col_periodo": "Período",
    "floresta_attribution": "Hansen/UMD/Google/USGS/NASA — Global Forest "
        "Change · 30 m",
    "floresta_age_title": "Idade do povoamento (NTEMS, 2019)",
    "floresta_age_run_button": "Obter idade do povoamento",
    "floresta_age_mean": "Idade média",
    "floresta_age_median": "Idade mediana",
    "floresta_age_forested_pct": "Fração florestal da zona",
    "floresta_age_note": "As idades são as publicadas, referentes a 2019 — "
        "não são avançadas até hoje. Mascaradas aos pixels florestais: uma "
        "fração florestal baixa significa que os números de idade "
        "descrevem só uma pequena parte desta zona.",
    "floresta_age_attribution": "NRCan / NFIS — idade da floresta NTEMS "
        "Canadá (2019) · 30 m",

    # --- Biomassa --------------------------------------------------------------- #
    "tab_biomassa": "Biomassa",
    "biomassa_col_ano": "Ano",
    "biomassa_col_mg_ha": "Mg/ha",
    "biomassa_col_total_mg": "Total (Mg)",
    "biomassa_attribution": "ESA CCI Biomass v6.0 — Santoro & Cartus "
        "(2025) · 100 m",
    "biomassa_canada_note": "A recuperação é mais fraca sobre terreno com "
        "cobertura de neve persistente e vegetação esparsa do norte do que "
        "sobre floresta temperada fechada.",

    # --- Paisagem ----------------------------------------------------------------- #
    "tab_paisagem": "Paisagem",
    "paisagem_ano": "Ano",
    "paisagem_empty": "Ainda sem dados.",
    "paisagem_legend_note": "A contagem de fragmentos segue as próprias "
        "distinções de classe do ACI, que resolvem lavouras finamente e "
        "floresta grosseiramente — comparável entre esta parcela e seus "
        "anéis, não entre uma paisagem agrícola e uma florestada.",
    "paisagem_col_zona": "Zona",
    "paisagem_col_area": "Área (ha)",
    "paisagem_col_fragmentos": "Fragmentos",
    "paisagem_col_densidade": "Densidade",
    "paisagem_col_maior": "Maior (%)",
    "paisagem_col_borda": "Densidade de borda",
    "paisagem_col_meff": "Meff (ha)",
    "paisagem_col_shannon": "Shannon",
    "paisagem_col_simpson": "Simpson",
    "paisagem_col_evenness": "Equitabilidade",
    "paisagem_attribution": "AAFC Annual Crop Inventory · 30 m",
    "connectivity_hint": "Distância média entre fragmentos florestais — "
        "uma segunda chamada ao Earth Engine mais uma busca local, por isso "
        "roda sob demanda.",
    "connectivity_run_button": "Obter distância entre fragmentos",
    "connectivity_degraded": "Mais fragmentos que o limite em uma ou mais "
        "zonas — a distância considerou apenas os primeiros retornados.",
    "connectivity_empty": "Ainda sem resultado.",
    "connectivity_n_fragments": "Fragmentos",
    "connectivity_enn_mean": "Distância média (m)",
    "connectivity_enn_median": "Distância mediana (m)",

    # --- Fogo --------------------------------------------------------------------- #
    "tab_fogo": "Fogo",
    "fogo_historio_anos": "Anos com alguma queimada",
    "fogo_frequencia_ocorrencias": "Frequência média de queimadas",
    "fogo_ultima_queimada": "Último ano de queimada",
    "fogo_below_resolution_prefix": "Esta zona é menor que cerca de ",
    "fogo_below_resolution_suffix": " ha — os pixels do MODIS têm ~21 ha, "
        "então estes números são dominados por efeitos de borda de pixel, "
        "não pela zona.",
    "fogo_attribution": "MODIS MCD64A1 v6.1 Burned Area — NASA LP DAAC · "
        "463 m",
    "fogo_source_modis": "MODIS · 500 m",
    "fogo_source_aci": "AAFC · 30 m",
    "fogo_modis_layer_note": "O mapa mostra todos os anos do registro "
        "combinados (2001–2025) — vermelho mais escuro queimou mais vezes.",
    "fogo_aci_layer_note": "O mapa mostra todos os anos do registro "
        "combinados (2009–2025) — vermelho mais escuro queimou mais vezes.",
    "fogo_aci_years_detected": "Anos com queimada detectada",
    "fogo_aci_last_year": "Ano de queimada mais recente",
    "fogo_aci_empty": "Ainda sem dados de Cobertura para esta zona — visite "
        "a aba Cobertura, ou aguarde o carregamento terminar. A classe de "
        "área queimada vem dessa mesma busca, sem custo adicional.",
    "fogo_aci_note": "A própria classe de área queimada do inventário de "
        "culturas (2009–2025, nacional a partir de 2011), 30 m — sete vezes "
        "mais fina que o MODIS, mas uma classe de cobertura da terra, não "
        "um produto dedicado de queimadas: pode perder um incêndio que o "
        "MODIS capta, se a cicatriz já tiver revegetado até a passagem do "
        "satélite naquele ano, do mesmo jeito que pode resolver o formato "
        "de uma queimada que o MODIS só vê como uma mancha borrada. Os "
        "dois nunca são somados num único número.",
    "fogo_aci_attribution": "Agriculture and Agri-Food Canada — Annual Crop "
        "Inventory, classe 60 \"Forest Fire and Burnt Area\" · 30 m",

    # --- Validação -------------------------------------------------------------------- #
    "tab_validacao": "Validação",
    "validacao_intro": "O Inventário Anual de Culturas conferido contra o "
        "NTEMS VLCE2, um produto nacional independente de cobertura da "
        "terra, para o mesmo ano. Comparado apenas em nível de grupo — veja "
        "a nota abaixo.",
    "validacao_ano": "Ano",
    "validacao_agreement_label": "Concordância em nível de grupo",
    "validacao_area_label": "Área comparada",
    "validacao_no_verdict": "Discordância entre dois produtos "
        "independentes não é erro de nenhum dos dois — isto informa onde "
        "eles diferem e não diz nada sobre qual está certo.",
    "validacao_group_note": "Comparado em nível de grupo, não de classe: o "
        "ACI resolve lavouras e não tem detalhe de tipo florestal, o VLCE2 "
        "o inverso. Uma taxa de concordância em nível de classe não teria "
        "sentido.",
    "validacao_col_aci": "Grupo ACI",
    "validacao_col_vlce2": "Grupo VLCE2",
    "validacao_col_area": "Área (ha)",
    "validacao_col_agreement": "Concordam?",
    "validacao_attribution": "AAFC Annual Crop Inventory · NTEMS VLCE2 "
        "(Hermosilla et al., Serviço Florestal Canadense)",

    # --- errors --------------------------------------------------------------------------- #
    "erro_fora_canada": "Esse ponto está fora do Canadá. Esta página cobre "
        "o Canadá; use a página do Brasil para coordenadas sul-americanas.",
    "erro_coordenada_invertida": "Parece uma coordenada invertida — "
        "trocando latitude e longitude o ponto cairia dentro do Canadá, mas "
        "nesta ordem não cai. A latitude vem primeiro.",
    "erro_zonas": "Não foi possível construir as zonas: {detail}",
    "erro_camada_aba": "A camada do mapa desta aba não pôde ser carregada.",
    "erro_trajetoria_aci": "A trajetória do inventário de culturas falhou: "
        "{detail}",
    "erro_aci_sem_classes": "Sem dados do inventário de culturas nesta "
        "zona — isso é esperado ao norte da cobertura do inventário.",
    "erro_lugar_nao_encontrado": "Nenhum lugar encontrado para “{query}”.",
    "erro_transicao": "As transições falharam: {detail}",
    "erro_perda_florestal": "A mudança florestal falhou: {detail}",
    "erro_idade_floresta": "A idade do povoamento falhou: {detail}",
    "erro_biomassa": "A biomassa falhou: {detail}",
    "erro_fogo": "A análise de área queimada falhou: {detail}",
    "erro_paisagem": "As métricas de paisagem falharam: {detail}",
    "erro_connectivity": "A conectividade entre fragmentos falhou: "
        "{detail}",
    "erro_validacao": "A comparação de validação falhou: {detail}",

    # --- misc ------------------------------------------------------------------------------- #
    "zona_parcela": "Parcela",

    # --- how-to-use dialog -------------------------------------------------------------------- #
    "help_trigger": "Como usar",
    "help_dialog_title": "Como usar esta página",
    "help_dialog_desc": "Sete passos de uma parcela até uma análise, e o "
        "que esta página não pode dizer.",
    "help_step1_title": "1. Encontre uma parcela",
    "help_step1_body": "Digite um Identificador de Parcela (PID, ex. "
        "010-322-060), clique no mapa, ou busque um município — a caixa de "
        "busca mostra como leu o que você digitou antes de agir.",
    "help_step2_title": "2. Leia o cartão da parcela",
    "help_step2_body": "Todo campo da malha é mostrado literalmente — "
        "situação, classe, tipo de titular, número do plano. O ParcelMap BC "
        "é um registro de limites, não de propriedade: não traz nomes de "
        "proprietários.",
    "help_step3_title": "3. Confira as zonas",
    "help_step3_body": "A parcela mais anéis concêntricos até 5 km, "
        "medidos para fora a partir do limite — toda análise abaixo roda "
        "sobre todas elas de uma vez.",
    "help_step4_title": "4. Cobertura, Transições, Floresta, Biomassa",
    "help_step4_body": "A trajetória do Inventário Anual de Culturas, suas "
        "transições ano a ano, perda/ganho florestal do Hansen mais a idade "
        "do povoamento do NTEMS, e biomassa da ESA CCI — cada aba calcula "
        "sob demanda.",
    "help_step5_title": "5. Paisagem e Fogo",
    "help_step5_body": "Métricas de fragmentação para todas as zonas de "
        "uma vez, mais uma métrica opcional de distância entre fragmentos; "
        "histórico de área queimada do MODIS — grosseiro a 463 m, sinalizado "
        "quando uma zona é pequena demais para ele resolver.",
    "help_step6_title": "6. Validação",
    "help_step6_body": "O inventário de culturas conferido contra um "
        "produto independente de cobertura da terra para o mesmo ano, em "
        "nível de grupo. Discordância não é um veredito para nenhum lado.",
    "help_step7_title": "7. Exportar",
    "help_step7_body": "Todo gráfico baixa como PNG, toda tabela como CSV, "
        "pelo ícone ao lado — para reprocessamento próprio, não uma "
        "captura de tela.",
    "help_limitations_title": "O que esta página não pode dizer",
    "help_limit_1": "O ParcelMap BC mostra limites legais, nunca "
        "propriedade — nenhum nome de proprietário aparece em lugar algum "
        "deste aplicativo.",
    "help_limit_2": "A busca de parcelas cobre apenas a Colúmbia Britânica; "
        "as camadas de cobertura da terra, floresta, biomassa e fogo cobrem "
        "todo o Canadá.",
    "help_limit_3": "O Inventário Anual de Culturas não tem dados ao norte "
        "de aproximadamente 54–58°N — uma aba Cobertura vazia ali é o "
        "conjunto de dados, não uma falha.",
    "help_limit_4": "Esta página não emite nenhum veredito sobre "
        "conformidade, uso da terra, ou qual de dois conjuntos de dados "
        "discordantes está correto.",

    # --- citation dialog ---------------------------------------------------------------------- #
    "cite_trigger": "Como citar",
    "cite_dialog_title": "Como citar",
    "cite_dialog_desc": "Camposcope Canadá e as fontes de dados que ele "
        "utiliza.",
    "cite_sources_title": "Fontes de dados",
    "cite_sources_desc": "Todas as fontes que esta página utiliza, mesmo "
        "que a parcela atual não use todas elas.",
    "cite_example_title": "Citação sugerida",

    # --- export dialog ------------------------------------------------------------------------ #
    "download_button": "Exportar",
    "export_dialog_title": "Exportar",
    "export_dialog_desc": "PNGs por gráfico e CSVs por tabela estão "
        "disponíveis pelo ícone ao lado de cada um. Uma planilha combinada e "
        "um relatório ainda não estão disponíveis nesta página.",
}
