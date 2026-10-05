import type { Readiness, Track } from './model.js';
export interface EditorTrack extends Track { missing: boolean; }
export interface EditorSnapshot { editId: string; revision: string; id: string; name: string; tracks: EditorTrack[]; missingTrackCount: number; }
export interface EditPreview { editId: string; previewId: string; revision: string; tracks: EditorTrack[]; assessment: { description: string; readiness: Readiness; qualityScore: number; warnings: string[] }; }
/**
 * Bounded local improvement preview returned by the AI `editor` surface after
 * `ai.apply`. It is deliberately separate from the legacy `EditPreview`: it carries the
 * exact proposal binding the backend must see again on the dedicated save, and it is
 * parsed field by field instead of trusted wholesale.
 */
export interface ImprovementPreview {
  editId: string;
  sourceRevision: string;
  proposalId: string;
  digest: string;
  before: EditorTrack[];
  after: EditorTrack[];
  assessment: { description: string; readiness: Readiness; qualityScore: number; warnings: string[] };
  addedIds: string[];
  removedIds: string[];
}
export interface EditorApi {
  openPlaylistEditor(input: { playlistId: string }): Promise<EditorSnapshot>;
  previewPlaylistEdit(input: { editId: string; trackIds: string[]; request: string }): Promise<EditPreview>;
  savePlaylistEdit(input: { editId: string; name: string; trackIds: string[] }): Promise<EditorSnapshot>;
  savePlaylistImprovement(input: { editId: string; name: string; proposalId: string; digest: string; draftIds: string[] }): Promise<EditorSnapshot>;
  discardPlaylistEdit(input: { editId: string }): Promise<EditorSnapshot>;
}
interface EditorHost {
  canAct(): boolean;
  changed(): void;
  dirtyChanged(dirty: boolean): void;
  navigate(): void;
  perform<T>(label: string, task: () => Promise<T>, apply: (value: T, currentRoute: boolean) => void, failure: (error: unknown) => void): Promise<void>;
}
const isConflict = (error: unknown): boolean => /stale_edit/.test(String(error)) || (error as { code?: unknown } | null)?.code === 'stale_edit';
const copy = (snapshot: EditorSnapshot): EditorSnapshot => ({ ...snapshot, tracks: snapshot.tracks.map((track) => ({ ...track })) });
const HEX_ID = /^[a-f0-9]{64}$/;
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
// Mirrors the backend improvement contract: MIN_IMPROVEMENT_TRACKS and MAX_DRAFT_TRACKS.
const MIN_IMPROVEMENT_TRACKS = 2;
const MAX_IMPROVEMENT_TRACKS = 80;
const READINESS_VALUES: Readiness[] = ['ready', 'needs_review', 'blocked'];
const BITRATE_MODES: string[] = ['CBR', 'VBR', 'ABR'];
const reject = (): never => { throw new Error('invalid_improvement'); };
const recordOf = (value: unknown): Record<string, unknown> => (value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : reject());
const text = (value: unknown, maximum: number): string => (typeof value === 'string' && value.length <= maximum ? value : reject());
const hexId = (value: unknown): string => (typeof value === 'string' && HEX_ID.test(value) ? value : reject());
const uuid = (value: unknown): string => (typeof value === 'string' && UUID.test(value) ? value : reject());
const optionalNumber = (value: unknown): number | null => (value === null ? null : typeof value === 'number' && Number.isFinite(value) ? value : reject());
const readiness = (value: unknown): Readiness => (READINESS_VALUES.includes(value as Readiness) ? value as Readiness : reject());
const boundedArray = (value: unknown, maximum: number): unknown[] => {
  if (!Array.isArray(value) || value.length > maximum) throw new Error('invalid_improvement');
  return value;
};
const sameOrder = (left: readonly EditorTrack[], right: readonly EditorTrack[]): boolean => left.length === right.length && left.every((track, index) => track.id === right[index].id);
/**
 * Copy only the public track fields the renderer renders. A `path`, an unknown key or a
 * wrongly typed known field never reaches the draft or the view.
 */
