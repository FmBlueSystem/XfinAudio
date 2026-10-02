import type { LiveApi } from './live.js';
import type { SeratoExportApi } from './serato-export.js';
import type { EditorApi } from './editor.js';
import type { MetadataReport } from './metadata.js';
export interface Track {
  id: string;
  title: string;
  artist: string;
  bpm: number | null;
  key: string | null;
  energy: number | null;
  duration: number | null;
  genre?: string;
  status?: string;
  missingFields?: string[];
}
export interface LibraryResult { tracks: Track[]; count: number; cancelled?: boolean; }
export type PrepVariant = 'safe' | 'balanced' | 'adventurous';
export type Readiness = 'ready' | 'needs_review' | 'blocked';
export interface PrepStrategy { name: string; displayName: string; description: string; requiresVibeMetadata: boolean; }
export interface PrepVariantSummary { name: PrepVariant; description: string; trackCount: number; readiness: Readiness; warnings: string[]; blockers: string[]; qualityScore: number; }
export interface PrepInput {
  targetTrackCount: number; name: string; strategy?: string; targetMinutes?: number;
  slotRole?: 'warmup' | 'peak_time' | 'chill' | null; genreFocus?: string;
  startTrackId?: string; endTrackId?: string; requiredTrackIds?: string[]; excludedTrackIds?: string[];
}
export interface PrepFields { count: string; name: string; strategy: string; minutes: string; role: string; genre: string; start: string; end: string; required: string[]; excluded: string[]; }
export interface ReviewResult {
  reviewId: string;
  tracks: Track[];
  warnings: string[];
  blockers: string[];
  name: string;
  variant: PrepVariant | 'saved';
  savedPlaylistId?: string;
  planId?: string;
  variants?: PrepVariantSummary[];
  readiness: Readiness;
  qualityScore?: number;
  canSave?: boolean;
}
export interface PlaylistSummary { id: string; name: string; trackCount: number; createdAt: string; }
export interface ProgressEvent {
  jobId: string;
  operation: string;
  phase: string;
  current?: number;
  total?: number;
  message?: string;
  stage?: string; readyCount?: number; failedCount?: number;
}
export interface XfinApi extends EditorApi, SeratoExportApi, LiveApi {
  chooseLibrary(): Promise<LibraryResult | null>;
  listLibrary(): Promise<LibraryResult>;
  getMetadataReport(): Promise<MetadataReport>;
  getPrepCatalog(): Promise<{ strategies: PrepStrategy[] }>;
  generatePrep(input: PrepInput): Promise<ReviewResult>;
  selectPrepVariant(input: { planId: string; variant: PrepVariant }): Promise<ReviewResult>;
  savePlaylist(input: { name: string; reviewId: string }): Promise<PlaylistSummary>;
  listPlaylists(): Promise<PlaylistSummary[]>;
  openPlaylist(input: { playlistId: string }): Promise<ReviewResult>;
  renamePlaylist(input: { playlistId: string; name: string }): Promise<PlaylistSummary>;
  duplicatePlaylist(input: { playlistId: string }): Promise<PlaylistSummary>;
  setDraftDirty(dirty: boolean): Promise<void>;
  cancelCurrent(): Promise<unknown>;
  onProgress(callback: (event: ProgressEvent) => void): () => void;
}
export type Route = 'library' | 'metadata' | 'prep' | 'review' | 'playlists' | 'editor' | 'serato' | 'live';
export type MetadataFilter = 'all' | 'ready' | 'incomplete';

export function normalizePrepName(value: string): string { return value.trim() || 'Sesión equilibrada'; }
export function isCoreFailure(event: Pick<ProgressEvent, 'operation' | 'phase'>): boolean {
  return event.operation === 'core' && event.phase === 'error';
}

export function canSaveReview(review: ReviewResult | null): boolean {
  return review !== null && ['safe', 'balanced', 'adventurous'].includes(review.variant) && review.canSave !== false
    && review.readiness !== 'blocked' && review.blockers.length === 0 && review.tracks.length > 0 && Boolean(review.reviewId);
}

