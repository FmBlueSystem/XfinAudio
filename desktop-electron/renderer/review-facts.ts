/**
 * Presentation only: the labels, thresholds and fix texts the review shows for what the core
 * already computed. Nothing here recalculates a score or a check.
 *
 * The transition thresholds reuse the readiness check «Puntuación media de transición», whose
 * only line is `build_dj_readiness_report(min_average_transition_score=0.65)` in
 * `quality/dj_readiness.py`: «Buena» is at or above it and «Débil» keeps the 0.5 floor.
 *
 * Both additive review facts are read structurally, so a payload from a core that predates
 * them yields no scores and no pending checks and the review renders as before.
 */
import type { Readiness } from './model.js';

export interface ReviewCheckFact { label: string; status: Readiness; detail: string; }

export const GOOD_TRANSITION_MIN = 0.65;
export const WEAK_TRANSITION_BELOW = 0.5;

export type TransitionTone = 'good' | 'fair' | 'weak';
export interface TransitionQuality { label: 'Buena' | 'Regular' | 'Débil'; tone: TransitionTone; text: string; }

/** Quality of one transition, with its percentage: «Débil · 42 %». */
export function transitionQuality(score: number): TransitionQuality {
  const percent = `${Math.round(score * 100)} %`;
  if (score >= GOOD_TRANSITION_MIN) return { label: 'Buena', tone: 'good', text: `Buena · ${percent}` };
  if (score >= WEAK_TRANSITION_BELOW) return { label: 'Regular', tone: 'fair', text: `Regular · ${percent}` };
  return { label: 'Débil', tone: 'weak', text: `Débil · ${percent}` };
}

/** The per-transition scores of a review payload, or null when an older core sent none. */
export function transitionScoresOf(value: unknown): number[] | null {
  const scores = (value as { transitionScores?: unknown } | null)?.transitionScores;
  if (!Array.isArray(scores) || scores.length === 0) return null;
  return scores.every((score) => typeof score === 'number' && Number.isFinite(score)) ? scores as number[] : null;
}

export interface ReviewCheckFix { label: string; detail: string; fix: string | null; action: 'metadata' | null; }

const mixFix = 'Mira la columna Mezcla: reemplaza o mueve una pista de las transiciones débiles.';
const regenerateFix = 'Vuelve a generar con otra cantidad o con otras pistas obligatorias.';
/** One entry per label the core publishes in `quality/dj_readiness.py`; any other label shows only its detail. */
const fixes: Record<string, { fix: string | null; action: 'metadata' | null }> = {
  'Metadatos requeridos': { fix: null, action: 'metadata' },
  'Continuidad de BPM': { fix: mixFix, action: null },
  'Continuidad de energía': { fix: mixFix, action: null },
  'Avisos de transición': { fix: mixFix, action: null },
  'Puntuación media de transición': { fix: mixFix, action: null },
  'Pistas repetidas': { fix: 'Reemplaza una de las pistas repetidas.', action: null },
  'Tamaño de la lista': { fix: regenerateFix, action: null },
  'Pistas obligatorias': { fix: regenerateFix, action: null },
};

/** The detail of one readiness check plus the fix the user can apply, when the label has one. */
export function reviewFix(check: ReviewCheckFact): ReviewCheckFix {
  return { label: check.label, detail: check.detail, ...(fixes[check.label] ?? { fix: null, action: null }) };
}

/** Every check of a review payload that is not ready, in the order the core sent them. */
export function pendingReviewChecks(value: unknown): ReviewCheckFix[] {
  const checks = (value as { readinessChecks?: unknown } | null)?.readinessChecks;
  if (!Array.isArray(checks)) return [];
  return checks
    .filter((check): check is ReviewCheckFact => typeof check?.label === 'string' && typeof check.detail === 'string' && check.status !== 'ready')
    .map(reviewFix);
}