function publicTrack(value: unknown): EditorTrack {
  const raw = recordOf(value);
  const track: EditorTrack = {
    id: hexId(raw.id),
    title: text(raw.title, 1000),
    artist: text(raw.artist, 1000),
    bpm: optionalNumber(raw.bpm),
    key: raw.key === null ? null : text(raw.key, 50),
    energy: optionalNumber(raw.energy),
    duration: optionalNumber(raw.duration),
    missing: typeof raw.missing === 'boolean' ? raw.missing : reject(),
  };
  if (Object.hasOwn(raw, 'genre')) track.genre = text(raw.genre, 500);
  if (Object.hasOwn(raw, 'status')) track.status = text(raw.status, 200);
  if (Object.hasOwn(raw, 'audioFormat')) track.audioFormat = raw.audioFormat === null ? null : text(raw.audioFormat, 100);
  if (Object.hasOwn(raw, 'audioCodec')) track.audioCodec = raw.audioCodec === null ? null : text(raw.audioCodec, 100);
  if (Object.hasOwn(raw, 'bitrateKbps')) track.bitrateKbps = optionalNumber(raw.bitrateKbps);
  if (Object.hasOwn(raw, 'bitrateMode')) track.bitrateMode = raw.bitrateMode === null ? null : BITRATE_MODES.includes(String(raw.bitrateMode)) ? raw.bitrateMode as 'CBR' | 'VBR' | 'ABR' : reject();
  if (Object.hasOwn(raw, 'missingFields')) track.missingFields = boundedArray(raw.missingFields, 50).map((field) => text(field, 200));
  return track;
}
const trackList = (value: unknown): EditorTrack[] => (Array.isArray(value) && value.length <= MAX_IMPROVEMENT_TRACKS ? value.map(publicTrack) : reject());
/** Parse an untrusted improvement payload; throw (caught by the caller) on any violation. */
function improvementPreview(value: unknown): ImprovementPreview {
  const raw = recordOf(value);
  const before = trackList(raw.before);
  const after = trackList(raw.after);
  if (before.length < MIN_IMPROVEMENT_TRACKS || after.length < MIN_IMPROVEMENT_TRACKS) reject();
  const beforeIds = before.map((track) => track.id);
  const afterIds = after.map((track) => track.id);
  if (new Set(beforeIds).size !== beforeIds.length || new Set(afterIds).size !== afterIds.length) reject();
  const assessment = recordOf(raw.assessment);
  const warnings = boundedArray(assessment.warnings, 500);
  const beforeSet = new Set(beforeIds);
  const afterSet = new Set(afterIds);
  return {
    editId: Object.hasOwn(raw, 'editId') ? uuid(raw.editId) : '',
    sourceRevision: text(raw.sourceRevision, 200),
    proposalId: uuid(raw.proposalId),
    digest: hexId(raw.digest),
    before,
    after,
    assessment: {
      description: text(assessment.description, 8000),
      readiness: readiness(assessment.readiness),
      qualityScore: typeof assessment.qualityScore === 'number' && Number.isFinite(assessment.qualityScore) ? assessment.qualityScore : reject(),
      warnings: warnings.map((warning) => text(warning, 1000)),
    },
    addedIds: afterIds.filter((id) => !beforeSet.has(id)),
    removedIds: beforeIds.filter((id) => !afterSet.has(id)),
  };
}

