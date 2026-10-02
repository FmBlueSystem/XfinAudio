import type { Track } from './model.js';
import { errorCode, userErrorMessage } from './errors.js';
export type LoudnessState = 'unmeasured' | 'measured' | 'too_short' | 'unmeasurable' | 'transient_failure' | 'unsupported';
export interface LoudnessTrack { track: Track; state: LoudnessState; complete: boolean; lufs: number | null; lra: number | null; truePeak: number | null; }
export interface LoudnessSnapshot {
  revision: string; enabled: boolean; targetLufs: number; toleranceLu: number; available: boolean;
  reason: 'ready' | 'missing_engine' | 'failed_engine'; totalTracks: number; tracks: LoudnessTrack[];
}
export interface LoudnessSettings { revision: string; enabled: boolean; targetLufs: number; toleranceLu: number; }
export interface LoudnessPreview { previewId: string; trackCount: number; backupBytes: number; force: boolean; tracks: Track[]; replaceComments: true; }
export interface LoudnessRunResult { cancelled: boolean; changedCount: number; unchangedCount: number; failureCount: number; backupCount: number; status: LoudnessSnapshot; warning?: string | null; }
export interface LoudnessApi {
  getLoudnessStatus(): Promise<LoudnessSnapshot>;
  saveLoudnessSettings(input: LoudnessSettings): Promise<LoudnessSnapshot>;
  previewLoudness(input: { trackIds: string[]; force: boolean }): Promise<LoudnessPreview>;
  runLoudness(input: { previewId: string }): Promise<LoudnessRunResult>;
  revealLoudnessBackups?(): Promise<{ found: boolean }>;
}
export interface LoudnessHost {
  canAct(): boolean; changed(): void; dirtyChanged(dirty: boolean): void;
  applied(snapshot: LoudnessSnapshot, reason: 'load' | 'save' | 'run'): void;
  /** Runs use the global cancellable operation gate; always deliver outcomes after navigation. */
  perform<T>(label: string, task: () => Promise<T>, apply: (value: T, currentRoute: boolean) => void, failure: (error: unknown) => void): Promise<void>;
}
const bounded = (value: unknown, min: number, max: number): value is number => typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max;
const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const opaque = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const validTrack = (track: Track): boolean => Boolean(track && opaque(track.id) && typeof track.title === 'string' && typeof track.artist === 'string');
const invalid = (): never => { throw new Error('Invalid loudness response'); };
function safeWarning(value: unknown): string | null {
  if (value === undefined || value === null || value === '') return null;
  if (typeof value === 'string' && value.length <= 500 && !/[\\/\p{C}]/u.test(value)) return value.trim() || null;
  return 'No se pudo actualizar el estado tras la escritura. Conserva las copias de seguridad y actualiza antes de continuar.';
}
function copySnapshot(value: LoudnessSnapshot): LoudnessSnapshot {
  if (!value || !opaque(value.revision) || typeof value.enabled !== 'boolean' || !bounded(value.targetLufs, -30, 0)
    || !bounded(value.toleranceLu, 0, 10) || typeof value.available !== 'boolean' || !['ready', 'missing_engine', 'failed_engine'].includes(value.reason)
    || value.available !== (value.reason === 'ready') || !count(value.totalTracks) || !Array.isArray(value.tracks) || value.totalTracks !== value.tracks.length) invalid();
  const ids = new Set<string>();
  const tracks = value.tracks.map((item) => {
    if (!item || !validTrack(item.track) || ids.has(item.track.id) || typeof item.complete !== 'boolean'
      || !['unmeasured', 'measured', 'too_short', 'unmeasurable', 'transient_failure', 'unsupported'].includes(item.state)
      || ![item.lufs, item.lra, item.truePeak].every((metric) => metric === null || bounded(metric, -Infinity, Infinity))
      || (item.complete && (item.state !== 'measured' || item.lufs === null || item.lra === null || item.truePeak === null))) invalid();
    ids.add(item.track.id); return { ...item, track: { ...item.track } };
  });
  return { ...value, tracks };
}
function copyPreview(value: LoudnessPreview, ids: string[], force: boolean): LoudnessPreview {
  if (!value || !/^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value.previewId)
    || value.replaceComments !== true || value.force !== force || value.trackCount !== ids.length || !count(value.backupBytes)
    || !Array.isArray(value.tracks) || value.tracks.length !== ids.length || new Set(value.tracks.map((track) => track.id)).size !== ids.length
    || !value.tracks.every((track) => validTrack(track) && ids.includes(track.id))) invalid();
  return { ...value, tracks: value.tracks.map((track) => ({ ...track })) };
}

