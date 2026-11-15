import assert from 'node:assert/strict';
import test from 'node:test';
import {
  GOOD_TRANSITION_MIN, WEAK_TRANSITION_BELOW, pendingReviewChecks, reviewFix, transitionQuality, transitionScoresOf,
} from '../renderer/review-facts.ts';

test('transition quality reuses the readiness average-score threshold and labels each band', () => {
  assert.equal(GOOD_TRANSITION_MIN, 0.65, 'the readiness check «Puntuación media de transición» gates at 0.65');
  assert.equal(WEAK_TRANSITION_BELOW, 0.5);
  assert.deepEqual(transitionQuality(1), { label: 'Buena', tone: 'good', text: 'Buena · 100 %' });
  assert.deepEqual(transitionQuality(0.65), { label: 'Buena', tone: 'good', text: 'Buena · 65 %' });
  assert.deepEqual(transitionQuality(0.649), { label: 'Regular', tone: 'fair', text: 'Regular · 65 %' });
  assert.deepEqual(transitionQuality(0.5), { label: 'Regular', tone: 'fair', text: 'Regular · 50 %' });
  assert.deepEqual(transitionQuality(0.42), { label: 'Débil', tone: 'weak', text: 'Débil · 42 %' });
  assert.deepEqual(transitionQuality(0), { label: 'Débil', tone: 'weak', text: 'Débil · 0 %' });
});

test('transition scores are read only from a payload that carries all of them', () => {
  assert.deepEqual(transitionScoresOf({ transitionScores: [0.8, 0.42] }), [0.8, 0.42]);
  for (const value of [null, {}, { transitionScores: undefined }, { transitionScores: [] }, { transitionScores: 'x' }, { transitionScores: [0.8, null] }, { transitionScores: [0.8, 'x'] }]) {
    assert.equal(transitionScoresOf(value), null, `no column for ${JSON.stringify(value)}`);
  }
});

test('every readiness label keeps its own fix and an unknown label shows only its detail', () => {
  const fix = (label) => reviewFix({ label, status: 'needs_review', detail: 'detalle' });
  assert.deepEqual(fix('Metadatos requeridos'), { label: 'Metadatos requeridos', detail: 'detalle', fix: null, action: 'metadata' });
  for (const label of ['Continuidad de BPM', 'Continuidad de energía', 'Avisos de transición', 'Puntuación media de transición']) {
    assert.equal(fix(label).fix, 'Mira la columna Mezcla: reemplaza o mueve una pista de las transiciones débiles.', label);
  }
  assert.equal(fix('Pistas repetidas').fix, 'Reemplaza una de las pistas repetidas.');
  for (const label of ['Tamaño de la lista', 'Pistas obligatorias']) {
    assert.equal(fix(label).fix, 'Vuelve a generar con otra cantidad o con otras pistas obligatorias.', label);
  }
  assert.deepEqual(fix('Verificación Serato'), { label: 'Verificación Serato', detail: 'detalle', fix: null, action: null });
  assert.deepEqual(fix('Metadatos requeridos').fix, null, 'the metadata fix is a button, not a sentence');
});

test('only checks that are not ready are pending, in core order, and a fieldless payload has none', () => {
  const checks = [
    { label: 'Metadatos requeridos', status: 'ready', detail: 'Todo completo' },
    { label: 'Continuidad de BPM', status: 'needs_review', detail: 'Salto 7.50%' },
    { label: 'Pistas repetidas', status: 'blocked', detail: 'Dos grupos' },
  ];
  assert.deepEqual(pendingReviewChecks({ readinessChecks: checks }).map((check) => check.label), ['Continuidad de BPM', 'Pistas repetidas']);
  assert.deepEqual(pendingReviewChecks({ readinessChecks: [{ label: 'Pistas repetidas', status: 'ready', detail: 'x' }] }), []);
  for (const value of [null, {}, { readinessChecks: undefined }, { readinessChecks: [] }, { readinessChecks: 'x' }, { readinessChecks: [{ label: 'x' }] }, { readinessChecks: [null] }]) {
    assert.deepEqual(pendingReviewChecks(value), [], JSON.stringify(value));
  }
});
