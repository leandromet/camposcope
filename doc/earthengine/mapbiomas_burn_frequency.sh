// ============================================================================
// MAPBIOMAS FOGO — FREQUÊNCIA DE ÁREA QUEIMADA
// Coleção 5 | Brasil | Google Earth Engine
//
// Produto: Número de vezes que cada pixel foi queimado no período
// Fonte: MapBiomas Fogo
// ============================================================================
// ----------------------------------------------------------------------------
// PARÂMETROS DO USUÁRIO
// ----------------------------------------------------------------------------
// Altere o período conforme as bandas disponíveis no asset.
var startYear = 1985;
var endYear = 2025;
// ----------------------------------------------------------------------------
// DADOS
// ----------------------------------------------------------------------------

var firePalettes = require(
  'users/workspaceipam/packages:mapbiomas-toolkit/utils/palettes'
);

var asset = 'projects/mapbiomas-public/assets/brazil/fire/collection5/' +
  'mapbiomas_fire_collection5_fire_frequency_v1';

var fireFrequency = ee.Image(asset);

var frequency = fireFrequency
  .select('fire_frequency_' + startYear + '_' + endYear)
  .selfMask();

var maxFrequency = endYear - startYear + 1;

var visParams = {
  min: 1,
  max: maxFrequency,
  palette: firePalettes.get('frequencia')
};
// ----------------------------------------------------------------------------
// MAPA
// ----------------------------------------------------------------------------
Map.setCenter(-53, -14, 4);

Map.addLayer(
  frequency,
  visParams,
  'Frequência de área queimada — ' + startYear + ' a ' + endYear,
  true
);
// ----------------------------------------------------------------------------
// LEGENDA
// ----------------------------------------------------------------------------
var legend = ui.Panel({
  style: {position: 'bottom-right', padding: '8px 12px', width: '250px'}
});

var title = ui.Label({
  value: 'MapBiomas Fogo Col. 5',
  style: {fontWeight: 'bold', fontSize: '16px', margin: '0 0 4px 0'}
});

var subtitle = ui.Label({
  value: 'Frequência de área queimada',
  style: {fontSize: '12px', color: '#555555', margin: '0 0 2px 0'}
});

var period = ui.Label({
  value: 'Período: ' + startYear + ' a ' + endYear,
  style: {fontSize: '12px', color: '#555555', margin: '0 0 8px 0'}
});

var colorBar = ui.Thumbnail({
  image: ee.Image.pixelLonLat().select(0),
  params: {
    bbox: [0, 0, 1, 0.1],
    dimensions: '220x14',
    format: 'png',
    min: 0,
    max: 1,
    palette: firePalettes.get('frequencia')
  },
  style: {stretch: 'horizontal', margin: '0 0 2px 0', maxHeight: '14px'}
});

var labels = ui.Panel({
  widgets: [
    ui.Label('1 vez', {margin: '0 0 0 0', fontSize: '11px'}),
    ui.Label(maxFrequency + ' vezes', {
      margin: '0 0 0 auto',
      fontSize: '11px',
      textAlign: 'right'
    })
  ],
  layout: ui.Panel.Layout.Flow('horizontal')
});

legend.add(title);
legend.add(subtitle);
legend.add(period);
legend.add(colorBar);
legend.add(labels);

Map.add(legend);