import { matchesSearch } from './model.js';
import type { Track } from './model.js';

export const TRACK_SEARCH_LIMIT = 10;

export interface TrackSearchResults { results: Track[]; total: number; }

/** Free-text opening-track search over the shared library projection; results keep library order. */
export function searchTracks(tracks: Track[], query: string, limit: number = TRACK_SEARCH_LIMIT): TrackSearchResults {
  if (!query.trim()) return { results: [], total: 0 };
  const matches = tracks.filter((track) => matchesSearch(track, query));
  return { results: matches.slice(0, Math.max(0, limit)), total: matches.length };
}
/** Combobox arrow movement: wraps at both ends and stays inert without options. */
export function nextActiveIndex(current: number, delta: number, count: number): number {
  if (count <= 0) return -1;
  if (current < 0 || current >= count) return delta > 0 ? 0 : count - 1;
  return (current + delta + count) % count;
}
export function trackChoiceTitle(track: Track): string { return track.title || 'Sin título'; }
export function trackChoiceArtist(track: Track): string { return track.artist || 'Artista desconocido'; }
export function trackChoiceBpm(track: Track): string {
  const bpm = track.bpm;
  return typeof bpm === 'number' && Number.isFinite(bpm) && bpm > 0 ? `${Math.round(bpm)} BPM` : 'Sin BPM';
}
export function trackChoiceKey(track: Track): string { return track.key?.trim() ? track.key.trim() : 'Sin tonalidad'; }
export function trackChoiceLabel(track: Track): string { return `${trackChoiceTitle(track)} · ${trackChoiceArtist(track)}`; }
export function trackChoiceMeta(track: Track): string { return `${trackChoiceBpm(track)} · ${trackChoiceKey(track)}`; }
export function unavailableTrackLabel(id: string): string { return `No disponible: ${id.slice(0, 8)}`; }
export function searchResultMessage(query: string, shown: number, total: number): string {
  const text = query.trim();
  if (!text) return '';
  if (total === 0) return `Sin coincidencias para «${text}».`;
  const prefix = total > shown ? `Mostrando ${shown} de ${total} coincidencias` : total === 1 ? '1 coincidencia' : `${total} coincidencias`;
  return `${prefix}. Usa las flechas para moverte y Enter para elegir.`;
}
export function selectedTrackMessage(label: string): string { return `Pista de apertura: ${label}.`; }
export function clearedTrackMessage(): string { return 'Sin preferencia de apertura.'; }
