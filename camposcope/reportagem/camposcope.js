/* Camposcope — demonstração em rolagem (/demonstracao).
 *
 * Os números vêm de /_demonstracao/camposcope.json (services/demonstracao.py),
 * montado pelos mesmos serviços da interface. Este arquivo só decide o que
 * cada passo mostra; nenhum valor é escrito à mão.
 */
(function () {
  var R = window.Reportagem, fmt = R.fmt, graf = R.graf;

  // cores de components/charts.py (HANSEN_PERIOD_COLOR) e dos anéis no mapa
  var PERIODO = {
    ate_2008: { cor: "#f5a524", rotulo: "Até 2008" },
    "2008_ate_registro": { cor: "#e5484d", rotulo: "2008 até o registro" },
    apos_registro: { cor: "#8b1a1a", rotulo: "Depois do registro" }
  };
  var COR_ZONA = { imovel: "#d98324", ring_500m: "#1f6f4a", ring_2km: "#4f8f6f", ring_5km: "#9cc2ac" };
  var CONTORNO = { color: "#ffd400", weight: 3, fillOpacity: 0 };

  function cod(ctx) { return ctx.params.get("car") || ""; }

  function zonaRot(d, k) { var z = d.zonas.filter(function (z) { return z.key === k; })[0]; return z ? z.label : k; }
  function imovelGeo(d) { return { type: "Feature", properties: {}, geometry: d.imovel.geometry }; }

  // classes presentes no imóvel num ano, maiores primeiro
  function classesNoAno(d, zona, i) {
    var h = d.historico, z = h.zonas[zona] || {};
    return Object.keys(z).map(function (c) { return { id: c, ha: z[c][i] || 0, nome: h.classes[c].nome, cor: h.classes[c].cor }; })
      .filter(function (x) { return x.ha > 0; }).sort(function (a, b) { return b.ha - a.ha; });
  }
  function legendaClasses(d, ano, zona) {
    var i = d.historico.anos.indexOf(ano); if (i < 0) return "";
    return "<b>MapBiomas " + ano + " · classes no imóvel</b>" + classesNoAno(d, zona || "imovel", i).slice(0, 6).map(function (c) {
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
  function faltou(el, nome) { el.innerHTML = '<p class="rp-fig-estado erro">' + nome + " não respondeu nesta visita <span class=\"selo ausente\">ausente</span></p>"; }

  R.iniciar({
    dados: function (ctx) { var c = cod(ctx); return "/_demonstracao/camposcope.json" + (c ? "?car=" + encodeURIComponent(c) : ""); },
    centro: [-12.5, -55.5], zoom: 5,

    aoCarregar: function (ctx, d) {
      var im = d.imovel, h = d.historico;
      var ultimo = h ? h.anos[h.anos.length - 1] : null;
      var top = h ? classesNoAno(d, "imovel", h.anos.length - 1)[0] : null;
      var tot = h ? classesNoAno(d, "imovel", h.anos.length - 1).reduce(function (a, c) { return a + c.ha; }, 0) : 0;
      var perda = d.hansen ? (d.hansen.perda.imovel || []).reduce(function (a, x) { return a + x.ha; }, 0) : null;
      ctx.preencher({
        "n-declarada": fmt.ha(im.area_declarada_ha),
        "n-calculada": fmt.ha(im.area_calculada_ha),
        "n-uso": top ? fmt.pct((100 * top.ha) / tot) : "—",
        "n-uso-rot": top ? fmt.esc(top.nome) + " em " + ultimo + ' <span class="selo real">real</span>' : "maior uso no último ano",
        "n-perda": perda === null ? "—" : fmt.ha(perda)
      });
      ctx.$("#topo-exemplo").textContent = im.cod_imovel + " · " + im.municipio + "/" + im.uf;
      var app = "/?car=" + encodeURIComponent(im.cod_imovel);
      ctx.$("#link-app").href = app; ctx.$("#cta-app").href = app;
      ctx.$("#rp-fig-url").textContent = "camposcope.umaterra.com.br/?car=" + im.cod_imovel;
      ctx.$("#abertura-exemplo").innerHTML = (d.exemplo_padrao ? "Exemplo desta página: " : "Imóvel escolhido: ") +
        "<b>" + fmt.esc(im.municipio) + "/" + fmt.esc(im.uf) + "</b>, código <code>" + fmt.esc(im.cod_imovel) + "</code>, " +
        "calculado pelos serviços do aplicativo em " + fmt.dataHora(d.gerado_em) + (d.exemplo_padrao ? " e guardado com esta página." : " (o resultado fica guardado por algumas horas).");
      var erros = Object.keys(d.erros || {});
      ctx.$("#fim-extra").innerHTML = erros.length
        ? "Neste cálculo não responderam: <b>" + erros.map(fmt.esc).join(", ") + "</b>. Os passos correspondentes dizem o que faltou."
        : "Todas as análises responderam no cálculo de " + fmt.dataHora(d.gerado_em) + ".";

      // textos com os números deste imóvel
      ctx.texto("busca", "Aqui, o código <code>" + fmt.esc(im.cod_imovel) + "</code> leva à camada <b>sicar_imoveis_" + im.uf.toLowerCase() +
        "</b>, que devolve um polígono em " + fmt.esc(im.municipio) + ". Em amarelo, a divisa; ao fundo, em transparência, os outros imóveis do estado.");
      var ov = sobrepostos(d);
      var dif = im.area_calculada_ha - im.area_declarada_ha;
      ctx.texto("declarado", "Este imóvel declara <b>" + fmt.ha(im.area_declarada_ha) + "</b>; o polígono mede <b>" + fmt.ha(im.area_calculada_ha) +
        "</b> (" + fmt.sinal(dif, 2) + " ha). Condição: <i>" + fmt.esc(im.condicao || "não informada") + "</i>. " +
        (ov.length ? "Há <b>" + ov.length + " registro" + (ov.length > 1 ? "s" : "") + " sobreposto" + (ov.length > 1 ? "s" : "") + "</b> a ele, em tracejado no mapa." : "Nenhum outro registro se sobrepõe a ele."));
      var z = d.zonas;
      ctx.texto("zonas", "Para um imóvel de " + fmt.ha(z[0].area_ha) + ", os anéis somam " + z.slice(1).map(function (x) { return "<b>" + fmt.ha(x.area_ha) + "</b>"; }).join(", ") +
        ". O anel de fora é " + fmt.n(z[3] ? z[3].area_ha / z[0].area_ha : 0, 0) + " vezes o imóvel: a vizinhança pesa mais que o próprio imóvel em qualquer média.");
    },

    passos: {
      busca: function (ctx, d) {
        var im = d.imovel;
        ctx.tiles({ sicar: camada(d, "sicar") });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("<b>Imóvel do CAR</b><span><i style=\"background:#ffd400\"></i>divisa declarada</span><span><i style=\"background:#e8a04a\"></i>outros imóveis (WMS do SICAR)</span>");
        ctx.$("#fig-busca").innerHTML = '<dl class="rp-ficha"><dt>Código</dt><dd><code>' + fmt.esc(im.cod_imovel) + "</code></dd>" +
          "<dt>Camada</dt><dd>sicar:sicar_imoveis_" + im.uf.toLowerCase() + "</dd><dt>Município</dt><dd>" + fmt.esc(im.municipio) + "/" + fmt.esc(im.uf) + "</dd></dl>";
      },

      declarado: function (ctx, d) {
        var im = d.imovel, ov = sobrepostos(d);
        ctx.tiles({});
        var vet = { imovel: { geojson: imovelGeo(d), estilo: CONTORNO } };
        if (ov.length) vet.sobrepostos = {
          geojson: { type: "FeatureCollection", features: ov.map(function (o) { return { type: "Feature", properties: { cod: o.cod_imovel, ha: o.overlap_ha }, geometry: o.geometry }; }) },
          estilo: { color: "#ff4fd8", weight: 2, dashArray: "6 5", fillOpacity: 0.06 },
          popup: function (f) { return fmt.esc(f.properties.cod) + "<br>sobreposição: " + fmt.ha(f.properties.ha); }
        };
        ctx.vetores(vet);
        ctx.enquadrar(ov.length ? vet.sobrepostos.geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<span><i style="background:#ffd400"></i>este imóvel</span>' + (ov.length ? '<span><i style="background:#ff4fd8"></i>registros sobrepostos</span>' : ""));
        var h = '<div class="rp-dupla"><div><div class="rp-caixa-tit">Campos do SICAR, como vieram <span class="selo declarado">declarado</span></div><dl class="rp-ficha">' +
          "<dt>Área declarada</dt><dd class=\"declarado\">" + fmt.ha(im.area_declarada_ha) + "</dd>" +
          "<dt>Módulos fiscais</dt><dd class=\"declarado\">" + fmt.n(im.m_fiscal, 2) + "</dd>" +
          "<dt>Tipo</dt><dd>" + fmt.esc(im.tipo_imovel) + "</dd><dt>Status</dt><dd>" + fmt.esc(im.status_imovel) + "</dd>" +
          "<dt>Condição</dt><dd>" + fmt.esc(im.condicao || "não informada") + "</dd>" +
          "<dt>Inscrito em</dt><dd>" + fmt.data(im.dat_criacao) + "</dd><dt>Atualizado em</dt><dd>" + (im.data_atualizacao ? fmt.data(im.data_atualizacao) : "não informada") + "</dd></dl></div>" +
          '<div><div class="rp-caixa-tit">Calculado aqui <span class="selo real">real</span></div><dl class="rp-ficha"><dt>Área do polígono</dt><dd>' + fmt.ha(im.area_calculada_ha) + "</dd>" +
          "<dt>Diferença</dt><dd>" + fmt.sinal(im.area_calculada_ha - im.area_declarada_ha, 2) + " ha (" + fmt.sinal(100 * (im.area_calculada_ha - im.area_declarada_ha) / im.area_declarada_ha, 1) + "%)</dd></dl>";
        if (ov.length) {
          h += '<div class="rp-caixa-tit" style="margin-top:10px">Registros sobrepostos</div>';
          h += ov.slice(0, 6).map(function (o) {
            return '<div style="font-size:12.5px;padding:3px 0;border-top:1px solid #eef2ef"><code>' + fmt.esc(o.cod_imovel.slice(0, 18)) + "…</code><br>" +
              fmt.ha(o.overlap_ha) + " em comum (" + fmt.pct(o.overlap_pct_do_imovel, 1) + " deste imóvel) · declara " + fmt.ha(o.area_declarada_ha) + "</div>";
          }).join("") + (ov.length > 6 ? '<div style="font-size:12px;color:#7b8a83">e mais ' + (ov.length - 6) + "</div>" : "");
        }
        ctx.$("#fig-declarado").innerHTML = h + "</div></div>";
      },

      zonas: function (ctx, d) {
        ctx.tiles({});
        var aneis = d.zonas.slice(1).map(function (z) { return { type: "Feature", properties: { key: z.key, label: z.label }, geometry: z.geojson.geometry || z.geojson }; });
        ctx.vetores({
          aneis: { geojson: { type: "FeatureCollection", features: aneis }, estilo: function (f) { return { color: COR_ZONA[f.properties.key], weight: 2, dashArray: "5 4", fillColor: COR_ZONA[f.properties.key], fillOpacity: 0.12 }; } },
          imovel: { geojson: imovelGeo(d), estilo: CONTORNO }
        });
        ctx.enquadrar(aneis[aneis.length - 1], { maxZoom: 13 });
        ctx.legendaMapa(d.zonas.map(function (z) { return '<span><i style="background:' + (z.key === "imovel" ? "#ffd400" : COR_ZONA[z.key]) + '"></i>' + fmt.esc(z.label) + "</span>"; }).join(""));
        graf.tabela(ctx.$("#fig-zonas"), {
          colunas: [{ rotulo: "Zona" }, { rotulo: "Área", n: true }, { rotulo: "× imóvel", n: true }],
          linhas: d.zonas.map(function (z) { return [graf.qd(z.key === "imovel" ? "#ffd400" : COR_ZONA[z.key]) + fmt.esc(z.label), fmt.ha(z.area_ha), fmt.n(z.area_ha / d.zonas[0].area_ha, 1)]; })
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
        var series = Object.keys(h.zonas.imovel).map(function (c) { return { rotulo: h.classes[c].nome, cor: h.classes[c].cor, valores: h.zonas.imovel[c] }; })
          .sort(function (a, b) { return b.valores[b.valores.length - 1] - a.valores[a.valores.length - 1]; });
        var reg = d.imovel.ano_criacao;
        graf.empilhado(el, { anos: h.anos, series: series, unidade: "ha", marcas: reg ? [{ ano: reg, rotulo: "inscrição no CAR (" + reg + ")" }] : [], rotulo: "Cobertura do imóvel por ano" });
        // a história em palavras: maior classe no início, no registro e no fim, e quando ela trocou
        var c0 = classesNoAno(d, "imovel", 0)[0], cf = classesNoAno(d, "imovel", h.anos.length - 1)[0], troca = null;
        for (var i = 1; i < h.anos.length; i++) { var ci = classesNoAno(d, "imovel", i)[0]; if (ci && c0 && ci.id !== c0.id) { troca = { ano: h.anos[i], c: ci }; break; } }
        var t = "Em " + h.anos[0] + ", a maior classe do imóvel era <b>" + fmt.esc(c0 ? c0.nome : "—") + "</b> (" + fmt.ha(c0 && c0.ha) + "). ";
        if (troca) t += "Em <b>" + troca.ano + "</b> ela deixa de ser a maior, ultrapassada por <b>" + fmt.esc(troca.c.nome) + "</b>. ";
        t += "Em " + ultimo + ", a maior é <b>" + fmt.esc(cf ? cf.nome : "—") + "</b>, com " + fmt.ha(cf && cf.ha) + ".";
        if (reg) { var ir = h.anos.indexOf(reg), cr = ir >= 0 ? classesNoAno(d, "imovel", ir)[0] : null; if (cr) t += " Na inscrição no CAR, em " + reg + ", já era <b>" + fmt.esc(cr.nome) + "</b>."; }
        ctx.texto("cobertura", t);
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
        ctx.legendaMapa(legendaClasses(d, h.anos[0], "ring_5km").replace("no imóvel", "até 5 km"));
        var series = d.zonas.map(function (z) { return { rotulo: z.label, cor: COR_ZONA[z.key], valores: nativaPct(d, z.key), espessura: z.key === "imovel" ? 3 : 2 }; });
        graf.linhas(el, { x: h.anos, series: series, unidade: "% de vegetação nativa", min: 0, max: 100, marcas: d.imovel.ano_criacao ? [{ x: d.imovel.ano_criacao, rotulo: "CAR" }] : [] });
        var p = series[0].valores, a = series[series.length - 1].valores, n = p.length - 1;
        ctx.texto("vizinhanca", "No imóvel, a vegetação nativa vai de <b>" + fmt.pct(p[0]) + "</b> em " + h.anos[0] + " para <b>" + fmt.pct(p[n]) + "</b> em " + h.anos[n] +
          ". No anel de 2 a 5 km, de " + fmt.pct(a[0]) + " para " + fmt.pct(a[n]) + ". " +
          (Math.abs((p[0] - p[n]) - (a[0] - a[n])) < 10 ? "As duas curvas caem juntas: a conversão foi da região, não só deste imóvel." : "As curvas se separam: o imóvel seguiu um caminho diferente do da vizinhança."));
      },

      transicoes: function (ctx, d) {
        var el = ctx.$("#fig-transicoes"), T = d.transicoes, h = d.historico;
        if (!T || !h) return faltou(el, "As transições");
        ctx.tiles({ mb: camada(d, "mb_" + T.ano_b, 0.8) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("");
        var fl = T.zonas.imovel || [], ids = {};
        fl.forEach(function (f) { ids[f.de] = 1; ids[f.para] = 1; });
        var nos = Object.keys(ids).map(function (c) { var k = h.classes[c] || { nome: "classe " + c, cor: "#9aa8a1" }; return { id: Number(c), rotulo: k.nome, cor: k.cor }; });
        graf.sankey(el, { esq: nos, dir: nos, fluxos: fl.map(function (f) { return { de: f.de, para: f.para, valor: f.ha }; }), rotuloEsq: String(T.ano_a), rotuloDir: String(T.ano_b), rotulo: "Transições" });
        var mud = fl.filter(function (f) { return f.de !== f.para; }).sort(function (a, b) { return b.ha - a.ha; });
        var tot = fl.reduce(function (a, f) { return a + f.ha; }, 0), mudou = mud.reduce(function (a, f) { return a + f.ha; }, 0);
        ctx.texto("transicoes", "Entre " + T.ano_a + " e " + T.ano_b + ", <b>" + fmt.ha(mudou) + "</b> do imóvel (" + fmt.pct(100 * mudou / tot) + ") mudaram de classe. " +
          (mud.length ? "O maior fluxo foi de <b>" + fmt.esc((h.classes[mud[0].de] || {}).nome) + "</b> para <b>" + fmt.esc((h.classes[mud[0].para] || {}).nome) + "</b>: " + fmt.ha(mud[0].ha) + "." : ""));
      },

      floresta: function (ctx, d) {
        var el = ctx.$("#fig-floresta"), H = d.hansen;
        if (!H) return faltou(el, "O Hansen/GLAD");
        ctx.tiles({ hansen: camada(d, "hansen_2008", 0.9) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<b>Hansen/GLAD</b><span><i style="background:#d4271e"></i>perda desde 2008</span><span><i style="background:#02d659"></i>ganho (sem data)</span>');
        var por = {}, fim = 2024;
        Object.keys(H.perda).forEach(function (z) { H.perda[z].forEach(function (x) { if (x.ano > fim) fim = x.ano; }); });
        (H.perda.imovel || []).forEach(function (x) { por[x.ano] = x; });
        var anos = []; for (var a = 2001; a <= fim; a++) anos.push(a);
        var reg = d.imovel.ano_criacao;
        graf.colunas(el, {
          x: anos.map(String), valores: anos.map(function (a) { return por[a] ? por[a].ha : 0; }), unidade: "ha de perda por ano",
          cor: function (rot) { var x = por[Number(rot)]; return x ? PERIODO[x.periodo].cor : "#ccc"; },
          marcas: [{ x: "2008", rotulo: "2008" }].concat(reg && reg > 2001 ? [{ x: String(reg), rotulo: "CAR " + reg }] : []),
          legenda: Object.keys(PERIODO).map(function (k) { return { rotulo: PERIODO[k].rotulo, cor: PERIODO[k].cor }; })
        });
        var soma = {}; (H.perda.imovel || []).forEach(function (x) { soma[x.periodo] = (soma[x.periodo] || 0) + x.ha; });
        ctx.texto("floresta", "Neste imóvel, com o limiar de " + H.limiar_pct + "% de copa: <b>" + fmt.ha(soma.ate_2008 || 0) + "</b> perdidos até 2008, <b>" +
          fmt.ha(soma["2008_ate_registro"] || 0) + "</b> entre 2008 e a inscrição" + (reg ? " (" + reg + ")" : "") + " e <b>" + fmt.ha(soma.apos_registro || 0) +
          "</b> depois dela. Ganho registrado: " + fmt.ha(H.ganho_ha) + ".");
      },

      biomassa: function (ctx, d) {
        var el = ctx.$("#fig-biomassa"), B = d.biomassa;
        if (!B) return faltou(el, "O ESA CCI");
        ctx.tiles({ bio: camada(d, "biomassa", 0.75) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<b>ESA CCI · biomassa acima do solo</b><span><i class="g" style="background:linear-gradient(90deg,#fff,#008000)"></i>0 → 500 Mg/ha</span>');
        var anos = (B.imovel || []).map(function (x) { return x.ano; });
        graf.linhas(el, {
          x: anos.map(String), unidade: "Mg/ha", min: 0,
          series: d.zonas.filter(function (z) { return B[z.key]; }).map(function (z) {
            var m = {}; B[z.key].forEach(function (x) { m[x.ano] = x.mgha; });
            return { rotulo: z.label, cor: COR_ZONA[z.key], valores: anos.map(function (a) { return m[a]; }), pontos: true, espessura: z.key === "imovel" ? 3 : 2 };
          })
        });
        var p = B.imovel || [];
        if (p.length) ctx.texto("biomassa", "No imóvel, a média vai de <b>" + fmt.n(p[0].mgha) + " Mg/ha</b> em " + p[0].ano + " para <b>" + fmt.n(p[p.length - 1].mgha) +
          " Mg/ha</b> em " + p[p.length - 1].ano + ". Repare como a série oscila de um ano para o outro sem que a cobertura mude: é o erro do produto, não a floresta.");
      },

      fogo: function (ctx, d) {
        var el = ctx.$("#fig-fogo"), F = d.fogo;
        if (!F) return faltou(el, "O MapBiomas Fogo");
        ctx.tiles({ fogo: camada(d, "fogo", 0.85) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa('<b>MapBiomas Fogo · vezes que queimou</b><span><i class="g" style="background:linear-gradient(90deg,#ffffb2,#fd8d3c,#bd0026,#800026)"></i>1 → muitas</span>');
        var an = F.anual.imovel || [];
        graf.colunas(el, { x: an.map(function (x) { return String(x.ano); }), valores: an.map(function (x) { return x.pct; }), unidade: "% do imóvel queimado no ano", cor: "#d9480f" });
        var r = F.resumo.imovel || {}, pior = an.slice().sort(function (a, b) { return b.pct - a.pct; })[0];
        var anosFogo = an.filter(function (x) { return x.pct > 0; }).length;
        ctx.texto("fogo", anosFogo ? "O imóvel teve fogo em <b>" + anosFogo + " dos " + an.length + " anos</b>. O pior foi <b>" + pior.ano + "</b>, com " + fmt.pct(pior.pct) +
          " da área queimada. A última queimada registrada no imóvel é de <b>" + (r.ultimo_ano || "—") + "</b>." : "Nenhuma cicatriz de fogo foi mapeada no imóvel desde 1985.");
      },

      spot: function (ctx, d) {
        var el = ctx.$("#fig-spot"), S = d.spot;
        ctx.tiles({ spot: camada(d, "spot", 1) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(imovelGeo(d), { maxZoom: 15 });
        ctx.legendaMapa("<b>SPOT 2008 · cor natural</b>");
        if (!S) return faltou(el, "O mosaico SPOT");
        el.innerHTML = '<div class="rp-cartoes">' +
          '<div class="rp-cartao"><b>' + fmt.pct(S.covered_pct) + "</b><small>do imóvel coberto pelo mosaico</small></div>" +
          '<div class="rp-cartao"><b>' + fmt.data(S.date_min) + "</b><small>pixel mais antigo</small></div>" +
          '<div class="rp-cartao"><b>' + fmt.data(S.date_max) + "</b><small>pixel mais recente</small></div>" +
          '<div class="rp-cartao"><b>' + fmt.pct(S.pre_cutoff_pct) + "</b><small>tomado antes de 22/07/2008</small></div></div>" +
          '<p class="rp-fig-legenda">' + fmt.esc(S.note_pt || "") + "</p>";
        ctx.texto("spot", S.has_coverage
          ? "Sob este imóvel, as imagens são de <b>" + fmt.data(S.date_min) + "</b> a <b>" + fmt.data(S.date_max) + "</b>, e " + fmt.pct(S.pre_cutoff_pct) + " delas foram tomadas antes do corte. " +
            (S.pre_cutoff_pct >= 99 ? "Aqui, a imagem serve de referência para a data." : "Uma parte foi tomada depois do corte e não mostra 22 de julho de 2008.")
          : "O mosaico não cobre este imóvel: não há imagem de 2008 para ele.");
      },

      validacao: function (ctx, d) {
        var el = ctx.$("#fig-validacao"), I = d.ibge;
        ctx.tiles({ ibge: camada(d, "ibge", 0.8) });
        ctx.vetores({ imovel: { geojson: imovelGeo(d), estilo: CONTORNO } });
        ctx.enquadrar(d.zonas[2] ? d.zonas[2].geojson : imovelGeo(d), { maxZoom: 14 });
        ctx.legendaMapa("<b>IBGE · vegetação 2022, rasterizada</b>54 classes, com a paleta do aplicativo");
        if (!I) return faltou(el, "O mapa do IBGE");
        var g = I.groups.filter(function (k) { return I.groups.some(function (m) { return (I.matrix[k] || {})[m] > 0.05 || (I.matrix[m] || {})[k] > 0.05; }); });
        graf.tabela(el, {
          colunas: [{ rotulo: "IBGE ↓ · MapBiomas →" }].concat(g.map(function (k) { return { rotulo: I.group_labels[k].replace("Antrópico — ", "").replace("Natural — ", ""), n: true }; })),
          linhas: g.map(function (k) { return [fmt.esc(I.group_labels[k])].concat(g.map(function (m) { var v = (I.matrix[k] || {})[m] || 0; return v > 0.05 ? (k === m ? "<b>" + fmt.pct(v, 1) + "</b>" : fmt.pct(v, 1)) : "·"; })); }),
          nota: "Parte do imóvel em cada par de classes. A diagonal, em negrito, é onde os dois mapas concordam."
        });
        ctx.texto("validacao", "Neste imóvel, o IBGE chama de floresta natural <b>" + fmt.pct(I.forest_ibge, 1) + "</b> da área; o MapBiomas, <b>" + fmt.pct(I.forest_mb, 1) +
          "</b>. " + (I.forest_ibge - I.forest_mb > 5 ? "A diferença é o que o IBGE ainda desenha como floresta e o MapBiomas já classifica como uso agropecuário." : "Aqui os dois mapas quase concordam."));
      },

      procedencia: function (ctx, d) {
        ctx.tiles({}); ctx.vetores({}); ctx.legendaMapa("");
        graf.tabela(ctx.$("#fig-procedencia"), {
          colunas: [{ rotulo: "Análise" }, { rotulo: "Fonte (asset)" }, { rotulo: "Escala", n: true }, { rotulo: "Calculado", n: true }],
          linhas: (d.procedencia || []).map(function (p) { return [fmt.esc(p.nome), "<code style=\"font-size:11px;overflow-wrap:anywhere\">" + fmt.esc(p.dataset) + "</code>", p.escala_m ? p.escala_m + " m" : "—", fmt.data(p.calculado_em)]; }),
          nota: "Imóvel consultado no SICAR em " + fmt.dataHora(d.imovel.consultado_em) + ". Esta tabela vai junto no relatório e na planilha."
        });
        ctx.texto("procedencia", "Para este imóvel foram " + (d.procedencia || []).length + " consultas ao Earth Engine e uma ao SICAR, todas do cálculo de " + fmt.dataHora(d.gerado_em) + ".");
      }
    }
  });
})();
