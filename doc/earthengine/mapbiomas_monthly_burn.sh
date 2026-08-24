// ============================================================================
// MAPBIOMAS FOGO — MÊS DA ÁREA QUEIMADA
// Coleção 5 | Brasil | Google Earth Engine
//
// Produto: Mês de ocorrência da área queimada
// Período disponível: 1985–2025
// Fonte: MapBiomas Fogo
// ============================================================================
// ----------------------------------------------------------------------------
// PARÂMETROS DO USUÁRIO
// ----------------------------------------------------------------------------
// Altere o ano para visualizar outra banda mensal.
// Anos disponíveis: 1985 a 2025.
var year = 2025;

// ----------------------------------------------------------------------------
// DADOS
// ----------------------------------------------------------------------------

var firePalettes = require(
  'users/workspaceipam/packages:mapbiomas-toolkit/utils/palettes'
);

var asset = 'projects/mapbiomas-public/assets/brazil/fire/collection5/' +
  'mapbiomas_fire_collection5_monthly_burned_v1';

var palette = firePalettes.get('mensal');

var monthlyBurned = ee.Image(asset);
var burnedMonth = monthlyBurned
  .select('burned_monthly_' + year)
  .selfMask();

var visParams = {
  min: 1,
  max: 12,
  palette: palette
};
// ----------------------------------------------------------------------------
// MAPA
// ----------------------------------------------------------------------------
Map.setCenter(-53, -14, 4);

Map.addLayer(
  burnedMonth,
  visParams,
  'Mês da área queimada — ' + year,
  true
);
// ----------------------------------------------------------------------------
// LEGENDA
// ----------------------------------------------------------------------------
var legend = ui.Panel({
  style: {position: 'bottom-right', padding: '8px 12px', width: '220px'}
});

var title = ui.Label({
  value: 'MapBiomas Fogo Col.5',
  style: {fontWeight: 'bold', fontSize: '16px', margin: '0 0 4px 0'}
});

var subtitle = ui.Label({
  value: 'Mês da área queimada — ' + year,
  style: {fontSize: '12px', color: '#555555', margin: '0 0 8px 0'}
});

legend.add(title);
legend.add(subtitle);

var months = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril',
  'Maio', 'Junho', 'Julho', 'Agosto',
  'Setembro', 'Outubro', 'Novembro', 'Dezembro'
];

months.forEach(function(month, index) {
  var colorBox = ui.Label({
    style: {
      backgroundColor: palette[index],
      padding: '7px',
      margin: '0 8px 3px 0'
    }
  });

  var label = ui.Label({
    value: month,
    style: {fontSize: '12px', margin: '0 0 3px 0'}
  });

  legend.add(ui.Panel({
    widgets: [colorBox, label],
    layout: ui.Panel.Layout.Flow('horizontal')
  }));
});

Map.add(legend);