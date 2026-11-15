/**
 * Presentation only: the notice a list that came out shorter than requested shows (S3), its
 * exact copy, and the S6 card name for an alternative the assistant proposes. Nothing here
 * calls the core, recalculates a count or reorders a plan.
 *
 * The only short list this module recognises is the engine's own warning
 * `Track count shortfall: selected N of M requested tracks`, built in
 * `recommendation/playlist_service.py`; every other warning keeps the translation `workflow.ts`
 * already gives it.
 */
import type { PrepVariant, PrepVariantSummary } from './model.js';

/** What the engine said: how many tracks it selected out of how many were requested. */
export interface ShortListFact { selected: number; requested: number; }

/** The `extended` field S1 adds to a review after `review.extend`. */
export interface ExtendedList { requested: number; added: number; outsideGenre: number; }

/** The alternative S3 offers: the plan variant and the count it produced. */
export interface LargerAlternative { variant: PrepVariant; trackCount: number; }

const SHORTFALL = /^Track count shortfall: selected (\d+) of (\d+) requested tracks$/;
export const SHORT_LIST_WITHOUT_GENRE = 'Generar sin género';
export const SHORT_LIST_NO_CANDIDATES = 'No hay más pistas que mezclen con esta lista.';
const alternativeNames: Record<PrepVariant, string> = { safe: 'segura', balanced: 'equilibrada', adventurous: 'exploratoria' };

/** The shortfall counts of one engine message, or null when this is not that exact message. */
function shortfallOf(message: unknown): ShortListFact | null {
  if (typeof message !== 'string') return null;
  const match = SHORTFALL.exec(message);
  if (!match) return null;
  const selected = Number(match[1]);
  const requested = Number(match[2]);
  if (!Number.isInteger(selected) || !Number.isInteger(requested) || selected < 0 || requested < 1) return null;
  return { selected, requested };
}

export function isShortListWarning(message: unknown): boolean { return shortfallOf(message) !== null; }

/** The first engine shortfall warning of a review payload, or null when the list is complete. */
export function shortListOf(warnings: unknown): ShortListFact | null {
  if (!Array.isArray(warnings)) return null;
  for (const warning of warnings) {
    const fact = shortfallOf(warning);
    if (fact) return fact;
  }
  return null;
}

/** «Salieron {N} de {M} pistas.» */
export function shortListTitle(fact: ShortListFact): string { return `Salieron ${fact.selected} de ${fact.requested} pistas.`; }

/** The second line, shown only when the generation used a genre. */
export function shortListGenre(genre: string): string {
  return `El género «${genre}» y las reglas de mezcla dejaron pocas candidatas.`;
}

/** «Ampliar a {M} pistas»: the target is the requested count the engine reported. */
export function extendLabel(target: number): string { return `Ampliar a ${target} pistas`; }

/** «Usar la alternativa de {K} pistas»: K is the largest alternative. */
export function alternativeLabel(count: number): string { return `Usar la alternativa de ${count} pistas`; }

/** «Se agregaron {added} pistas.» plus the outside-genre count only when there is one. */
export function extendedLine(extended: ExtendedList): string {
  const line = `Se agregaron ${extended.added} pistas.`;
  return extended.outsideGenre > 0 ? `${line} ${extended.outsideGenre} son de otros géneros.` : line;
}

/** «Usar la alternativa {segura|equilibrada|exploratoria} ({trackCount} pistas)» of a chat card. */
export function alternativeCardText(variant: PrepVariant, trackCount: number): string {
  return `Usar la alternativa ${alternativeNames[variant]} (${trackCount} pistas)`;
}

/**
 * The alternative S3 offers when the plan can give a longer list: the largest variant other
 * than the one on screen, and only when it carries more tracks than the list itself.
 */
export function largerAlternative(variants: readonly PrepVariantSummary[] | null | undefined, currentVariant: string, currentCount: number): LargerAlternative | null {
  if (!Array.isArray(variants)) return null;
  let best: LargerAlternative | null = null;
  for (const item of variants) {
    if (!item || item.name === currentVariant) continue;
    if (!Number.isInteger(item.trackCount) || item.trackCount <= currentCount) continue;
    if (!best || item.trackCount > best.trackCount) best = { variant: item.name, trackCount: item.trackCount };
  }
  return best;
}
