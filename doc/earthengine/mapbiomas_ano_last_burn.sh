// ============================================================================
// MAPBIOMAS FOGO — ANO DO ÚLTIMO FOGO
// Coleção 5 | Brasil | Google Earth Engine
//
// Produto: Ano mais recente de ocorrência de fogo por pixel
// Fonte: MapBiomas Fogo
// ============================================================================
// ----------------------------------------------------------------------------
// PARÂMETROS DO USUÁRIO
// ----------------------------------------------------------------------------
// Banda de referência disponível no produto.
// A banda classification_2026 representa o último fogo registrado até 2025.
var referenceYear = 2026;

// ----------------------------------------------------------------------------
// DADOS
// ----------------------------------------------------------------------------
var firePalettes = require(
  'users/workspaceipam/packages:mapbiomas-toolkit/utils/palettes'
);

var asset = 'projects/mapbiomas-public/assets/brazil/fire/collection5/' +
  'mapbiomas_fire_collection5_year_last_fire_v1';

var palette = firePalettes.get('ano_do_ultimo_fogo');

var yearLastFire = ee.Image(asset)
  .select('classification_' + referenceYear)
  .selfMask();

var visParams = {
  min: 1985,
  max: referenceYear - 1,
  palette: palette
};
// ----------------------------------------------------------------------------
// MAPA
// ----------------------------------------------------------------------------
Map.setCenter(-53, -14, 4);

Map.addLayer(
  yearLastFire,
  visParams,
  'Ano do último fogo — até ' + (referenceYear - 1),
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
  value: 'Ano do último fogo',
  style: {fontSize: '12px', color: '#555555', margin: '0 0 2px 0'}
});

var period = ui.Label({
  value: 'Período: 1985 a ' + (referenceYear - 1),
  style: {fontSize: '12px', color: '#555555', margin: '0 0 8px 0'}
});

var colorBar = ui.Thumbnail({
  image: ee.Image.pixelLonLat().select('longitude'),
  params: {
    bbox: [0, 0, 1, 0.1],
    dimensions: '220x14',
    format: 'png',
    min: 0,
    max: 1,
    palette: palette
  },
  style: {stretch: 'horizontal', margin: '0 0 2px 0', maxHeight: '14px'}
});

var labels = ui.Panel({
  widgets: [
    ui.Label('1985', {fontSize: '11px', margin: '0'}),
    ui.Label(String(referenceYear - 1), {
      fontSize: '11px',
      margin: '0 0 0 auto',
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