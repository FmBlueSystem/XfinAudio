import assert from 'node:assert/strict';
import test from 'node:test';
import { localizeStrategy } from '../renderer/strategy-labels.ts';

// English display name and description exactly as
// src/xfinaudio/recommendation/strategies.py publishes them for each stable name.
const strategies = [
  ['harmonic_journey', 'Harmonic Journey', 'Prioritize Camelot-compatible movement while keeping BPM and energy smooth.', 'Viaje armónico', 'Prioriza el movimiento compatible en Camelot manteniendo el BPM y la energía estables.'],
  ['warmup', 'Warmup', 'Start controlled with lower-to-mid energy tracks.', 'Calentamiento', 'Empieza controlado, con pistas de energía baja a media.'],
  ['build', 'Build', 'Prefer a gradually rising energy curve.', 'Construcción', 'Prefiere una curva de energía que sube poco a poco.'],
  ['peak_time', 'Peak Time', 'Focus the recommendation on high-energy records.', 'Hora punta', 'Centra la recomendación en pistas de energía alta.'],
  ['chill', 'Chill', 'Prefer lower energy and lower BPM selections.', 'Relax', 'Prefiere pistas de energía y BPM más bajos.'],
  ['same_energy', 'Same Energy', 'Hard limit: only tracks within ±1 energy level of the anchor. Color is weighted but not limited.', 'Misma energía', 'Límite estricto: solo pistas a ±1 nivel de energía de la pista ancla. El color se pondera pero no se limita.'],
  ['same_vibe', 'Same Vibe', 'Emphasize shared tags and genre when vibe metadata exists.', 'Mismo ambiente', 'Da prioridad a las etiquetas y al género compartidos cuando existen metadatos de ambiente.'],
  ['same_color', 'Same Color', "Hard filter: only tracks matching the anchor's spectral color. Energy is weighted but not limited.", 'Mismo color', 'Filtro estricto: solo pistas con el color espectral de la pista ancla. La energía se pondera pero no se limita.'],
  ['same_genre', 'Same Genre', 'Constrain the playlist to the dominant primary genre of the anchor tracks.', 'Mismo género', 'Limita la lista al género principal dominante de las pistas ancla.'],
  ['same_color_energy', 'Same Color & Energy', "Hard filters: only tracks matching the anchor's color AND the anchor's exact energy level.", 'Mismo color y energía', 'Filtros estrictos: solo pistas con el color de la pista ancla Y su nivel exacto de energía.'],
  ['consistent_loudness', 'Consistent Loudness', 'Hard filter: measured tracks must stay within the configured integrated loudness band.', 'Sonoridad constante', 'Filtro estricto: las pistas medidas deben quedar dentro de la banda de sonoridad integrada configurada.'],
];

for (const [name, displayName, description, label, esperado] of strategies) {
  test(`strategy ${name} shows its Spanish name and description`, () => {
    const localized = localizeStrategy({ name, displayName, description });
    assert.deepEqual(localized, { label, description: esperado });
    assert.doesNotMatch(`${localized.label} ${localized.description}`, /vibe/i);
  });
}

test('a strategy name the table does not know keeps the core text', () => {
  const unknown = { name: 'future_strategy', displayName: 'Future Strategy', description: 'Core English text.' };
  assert.deepEqual(localizeStrategy(unknown), { label: 'Future Strategy', description: 'Core English text.' });
  assert.deepEqual(localizeStrategy({ name: 'chill', displayName: '', description: '' }), { label: 'Relax', description: 'Prefiere pistas de energía y BPM más bajos.' });
});
