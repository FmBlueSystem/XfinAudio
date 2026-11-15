/**
 * Presentation only: what the prep screen says about the library tracks that cannot enter a list.
 *
 * The core keeps only tracks with `metadata_status == "complete"` in the candidate pool
 * (`recommendation/candidate_pool.py`), so the screen warns before generating instead of after.
 * The count reads `status`/`missingFields` exactly as `headless/common.py` publishes them, and
 * falls back to the metadata each track carries so an older payload still counts correctly.
 */
import { hasPrepMetadata, type Track } from './model.js';

export interface PrepTracksGate {
  total: number;
  complete: number;
  leftOut: number;
  fields: string[];
  message: string;
  canGenerate: boolean;
}
export interface LeftOutNoticeHost { canAct(): boolean; openMetadata(): void; }
type PrepField = 'bpm' | 'camelot_key' | 'energy_level';
const fieldLabels: Record<PrepField, string> = { bpm: 'BPM', camelot_key: 'key', energy_level: 'energía' };
const fieldOrder: readonly PrepField[] = ['bpm', 'camelot_key', 'energy_level'];
export const NEEDS_TWO_TRACKS = 'Necesitas al menos dos pistas con BPM, key y energía para generar una lista.';

const isComplete = (track: Track): boolean =>
  typeof track.status === 'string' && track.status.length > 0 ? track.status === 'complete' : hasPrepMetadata(track);

/** The fields the core reports, or — for a payload that does not report them — the ones the track lacks. */
const missingFields = (track: Track): PrepField[] => {
  if (Array.isArray(track.missingFields)) return fieldOrder.filter((field) => track.missingFields!.includes(field));
  const missing: PrepField[] = [];
  if (!(Number.isFinite(track.bpm) && (track.bpm ?? 0) > 0)) missing.push('bpm');
  if (!track.key) missing.push('camelot_key');
  if (!Number.isFinite(track.energy)) missing.push('energy_level');
  return missing;
};
const joinFields = (fields: readonly PrepField[]): string =>
  fields.length < 2 ? fields.map((field) => fieldLabels[field]).join('') : `${fields.slice(0, -1).map((field) => fieldLabels[field]).join(', ')} y ${fieldLabels[fields[fields.length - 1]]}`;

/** Counts complete tracks, names why the rest stay out, and says whether generating is possible. */
export function summarizePrepTracks(tracks: readonly Track[]): PrepTracksGate {
  const complete = tracks.filter(isComplete).length;
  const leftOut = tracks.length - complete;
  const fields = fieldOrder.filter((field) => tracks.some((track) => !isComplete(track) && missingFields(track).includes(field)));
  const canGenerate = complete >= 2;
  const message = tracks.length === 0 ? ''
    : !canGenerate ? NEEDS_TWO_TRACKS
    : leftOut === 0 ? ''
    : fields.length === 0 ? `${leftOut} de ${tracks.length} pistas no entran en la lista porque no tienen los metadatos completos.`
    : `${leftOut} de ${tracks.length} pistas no entran en la lista porque les falta ${joinFields(fields)}.`;
  return { total: tracks.length, complete, leftOut, fields, message, canGenerate };
}

/** Renders the notice above the generate button and returns the same gate the render used. */
export function createLeftOutNotice(root: HTMLElement, host: LeftOutNoticeHost): (tracks: readonly Track[]) => PrepTracksGate {
  const message = document.createElement('p'); message.id = 'prep-left-out-message'; message.className = 'review-notice';
  message.setAttribute('role', 'status');
  const metadata = document.createElement('button'); metadata.id = 'prep-left-out-metadata';
  metadata.type = 'button'; metadata.className = 'button subtle'; metadata.textContent = 'Completar metadatos';
  metadata.addEventListener('click', () => { if (!metadata.disabled && host.canAct()) host.openMetadata(); });
  root.replaceChildren(message, metadata);
  return (tracks) => {
    const gate = summarizePrepTracks(tracks);
    root.hidden = gate.message === '';
    message.textContent = gate.message;
    metadata.hidden = gate.leftOut === 0;
    metadata.disabled = !host.canAct() || gate.leftOut === 0;
    return gate;
  };
}