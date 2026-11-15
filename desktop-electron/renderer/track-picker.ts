import { trackChoiceLabel, trackChoiceMeta, unavailableTrackLabel } from './track-search.js';
import type { Track } from './model.js';

export type TrackPickerKind = 'end' | 'required' | 'excluded';

/** A chosen track as the picker shows it: the shared labels, or the unavailable marker. */
export interface TrackPickerChoice { id: string; label: string; meta: string; available: boolean; }

const emptyLabels: Record<TrackPickerKind, string> = {
  end: 'Sin preferencia',
  required: 'Sin pistas obligatorias',
  excluded: 'Sin pistas excluidas',
};
const clearedMessages: Record<TrackPickerKind, string> = {
  end: 'Sin preferencia de cierre.',
  required: 'Sin pistas obligatorias.',
  excluded: 'Sin pistas excluidas.',
};
const chosenPrefixes: Record<TrackPickerKind, string> = {
  end: 'Pista de cierre',
  required: 'Pista obligatoria',
  excluded: 'Pista excluida',
};

export function emptyChoiceLabel(kind: TrackPickerKind): string { return emptyLabels[kind]; }
/** A chosen track that left the library keeps its identity and is shown as unavailable. */
export function pickerChoice(id: string, tracks: Track[]): TrackPickerChoice {
  const track = tracks.find((item) => item.id === id);
  if (!track) return { id, label: unavailableTrackLabel(id), meta: 'Ya no está en la biblioteca.', available: false };
  return { id, label: trackChoiceLabel(track), meta: trackChoiceMeta(track), available: true };
}
export function pickerChoices(ids: string[], tracks: Track[]): TrackPickerChoice[] {
  return ids.filter(Boolean).map((id) => pickerChoice(id, tracks));
}
/** The closing picker replaces its only choice; the other two append once, in user order. */
export function chooseIds(current: string[], id: string, multiple: boolean): string[] {
  if (!multiple) return [id];
  return current.includes(id) ? [...current] : [...current, id];
}
export function removeId(current: string[], id: string): string[] { return current.filter((value) => value !== id); }
export function chosenMessage(kind: TrackPickerKind, label: string): string { return `${chosenPrefixes[kind]}: ${label}.`; }
export function clearedMessage(kind: TrackPickerKind): string { return clearedMessages[kind]; }
export function removedMessage(label: string): string { return `Quitada: ${label}.`; }
export function chipRemoveLabel(label: string): string { return `Quitar ${label}`; }
