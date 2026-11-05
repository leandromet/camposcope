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
    "start_hint": "Clique em algum lugar do Canadá para começar",
    "nav_toggle_layers_aria": "Mostrar camadas",
    "drawer_title": "Camadas",
    "drawer_close_aria": "Fechar",
    "sidebar_show_aria": "Mostrar painel lateral",
    "sidebar_hide_aria": "Ocultar painel lateral",
    "sheet_handle_aria": "Redimensionar painel — arraste ou use as setas",
    "results_resize_aria": "Redimensionar o painel de resultados",
    "results_resize_label": "Redimensionar",
    "results_resize_hint": "Alterna a altura do painel entre compacto, médio e expandido.",
    "mobile_options_toggle": "Opções de busca",
    "mobile_layers_group_toggle": "Camadas",
    "mobile_panel_toggle": "Dados e opções",
    "mobile_parcel_zones_toggle": "Parcela e zonas",
    "close_button": "Fechar",
    "calcular": "Calcular",
    "calculando": "Calculando…",

    # --- search panel ------------------------------------------------------ #
    "search_title": "Busca",
    "search_placeholder": "endereço, código postal, PID, coordenada, município…",
    "search_read_as": "lido como:",
    "search_button": "Buscar",
    "search_button_busy": "Buscando…",
    "search_areas_heading": "Municípios e distritos regionais",
    "search_places_heading": "Lugares e endereços",
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
    "echo_postal": "código postal",
    "search_as_place": "Buscar como endereço ou lugar",
    "search_place_hint": "clique em uma parcela no mapa para analisá-la",
    "precision_endereco": "endereço",
    "precision_rua": "rua",
    "precision_cep": "código postal",
    "precision_bairro": "bairro",
    "precision_cidade": "cidade",
    "precision_regiao": "região",
    "precision_lugar": "lugar",
    "erro_postal_nao_encontrado": (
        "Código postal {code} não encontrado. Tente o endereço."
    ),

    # --- quick start (components/quickstart.py) ------------------------- #
    "qs_title": "Comece em 30 segundos",
    "qs_step1_lead": "Busque",
    "qs_step1_body": (
        "um endereço, código postal, PID, coordenada ou município da "
        "Colúmbia Britânica — ou simplesmente navegue pelo mapa."
    ),
    "qs_step2_lead": "Clique em uma parcela",
    "qs_step2_body": (
        "na Colúmbia Britânica, ou em qualquer lugar do Canadá, para "
        "selecioná-la. Se houver parcelas sobrepostas, você escolhe qual."
    ),
    "qs_step3_lead": "Leia os resultados",
    "qs_step3_body": (
        "no painel do mapa: histórico do inventário de culturas, perda e idade "
        "da floresta, biomassa e fogo."
    ),
    "qs_step4_lead": "Exporte",
    "qs_step4_body": "gráficos, tabelas e dados pelo botão Exportar.",
    "qs_more": (
        "Há muito mais: anéis de entorno, métricas de paisagem, validação da "
        "cobertura e registros de espécies."
    ),
    "qs_got_it": "Entendi",
    "qs_full_howto": "Ver o guia completo",
    "qs_close_aria": "Fechar o início rápido",
    "help_show_quickstart": "Mostrar o início rápido de novo",
    "area_browser_title": "Parcelas nesta área",
    "area_browser_total": "parcelas",
    "area_browser_prev": "‹ anterior",
    "area_browser_next": "próxima ›",
    "bc_only_note": "A busca de parcelas cobre apenas a Colúmbia Britânica.",

    # --- parcel card -------------------------------------------------------- #
    "parcel_title": "Parcela",
    "parcel_identifier": "Identificador",
    "parcel_details_toggle": "Detalhes do registro",
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
    "parcel_neighbours_note": "Raro em uma malha cadastral — geralmente uma "
        "parcela de espaço aéreo ou de condomínio sobreposta ao mesmo "
        "terreno.",
    "zones_title": "Zonas",
    "zones_note": "Anéis medidos para fora a partir do limite da parcela.",
    "zona_park": "Área protegida",
    "zona_square": "Área de análise",

    # --- cartão de área protegida (sem parcela, mas há um parque) --------- #
    "park_title": "Área protegida",
    "park_no_parcel_note": "Nenhuma parcela aqui — este ponto cai dentro "
        "de uma área protegida, então este limite é a área de análise.",
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
    "park_disclosure": "Fonte: World Database on Protected Areas (WDPA), "
        "UNEP-WCMC/IUCN. É um registro de conservação, não um título de "
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
        "administrativo de nenhum tipo — é um quadrado de tamanho fixo "
        "desenhado ao redor de uma coordenada, para monitoramento "
        "consistente de terra sem limite registrado ou protegido próprio.",

    # --- layers panel / legend ---------------------------------------------- #
    "layers_title": "Mapa base",
    "layers_loading": "Carregando…",
    "layers_landsat_hint": "Composto anual — escolha o ano abaixo.",
    "layers_parcel_wms": "Malha de parcelas (contexto)",
    "layers_parcel_wms_note": "Todas as parcelas do ParcelMap BC, "
        "desenhadas pelo servidor — visível a partir do zoom 12.",
    "layers_ecozones": "Divisão ecológica",
    "layers_ecozone_level_ecozone": "Ecozona",
    "layers_ecozone_level_ecoregion": "Ecorregião",
    "layers_ecozone_level_ecodistrict": "Ecodistrito",
    "layers_ecozones_note": "Apenas orientação — limites aproximados que "
        "não decidem nada. As ecozonas são amplas (quinze cobrem todo o "
        "Canadá); ecorregião e ecodistrito são níveis mais finos da mesma "
        "divisão — o ecodistrito não tem nome próprio, só a ecorregião e a "
        "ecozona a que pertence.",
    "legend_title": "Legenda",
    "legend_collapse_aria": "Recolher a legenda",
    "legend_expand_aria": "Expandir a legenda",
    "legend_aci": "Inventário de Culturas (AAFC)",
    "legend_aci_palette": "Cores da legenda oficial do AAFC.",
    "legend_run_calcular": "Clique em Calcular na aba Validação para ver as classes.",
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
    "legend_choose_years": "Escolha os anos na aba Transições.",
    "legend_drag_to_compare": "Arraste a barra no mapa para comparar.",
    "legend_gbif_zoom_note": "Aproxime o mapa para ver os pontos.",
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
    "cobertura_degraded": "Este resultado foi refeito em escala mais "
        "grosseira após uma falha do Earth Engine. Ele é utilizável, mas "
        "consulte o registro de proveniência para saber o que mudou.",
    "cobertura_out_of_range": "O Inventário Anual de Culturas não tem "
        "cobertura tão ao norte — isso é esperado acima de "
        "cerca de 54–58°N, não uma falha. As abas Floresta, "
        "Biomassa e Fogo continuam funcionando.",
    "cobertura_attribution": "Agriculture and Agri-Food Canada — Annual "
        "Crop Inventory · 30 m",

    # --- Transições ----------------------------------------------------------- #
    "tab_transicoes": "Transições",
    "transicoes_intro": "Como a cobertura da terra mudou entre dois anos, "
        "para a zona ativa.",
    "transicoes_de": "De",
    "transicoes_para": "Para",
    "transicoes_maiores": "Maiores transições",
    "transicoes_min_gap_note_prefix": "Pares de anos com menos de",
    "transicoes_min_gap_note_suffix": "anos de diferença são recusados — entre anos "
        "consecutivos, a maior parte das 'transições' do inventário é "
        "rotação de lavoura, não mudança de uso da terra.",

    # --- Floresta -------------------------------------------------------------- #
    "tab_floresta": "Floresta",
    "floresta_split_start_date": "Dividido na data de início",
    "floresta_split_undivided": "Não dividido",
    "floresta_before_parcel": "Antes de a parcela existir",
    "floresta_after_parcel": "Depois da criação da parcela",
    "floresta_undivided_total": "Perda total (não dividida)",
    "floresta_ganho_sem_data": "Ganho (sem data)",
    "floresta_no_start_date_note": "O registro desta parcela não traz data "
        "de início, então a perda é mostrada como uma única série não "
        "dividida, em vez de dividida em uma data de referência inventada.",
    "floresta_col_ano": "Ano",
    "floresta_col_perda": "Perda (ha)",
    "floresta_col_periodo": "Período",
    "floresta_attribution": "Hansen/UMD/Google/USGS/NASA — Global Forest "
        "Change · 30 m",
    "floresta_age_title": "Idade do povoamento (NTEMS, 2019)",
    "floresta_age_run_button": "Obter idade do povoamento",
    "floresta_age_mean": "Idade média",
    "floresta_age_median": "Idade mediana",
    "floresta_age_unit": "anos",
    "floresta_age_forested_pct": "Fração florestal da zona",
    "floresta_age_note": "As idades são as publicadas, referentes a 2019 — "
        "não foram atualizadas até hoje. Calculadas apenas sobre os pixels "
        "florestais: uma fração florestal baixa significa que as idades "
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
    "biomassa_canada_note": "A estimativa é menos precisa em terreno com "
        "cobertura de neve persistente e vegetação esparsa do norte do que "
        "em floresta temperada fechada.",

    # --- Paisagem ----------------------------------------------------------------- #
    "tab_paisagem": "Paisagem",
    "paisagem_ano": "Ano",
    "paisagem_empty": "Ainda sem dados.",
    "paisagem_legend_note": "A contagem de fragmentos segue as próprias "
        "distinções de classe do ACI, que distinguem lavouras com detalhe e "
        "floresta de forma grosseira — comparável entre esta parcela e seus "
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
        "exige uma segunda consulta ao Earth Engine e uma busca local, por "
        "isso roda sob demanda.",
    "connectivity_run_button": "Obter distância entre fragmentos",
    "connectivity_degraded": "Uma ou mais zonas têm mais fragmentos do que o "
        "limite — a distância considerou apenas os primeiros retornados.",
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
    "fogo_current_year_prefix": "O ano de ",
    "fogo_current_year_suffix": " ainda está em andamento — o MODIS continua "
        "publicando novos meses ao longo do ano, então esta barra (com "
        "hachuras no gráfico) é um total parcial, não uma temporada "
        "encerrada.",
    "fogo_source_modis": "MODIS · 500 m",
    "fogo_source_aci": "AAFC · 30 m",
    "fogo_modis_layer_note_prefix": "O mapa mostra todos os anos do registro "
        "combinados (2001–",
    "fogo_modis_layer_note_suffix": ") — vermelho mais escuro queimou mais "
        "vezes. O último ano ainda está em andamento.",
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
        "independentes não é erro de nenhum dos dois — isto mostra onde "
        "eles diferem, sem dizer qual está certo.",
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

    # --- GBIF ----------------------------------------------------------------------------- #
    "tab_gbif": "GBIF",
    "gbif_zoom_note": "No mapa: aproxime (zoom 10 ou mais) para ver os "
        "pontos de ocorrência — em zoom de país, uma única vista pode "
        "conter dezenas de milhares de registros. \"Calcular\" busca algo "
        "diferente: a contagem exata de espécies em cada zona, sem esse "
        "limite de zoom.",
    "gbif_attribution": "GBIF.org — Global Biodiversity Information Facility",
    "gbif_col_species": "Espécie",
    "gbif_col_records": "Registros",
    "gbif_records_word": "registros",
    "gbif_species_word": "espécies",
    "gbif_zone_empty": "Nenhuma espécie registrada nesta zona.",
    "gbif_empty": "Ainda sem resultado. Clique em Calcular para buscar as "
        "espécies já registradas no GBIF em cada zona ao redor da "
        "parcela.",
    "gbif_cumulative_note": "É uma consulta agregada — conta os registros "
        "sem baixá-los. Os totais de cada zona abaixo são cumulativos: a "
        "zona \"2 km – 5 km\" já inclui tudo que está na parcela e nos "
        "anéis mais internos, não apenas o que está exclusivamente entre "
        "2 e 5 km.",
    "gbif_export_ods_hint": "Planilha ODS: uma aba de metadados (parcela, "
        "ressalvas e licenças) e uma aba por zona, com as espécies e seus "
        "registros.",
    "gbif_export_csv_hint": "CSV único com todas as zonas (zona, espécie, "
        "registros, % da zona). Sem os metadados — as ressalvas da "
        "planilha valem igual.",
    "gbif_export_nothing": "Calcule as espécies antes de exportar.",

    # --- errors --------------------------------------------------------------------------- #
    "erro_fora_canada": "Esse ponto está fora do Canadá. Esta página cobre "
        "o Canadá; use a página do Brasil para coordenadas sul-americanas.",
    "erro_coordenada_invertida": "Parece uma coordenada invertida — "
        "se você trocar latitude e longitude, o ponto cai dentro do Canadá; "
        "na ordem atual, não. A latitude vem primeiro.",
    "erro_zonas": "Não foi possível construir as zonas: {detail}",
    "erro_camada_aba": "A camada do mapa desta aba não pôde ser carregada.",
    "erro_trajetoria_aci": "Não foi possível obter a trajetória do inventário de culturas: "
        "{detail}",
    "erro_aci_sem_classes": "Sem dados do inventário de culturas nesta "
        "zona — isso é esperado ao norte da cobertura do inventário.",
    "erro_lugar_nao_encontrado": "Nenhum lugar encontrado para “{query}”.",
    "erro_transicao": "Não foi possível calcular as transições: {detail}",
    "erro_perda_florestal": "Não foi possível calcular a mudança florestal: {detail}",
    "erro_idade_floresta": "Não foi possível obter a idade do povoamento: {detail}",
    "erro_biomassa": "Não foi possível calcular a biomassa: {detail}",
    "erro_fogo": "Não foi possível calcular a área queimada: {detail}",
    "erro_paisagem": "Não foi possível calcular as métricas de paisagem: {detail}",
    "erro_connectivity": "Não foi possível calcular a conectividade entre "
        "fragmentos: {detail}",
    "erro_validacao": "Não foi possível calcular a comparação de validação: {detail}",

    # --- misc ------------------------------------------------------------------------------- #
    "zona_parcela": "Parcela",

    # --- how-to-use dialog -------------------------------------------------------------------- #
    "help_trigger": "Como usar",
    "help_dialog_title": "Como usar esta página",
    "help_demo_link": "Prefere ver funcionando? Abra a demonstração passo a passo com uma parcela real em Kelowna (em inglês) →",
    "help_dialog_desc": "Sete passos de uma parcela até uma análise, e o "
        "que esta página não pode dizer.",
    "help_step1_title": "1. Encontre uma parcela",
    "help_step1_body": "Digite um Identificador de Parcela (PID, ex. "
        "010-322-060), clique no mapa, ou busque um município — a caixa de "
        "busca mostra como leu o que você digitou antes de agir.",
    "help_step2_title": "2. Leia o cartão da parcela",
    "help_step2_body": "Cada campo da malha é exibido como no original — "
        "situação, classe, tipo de titular, número do plano. O ParcelMap BC "
        "é um registro de limites, não de propriedade: não traz nomes de "
        "proprietários.",
    "help_step3_title": "3. Confira as zonas",
    "help_step3_body": "A parcela mais anéis concêntricos até 5 km, "
        "medidos para fora a partir do limite — todas as análises abaixo "
        "são feitas sobre todas elas de uma vez.",
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
        "de aproximadamente 54–58°N — uma aba Cobertura vazia nessa região reflete o "
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