/** Local draft only. The host serializes bridge work with the app-wide gate. */
export class SavedPlaylistEditor {
  draft: EditorSnapshot | null = null;
  preview: EditPreview | null = null;
  improvement: ImprovementPreview | null = null;
  pendingPlaylistId: string | null = null;
  request = '';
  error = '';
  private base: EditorSnapshot | null = null;
  private generation = 0;
  private binding: { editId: string; proposalId: string; digest: string; afterIds: string[] } | null = null;
  private api: EditorApi;
  private host: EditorHost;
  constructor(api: EditorApi, host: EditorHost) { this.api = api; this.host = host; }
  get dirty(): boolean {
    return Boolean(this.draft && this.base && (this.draft.name !== this.base.name || this.draft.tracks.length !== this.base.tracks.length || this.draft.tracks.some((track, index) => track.id !== this.base?.tracks[index]?.id)));
  }
  get canSave(): boolean { return Boolean(this.draft && this.dirty && this.draft.name.trim().length > 0 && this.draft.name.trim().length <= 200 && this.draft.tracks.length <= 500); }
  /** True only while the draft still holds the exact order the bound proposal authorized. */
  get improvementBound(): boolean { return this.boundProposal() !== null; }
  private boundProposal(): { proposalId: string; digest: string } | null {
    const binding = this.binding;
    if (!binding || !this.draft || this.draft.editId !== binding.editId) return null;
    const ids = this.draft.tracks.map((track) => track.id);
    return ids.length === binding.afterIds.length && ids.every((id, index) => id === binding.afterIds[index]) ? binding : null;
  }
  private revokeImprovement(): void { this.improvement = null; this.binding = null; }
  private notify(): void { this.host.dirtyChanged(this.dirty); this.host.changed(); }
  invalidatePreview(): void { this.generation++; this.preview = null; this.host.changed(); }
  resetAfterScan(): void {
    this.revokeImprovement();
    this.invalidatePreview();
    if (this.dirty) return;
    this.draft = this.base = null; this.pendingPlaylistId = null; this.request = ''; this.error = '';
    this.invalidatePreview(); this.notify();
  }
  private accept(snapshot: EditorSnapshot): void {
    this.revokeImprovement();
    this.base = copy(snapshot); this.draft = copy(snapshot); this.pendingPlaylistId = null; this.error = '';
    this.invalidatePreview(); this.notify();
  }
  private fail = (error: unknown): void => {
    this.error = isConflict(error) ? 'La playlist cambió desde que abriste el editor. Tu borrador sigue aquí. Descarta los cambios para cargar la versión guardada actual.' : 'No se pudo completar la operación. Tu borrador se conserva; vuelve a intentarlo.';
    this.notify();
  };
  async open(playlistId: string): Promise<void> {
    if (!this.host.canAct()) return;
    if (this.draft?.id === playlistId && this.dirty) { this.pendingPlaylistId = null; this.host.navigate(); this.host.changed(); return; }
    if (this.dirty) { this.revokeImprovement(); this.pendingPlaylistId = playlistId; this.host.navigate(); this.host.changed(); return; }
    await this.host.perform('Abriendo editor…', () => this.api.openPlaylistEditor({ playlistId }), (snapshot, current) => {
      if (!current) { this.resetAfterScan(); return; }
      this.request = ''; this.accept(snapshot); this.host.navigate();
    }, this.fail);
  }
  cancelSwitch(): void { this.pendingPlaylistId = null; this.host.changed(); }
  async confirmSwitch(): Promise<void> {
    const next = this.pendingPlaylistId;
    if (!next || !this.host.canAct()) return;
    let current = false;
    await this.discard((value) => { current = value; });
    if (current && !this.dirty) await this.open(next);
  }
  rename(name: string): void {
    if (!this.draft || !this.host.canAct()) return;
    this.revokeImprovement();
    this.draft = { ...this.draft, name }; this.error = ''; this.invalidatePreview(); this.notify();
  }
  move(index: number, direction: -1 | 1): void {
    if (!this.draft || !this.host.canAct()) return;
    const tracks = [...this.draft.tracks]; const next = index + direction;
    if (!Number.isInteger(index) || index < 0 || next < 0 || index >= tracks.length || next >= tracks.length) return;
    [tracks[index], tracks[next]] = [tracks[next], tracks[index]];
    this.updateTracks(tracks);
  }
  remove(index: number): void {
    if (!this.draft || !this.host.canAct() || !Number.isInteger(index) || index < 0 || index >= this.draft.tracks.length) return;
    this.updateTracks(this.draft.tracks.filter((_, position) => position !== index));
  }
  private updateTracks(tracks: EditorTrack[]): void {
    if (!this.draft) return;
    this.revokeImprovement();
    this.draft = { ...this.draft, tracks: [...tracks], missingTrackCount: tracks.filter((track) => track.missing).length };
    this.error = ''; this.invalidatePreview(); this.notify();
  }
  setRequest(value: string): void {
    if (!this.host.canAct()) return;
    this.revokeImprovement();
    this.request = value; this.invalidatePreview();
  }
  async requestPreview(): Promise<void> {
    if (!this.draft || !this.host.canAct() || !this.request.trim() || this.request.length > 500 || this.draft.tracks.length < 2 || this.draft.tracks.length > 500) return;
    this.invalidatePreview(); this.error = '';
    const generation = this.generation; const draft = this.draft;
    await this.host.perform('Evaluando propuesta local…', () => this.api.previewPlaylistEdit({ editId: draft.editId, trackIds: draft.tracks.map((track) => track.id), request: this.request.trim() }), (preview, current) => {
      if (!current || generation !== this.generation || this.draft?.editId !== draft.editId || preview.editId !== draft.editId || preview.revision !== draft.revision) return;
      this.preview = preview; this.host.changed();
    }, (error) => { if (generation === this.generation) this.fail(error); });
  }
  applyPreview(): void {
    if (!this.preview || !this.draft || !this.host.canAct() || this.preview.editId !== this.draft.editId || this.preview.revision !== this.draft.revision || this.preview.assessment.readiness === 'blocked') return;
    this.updateTracks(this.preview.tracks);
  }
  /**
   * Show a bounded improvement preview without applying or saving anything. The payload
   * must match the current session revision and the exact current draft order, so a late
   * result from another session or an older draft can never become applicable.
   */
  setImprovementPreview(value: unknown, editId?: string): boolean {
    if (!this.draft || !this.host.canAct() || (editId !== undefined && editId !== this.draft.editId)) return false;
    let parsed: ImprovementPreview;
    try { parsed = improvementPreview(value); } catch { return false; }
    if (parsed.editId && parsed.editId !== this.draft.editId) return false;
    if (parsed.sourceRevision !== this.draft.revision || !sameOrder(parsed.before, this.draft.tracks)) return false;
    this.improvement = parsed; this.host.changed();
    return true;
  }
  /**
   * Explicit local apply. Only the in-memory draft changes, and it becomes bound to the
   * exact proposal so the dedicated save can prove the same order later.
   */
  applyImprovementPreview(): boolean {
    const preview = this.improvement;
    if (!preview || !this.draft || !this.host.canAct()) return false;
    if (preview.editId && preview.editId !== this.draft.editId) { this.revokeImprovement(); this.host.changed(); return false; }
    if (preview.sourceRevision !== this.draft.revision || !sameOrder(preview.before, this.draft.tracks)) { this.revokeImprovement(); this.host.changed(); return false; }
    if (preview.assessment.readiness === 'blocked') return false;
    const editId = preview.editId || this.draft.editId;
    const afterIds = preview.after.map((track) => track.id);
    this.updateTracks(preview.after.map((track) => ({ ...track })));
    this.binding = { editId, proposalId: preview.proposalId, digest: preview.digest, afterIds };
    this.host.changed();
    return true;
  }
  async save(): Promise<void> {
    if (!this.draft || !this.canSave || !this.host.canAct()) return;
    const draft = this.draft;
    const name = draft.name.trim();
    const bound = this.boundProposal();
    if (bound) {
      await this.host.perform('Guardando cambios…', () => this.api.savePlaylistImprovement({ editId: draft.editId, name, proposalId: bound.proposalId, digest: bound.digest, draftIds: draft.tracks.map((track) => track.id) }), (snapshot) => this.accept(snapshot), this.fail);
      return;
    }
    await this.host.perform('Guardando cambios…', () => this.api.savePlaylistEdit({ editId: draft.editId, name, trackIds: draft.tracks.map((track) => track.id) }), (snapshot) => this.accept(snapshot), this.fail);
  }
  async discard(after?: (currentRoute: boolean) => void): Promise<void> {
    if (!this.draft || !this.host.canAct()) return;
    const draft = this.draft;
    await this.host.perform('Recargando versión guardada…', async () => {
      try { return await this.api.discardPlaylistEdit({ editId: draft.editId }); }
      catch (error) { if (!isConflict(error)) throw error; return this.api.openPlaylistEditor({ playlistId: draft.id }); }
    }, (snapshot, current) => { this.accept(snapshot); after?.(current); }, this.fail);
  }
}
