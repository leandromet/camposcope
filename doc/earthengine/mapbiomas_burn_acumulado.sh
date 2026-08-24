// ============================================================================
// MAPBIOMAS FOGO — ÁREA QUEIMADA ACUMULADA
// Coleção 5 | Brasil | Google Earth Engine
//
// Produto: Área queimada acumulada por período
// Fonte: MapBiomas Fogo
// ============================================================================


// ----------------------------------------------------------------------------
// PARÂMETROS DO USUÁRIO
// ----------------------------------------------------------------------------

// Altere o período de análise.
// Período disponível: 1985 a 2025.
var startYear = 1985;
var endYear = 2025;


// ----------------------------------------------------------------------------
// DADOS
// ----------------------------------------------------------------------------

var asset = 'projects/mapbiomas-public/assets/brazil/fire/collection5/' +
  'mapbiomas_fire_collection5_accumulated_burned_v1';

var accumulatedBurned = ee.Image(asset);

var burnedArea = accumulatedBurned
  .select('fire_accumulated_' + startYear + '_' + endYear)
  .selfMask();

var visParams = {
  min: 1,
  max: 1,
  palette: ['#FF0000']
};


// ----------------------------------------------------------------------------
// MAPA
// ----------------------------------------------------------------------------

Map.setCenter(-53, -14, 4);

Map.addLayer(
  burnedArea,
  visParams,
  'Área queimada acumulada — ' + startYear + ' a ' + endYear,
  true
);


// ----------------------------------------------------------------------------
// LEGENDA
// ----------------------------------------------------------------------------

var legend = ui.Panel({
  style: {position: 'bottom-right', padding: '8px 12px', width: '235px'}
});

var title = ui.Label({
  value: 'MapBiomas Fogo Col. 5',
  style: {fontWeight: 'bold', fontSize: '16px', margin: '0 0 4px 0'}
});

var subtitle = ui.Label({
  value: 'Área queimada acumulada',
  style: {fontSize: '12px', color: '#555555', margin: '0 0 2px 0'}
});

var period = ui.Label({
  value: 'Período: ' + startYear + ' a ' + endYear,
  style: {fontSize: '12px', color: '#555555', margin: '0 0 8px 0'}
});

var colorBox = ui.Label({
  style: {backgroundColor: '#FF0000', padding: '8px', margin: '0 8px 0 0'}
});

var label = ui.Label({
  value: 'Área queimada',
  style: {fontSize: '13px'}
});

var legendItem = ui.Panel({
  widgets: [colorBox, label],
  layout: ui.Panel.Layout.Flow('horizontal')
});

legend.add(title);
legend.add(subtitle);
legend.add(period);
legend.add(legendItem);

Map.add(legend);