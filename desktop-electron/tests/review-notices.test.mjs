import assert from 'node:assert/strict';
import test from 'node:test';
import { localizeReviewNotice } from '../renderer/workflow.ts';

// Every English text the core can put in a generated review, copied verbatim from
// src/xfinaudio/recommendation/{playlist_service,prep_copilot,scoring}.py with real values.
const notices = [
  // playlist_service.py
  ['Excluded 5 incomplete track(s)', 'Se excluyeron 5 pista(s) con metadatos incompletos'],
  ['Mandatory manual prefix exceeds the BPM ceiling; revise the manual order', 'El orden manual obligatorio supera el límite de salto de BPM; revisa el orden manual'],
  ['start_path ignored because manual order prefix is applied', 'Se ignoró la pista de apertura porque se aplica el orden manual'],
  ['same_vibe metadata unavailable; falling back to harmonic sequencing', 'No hay metadatos de ambiente para mismo ambiente; se vuelve a la secuencia armónica'],
  ['Arc target of 8 track(s) is shorter than the 10 manually ordered track(s); no generated tracks were added', 'El objetivo de arco de 8 pista(s) es menor que las 10 pistas en orden manual; no se añadieron pistas generadas'],
  ['Duration is unknown for one or more tracks; slot coverage cannot be verified', 'La duración de una o más pistas es desconocida; no se puede verificar la cobertura del hueco'],
  ['Duration shortfall: the selected playable tracks do not cover the requested slot', 'Faltan minutos: las pistas reproducibles seleccionadas no cubren el hueco solicitado'],
  ['Track count shortfall: selected 6 of 10 requested tracks', 'Se seleccionaron 6 de las 10 pistas solicitadas'],
  ["Genre 'Classical' left the set short: 4 track(s) for a slot that wants about 9", 'El género «Classical» dejó la lista corta: 4 pista(s) para un hueco de unas 9'],
  ['Filtered 3 track(s) outside chill energy range', 'Se filtraron 3 pista(s) fuera del rango de energía de chill'],
  ['Filtered 2 track(s) outside chill BPM range', 'Se filtraron 2 pista(s) fuera del rango de BPM de chill'],
  ['Filtered 4 track(s) outside loudness target band', 'Se filtraron 4 pista(s) fuera de la banda de sonoridad objetivo'],
  ['Loudness coverage 12 of 20 applied; 8 left in', 'Sonoridad medida en 12 de 20 pistas; 8 quedan dentro'],
  ['Mandatory control tracks are missing after playlist gates; no complete controlled set returned', 'Faltan pistas de control obligatorias después de los filtros de la lista; no se devolvió un conjunto controlado completo'],
  ['Mandatory controls exceed the requested track count; no tracks were silently discarded', 'Las pistas de control obligatorias superan el número de pistas solicitado; no se descartó ninguna pista en silencio'],
  ['same_genre filter applied: House', 'Filtro de mismo género aplicado: House'],
  ["same_genre: no candidates match anchor genre 'Techno'; falling back to unfiltered scoring", 'Mismo género: ninguna pista coincide con el género ancla «Techno»; se vuelve a la puntuación sin filtro'],
  ["No candidates in genre 'Trance'; showing every genre instead", 'No hay pistas del género «Trance»; se muestran todos los géneros'],
  ["Genre locked to 'House'", 'Género fijado en «House»'],
  ['same_color: anchor is missing a colour or spectral profile prerequisite; no generated candidates were produced', 'same_color: a la pista ancla le falta el requisito de color o perfil espectral; no se generaron candidatos'],
  ['same_color filter applied: red', 'Filtro de same_color aplicado: red'],
  ['same_color: strict colour eligibility excluded every generated candidate; returning only preserved controls without widening to unfiltered scoring', 'same_color: la elegibilidad estricta de color excluyó todos los candidatos generados; solo se devuelven los controles conservados, sin ampliar a la puntuación sin filtro'],
  ['same_color_energy: strict eligibility left 2 generated candidate(s) for 5 requested slot(s)', 'same_color_energy: la elegibilidad estricta dejó 2 candidato(s) generado(s) para 5 hueco(s) solicitado(s)'],
  ['Filtered 2 track(s) outside same_energy energy tolerance', 'Se filtraron 2 pista(s) fuera de la tolerancia de energía de same_energy'],
  // scoring.py transition explanations and warnings
  ['Harmonic compatibility score is 0.87', 'Compatibilidad armónica: 0.87'],
  ['BPM difference is 1.25%', 'Diferencia de BPM: 1.25%'],
  ['Energy level difference is 2', 'Diferencia de nivel de energía: 2'],
  ['Energy handoff (out→in) difference is -1', 'Salto de energía (salida→entrada): -1'],
  ['Energy boost 8A → 9A: a semitone up lifts the floor, but cut rather than blend — overlapping these keys clashes', 'Subida de energía 8A → 9A: subir medio tono levanta la pista, pero corta en vez de mezclar; superponer estas tonalidades choca'],
  ['Energy boost 8A → 9A: a whole step up lifts the floor, but cut rather than blend — overlapping these keys clashes', 'Subida de energía 8A → 9A: subir un tono completo levanta la pista, pero corta en vez de mezclar; superponer estas tonalidades choca'],
  ['Tag overlap is 2/3', 'Etiquetas en común: 2/3'],
  ['Spectral similarity is 0.75', 'Similitud espectral: 0.75'],
  ['Edge spectral similarity (out→in) is 0.62', 'Similitud espectral de los extremos (salida→entrada): 0.62'],
  ['Tonal compatibility is 0.5', 'Compatibilidad tonal: 0.5'],
  ['Danceability similarity is 0.71', 'Similitud de bailabilidad: 0.71'],
  ['Pitch/key normalization shifted left key from 8A to 8B', 'La normalización de tono/tonalidad movió la tonalidad izquierda de 8A a 8B'],
  ['Pitch/key normalization shifted right key from 8A to 8B', 'La normalización de tono/tonalidad movió la tonalidad derecha de 8A a 8B'],
  ['invalid Camelot key', 'Tonalidad Camelot inválida'],
  // prep_copilot.py
  ['Duration shortfall: the hard track count cap prevents this variant from covering the booked slot', 'Faltan minutos: el límite estricto de pistas impide que esta variante cubra el hueco reservado'],
  ['Incoming pool: 42 track(s)', 'Pistas de partida: 42'],
  ["Genre focus 'House': no match; full candidate pool retained", 'Enfoque de género «House»: sin coincidencias; se conserva todo el conjunto de candidatas'],
  ['adventurous variant may bridge outside genre focus: House', 'La variante exploratoria puede conectar fuera del enfoque de género: House'],
  ["No tracks match genre focus 'House'; keeping the full candidate pool", 'Ninguna pista coincide con el enfoque de género «House»; se conserva todo el conjunto de candidatas'],
  ['Genre focus: none set', 'Enfoque de género: sin definir'],
  ["Genre focus 'House': not applied (bridging allowed)", 'Enfoque de género «House»: no aplicado (se permiten conexiones)'],
  ["Genre focus 'House': 42 -> 18 track(s), 24 outside focus", 'Enfoque de género «House»: de 42 a 18 pista(s), 24 fuera del enfoque'],
  ["Genre focus 'House': matched all 18 track(s)", 'Enfoque de género «House»: coinciden las 18 pista(s)'],
  ['Genre focus matched only the anchor: kept 1 of 42 pool track(s) after all gates', 'El enfoque de género solo coincidió con la pista ancla: se conservaron 1 de 42 pista(s) tras todos los filtros'],
  ['Only the anchor survived the gates: kept 1 of 42 pool track(s)', 'Solo la pista ancla sobrevivió a los filtros: se conservaron 1 de 42 pista(s)'],
  ['3 required track(s) could not pass playlist gates', '3 pista(s) obligatoria(s) no pudieron pasar los filtros de la lista'],
  ['All required tracks are present in the playlist variant', 'Todas las pistas obligatorias están en la variante de la lista'],
  ['A required transition cannot satisfy the adjacent BPM gate', 'Una transición obligatoria no puede cumplir el filtro de BPM entre pistas vecinas'],
  ['Blocked — 2 blocker(s), 1 review item(s); required tracks missing', 'Bloqueada — 2 bloqueo(s), 1 aviso(s); faltan pistas obligatorias'],
  ['Strictest option: stays close to the requested genre focus and hard gates.', 'Opción más estricta: se mantiene cerca del enfoque de género solicitado y de los filtros estrictos.'],
  ['Middle option: allows tagged bridges while preserving the set intent.', 'Opción intermedia: permite conexiones entre géneros etiquetados y conserva la intención de la sesión.'],
  ['Exploratory option: allows broader bridges but keeps readiness checks visible.', 'Opción exploratoria: permite conexiones más amplias pero mantiene visibles las comprobaciones de preparación.'],
  // optimizer.py and candidate_pool.py (small fixes S3)
  ['Arc subset proven infeasible: mandatory path(s) not in the candidate pool: /m/a.mp3, /m/b.mp3', 'No hay una lista posible: hay pistas obligatorias fuera de las candidatas: /m/a.mp3, /m/b.mp3'],
  ['Arc subset proven infeasible: 5 mandatory paths exceed target length 4', 'No hay una lista posible: las 5 pistas obligatorias superan el largo pedido de 4'],
  ['Arc subset proven infeasible: one path cannot be both start and terminal for a multi-track target', 'No hay una lista posible: una misma pista no puede abrir y cerrar una lista de varias pistas'],
  ['Arc subset proven infeasible: no candidate is BPM-compatible with the required start seam', 'No hay una lista posible: ninguna candidata tiene un BPM compatible con la pista de apertura'],
  ['Arc subset proven infeasible: required end_path is unreachable within the available hops', 'No hay una lista posible: la pista de cierre no se alcanza con las pistas disponibles'],
  ['Arc subset proven infeasible: mandatory paths cannot coexist in one BPM-valid path: /m/a.mp3, /m/b.mp3', 'No hay una lista posible: estas pistas obligatorias no caben juntas sin saltos de BPM: /m/a.mp3, /m/b.mp3'],
  ['Arc subset proven infeasible: only 3 BPM-reachable candidates for target length 8', 'No hay una lista posible: solo 3 candidatas alcanzables por BPM para un largo de 8'],
  ['Arc subset proven infeasible: mandatory paths cannot satisfy the fixed-end hop budget', 'No hay una lista posible: las pistas obligatorias no llegan a la pista de cierre con el largo pedido'],
  ['Arc subset proven infeasible: only 6 candidates satisfy the fixed-end hop budget', 'No hay una lista posible: solo 6 candidatas llegan a la pista de cierre con el largo pedido'],
  ['Arc subset beam search budget exhausted without a full path; this is not proof that none exists', 'La búsqueda se detuvo sin encontrar una lista completa; eso no prueba que no exista'],
  ['Arc subset proven infeasible: no BPM-valid target-length path satisfies every mandatory control', 'No hay una lista posible: ninguna lista del largo pedido sin saltos de BPM cumple todos los controles obligatorios'],
  ['Start track "Song A" is incomplete or unavailable and will be ignored.', 'La pista de apertura «Song A» tiene datos incompletos o no está disponible; se ignorará.'],
  ['End track "Song B" is incomplete or unavailable and will be ignored.', 'La pista de cierre «Song B» tiene datos incompletos o no está disponible; se ignorará.'],
  ['2 manually-ordered track(s) are incomplete or unavailable and will be ignored.', '2 pista(s) del orden manual tienen datos incompletos o no están disponibles; se ignorarán.'],
];

for (const [english, spanish] of notices) {
  test(`review notice "${english}" is shown in Spanish`, () => {
    assert.equal(localizeReviewNotice(english), spanish);
  });
}

test('a notice that matches no pattern is shown unchanged', () => {
  for (const message of [
    'Some future English notice nobody translated yet',
    'Cambios espectrales: red→blue (2 veces)',
    'Se descartaron 2 pista(s) generada(s) porque el salto entre BPM vecinos superó el 3.0%',
    'Tonalidad Camelot inválida',
  ]) assert.equal(localizeReviewNotice(message), message);
});

test('Spanish notices and published numbers survive localization unchanged', () => {
  assert.equal(localizeReviewNotice('Se seleccionaron 3 de las 20 pistas solicitadas'), 'Se seleccionaron 3 de las 20 pistas solicitadas');
  assert.match(localizeReviewNotice('Track count shortfall: selected 3 of 20 requested tracks'), /3 de las 20/);
  assert.match(localizeReviewNotice('Filtered 12 track(s) outside chill energy range'), /^Se filtraron 12 pista\(s\)/);
});
