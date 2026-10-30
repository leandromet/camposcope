/* Camposcope — the Canada walkthrough (/walkthrough, a Kelowna parcel).
 *
 * The numbers come from /_demonstracao/camposcope_ca.json
 * (canada/services/demonstracao.py), built by the Canada page's own services.
 * This file only decides what each step shows; no value is written by hand.
 * English only: the Portuguese walkthrough opens a Brazilian property
 * (camposcope.js), so the text here is not passed through ctx.t.
 */
(function () {
  var R = window.Reportagem, fmt = R.fmt, graf = R.graf;

  var ZONA = { parcela: "Parcel", ring_500m: "0–500 m", ring_2km: "500 m–2 km", ring_5km: "2–5 km" };
  var COR_ZONA = { parcela: "#d98324", ring_500m: "#1f6f4a", ring_2km: "#4f8f6f", ring_5km: "#9cc2ac" };
  var CONTORNO = { color: "#ffd400", weight: 3, fillOpacity: 0 };
  // hansen.py: PERIOD_* — split at the parcel's start date, or undivided
  var PERIODO = {
    sem_divisao: { cor: "#e5484d", rot: "Loss (undivided)" },
    antes_da_parcela: { cor: "#f5a524", rot: "Before the parcel" },
    apos_a_parcela: { cor: "#8b1a1a", rot: "After the parcel" }
  };

  function pid(ctx) { return (ctx.params.get("pid") || "").replace(/\D/g, ""); }
  function nomeZona(k) { return ZONA[k] || k; }
  function parcelaGeo(d) { return { type: "Feature", properties: {}, geometry: d.parcela.geometry }; }
  function classesNoAno(d, zona, i) {
    var h = d.historico, z = h.zonas[zona] || {};
    return Object.keys(z).map(function (c) { return { id: c, ha: z[c][i] || 0, nome: h.classes[c].nome_en || h.classes[c].nome, cor: h.classes[c].cor }; })
      .filter(function (x) { return x.ha > 0; }).sort(function (a, b) { return b.ha - a.ha; });
  }
  function legendaClasses(d, ano, zona) {
    var i = d.historico.anos.indexOf(ano); if (i < 0) return "";
    return "<b>AAFC crop inventory " + ano + " · classes " + (zona === "ring_5km" ? "within 5 km" : "on the parcel") + "</b>" +
      classesNoAno(d, zona || "parcela", i).slice(0, 6).map(function (c) { return '<span><i style="background:' + c.cor + '"></i>' + fmt.esc(c.nome) + "</span>"; }).join("");
  }
  function nativaPct(d, zona) {
    var h = d.historico, z = h.zonas[zona] || {}, nat = h.nativas.map(String);
    return h.anos.map(function (_, i) {
      var tot = 0, n = 0;
      Object.keys(z).forEach(function (c) { tot += z[c][i] || 0; if (nat.indexOf(c) >= 0) n += z[c][i] || 0; });
      return tot > 0 ? (100 * n) / tot : null;
    });
  }
  function camada(d, k, op) { var c = d.camadas[k]; return c ? Object.assign({}, c, op ? { opacity: op } : {}) : null; }
  function faltou(el, nome) {
    el.innerHTML = '<p class="rp-fig-estado erro">' + nome + ' did not respond this time <span class="selo ausente">missing</span></p>';
  }
  function grupo(d, k) { var g = (d.vlce2 && d.vlce2.grupos[k]) || {}; return g.nome_en || k; }
  // the chart's short labels: "Cropland and pasture" → "Cropland"
  function grupoCurto(d, k) { return grupo(d, k).split(/ and |, | \/ /)[0]; }

  R.iniciar({
    dados: function (ctx) { var p = pid(ctx); return "/_demonstracao/camposcope_ca.json" + (p ? "?pid=" + p : ""); },
    centro: [49.86, -119.39], zoom: 11,

    aoCarregar: function (ctx, d) {
      var pa = d.parcela, h = d.historico;
      var ultimo = h ? h.anos[h.anos.length - 1] : null;
      var lista = h ? classesNoAno(d, "parcela", h.anos.length - 1) : [];
      var top = lista[0], tot = lista.reduce(function (a, c) { return a + c.ha; }, 0);
      var v = d.vlce2 && d.vlce2.resumo.parcela;
      ctx.preencher({
        "n-registrada": fmt.ha(pa.area_registrada_ha),
        "n-calculada": fmt.ha(pa.area_calculada_ha),
        "n-uso": top ? fmt.pct((100 * top.ha) / tot) : "—",
        "n-uso-rot": top ? fmt.esc(top.nome.toLowerCase()) + " in " + ultimo + ' <span class="selo real">measured</span>' : "main land use in the latest year",
        "n-concorda": v ? fmt.pct(v.concordancia_pct) : "—",
        "n-concorda-rot": "of the parcel where the crop inventory and VLCE2 " + (d.vlce2 ? d.vlce2.ano + " " : "") + 'agree <span class="selo real">measured</span>'
      });
      ctx.$("#topo-exemplo").textContent = "PID " + pa.identificador + " · " + pa.municipio;
      var app = "/canada?pid=" + encodeURIComponent(pa.pid || pa.fabric_id) + "&lang=en";
      ctx.$("#link-app").href = app; ctx.$("#cta-app").href = app;
      ctx.$("#rp-fig-url").textContent = "camposcope.umaterra.com.br" + app;
      ctx.$("#abertura-exemplo").innerHTML = (d.exemplo_padrao ? "This page's example: an orchard parcel on the East Kelowna bench, " : "Chosen parcel: ") +
        "<b>" + fmt.esc(pa.municipio) + "</b>, PID <code>" + fmt.esc(pa.identificador) + "</code>, computed by the app's services on " + fmt.dataHora(d.gerado_em) +
        (d.exemplo_padrao ? " and stored with this page." : " (the result is kept for a few hours).");
      var erros = Object.keys(d.erros || {});
      ctx.$("#fim-extra").innerHTML = erros.length
        ? "These did not respond this time: <b>" + erros.map(fmt.esc).join(", ") + "</b>. The matching steps say what is missing."
        : "Every analysis responded in the run of " + fmt.dataHora(d.gerado_em) + ".";

      ctx.texto("busca", "Here the PID <code>" + fmt.esc(pa.identificador) + "</code> returns one polygon in " + fmt.esc(pa.municipio) +
        ", " + fmt.esc(pa.distrito) + ". The parcel is in yellow; the fabric's other parcels show faintly behind it.");
      var dif = pa.area_calculada_ha - pa.area_registrada_ha;
      ctx.texto("registro", "The fabric records a <b>" + fmt.esc(pa.classe.toLowerCase()) + "</b> parcel, owner type <b>" + fmt.esc(pa.tipo_dono.toLowerCase()) +
        "</b>, on plan " + fmt.esc(pa.plano) + ", of <b>" + fmt.ha(pa.area_registrada_ha) + "</b>. Measured here, the polygon is " + fmt.ha(pa.area_calculada_ha) +
        " (" + fmt.sinal(dif, 2) + " ha): " + (Math.abs(dif) < 0.05 * pa.area_registrada_ha ? "a surveyed fabric and its own geometry agree." : "a gap worth a look at the plan.") +
        (pa.ano_inicio ? "" : " The fabric has no start date for it, as for most older parcels."));
      var z = d.zonas, vezes = z[3] ? z[3].area_ha / z[0].area_ha : 0;
      ctx.texto("zonas", "For a parcel of " + fmt.ha(z[0].area_ha) + ", the bands cover " + z.slice(1).map(function (x) { return "<b>" + fmt.ha(x.area_ha) + "</b>"; }).join(", ") +
        ". The outer band alone is " + fmt.n(vezes, 0) + " times the parcel: in any average, the neighbourhood outweighs it.");
    },

    passos: {
      busca: function (ctx, d) {
        var pa = d.parcela;
        ctx.tiles({ pmbc: camada(d, "pmbc") });
        ctx.vetores({ parcela: { geojson: parcelaGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(parcelaGeo(d), { maxZoom: 15 });
        ctx.legendaMapa('<b>ParcelMap BC</b><span><i style="background:#ffd400"></i>this parcel</span><span><i style="background:#e8a04a"></i>other parcels (WMS)</span>');
        ctx.$("#fig-busca").innerHTML = '<dl class="rp-ficha"><dt>PID</dt><dd><code>' + fmt.esc(pa.identificador) + "</code></dd><dt>Fabric id</dt><dd>" + fmt.esc(String(pa.fabric_id)) +
          "</dd><dt>Municipality</dt><dd>" + fmt.esc(pa.municipio) + "</dd><dt>Regional district</dt><dd>" + fmt.esc(pa.distrito) + "</dd></dl>";
      },

      registro: function (ctx, d) {
        var pa = d.parcela;
        ctx.tiles({ pmbc: camada(d, "pmbc") });
        ctx.vetores({ parcela: { geojson: parcelaGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(parcelaGeo(d), { maxZoom: 16 });
        ctx.legendaMapa('<span><i style="background:#ffd400"></i>this parcel</span>');
        var pct = 100 * (pa.area_calculada_ha - pa.area_registrada_ha) / pa.area_registrada_ha;
        ctx.$("#fig-registro").innerHTML = '<div class="rp-dupla"><div><div class="rp-caixa-tit">ParcelMap BC fields, as published <span class="selo declarado">registered</span></div><dl class="rp-ficha">' +
          "<dt>Class</dt><dd>" + fmt.esc(pa.classe) + "</dd><dt>Owner type</dt><dd>" + fmt.esc(pa.tipo_dono) + "</dd><dt>Status</dt><dd>" + fmt.esc(pa.status) +
          "</dd><dt>Plan</dt><dd>" + fmt.esc(pa.plano) + "</dd><dt>Registered area</dt><dd>" + fmt.ha(pa.area_registrada_ha) +
          "</dd><dt>Start date</dt><dd>" + (pa.ano_inicio || "not recorded") + "</dd><dt>Updated</dt><dd>" + (pa.atualizado_em ? fmt.data(pa.atualizado_em.replace(/Z$/, "")) : "—") + "</dd></dl></div>" +
          '<div><div class="rp-caixa-tit">Measured here <span class="selo real">measured</span></div><dl class="rp-ficha"><dt>Polygon area</dt><dd>' + fmt.ha(pa.area_calculada_ha) +
          "</dd><dt>Difference</dt><dd>" + fmt.sinal(pa.area_calculada_ha - pa.area_registrada_ha, 2) + " ha (" + fmt.sinal(pct, 1) + "%)</dd></dl></div></div>";
      },

      zonas: function (ctx, d) {
        ctx.tiles({});
        var aneis = d.zonas.slice(1).map(function (z) { return { type: "Feature", properties: { key: z.key }, geometry: z.geojson.geometry || z.geojson }; });
        ctx.vetores({
          aneis: { geojson: { type: "FeatureCollection", features: aneis }, estilo: function (f) { return { color: COR_ZONA[f.properties.key], weight: 2, dashArray: "5 4", fillColor: COR_ZONA[f.properties.key], fillOpacity: 0.12 }; } },
          parcela: { geojson: parcelaGeo(d), estilo: CONTORNO }
        });
        ctx.enquadrar(aneis[aneis.length - 1], { maxZoom: 13 });
        ctx.legendaMapa(d.zonas.map(function (z) { return '<span><i style="background:' + (z.key === "parcela" ? "#ffd400" : COR_ZONA[z.key]) + '"></i>' + fmt.esc(nomeZona(z.key)) + "</span>"; }).join(""));
        graf.tabela(ctx.$("#fig-zonas"), {
          colunas: [{ rotulo: "Zone" }, { rotulo: "Area", n: true }, { rotulo: "× parcel", n: true }],
          linhas: d.zonas.map(function (z) { return [graf.qd(z.key === "parcela" ? "#ffd400" : COR_ZONA[z.key]) + fmt.esc(nomeZona(z.key)), fmt.ha(z.area_ha), fmt.n(z.area_ha / d.zonas[0].area_ha, 1)]; })
        });
      },

      cobertura: function (ctx, d) {
        var el = ctx.$("#fig-cobertura"), h = d.historico;
        if (!h) return faltou(el, "The crop inventory");
        var ultimo = h.anos[h.anos.length - 1];
        ctx.tiles({ aci: camada(d, "aci_" + ultimo, 0.8) });
        ctx.vetores({ parcela: { geojson: parcelaGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(parcelaGeo(d), { maxZoom: 15 });
        ctx.legendaMapa(legendaClasses(d, ultimo));
        var series = Object.keys(h.zonas.parcela).map(function (c) { return { rotulo: h.classes[c].nome_en || h.classes[c].nome, cor: h.classes[c].cor, valores: h.zonas.parcela[c] }; })
          .filter(function (s) { return s.valores.some(function (v) { return v > 0; }); })
          .sort(function (a, b) { return b.valores[b.valores.length - 1] - a.valores[a.valores.length - 1]; });
        graf.empilhado(el, { anos: h.anos, series: series, unidade: "ha" });
        var c0 = classesNoAno(d, "parcela", 0)[0], cf = classesNoAno(d, "parcela", h.anos.length - 1)[0], troca = null;
        for (var i = 1; i < h.anos.length; i++) { var ci = classesNoAno(d, "parcela", i)[0]; if (ci && c0 && ci.id !== c0.id) { troca = { ano: h.anos[i], c: ci }; break; } }
        var b = function (x) { return "<b>" + fmt.esc(x ? x.nome.toLowerCase() : "—") + "</b>"; };
        ctx.texto("cobertura", "In " + h.anos[0] + ", the largest class on the parcel was " + b(c0) + " (" + fmt.ha(c0 && c0.ha) + "). " +
          (troca ? "In <b>" + troca.ano + "</b>, " + b(troca.c) + " takes over. " : "") + "In " + ultimo + ", " + b(cf) + " covers " + fmt.ha(cf && cf.ha) + ". " +
          (troca ? "Whether that is a new planting or an old one the inventory learned to see, the record alone cannot say: compare the satellite basemap of both years before calling it new." : ""));
      },

      vizinhanca: function (ctx, d) {
        var el = ctx.$("#fig-vizinhanca"), h = d.historico;
        if (!h) return faltou(el, "The crop inventory");
        ctx.tiles({ aci: camada(d, "aci_" + h.anos[0], 0.8) });
        ctx.vetores({
          aneis: { geojson: d.zonas[d.zonas.length - 1].geojson, estilo: { color: COR_ZONA.ring_5km, weight: 2, dashArray: "5 4", fillOpacity: 0 } },
          parcela: { geojson: parcelaGeo(d), estilo: CONTORNO }
        });
        ctx.enquadrar(d.zonas[d.zonas.length - 1].geojson, { maxZoom: 13 });
        ctx.legendaMapa(legendaClasses(d, h.anos[0], "ring_5km"));
        var series = d.zonas.map(function (z) { return { rotulo: nomeZona(z.key), cor: COR_ZONA[z.key], valores: nativaPct(d, z.key), espessura: z.key === "parcela" ? 3 : 2 }; });
        graf.linhas(el, { x: h.anos, series: series, unidade: "% natural vegetation", min: 0, max: 100 });
        var p = series[0].valores, a = series[series.length - 1].valores, n = p.length - 1;
        var juntas = Math.abs((p[0] - p[n]) - (a[0] - a[n])) < 10;
        ctx.texto("vizinhanca", "On the parcel, natural vegetation goes from <b>" + fmt.pct(p[0]) + "</b> in " + h.anos[0] + " to <b>" + fmt.pct(p[n]) + "</b> in " + h.anos[n] +
          "; in the 2–5 km band, from " + fmt.pct(a[0]) + " to " + fmt.pct(a[n]) + ". " +
          (juntas ? "The curves move together: whatever changed, changed across the valley." : "The curves part ways: the parcel took its own path, or the inventory changed its mind about it."));
      },

      transicoes: function (ctx, d) {
        var el = ctx.$("#fig-transicoes"), T = d.transicoes, h = d.historico;
        if (!T || !h) return faltou(el, "The transitions");
        ctx.tiles({ aci: camada(d, "aci_" + T.ano_b, 0.8) });
        ctx.vetores({ parcela: { geojson: parcelaGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(parcelaGeo(d), { maxZoom: 15 });
        ctx.legendaMapa("");
        var fl = T.zonas.parcela || [], ids = {};
        fl.forEach(function (f) { ids[f.de] = 1; ids[f.para] = 1; });
        var nome = function (c) { var k = h.classes[c]; return k ? (k.nome_en || k.nome) : "class " + c; };
        var nos = Object.keys(ids).map(function (c) { return { id: Number(c), rotulo: nome(c), cor: (h.classes[c] || {}).cor || "#9aa8a1" }; });
        graf.sankey(el, { esq: nos, dir: nos, fluxos: fl.map(function (f) { return { de: f.de, para: f.para, valor: f.ha }; }), rotuloEsq: String(T.ano_a), rotuloDir: String(T.ano_b) });
        var mud = fl.filter(function (f) { return f.de !== f.para; }).sort(function (a, b) { return b.ha - a.ha; });
        var tot = fl.reduce(function (a, f) { return a + f.ha; }, 0), mudou = mud.reduce(function (a, f) { return a + f.ha; }, 0);
        ctx.texto("transicoes", "Between " + T.ano_a + " and " + T.ano_b + ", <b>" + fmt.ha(mudou) + "</b> of the parcel (" + fmt.pct(100 * mudou / tot) + ") changed class. " +
          (mud.length ? "The largest flow: <b>" + fmt.esc(nome(mud[0].de).toLowerCase()) + "</b> → <b>" + fmt.esc(nome(mud[0].para).toLowerCase()) + "</b>, " + fmt.ha(mud[0].ha) + "." : ""));
      },

      floresta: function (ctx, d) {
        var el = ctx.$("#fig-floresta"), H = d.hansen;
        if (!H) return faltou(el, "Hansen/GLAD");
        ctx.tiles({ hansen: camada(d, "hansen_2001", 0.9) });
        ctx.vetores({ parcela: { geojson: parcelaGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : parcelaGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<b>Hansen/GLAD</b><span><i style="background:#d4271e"></i>loss since 2001</span><span><i style="background:#02d659"></i>gain (undated)</span>');
        var fim = 2024, por = {};
        Object.keys(H.perda).forEach(function (z) { H.perda[z].forEach(function (x) { if (x.ano > fim) fim = x.ano; }); });
        // the parcel is small; the 0–2 km neighbourhood carries the signal, so both are drawn
        var anos = []; for (var a = 2001; a <= fim; a++) anos.push(a);
        ["parcela", "ring_500m", "ring_2km"].forEach(function (k) { (H.perda[k] || []).forEach(function (x) { por[x.ano] = (por[x.ano] || 0) + x.ha; }); });
        graf.colunas(el, { x: anos.map(String), valores: anos.map(function (a) { return por[a] || 0; }), unidade: "ha of tree cover lost per year, parcel + 0–2 km", cor: PERIODO.sem_divisao.cor });
        var soma = function (k) { return (H.perda[k] || []).reduce(function (s, x) { return s + x.ha; }, 0); };
        var pior = anos.slice().sort(function (x, y) { return (por[y] || 0) - (por[x] || 0); })[0];
        ctx.texto("floresta", "Counting canopy above " + H.limiar_pct + "% as forest, the parcel lost <b>" + fmt.ha(soma("parcela")) + "</b> since 2001, the first 2 km around it <b>" +
          fmt.ha(soma("ring_500m") + soma("ring_2km")) + "</b>, and the 2–5 km band " + fmt.ha(soma("ring_5km")) + ". The worst year nearby was <b>" + pior + "</b>. " +
          (H.divide_em ? "" : "With no start date in the fabric, the series is not split.") + " Recorded gain on the parcel: " + fmt.ha(H.ganho_ha) + ".");
      },

      biomassa: function (ctx, d) {
        var el = ctx.$("#fig-biomassa"), B = d.biomassa;
        if (!B) return faltou(el, "ESA CCI");
        ctx.tiles({ bio: camada(d, "biomassa", 0.75) });
        ctx.vetores({ parcela: { geojson: parcelaGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : parcelaGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<b>ESA CCI · above-ground biomass</b><span><i class="g" style="background:linear-gradient(90deg,#fff,#008000)"></i>0 → 500 Mg/ha</span>');
        var anos = (B.parcela || []).map(function (x) { return x.ano; });
        graf.linhas(el, {
          x: anos.map(String), unidade: "Mg/ha", min: 0,
          series: d.zonas.filter(function (z) { return B[z.key]; }).map(function (z) {
            var m = {}; B[z.key].forEach(function (x) { m[x.ano] = x.mgha; });
            return { rotulo: nomeZona(z.key), cor: COR_ZONA[z.key], valores: anos.map(function (a) { return m[a]; }), pontos: true, espessura: z.key === "parcela" ? 3 : 2 };
          })
        });
        var p = B.parcela || [];
        if (p.length) ctx.texto("biomassa", "On the parcel, the mean goes from <b>" + fmt.n(p[0].mgha) + " Mg/ha</b> in " + p[0].ano + " to <b>" + fmt.n(p[p.length - 1].mgha) +
          " Mg/ha</b> in " + p[p.length - 1].ano + ". Notice how the series jumps from year to year while the orchard stays an orchard: that is the product's error, not the trees.");
      },

      fogo: function (ctx, d) {
        var el = ctx.$("#fig-fogo"), F = d.fogo;
        if (!F) return faltou(el, "MODIS");
        ctx.tiles({ fogo: camada(d, "fogo", 0.85) });
        ctx.vetores({
          aneis: { geojson: d.zonas[d.zonas.length - 1].geojson, estilo: { color: COR_ZONA.ring_5km, weight: 2, dashArray: "5 4", fillOpacity: 0 } },
          parcela: { geojson: parcelaGeo(d), estilo: CONTORNO }
        });
        ctx.enquadrar(d.zonas[d.zonas.length - 1].geojson, { maxZoom: 13 });
        ctx.legendaMapa('<b>MODIS · times burned since 2001</b><span><i class="g" style="background:linear-gradient(90deg,#ffffb2,#fd8d3c,#bd0026)"></i>1 → many</span>');
        // fire_history_pct is the share of the record's YEARS with any burn, not of the area
        var an = F.anual.ring_5km || [], rp = F.resumo.parcela || {};
        graf.colunas(el, { x: an.map(function (x) { return String(x.ano); }), valores: an.map(function (x) { return x.pct; }),
          unidade: "% of the 2–5 km band burned that year (MODIS, 500 m)", cor: "#d9480f" });
        var comFogo = an.filter(function (x) { return x.pct > 0; }), pior = an.slice().sort(function (a, b) { return b.pct - a.pct; })[0];
        var ultimoAno = an.length ? an[an.length - 1].ano : null;
        ctx.texto("fogo", (comFogo.length ? "MODIS saw fire in the 2–5 km band in <b>" + comFogo.length + " of " + an.length + " years</b>; the worst was <b>" + pior.ano +
            "</b>, when " + fmt.pct(pior.pct, 1) + " of the band burned. " : "No burn has been mapped within 5 km since 2001. ") +
          (ultimoAno ? "The " + ultimoAno + " column is the year in progress. " : "") +
          (rp.abaixo_resolucao ? "The parcel itself is smaller than one 21 ha MODIS pixel, and the app flags any zone under 500 ha: its zero means “nothing large enough to see”, not “never burned”." : ""));
      },

      validacao: function (ctx, d) {
        var el = ctx.$("#fig-validacao"), V = d.vlce2;
        if (!V) return faltou(el, "VLCE2");
        ctx.tiles({ v: camada(d, "vlce2_" + V.ano, 0.8) });
        ctx.vetores({ parcela: { geojson: parcelaGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(parcelaGeo(d), { maxZoom: 15 });
        ctx.legendaMapa("<b>VLCE2 " + V.ano + " · Canadian Forest Service land cover</b>");
        var M = V.matriz.parcela || [], tot = M.reduce(function (s, x) { return s + x.ha; }, 0);
        graf.barrasH(el, { xRotulo: 190, max: 100, linhas: M.slice().sort(function (a, b) { return b.ha - a.ha; }).slice(0, 7).map(function (x) {
          return { rotulo: grupoCurto(d, x.aci) + " → " + grupoCurto(d, x.vlce2), sub: x.aci === x.vlce2 ? "agree" : "disagree", valor: 100 * x.ha / tot,
                   cor: x.aci === x.vlce2 ? "#1f6f4a" : "#d98324", texto: fmt.pct(100 * x.ha / tot, 1) + " · " + fmt.ha(x.ha) };
        }), rotulo: "Crop inventory → VLCE2, " + V.ano });
        var top = M.slice().sort(function (a, b) { return b.ha - a.ha; })[0], s = V.resumo;
        ctx.texto("validacao", "On this parcel the two maps agree on <b>" + fmt.pct(s.parcela.concordancia_pct) + "</b> of the area, and on " + fmt.pct(s.ring_5km.concordancia_pct) +
          " of the 2–5 km band. " + (top && top.aci !== top.vlce2 ? "The biggest disagreement: what the crop inventory calls <b>" + fmt.esc(grupo(d, top.aci).toLowerCase()) +
          "</b>, VLCE2 calls <b>" + fmt.esc(grupo(d, top.vlce2).toLowerCase()) + "</b> (" + fmt.ha(top.ha) + "). A forest map has no class for an orchard, so it files the rows of trees and grass between them under shrub and herb." : ""));
      },

      procedencia: function (ctx, d) {
        ctx.tiles({}); ctx.vetores({}); ctx.legendaMapa("");
        graf.tabela(ctx.$("#fig-procedencia"), {
          colunas: [{ rotulo: "Analysis" }, { rotulo: "Source (asset)" }, { rotulo: "Scale", n: true }, { rotulo: "Computed", n: true }],
          linhas: (d.procedencia || []).map(function (p) { return [fmt.esc(p.nome), '<code style="font-size:11px;overflow-wrap:anywhere">' + fmt.esc(p.dataset) + "</code>", p.escala_m ? p.escala_m + " m" : "—", fmt.data(p.calculado_em)]; }),
          nota: "Parcel fetched from ParcelMap BC on " + fmt.dataHora(d.parcela.consultado_em) + ". This table travels with the report and the spreadsheet."
        });
        ctx.texto("procedencia", "This parcel took " + (d.procedencia || []).length + " Earth Engine queries and one ParcelMap BC query, all from the run of " + fmt.dataHora(d.gerado_em) + ".");
      }
    }
  });
})();