/** Settings stay local until Save; Preview never writes. Run asks main for native confirmation. */
export class LoudnessController {
  private api: LoudnessApi; private host: LoudnessHost;
  private base: LoudnessSnapshot | null = null; private draft: LoudnessSnapshot | null = null;
  private selection = new Set<string>(); private context = 0; private generation = 0; private conflict = false;
  pending: 'load' | 'save' | 'preview' | 'run' | 'reveal' | null = null;
  backupNotice = '';
  error = ''; statusFresh = false; page = 0;
  preview: LoudnessPreview | null = null; result: LoudnessRunResult | null = null;
  constructor(api: LoudnessApi, host: LoudnessHost) { this.api = api; this.host = host; }
  get snapshot(): LoudnessSnapshot | null { return this.draft; }
  get dirty(): boolean { return Boolean(this.draft && this.base && (this.draft.enabled !== this.base.enabled || this.draft.targetLufs !== this.base.targetLufs || this.draft.toleranceLu !== this.base.toleranceLu)); }
  get canSave(): boolean { return !this.pending && !this.conflict && this.dirty; }
  get selectedIds(): string[] { return [...this.selection]; }
  get pageCount(): number { return Math.max(1, Math.ceil((this.draft?.tracks.length ?? 0) / 100)); }
  get visibleTracks(): LoudnessTrack[] { return this.draft?.tracks.slice(this.page * 100, this.page * 100 + 100) ?? []; }
  get canPreview(): boolean { return !this.pending && this.statusFresh && !this.dirty && !this.conflict && Boolean(this.draft?.enabled && this.draft.available) && this.selection.size > 0 && this.selection.size <= 500; }
  get canRun(): boolean { return this.canPreview && Boolean(this.preview); }
  get canRevealBackups(): boolean { return !this.pending && typeof this.api.revealLoudnessBackups === 'function'; }
  private notify(): void { this.host.dirtyChanged(this.dirty); this.host.changed(); }
  private invalidatePreview(): void { this.generation++; this.preview = null; }
  /** Call on library change, rescan or disconnect, not ordinary navigation. Dirty settings and receipts survive. */
  invalidateContext(): void { this.context++; this.statusFresh = false; this.selection.clear(); this.invalidatePreview(); this.notify(); }
  private accept(value: LoudnessSnapshot, reason: 'load' | 'save' | 'run', fresh = true): void {
    const snapshot = copySnapshot(value);
    this.base = snapshot; this.draft = { ...snapshot }; this.conflict = false; this.statusFresh = fresh; this.error = '';
    const known = new Set(snapshot.tracks.map((item) => item.track.id)); this.selection = new Set([...this.selection].filter((id) => known.has(id)));
    this.page = Math.min(this.page, this.pageCount - 1); this.invalidatePreview(); this.host.applied(copySnapshot(snapshot), reason); this.notify();
  }
  private fail(error: unknown): void {
    const code = errorCode(error);
    if (code === 'stale_settings' || code === 'stale_revision') {
      this.conflict = true; this.invalidatePreview();
      this.error = 'Los ajustes guardados cambiaron. Tu borrador se conserva; descarta los cambios y actualiza antes de guardar.';
    } else if (code === 'stale_loudness') {
      this.statusFresh = false; this.invalidatePreview(); this.error = 'Las pistas o los ajustes cambiaron. Actualiza los datos y prepara otra vista previa.';
    } else if (code === 'loudness_unavailable' || code === 'loudness_disabled') {
      this.statusFresh = false; this.invalidatePreview();
      this.error = code === 'loudness_unavailable' ? 'El motor de sonoridad no está disponible. Actualiza el estado antes de intentarlo de nuevo.'
        : 'El análisis de sonoridad está desactivado. Actualiza el estado, revisa y guarda los ajustes antes de continuar.';
    }
    else this.error = userErrorMessage(error);
    this.notify();
  }
  private async perform<T>(kind: NonNullable<LoudnessController['pending']>, label: string, task: () => Promise<T>, apply: (value: T, current: boolean) => void, failure: (error: unknown) => void): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    this.pending = kind; this.error = ''; this.host.changed();
    try { await this.host.perform(label, task, apply, failure); } catch (error) { failure(error); }
    finally { this.pending = null; this.notify(); }
  }
  async load(): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    if (this.dirty) { this.error = 'Tienes ajustes sin guardar. Guarda o descarta los cambios antes de actualizar.'; this.notify(); return; }
    this.invalidatePreview(); const context = this.context;
    await this.perform('load', 'Cargando sonoridad…', () => this.api.getLoudnessStatus(), (value) => { if (context === this.context) this.accept(value, 'load'); }, (error) => { if (context === this.context) this.fail(error); });
  }
  private edit(field: 'enabled' | 'targetLufs' | 'toleranceLu', value: boolean | number): void {
    if (!this.draft || this.pending || !this.host.canAct()) return;
    const valid = field === 'enabled' ? typeof value === 'boolean' : bounded(value, field === 'targetLufs' ? -30 : 0, field === 'targetLufs' ? 0 : 10);
    if (!valid) { this.error = 'Revisa los límites: objetivo entre −30 y 0 LUFS, tolerancia entre 0 y 10 LU.'; this.notify(); return; }
    if (this.draft[field] === value) return;
    this.draft = { ...this.draft, [field]: value }; this.invalidatePreview(); if (!this.conflict) this.error = ''; this.notify();
  }
  setEnabled(value: boolean): void { this.edit('enabled', value); }
  setTarget(value: number): void { this.edit('targetLufs', value); }
  setTolerance(value: number): void { this.edit('toleranceLu', value); }
  async save(): Promise<void> {
    if (!this.canSave || !this.draft || !this.host.canAct()) return;
    const { revision, enabled, targetLufs, toleranceLu } = this.draft; const context = this.context; this.invalidatePreview();
    await this.perform('save', 'Guardando sonoridad…', () => this.api.saveLoudnessSettings({ revision, enabled, targetLufs, toleranceLu }), (value) => { if (context === this.context) this.accept(value, 'save'); }, (error) => { if (context === this.context) this.fail(error); });
  }
  discard(): void {
    if (!this.base || this.pending || !this.host.canAct()) return;
    this.draft = { ...this.base }; this.invalidatePreview(); this.error = this.conflict ? 'Borrador descartado. Pulsa Actualizar para cargar los ajustes vigentes.' : ''; this.notify();
  }
  setSelection(ids: string[]): void {
    if (this.pending || !this.host.canAct() || !this.statusFresh || !this.draft) return;
    const unique = Array.isArray(ids) ? [...new Set(ids)] : []; const known = new Set(this.draft.tracks.map((item) => item.track.id));
    if (!Array.isArray(ids) || unique.length > 500 || !unique.every((id) => opaque(id) && known.has(id))) {
      this.error = 'Selecciona como máximo 500 pistas conocidas. No se ha recortado ni cambiado tu selección.'; this.notify(); return;
    }
    if (unique.length === this.selection.size && unique.every((id) => this.selection.has(id))) return;
    this.selection = new Set(unique); this.invalidatePreview(); this.error = ''; this.notify();
  }
  toggleTrack(id: string, selected: boolean): void { if (typeof selected === 'boolean') this.setSelection(selected ? [...this.selection, id] : [...this.selection].filter((value) => value !== id)); }
  clearSelection(): void { this.setSelection([]); }
  selectAll(): void { this.setSelection(this.draft?.tracks.map((item) => item.track.id) ?? []); }
  selectPage(): void { this.setSelection([...this.selection, ...this.visibleTracks.map((item) => item.track.id)]); }
  setPage(page: number): void {
    if (this.pending || !this.host.canAct() || !count(page) || page >= this.pageCount) return;
    this.page = page; this.host.changed();
  }
  async requestPreview(force = false): Promise<void> {
    if (!this.canPreview || !this.host.canAct() || typeof force !== 'boolean') return;
    if (force && this.selection.size !== 1) { this.error = 'Reanalizar requiere exactamente una pista.'; this.notify(); return; }
    this.invalidatePreview(); const generation = this.generation; const trackIds = this.selectedIds;
    await this.perform('preview', 'Preparando vista previa de sonoridad…', () => this.api.previewLoudness({ trackIds, force }), (value, current) => {
      if (current && generation === this.generation) { this.preview = copyPreview(value, trackIds, force); this.host.changed(); }
    }, (error) => { if (generation === this.generation) this.fail(error); });
  }
  async reanalyze(trackId: string): Promise<void> {
    if (this.pending || !this.host.canAct() || this.dirty || !this.statusFresh || !this.draft?.enabled || !this.draft.available || !this.draft.tracks.some((item) => item.track.id === trackId)) return;
    this.setSelection([trackId]); await this.requestPreview(true);
  }
  async run(): Promise<void> {
    if (!this.canRun || !this.preview || !this.host.canAct()) return;
    const { previewId, trackCount } = this.preview; const context = this.context; this.result = null;
    await this.perform('run', 'Confirmando análisis y escritura de sonoridad…', () => this.api.runLoudness({ previewId }), (value) => {
      if (!value || typeof value.cancelled !== 'boolean' || ![value.changedCount, value.unchangedCount, value.failureCount, value.backupCount].every((n) => count(n) && n <= trackCount)
        || value.changedCount + value.unchangedCount + value.failureCount > trackCount) invalid();
      const status = copySnapshot(value.status); const warning = safeWarning(value.warning); this.result = { ...value, status, warning }; this.invalidatePreview();
      if (context === this.context) this.accept(status, 'run', !warning); else this.notify();
    }, (error) => { this.invalidatePreview(); this.fail(error); });
  }
  async revealBackups(): Promise<void> {
    if (!this.canRevealBackups || !this.host.canAct()) return;
    this.backupNotice = '';
    await this.perform('reveal', 'Mostrando copias de seguridad…', () => this.api.revealLoudnessBackups!(), (value) => {
      if (!value || typeof value.found !== 'boolean') invalid();
      this.backupNotice = value.found ? 'Carpeta de copias de seguridad abierta. Mostrar las copias no restaura ni modifica los archivos de audio.'
        : 'Todavía no hay copias de seguridad de sonoridad.';
      this.host.changed();
    }, (error) => this.fail(error));
  }
}