export function hasPrepMetadata(track: Track): boolean {
  return Number.isFinite(track.bpm) && (track.bpm ?? 0) > 0 && Boolean(track.key)
    && Number.isFinite(track.energy);
}
export function filterTracks(tracks: Track[], query: string, metadata: MetadataFilter): Track[] {
  const search = query.trim().toLocaleLowerCase();
  return tracks.filter((track) => {
    const match = `${track.title} ${track.artist} ${track.key ?? ''} ${track.genre ?? ''}`.toLocaleLowerCase().includes(search);
    return match && (metadata === 'all' || hasPrepMetadata(track) === (metadata === 'ready'));
  });
}
export function formatDuration(value: number | null): string {
  if (value === null || !Number.isFinite(value) || value < 0) return '—';
  const seconds = Math.floor(value);
  const minutes = Math.floor(seconds / 60);
  return `${minutes >= 60 ? `${Math.floor(minutes / 60)}:` : ''}${minutes >= 60 ? String(minutes % 60).padStart(2, '0') : minutes}:${String(seconds % 60).padStart(2, '0')}`;
}
export function validateTrackCount(value: string): number | null {
  if (!/^\d+$/.test(value.trim())) return null;
  const count = Number(value);
  return Number.isInteger(count) && count >= 2 && count <= 100 ? count : null;
}
export function buildPrepInput(fields: PrepFields, tracks: Track[], strategies: PrepStrategy[]): PrepInput {
  const count = validateTrackCount(fields.count);
  if (count === null) throw new Error('Introduce un número entero entre 2 y 100 pistas');
  const name = normalizePrepName(fields.name);
  if (name.length > 200) throw new Error('El nombre admite hasta 200 caracteres');
  const input: PrepInput = { targetTrackCount: count, name };
  if (fields.strategy) {
    if (!strategies.some((strategy) => strategy.name === fields.strategy)) throw new Error('Elige una estrategia disponible');
    input.strategy = fields.strategy;
  }
  if (fields.minutes.trim()) {
    const minutes = Number(fields.minutes);
    if (!Number.isFinite(minutes) || minutes <= 0 || minutes > 600) throw new Error('La duración debe ser mayor que 0 y no superar 600 minutos');
    input.targetMinutes = minutes;
  }
  if (fields.role) {
    if (!['warmup', 'peak_time', 'chill'].includes(fields.role)) throw new Error('Elige un momento válido para la sesión');
    input.slotRole = fields.role as PrepInput['slotRole'];
  }
  if (fields.genre.trim()) {
    if (fields.genre.trim().length > 100) throw new Error('El género admite hasta 100 caracteres');
    input.genreFocus = fields.genre.trim();
  }
  const known = new Set(tracks.map((track) => track.id));
  const valid = (id: string) => /^[a-f0-9]{64}$/.test(id) && known.has(id);
  if ([fields.start, fields.end, ...fields.required, ...fields.excluded].filter(Boolean).some((id) => !valid(id))) throw new Error('Selecciona solo pistas de la biblioteca actual');
  for (const ids of [fields.required, fields.excluded]) {
    if (ids.some((id) => !valid(id)) || ids.length > 100 || new Set(ids).size !== ids.length) throw new Error('Selecciona hasta 100 pistas distintas en cada lista');
  }
  if (fields.start && fields.start === fields.end) throw new Error('La apertura y el cierre deben ser pistas distintas');
  const protectedIds = new Set([fields.start, fields.end, ...fields.required].filter(Boolean));
  if (fields.excluded.some((id) => protectedIds.has(id))) throw new Error('Una pista excluida no puede ser obligatoria, de apertura o de cierre');
  if (protectedIds.size > count) throw new Error('Hay más pistas obligatorias, de apertura y de cierre que el número solicitado');
  if (fields.start) input.startTrackId = fields.start;
  if (fields.end) input.endTrackId = fields.end;
  if (fields.required.length) input.requiredTrackIds = [...fields.required];
  if (fields.excluded.length) input.excludedTrackIds = [...fields.excluded];
  return input;
}
export function audioUrl(id: string): string {
  if (!/^[a-zA-Z0-9_-]+$/.test(id)) throw new Error('Identificador de pista no válido');
  return `xfin-audio://track/${id}`;
}
export interface OperationToken { readonly id: number; readonly routeRevision: number; }
export class OperationGate {
  private sequence = 0;
  private active: { token: OperationToken; cancelled: boolean } | null = null;
  get busy(): boolean { return this.active !== null; }
  get cancelled(): boolean { return this.active?.cancelled ?? false; }
  begin(routeRevision: number): OperationToken | null {
    if (this.active) return null;
    const token = { id: ++this.sequence, routeRevision };
    this.active = { token, cancelled: false };
    return token;
  }
  isCurrent(token: OperationToken): boolean {
    return this.active?.token.id === token.id && !this.active.cancelled;
  }
  requestCancel(): void { if (this.active) this.active.cancelled = true; }
  finish(token: OperationToken): boolean {
    if (this.active?.token.id !== token.id) return false;
    this.active = null;
    return true;
  }
}
