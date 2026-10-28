/* Camposcope — demonstração em rolagem (/demonstracao, e /walkthrough em inglês).
 *
 * Os números vêm de /_demonstracao/camposcope.json (services/demonstracao.py),
 * montado pelos mesmos serviços da interface. Este arquivo só decide o que
 * cada passo mostra; nenhum valor é escrito à mão. Os textos vêm nas duas
 * línguas, t("pt", "en"), e a página escolhe pela própria língua.
 */
(function () {
  var R = window.Reportagem, fmt = R.fmt, graf = R.graf;
  var t, en;   // definidos em aoCarregar (dependem da língua da página)

  // cores de components/charts.py (HANSEN_PERIOD_COLOR) e dos anéis no mapa
  var PERIODO = {
    ate_2008: { cor: "#f5a524", pt: "Até 2008", en: "Up to 2008" },
    "2008_ate_registro": { cor: "#e5484d", pt: "De 2008 à inscrição", en: "2008 to registration" },
    apos_registro: { cor: "#8b1a1a", pt: "Depois da inscrição", en: "After registration" }
  };
  var ZONA = { imovel: ["Imóvel", "Property"], ring_500m: ["0–500 m", "0–500 m"], ring_2km: ["500 m–2 km", "500 m–2 km"], ring_5km: ["2–5 km", "2–5 km"] };
  var COR_ZONA = { imovel: "#d98324", ring_500m: "#1f6f4a", ring_2km: "#4f8f6f", ring_5km: "#9cc2ac" };
  var CONTORNO = { color: "#ffd400", weight: 3, fillOpacity: 0 };
  // os grupos de services/ibge_vegetation.bucket_matrix, nas duas línguas
  var GRUPO_IBGE = {
    natural_forest: ["Natural — floresta", "Natural — forest"], natural_non_forest: ["Natural — não florestal", "Natural — non-forest"],
    anthropic_forest: ["Antrópico — floresta plantada", "Human — planted forest"], anthropic_regrowth: ["Antrópico — vegetação secundária", "Human — secondary growth"],
    anthropic_non_forest: ["Antrópico — agropecuária/urbano", "Human — farming/urban"], water: ["Água", "Water"], other: ["Outros/sem dados", "Other/no data"]
  };

  function cod(ctx) { return ctx.params.get("car") || ""; }
  function nomeZona(k) { return (ZONA[k] || [k, k])[en ? 1 : 0]; }
  function nomeClasse(c) { return en ? (c.nome_en || c.nome) : c.nome; }
  function imovelGeo(d) { return { type: "Feature", properties: {}, geometry: d.imovel.geometry }; }

  // classes presentes numa zona num ano, maiores primeiro
  function classesNoAno(d, zona, i) {
    var h = d.historico, z = h.zonas[zona] || {};
    return Object.keys(z).map(function (c) { return { id: c, ha: z[c][i] || 0, nome: nomeClasse(h.classes[c]), cor: h.classes[c].cor }; })
      .filter(function (x) { return x.ha > 0; }).sort(function (a, b) { return b.ha - a.ha; });
  }
  function legendaClasses(d, ano, zona) {
    var i = d.historico.anos.indexOf(ano); if (i < 0) return "";
    var onde = zona === "ring_5km" ? t("até 5 km", "within 5 km") : t("no imóvel", "on the property");
    return "<b>MapBiomas " + ano + " · " + t("classes ", "classes ") + onde + "</b>" + classesNoAno(d, zona || "imovel", i).slice(0, 6).map(function (c) {
      return '<span><i style="background:' + c.cor + '"></i>' + fmt.esc(c.nome) + "</span>";
    }).join("");
  }
  function nativaPct(d, zona) {
    var h = d.historico, z = h.zonas[zona] || {}, nat = h.nativas.map(String);
    return h.anos.map(function (_, i) {
      var tot = 0, n = 0;
      Object.keys(z).forEach(function (c) { tot += z[c][i] || 0; if (nat.indexOf(c) >= 0) n += z[c][i] || 0; });
      return tot > 0 ? (100 * n) / tot : null;
    });
  }
  // como zones.overlap_areas no aplicativo: quem só encosta na divisa não conta
  function sobrepostos(d) { return (d.sobrepostos || []).filter(function (o) { return o.overlap_ha > 0; }); }
  function camada(d, k, op) { var c = d.camadas[k]; return c ? Object.assign({}, c, op ? { opacity: op } : {}) : null; }
  function faltou(el, nome) {
    el.innerHTML = '<p class="rp-fig-estado erro">' + nome + t(" não respondeu desta vez ", " did not respond this time ") +
      '<span class="selo ausente">' + t("ausente", "missing") + "</span></p>";
  }

  R.iniciar({
    dados: function (ctx) { var c = cod(ctx); return "/_demonstracao/camposcope.json" + (c ? "?car=" + encodeURIComponent(c) : ""); },
    centro: [-12.5, -55.5], zoom: 5,

    aoCarregar: function (ctx, d) {
      t = ctx.t; en = ctx.lang === "en";
      var im = d.imovel, h = d.historico;
      var ultimo = h ? h.anos[h.anos.length - 1] : null;
      var lista = h ? classesNoAno(d, "imovel", h.anos.length - 1) : [];
      var top = lista[0], tot = lista.reduce(function (a, c) { return a + c.ha; }, 0);
      var perda = d.hansen ? (d.hansen.perda.imovel || []).reduce(function (a, x) { return a + x.ha; }, 0) : null;
      ctx.preencher({
        "n-declarada": fmt.ha(im.area_declarada_ha),
        "n-calculada": fmt.ha(im.area_calculada_ha),
        "n-uso": top ? fmt.pct((100 * top.ha) / tot) : "—",
        "n-uso-rot": top ? t("de ", "") + fmt.esc(top.nome.toLowerCase()) + t(" em ", " in ") + ultimo + ' <span class="selo real">' + t("real", "measured") + "</span>" : t("principal uso no último ano", "main use in the latest year"),
        "n-perda": perda === null ? "—" : fmt.ha(perda)
      });
      ctx.$("#topo-exemplo").textContent = im.cod_imovel + " · " + im.municipio + "/" + im.uf;
      var app = "/?car=" + encodeURIComponent(im.cod_imovel) + (en ? "&lang=en" : "");
      ctx.$("#link-app").href = app; ctx.$("#cta-app").href = app;
      ctx.$("#rp-fig-url").textContent = "camposcope.umaterra.com.br" + app;
      ctx.$("#abertura-exemplo").innerHTML = (d.exemplo_padrao ? t("Exemplo desta página: ", "This page's example: ") : t("Imóvel escolhido: ", "Chosen property: ")) +
        "<b>" + fmt.esc(im.municipio) + "/" + fmt.esc(im.uf) + "</b>, " + t("código", "code") + " <code>" + fmt.esc(im.cod_imovel) + "</code>, " +
        t("calculado pelos serviços do aplicativo em ", "computed by the app's services on ") + fmt.dataHora(d.gerado_em) +
        (d.exemplo_padrao ? t(" e guardado com esta página.", " and stored with this page.") : t(" (o resultado fica guardado por algumas horas).", " (the result is kept for a few hours)."));
      var erros = Object.keys(d.erros || {});
      ctx.$("#fim-extra").innerHTML = erros.length
        ? t("Desta vez não responderam: ", "These did not respond this time: ") + "<b>" + erros.map(fmt.esc).join(", ") + "</b>. " + t("Os passos correspondentes dizem o que faltou.", "The matching steps say what is missing.")
        : t("Todas as análises responderam no cálculo de ", "Every analysis responded in the run of ") + fmt.dataHora(d.gerado_em) + ".";

      ctx.texto("busca", t("Aqui, o código <code>" + fmt.esc(im.cod_imovel) + "</code> leva à camada <b>sicar_imoveis_" + im.uf.toLowerCase() +
          "</b>, que devolve um polígono em " + fmt.esc(im.municipio) + ". Em amarelo, a divisa; ao fundo, em transparência, os outros imóveis do estado.",
        "Here the code <code>" + fmt.esc(im.cod_imovel) + "</code> leads to the <b>sicar_imoveis_" + im.uf.toLowerCase() +
          "</b> layer, which returns one polygon in " + fmt.esc(im.municipio) + ". The boundary is in yellow; the state's other properties show faintly behind it."));
      var ov = sobrepostos(d), dif = im.area_calculada_ha - im.area_declarada_ha;
      var condicao = "<i>" + fmt.esc(im.condicao || t("não informada", "not stated")) + "</i>";
      ctx.texto("declarado", t("Este imóvel declara <b>" + fmt.ha(im.area_declarada_ha) + "</b>, e o polígono mede <b>" + fmt.ha(im.area_calculada_ha) +
          "</b> (" + fmt.sinal(dif, 2) + " ha). A condição no SICAR é " + condicao + ". " +
          (ov.length ? (ov.length > 1 ? "Outros <b>" + ov.length + " registros</b> se sobrepõem a ele" : "<b>Um outro registro</b> se sobrepõe a ele") + ", em tracejado no mapa." : "Nenhum outro registro se sobrepõe a ele."),
        "This property declares <b>" + fmt.ha(im.area_declarada_ha) + "</b>, and its polygon measures <b>" + fmt.ha(im.area_calculada_ha) +
          "</b> (" + fmt.sinal(dif, 2) + " ha). Its condition in SICAR reads " + condicao + " (as published). " +
          (ov.length ? "<b>" + ov.length + " other registration" + (ov.length > 1 ? "s" : "") + "</b> overlap it, dashed on the map." : "No other registration overlaps it.")));
      var z = d.zonas, vezes = z[3] ? z[3].area_ha / z[0].area_ha : 0;
      ctx.texto("zonas", t("Para um imóvel de " + fmt.ha(z[0].area_ha) + ", as faixas somam " + z.slice(1).map(function (x) { return "<b>" + fmt.ha(x.area_ha) + "</b>"; }).join(", ") +
          ". Só a faixa de fora tem " + fmt.n(vezes, 0) + " vezes a área do imóvel: em qualquer média, a vizinhança pesa mais que ele.",
        "For a property of " + fmt.ha(z[0].area_ha) + ", the bands cover " + z.slice(1).map(function (x) { return "<b>" + fmt.ha(x.area_ha) + "</b>"; }).join(", ") +
          ". The outer band alone is " + fmt.n(vezes, 0) + " times the property: in any average, the neighbourhood outweighs it."));
    },

    passos: {
      busca: function (ctx, d) {
        var im = d.imovel;
        ctx.tiles({ sicar: camada(d, "sicar") });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("<b>" + t("Imóvel do CAR", "CAR property") + '</b><span><i style="background:#ffd400"></i>' + t("divisa declarada", "declared boundary") +
          '</span><span><i style="background:#e8a04a"></i>' + t("outros imóveis (WMS do SICAR)", "other properties (SICAR WMS)") + "</span>");
        ctx.$("#fig-busca").innerHTML = '<dl class="rp-ficha"><dt>' + t("Código", "Code") + "</dt><dd><code>" + fmt.esc(im.cod_imovel) + "</code></dd>" +
          "<dt>" + t("Camada", "Layer") + "</dt><dd>sicar:sicar_imoveis_" + im.uf.toLowerCase() + "</dd><dt>" + t("Município", "Municipality") + "</dt><dd>" + fmt.esc(im.municipio) + "/" + fmt.esc(im.uf) + "</dd></dl>";
      },

      declarado: function (ctx, d) {
        var im = d.imovel, ov = sobrepostos(d);
        ctx.tiles({});
        var vet = { imovel: { geojson: imovelGeo(d), estilo: CONTORNO } };
        if (ov.length) vet.sobrepostos = {
          geojson: { type: "FeatureCollection", features: ov.map(function (o) { return { type: "Feature", properties: { cod: o.cod_imovel, ha: o.overlap_ha }, geometry: o.geometry }; }) },
          estilo: { color: "#ff4fd8", weight: 2, dashArray: "6 5", fillOpacity: 0.06 },
          popup: function (f) { return fmt.esc(f.properties.cod) + "<br>" + t("em comum: ", "in common: ") + fmt.ha(f.properties.ha); }
        };
        ctx.vetores(vet);
        ctx.enquadrar(ov.length ? vet.sobrepostos.geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<span><i style="background:#ffd400"></i>' + t("este imóvel", "this property") + "</span>" + (ov.length ? '<span><i style="background:#ff4fd8"></i>' + t("registros sobrepostos", "overlapping registrations") + "</span>" : ""));
        var pct = 100 * (im.area_calculada_ha - im.area_declarada_ha) / im.area_declarada_ha;
        var h = '<div class="rp-dupla"><div><div class="rp-caixa-tit">' + t("Campos do SICAR, como vieram", "SICAR fields, as published") + ' <span class="selo declarado">' + t("declarado", "declared") + '</span></div><dl class="rp-ficha">' +
          "<dt>" + t("Área declarada", "Declared area") + '</dt><dd class="declarado">' + fmt.ha(im.area_declarada_ha) + "</dd>" +
          "<dt>" + t("Módulos fiscais", "Fiscal modules") + '</dt><dd class="declarado">' + fmt.n(im.m_fiscal, 2) + "</dd>" +
          "<dt>" + t("Tipo", "Type") + "</dt><dd>" + fmt.esc(im.tipo_imovel) + "</dd><dt>" + t("Status", "Status") + "</dt><dd>" + fmt.esc(im.status_imovel) + "</dd>" +
          "<dt>" + t("Condição", "Condition") + "</dt><dd>" + fmt.esc(im.condicao || t("não informada", "not stated")) + "</dd>" +
          "<dt>" + t("Inscrito em", "Registered") + "</dt><dd>" + fmt.data(im.dat_criacao) + "</dd><dt>" + t("Atualizado em", "Updated") + "</dt><dd>" + (im.data_atualizacao ? fmt.data(im.data_atualizacao) : t("não informada", "not stated")) + "</dd></dl></div>" +
          '<div><div class="rp-caixa-tit">' + t("Medido aqui", "Measured here") + ' <span class="selo real">' + t("real", "measured") + '</span></div><dl class="rp-ficha"><dt>' + t("Área do polígono", "Polygon area") + "</dt><dd>" + fmt.ha(im.area_calculada_ha) + "</dd>" +
          "<dt>" + t("Diferença", "Difference") + "</dt><dd>" + fmt.sinal(im.area_calculada_ha - im.area_declarada_ha, 2) + " ha (" + fmt.sinal(pct, 1) + "%)</dd></dl>";
        if (ov.length) {
          h += '<div class="rp-caixa-tit" style="margin-top:10px">' + t("Registros sobrepostos", "Overlapping registrations") + "</div>";
          h += ov.slice(0, 6).map(function (o) {
            return '<div style="font-size:12.5px;padding:3px 0;border-top:1px solid #eef2ef"><code>' + fmt.esc(o.cod_imovel.slice(0, 18)) + "…</code><br>" +
              fmt.ha(o.overlap_ha) + t(" em comum (", " in common (") + fmt.pct(o.overlap_pct_do_imovel, 1) + t(" deste imóvel) · declara ", " of this property) · declares ") + fmt.ha(o.area_declarada_ha) + "</div>";
          }).join("") + (ov.length > 6 ? '<div style="font-size:12px;color:#7b8a83">' + t("e mais ", "and ") + (ov.length - 6) + t("", " more") + "</div>" : "");
        }
        ctx.$("#fig-declarado").innerHTML = h + "</div></div>";
      },

      zonas: function (ctx, d) {
        ctx.tiles({});
        var aneis = d.zonas.slice(1).map(function (z) { return { type: "Feature", properties: { key: z.key }, geometry: z.geojson.geometry || z.geojson }; });
        ctx.vetores({
          aneis: { geojson: { type: "FeatureCollection", features: aneis }, estilo: function (f) { return { color: COR_ZONA[f.properties.key], weight: 2, dashArray: "5 4", fillColor: COR_ZONA[f.properties.key], fillOpacity: 0.12 }; } },
          imovel: { geojson: imovelGeo(d), estilo: CONTORNO }
        });
        ctx.enquadrar(aneis[aneis.length - 1], { maxZoom: 13 });
        ctx.legendaMapa(d.zonas.map(function (z) { return '<span><i style="background:' + (z.key === "imovel" ? "#ffd400" : COR_ZONA[z.key]) + '"></i>' + fmt.esc(nomeZona(z.key)) + "</span>"; }).join(""));
        graf.tabela(ctx.$("#fig-zonas"), {
          colunas: [{ rotulo: t("Zona", "Zone") }, { rotulo: t("Área", "Area"), n: true }, { rotulo: t("× imóvel", "× property"), n: true }],
          linhas: d.zonas.map(function (z) { return [graf.qd(z.key === "imovel" ? "#ffd400" : COR_ZONA[z.key]) + fmt.esc(nomeZona(z.key)), fmt.ha(z.area_ha), fmt.n(z.area_ha / d.zonas[0].area_ha, 1)]; })
        });
      },

      cobertura: function (ctx, d) {
        var el = ctx.$("#fig-cobertura"), h = d.historico;
        if (!h) return faltou(el, "O MapBiomas");
        var ultimo = h.anos[h.anos.length - 1];
        ctx.tiles({ mb: camada(d, "mb_" + ultimo, 0.8) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa(legendaClasses(d, ultimo));
        var series = Object.keys(h.zonas.imovel).map(function (c) { return { rotulo: nomeClasse(h.classes[c]), cor: h.classes[c].cor, valores: h.zonas.imovel[c] }; })
          .sort(function (a, b) { return b.valores[b.valores.length - 1] - a.valores[a.valores.length - 1]; });
        var reg = d.imovel.ano_criacao;
        graf.empilhado(el, { anos: h.anos, series: series, unidade: "ha", marcas: reg ? [{ ano: reg, rotulo: t("inscrição no CAR (", "CAR registration (") + reg + ")" }] : [] });
        // a história em palavras: a maior classe no começo, na inscrição e no fim, e quando ela mudou
        var c0 = classesNoAno(d, "imovel", 0)[0], cf = classesNoAno(d, "imovel", h.anos.length - 1)[0], troca = null;
        for (var i = 1; i < h.anos.length; i++) { var ci = classesNoAno(d, "imovel", i)[0]; if (ci && c0 && ci.id !== c0.id) { troca = { ano: h.anos[i], c: ci }; break; } }
        var ir = reg ? h.anos.indexOf(reg) : -1, cr = ir >= 0 ? classesNoAno(d, "imovel", ir)[0] : null;
        var b = function (x) { return "<b>" + fmt.esc(x ? x.nome.toLowerCase() : "—") + "</b>"; };
        ctx.texto("cobertura", t(
          "Em " + h.anos[0] + ", o que mais havia no imóvel era " + b(c0) + " (" + fmt.ha(c0 && c0.ha) + "). " +
          (troca ? "Em <b>" + troca.ano + "</b>, " + b(troca.c) + " passa à frente. " : "") +
          "Em " + ultimo + ", " + b(cf) + " ocupa " + fmt.ha(cf && cf.ha) + "." + (cr ? " Na inscrição no CAR, em " + reg + ", já predominava " + b(cr) + "." : ""),
          "In " + h.anos[0] + ", the largest class on the property was " + b(c0) + " (" + fmt.ha(c0 && c0.ha) + "). " +
          (troca ? "In <b>" + troca.ano + "</b>, " + b(troca.c) + " takes over. " : "") +
          "In " + ultimo + ", " + b(cf) + " covers " + fmt.ha(cf && cf.ha) + "." + (cr ? " By the CAR registration in " + reg + ", " + b(cr) + " already dominated." : "")));
      },

      vizinhanca: function (ctx, d) {
        var el = ctx.$("#fig-vizinhanca"), h = d.historico;
        if (!h) return faltou(el, "O MapBiomas");
        ctx.tiles({ mb: camada(d, "mb_" + h.anos[0], 0.8) });
        ctx.vetores({
          aneis: { geojson: d.zonas[d.zonas.length - 1].geojson, estilo: { color: COR_ZONA.ring_5km, weight: 2, dashArray: "5 4", fillOpacity: 0 } },
          imovel: { geojson: imovelGeo(d), estilo: CONTORNO }
        });
        ctx.enquadrar(d.zonas[d.zonas.length - 1].geojson, { maxZoom: 13 });
        ctx.legendaMapa(legendaClasses(d, h.anos[0], "ring_5km"));
        var series = d.zonas.map(function (z) { return { rotulo: nomeZona(z.key), cor: COR_ZONA[z.key], valores: nativaPct(d, z.key), espessura: z.key === "imovel" ? 3 : 2 }; });
        graf.linhas(el, { x: h.anos, series: series, unidade: t("% de vegetação nativa", "% native vegetation"), min: 0, max: 100, marcas: d.imovel.ano_criacao ? [{ x: d.imovel.ano_criacao, rotulo: "CAR" }] : [] });
        var p = series[0].valores, a = series[series.length - 1].valores, n = p.length - 1;
        var juntas = Math.abs((p[0] - p[n]) - (a[0] - a[n])) < 10;
        ctx.texto("vizinhanca", t(
          "No imóvel, a vegetação nativa vai de <b>" + fmt.pct(p[0]) + "</b> em " + h.anos[0] + " a <b>" + fmt.pct(p[n]) + "</b> em " + h.anos[n] +
          "; na faixa de 2 a 5 km, de " + fmt.pct(a[0]) + " a " + fmt.pct(a[n]) + ". " +
          (juntas ? "As curvas descem juntas: a conversão foi da região, não só deste imóvel." : "As curvas se afastam: o imóvel seguiu um caminho próprio."),
          "On the property, native vegetation goes from <b>" + fmt.pct(p[0]) + "</b> in " + h.anos[0] + " to <b>" + fmt.pct(p[n]) + "</b> in " + h.anos[n] +
          "; in the 2–5 km band, from " + fmt.pct(a[0]) + " to " + fmt.pct(a[n]) + ". " +
          (juntas ? "The curves fall together: the conversion was regional, not just this property's." : "The curves part ways: the property took its own path.")));
      },

      transicoes: function (ctx, d) {
        var el = ctx.$("#fig-transicoes"), T = d.transicoes, h = d.historico;
        if (!T || !h) return faltou(el, t("As transições", "The transitions"));
        ctx.tiles({ mb: camada(d, "mb_" + T.ano_b, 0.8) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("");
        var fl = T.zonas.imovel || [], ids = {};
        fl.forEach(function (f) { ids[f.de] = 1; ids[f.para] = 1; });
        var nome = function (c) { var k = h.classes[c]; return k ? nomeClasse(k) : t("classe ", "class ") + c; };
        var nos = Object.keys(ids).map(function (c) { return { id: Number(c), rotulo: nome(c), cor: (h.classes[c] || {}).cor || "#9aa8a1" }; });
        graf.sankey(el, { esq: nos, dir: nos, fluxos: fl.map(function (f) { return { de: f.de, para: f.para, valor: f.ha }; }), rotuloEsq: String(T.ano_a), rotuloDir: String(T.ano_b) });
        var mud = fl.filter(function (f) { return f.de !== f.para; }).sort(function (a, b) { return b.ha - a.ha; });
        var tot = fl.reduce(function (a, f) { return a + f.ha; }, 0), mudou = mud.reduce(function (a, f) { return a + f.ha; }, 0);
        var maior = mud.length ? "<b>" + fmt.esc(nome(mud[0].de).toLowerCase()) + "</b> → <b>" + fmt.esc(nome(mud[0].para).toLowerCase()) + "</b>, " + fmt.ha(mud[0].ha) : "";
        ctx.texto("transicoes", t(
          "Entre " + T.ano_a + " e " + T.ano_b + ", <b>" + fmt.ha(mudou) + "</b> do imóvel (" + fmt.pct(100 * mudou / tot) + ") trocaram de classe. " + (maior ? "O maior fluxo: " + maior + "." : ""),
          "Between " + T.ano_a + " and " + T.ano_b + ", <b>" + fmt.ha(mudou) + "</b> of the property (" + fmt.pct(100 * mudou / tot) + ") changed class. " + (maior ? "The largest flow: " + maior + "." : "")));
      },

      floresta: function (ctx, d) {
        var el = ctx.$("#fig-floresta"), H = d.hansen;
        if (!H) return faltou(el, "O Hansen/GLAD");
        ctx.tiles({ hansen: camada(d, "hansen_2008", 0.9) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<b>Hansen/GLAD</b><span><i style="background:#d4271e"></i>' + t("perda desde 2008", "loss since 2008") + '</span><span><i style="background:#02d659"></i>' + t("ganho (sem data)", "gain (undated)") + "</span>");
        var por = {}, fim = 2024;
        Object.keys(H.perda).forEach(function (z) { H.perda[z].forEach(function (x) { if (x.ano > fim) fim = x.ano; }); });
        (H.perda.imovel || []).forEach(function (x) { por[x.ano] = x; });
        var anos = []; for (var a = 2001; a <= fim; a++) anos.push(a);
        var reg = d.imovel.ano_criacao;
        graf.colunas(el, {
          x: anos.map(String), valores: anos.map(function (a) { return por[a] ? por[a].ha : 0; }), unidade: t("ha de perda por ano", "ha lost per year"),
          cor: function (rot) { var x = por[Number(rot)]; return x ? PERIODO[x.periodo].cor : "#ccc"; },
          marcas: [{ x: "2008", rotulo: "2008" }].concat(reg && reg > 2001 ? [{ x: String(reg), rotulo: "CAR " + reg }] : []),
          legenda: Object.keys(PERIODO).map(function (k) { return { rotulo: PERIODO[k][en ? "en" : "pt"], cor: PERIODO[k].cor }; })
        });
        var soma = {}; (H.perda.imovel || []).forEach(function (x) { soma[x.periodo] = (soma[x.periodo] || 0) + x.ha; });
        var a1 = fmt.ha(soma.ate_2008 || 0), a2 = fmt.ha(soma["2008_ate_registro"] || 0), a3 = fmt.ha(soma.apos_registro || 0);
        ctx.texto("floresta", t(
          "Contando como floresta a copa acima de " + H.limiar_pct + "%, o imóvel perdeu <b>" + a1 + "</b> até 2008, <b>" + a2 + "</b> entre 2008 e a inscrição" +
          (reg ? " (" + reg + ")" : "") + " e <b>" + a3 + "</b> depois dela. O ganho registrado foi de " + fmt.ha(H.ganho_ha) + ".",
          "Counting canopy above " + H.limiar_pct + "% as forest, the property lost <b>" + a1 + "</b> up to 2008, <b>" + a2 + "</b> between 2008 and registration" +
          (reg ? " (" + reg + ")" : "") + ", and <b>" + a3 + "</b> after it. Recorded gain: " + fmt.ha(H.ganho_ha) + "."));
      },

      biomassa: function (ctx, d) {
        var el = ctx.$("#fig-biomassa"), B = d.biomassa;
        if (!B) return faltou(el, "O ESA CCI");
        ctx.tiles({ bio: camada(d, "biomassa", 0.75) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("<b>ESA CCI · " + t("biomassa acima do solo", "above-ground biomass") + '</b><span><i class="g" style="background:linear-gradient(90deg,#fff,#008000)"></i>0 → 500 Mg/ha</span>');
        var anos = (B.imovel || []).map(function (x) { return x.ano; });
        graf.linhas(el, {
          x: anos.map(String), unidade: "Mg/ha", min: 0,
          series: d.zonas.filter(function (z) { return B[z.key]; }).map(function (z) {
            var m = {}; B[z.key].forEach(function (x) { m[x.ano] = x.mgha; });
            return { rotulo: nomeZona(z.key), cor: COR_ZONA[z.key], valores: anos.map(function (a) { return m[a]; }), pontos: true, espessura: z.key === "imovel" ? 3 : 2 };
          })
        });
        var p = B.imovel || [];
        if (p.length) ctx.texto("biomassa", t(
          "No imóvel, a média passa de <b>" + fmt.n(p[0].mgha) + " Mg/ha</b> em " + p[0].ano + " para <b>" + fmt.n(p[p.length - 1].mgha) + " Mg/ha</b> em " + p[p.length - 1].ano +
          ". Note como a série sobe e desce de um ano para o outro sem que a cobertura mude: é o erro do produto, não a floresta.",
          "On the property, the mean goes from <b>" + fmt.n(p[0].mgha) + " Mg/ha</b> in " + p[0].ano + " to <b>" + fmt.n(p[p.length - 1].mgha) + " Mg/ha</b> in " + p[p.length - 1].ano +
          ". Notice how the series jumps from year to year while the land cover does not change: that is the product's error, not the forest."));
      },

      fogo: function (ctx, d) {
        var el = ctx.$("#fig-fogo"), F = d.fogo;
        if (!F) return faltou(el, "O MapBiomas Fogo");
        ctx.tiles({ fogo: camada(d, "fogo", 0.85) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("<b>MapBiomas " + t("Fogo · vezes que queimou", "Fire · times burned") + '</b><span><i class="g" style="background:linear-gradient(90deg,#ffffb2,#fd8d3c,#bd0026,#800026)"></i>' + t("1 → muitas", "1 → many") + "</span>");
        var an = F.anual.imovel || [];
        graf.colunas(el, { x: an.map(function (x) { return String(x.ano); }), valores: an.map(function (x) { return x.pct; }), unidade: t("% do imóvel queimado no ano", "% of the property burned that year"), cor: "#d9480f" });
        var r = F.resumo.imovel || {}, pior = an.slice().sort(function (a, b) { return b.pct - a.pct; })[0];
        var anosFogo = an.filter(function (x) { return x.pct > 0; }).length;
        ctx.texto("fogo", anosFogo ? t(
          "O fogo chegou ao imóvel em <b>" + anosFogo + " dos " + an.length + " anos</b>. O pior foi <b>" + pior.ano + "</b>, quando queimou " + fmt.pct(pior.pct) +
          " da área. A última queimada registrada no imóvel é de <b>" + (r.ultimo_ano || "—") + "</b>.",
          "Fire reached the property in <b>" + anosFogo + " of " + an.length + " years</b>. The worst was <b>" + pior.ano + "</b>, when " + fmt.pct(pior.pct) +
          " of it burned. The last recorded fire on the property was in <b>" + (r.ultimo_ano || "—") + "</b>.")
          : t("Nenhuma cicatriz de fogo foi mapeada no imóvel desde 1985.", "No burn scar has been mapped on the property since 1985."));
      },

      spot: function (ctx, d) {
        var el = ctx.$("#fig-spot"), S = d.spot;
        ctx.tiles({ spot: camada(d, "spot", 1) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 15 });
        ctx.legendaMapa("<b>SPOT 2008 · " + t("cor natural", "true colour") + "</b>");
        if (!S) return faltou(el, t("O mosaico SPOT", "The SPOT mosaic"));
        el.innerHTML = '<div class="rp-cartoes">' +
          '<div class="rp-cartao"><b>' + fmt.pct(S.covered_pct) + "</b><small>" + t("do imóvel coberto pelo mosaico", "of the property covered by the mosaic") + "</small></div>" +
          '<div class="rp-cartao"><b>' + fmt.data(S.date_min) + "</b><small>" + t("imagem mais antiga", "oldest image") + "</small></div>" +
          '<div class="rp-cartao"><b>' + fmt.data(S.date_max) + "</b><small>" + t("imagem mais recente", "newest image") + "</small></div>" +
          '<div class="rp-cartao"><b>' + fmt.pct(S.pre_cutoff_pct) + "</b><small>" + t("feito antes de 22/07/2008", "taken before 22 July 2008") + "</small></div></div>" +
          '<p class="rp-fig-legenda">' + t("A data varia de pixel para pixel. O Camposcope não classifica área consolidada nem avalia regularidade.",
            "The date varies from pixel to pixel. Camposcope does not classify consolidated area or assess compliance.") + "</p>";
        ctx.texto("spot", S.has_coverage ? t(
          "Sobre este imóvel, as imagens são de <b>" + fmt.data(S.date_min) + "</b> a <b>" + fmt.data(S.date_max) + "</b>, e " + fmt.pct(S.pre_cutoff_pct) + " delas são anteriores ao corte. " +
          (S.pre_cutoff_pct >= 99 ? "Aqui, a imagem serve de referência para a data." : "Uma parte é posterior ao corte e não mostra o 22 de julho de 2008."),
          "Over this property the images date from <b>" + fmt.data(S.date_min) + "</b> to <b>" + fmt.data(S.date_max) + "</b>, and " + fmt.pct(S.pre_cutoff_pct) + " of them predate the cut-off. " +
          (S.pre_cutoff_pct >= 99 ? "Here the image is a fair reference for the date." : "Part of it was taken after the cut-off and does not show 22 July 2008."))
          : t("O mosaico não cobre este imóvel: não há imagem de 2008 para ele.", "The mosaic does not cover this property: there is no 2008 image for it."));
      },

      validacao: function (ctx, d) {
        var el = ctx.$("#fig-validacao"), I = d.ibge;
        ctx.tiles({ ibge: camada(d, "ibge", 0.8) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("<b>" + t("IBGE · vegetação 2022, rasterizada", "IBGE · vegetation 2022, rasterised") + "</b>" + t("54 classes, com a paleta do aplicativo", "54 classes, in the app's palette"));
        if (!I) return faltou(el, t("O mapa do IBGE", "IBGE's map"));
        var rot = function (k) { return (GRUPO_IBGE[k] || [k, k])[en ? 1 : 0]; };
        var curto = function (k) { return rot(k).replace(/^(Antrópico|Natural|Human) — /, ""); };
        var g = I.groups.filter(function (k) { return I.groups.some(function (m) { return (I.matrix[k] || {})[m] > 0.05 || (I.matrix[m] || {})[k] > 0.05; }); });
        graf.tabela(el, {
          colunas: [{ rotulo: "IBGE ↓ · MapBiomas →" }].concat(g.map(function (k) { return { rotulo: curto(k), n: true }; })),
          linhas: g.map(function (k) { return [fmt.esc(rot(k))].concat(g.map(function (m) { var v = (I.matrix[k] || {})[m] || 0; return v > 0.05 ? (k === m ? "<b>" + fmt.pct(v, 1) + "</b>" : fmt.pct(v, 1)) : "·"; })); }),
          nota: t("Parte do imóvel em cada par de classes. Na diagonal, em negrito, os dois mapas concordam.", "Share of the property in each pair of classes. On the diagonal, in bold, the two maps agree.")
        });
        var gap = I.forest_ibge - I.forest_mb > 5;
        ctx.texto("validacao", t(
          "Neste imóvel, o IBGE vê floresta natural em <b>" + fmt.pct(I.forest_ibge, 1) + "</b> da área, e o MapBiomas em <b>" + fmt.pct(I.forest_mb, 1) + "</b>. " +
          (gap ? "A diferença é o que o IBGE ainda desenha como floresta e o MapBiomas já classifica como uso agropecuário." : "Aqui os dois mapas praticamente concordam."),
          "On this property IBGE sees natural forest on <b>" + fmt.pct(I.forest_ibge, 1) + "</b> of the area, and MapBiomas on <b>" + fmt.pct(I.forest_mb, 1) + "</b>. " +
          (gap ? "The gap is what IBGE still draws as forest and MapBiomas already classifies as farmland." : "Here the two maps broadly agree.")));
      },

      procedencia: function (ctx, d) {
        ctx.tiles({}); ctx.vetores({}); ctx.legendaMapa("");
        graf.tabela(ctx.$("#fig-procedencia"), {
          colunas: [{ rotulo: t("Análise", "Analysis") }, { rotulo: t("Fonte (asset)", "Source (asset)") }, { rotulo: t("Escala", "Scale"), n: true }, { rotulo: t("Calculado", "Computed"), n: true }],
          linhas: (d.procedencia || []).map(function (p) { return [fmt.esc(p.nome), '<code style="font-size:11px;overflow-wrap:anywhere">' + fmt.esc(p.dataset) + "</code>", p.escala_m ? p.escala_m + " m" : "—", fmt.data(p.calculado_em)]; }),
          nota: t("Imóvel consultado no SICAR em ", "Property fetched from SICAR on ") + fmt.dataHora(d.imovel.consultado_em) + t(". Esta tabela acompanha o relatório e a planilha.", ". This table travels with the report and the spreadsheet.")
        });
        var n = (d.procedencia || []).length;
        ctx.texto("procedencia", t(
          "Para este imóvel foram " + n + " consultas ao Earth Engine e uma ao SICAR, todas do cálculo de " + fmt.dataHora(d.gerado_em) + ".",
          "This property took " + n + " Earth Engine queries and one SICAR query, all from the run of " + fmt.dataHora(d.gerado_em) + "."));
      }
    }
  });
})();
