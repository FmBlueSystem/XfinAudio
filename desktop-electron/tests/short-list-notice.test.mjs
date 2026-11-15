import assert from 'node:assert/strict';
import test from 'node:test';
// The module imports only types from its neighbours, so it loads straight from the source.
import {
  SHORT_LIST_NO_CANDIDATES, SHORT_LIST_WITHOUT_GENRE, alternativeCardText, alternativeLabel, extendLabel,
  extendedLine, isShortListWarning, largerAlternative, shortListGenre, shortListOf, shortListTitle,
} from '../renderer/short-list-notice.ts';

const shortfall = (selected, requested) => `Track count shortfall: selected ${selected} of ${requested} requested tracks`;
const variants = (...items) => items.map(([name, trackCount]) => ({ name, description: `${name} del motor`, trackCount, readiness: 'ready', warnings: [], blockers: [], qualityScore: .8 }));

test('the engine shortfall warning is the only thing that counts as a short list', () => {
  assert.deepEqual(shortListOf([shortfall(4, 20)]), { selected: 4, requested: 20 });
  assert.deepEqual(shortListOf(['Excluded 2 incomplete track(s)', shortfall(4, 20), 'Filtered 3 track(s)']), { selected: 4, requested: 20 });
  assert.equal(shortListOf([]), null);
  assert.equal(shortListOf(undefined), null);
  assert.equal(shortListOf('not a list'), null);
  assert.equal(shortListOf([shortfall(4, 20).replace('selected', 'kept')]), null, 'only the exact engine text');
  assert.equal(shortListOf(['Track count shortfall: selected 4 of 20 requested tracks!']), null);
  assert.equal(shortListOf(['Se seleccionaron 4 de las 20 pistas solicitadas']), null, 'a translated line is not the engine text');
  assert.equal(isShortListWarning(shortfall(4, 20)), true);
  assert.equal(isShortListWarning(shortfall(4, 20).toUpperCase()), false);
  assert.equal(isShortListWarning('Excluded 2 incomplete track(s)'), false);
});

test('S3 copy is exact for the short list, its genre line and its three actions', () => {
  const fact = { selected: 4, requested: 20 };
  assert.equal(shortListTitle(fact), 'Salieron 4 de 20 pistas.');
  assert.equal(shortListTitle({ selected: 1, requested: 2 }), 'Salieron 1 de 2 pistas.');
  assert.equal(shortListGenre('Synth Pop & New Wave'), 'El género «Synth Pop & New Wave» y las reglas de mezcla dejaron pocas candidatas.');
  assert.equal(extendLabel(20), 'Ampliar a 20 pistas');
  assert.equal(alternativeLabel(20), 'Usar la alternativa de 20 pistas');
  assert.equal(SHORT_LIST_WITHOUT_GENRE, 'Generar sin género');
  assert.equal(SHORT_LIST_NO_CANDIDATES, 'No hay más pistas que mezclen con esta lista.');
});

test('the extension result line names the added tracks and only then the ones from other genres', () => {
  assert.equal(extendedLine({ requested: 16, added: 16, outsideGenre: 0 }), 'Se agregaron 16 pistas.');
  assert.equal(extendedLine({ requested: 16, added: 3, outsideGenre: 0 }), 'Se agregaron 3 pistas.');
  assert.equal(extendedLine({ requested: 16, added: 16, outsideGenre: 6 }), 'Se agregaron 16 pistas. 6 son de otros géneros.');
});

test('S6 names the alternative in the panel and keeps the plan order', () => {
  assert.equal(alternativeCardText('safe', 4), 'Usar la alternativa segura (4 pistas)');
  assert.equal(alternativeCardText('balanced', 20), 'Usar la alternativa equilibrada (20 pistas)');
  assert.equal(alternativeCardText('adventurous', 20), 'Usar la alternativa exploratoria (20 pistas)');
});

test('the alternative offered is the largest one other than the list on screen and longer than it', () => {
  const plan = variants(['safe', 4], ['balanced', 4], ['adventurous', 20]);
  assert.deepEqual(largerAlternative(plan, 'balanced', 4), { variant: 'adventurous', trackCount: 20 });
  assert.deepEqual(largerAlternative(variants(['safe', 6], ['balanced', 6], ['adventurous', 20]), 'adventurous', 4), { variant: 'safe', trackCount: 6 }, 'the largest of the others wins, and a tie keeps the plan order');
  assert.equal(largerAlternative(plan, 'balanced', 20), null, 'nothing is longer than the list itself');
  assert.equal(largerAlternative(plan, 'saved', 20), null);
  assert.equal(largerAlternative(undefined, 'balanced', 4), null);
  assert.equal(largerAlternative(null, 'balanced', 4), null);
  assert.equal(largerAlternative([], 'balanced', 0), null);
  assert.equal(largerAlternative(variants(['safe', 2]), 'safe', 0), null, 'the alternative on screen is never offered back');
});
