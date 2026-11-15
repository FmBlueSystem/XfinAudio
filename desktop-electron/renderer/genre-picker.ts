/** Genre catalog shared by the Prep genre picker: grouping, filtering and Spanish copy. */
import { normalizeSearchText } from './model.js';

export type GenreGroupKind = 'compatible' | 'library';
export interface GenreOption { name: string; count: number; }
export interface GenreGroup { kind: GenreGroupKind; genres: GenreOption[]; }
export interface GenreCatalog { groups: GenreGroup[]; totalGenres: number; seedTitle: string | null; genreAvailable: boolean; }
/** The selector the read-only core method receives; both parts are optional. */
export interface GenreRequest { startTrackId?: string; genre?: string; }

export const MAX_GENRE_LENGTH = 100;
export const MAX_GENRE_OPTIONS = 5000;
export const REST_HEADING = 'Resto de la biblioteca';
export const FALLBACK_SEED_TITLE = 'la pista de apertura';
export const EMPTY_GENRE_LABEL = 'Sin género preferido';
export const GENRE_LOAD_FAILED = 'No se pudieron cargar los géneros de la biblioteca.';
export const GENRE_UNAVAILABLE_META = 'Ya no está en la biblioteca.';
export const GENRE_BUSY = 'Espera a que termine la operación en curso.';

/** The first group a seeded library is shown under, exactly as the user asked for it. */
export function compatibleHeading(seedTitle: string | null): string {
  return `Compatibles con «${seedTitle?.trim() || FALLBACK_SEED_TITLE}»`;
}
export function genreGroupHeading(group: GenreGroup, seedTitle: string | null): string {
  return group.kind === 'compatible' ? compatibleHeading(seedTitle) : REST_HEADING;
}
/** One option line: the genre as stored in the library and its track count, e.g. «Deep House (124)». */
export function genreOptionLabel(option: GenreOption): string { return `${option.name} (${option.count})`; }
export function genreFocusCountLabel(count: number): string { return `${count} ${count === 1 ? 'pista' : 'pistas'}`; }
export function sameGenre(left: string, right: string): boolean {
  return left.trim().toLocaleLowerCase() === right.trim().toLocaleLowerCase();
}
/** Filtering never reorders and never invents a genre: empty groups simply disappear. */
export function filterGenres(groups: GenreGroup[], query: string): GenreGroup[] {
  const text = normalizeSearchText(query.trim());
  if (!text) return groups.map((group) => ({ kind: group.kind, genres: [...group.genres] }));
  return groups
    .map((group) => ({ kind: group.kind, genres: group.genres.filter((option) => normalizeSearchText(option.name).includes(text)) }))
    .filter((group) => group.genres.length > 0);
}
export function genreResultMessage(query: string, shown: number): string {
  const text = query.trim();
  if (text && shown === 0) return `Sin géneros que coincidan con «${text}».`;
  if (!text && shown === 0) return 'La biblioteca no tiene géneros todavía.';
  const prefix = shown === 1 ? '1 género' : `${shown} géneros`;
  return `${prefix}. Usa las flechas para moverte y Enter para elegir.`;
}
export function selectedGenreMessage(name: string): string { return `Género preferido: ${name}.`; }
export function clearedGenreMessage(): string { return 'Sin género preferido.'; }
export function unavailableGenreLabel(value: string): string { return `No disponible: «${value}»`; }

const invalid = (): never => {
  throw Object.assign(new Error('Invalid genre catalog'), { code: 'genres_unavailable' });
};
const isCount = (value: unknown): value is number => typeof value === 'number' && Number.isInteger(value) && value >= 1;
const isName = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0 && value.length <= MAX_GENRE_LENGTH;

/** Fail closed on any malformed catalog: the picker never renders a genre the core did not send. */
export function validateGenreCatalog(value: unknown): GenreCatalog {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid();
  const record = value as Record<string, unknown>;
  if (!Array.isArray(record.groups) || record.groups.length > 2) return invalid();
  const groups = record.groups.map((raw): GenreGroup => {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return invalid();
    const group = raw as Record<string, unknown>;
    if (group.kind !== 'compatible' && group.kind !== 'library') return invalid();
    if (!Array.isArray(group.genres) || group.genres.length > MAX_GENRE_OPTIONS) return invalid();
    const genres = group.genres.map((option): GenreOption => {
      if (!option || typeof option !== 'object' || Array.isArray(option)) return invalid();
      const genre = option as Record<string, unknown>;
      if (!isName(genre.name) || !isCount(genre.count)) return invalid();
      return { name: genre.name, count: genre.count };
    });
    return { kind: group.kind, genres };
  });
  if (typeof record.totalGenres !== 'number' || !Number.isInteger(record.totalGenres) || record.totalGenres < 0) return invalid();
  if (record.seedTitle !== null && typeof record.seedTitle !== 'string') return invalid();
  if (typeof record.genreAvailable !== 'boolean') return invalid();
  return { groups, totalGenres: record.totalGenres, seedTitle: record.seedTitle ?? null, genreAvailable: record.genreAvailable };
}
