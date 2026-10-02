import type { Readiness, Track } from './model.js';
export interface EditorTrack extends Track { missing: boolean; }
export interface EditorSnapshot { editId: string; revision: string; id: string; name: string; tracks: EditorTrack[]; missingTrackCount: number; }
export interface EditPreview { editId: string; previewId: string; revision: string; tracks: EditorTrack[]; assessment: { description: string; readiness: Readiness; qualityScore: number; warnings: string[] }; }
export interface EditorApi {
  openPlaylistEditor(input: { playlistId: string }): Promise<EditorSnapshot>;
  previewPlaylistEdit(input: { editId: string; trackIds: string[]; request: string }): Promise<EditPreview>;
  savePlaylistEdit(input: { editId: string; name: string; trackIds: string[] }): Promise<EditorSnapshot>;
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

/** Local draft only. The host serializes bridge work with the app-wide gate. */
export class SavedPlaylistEditor {
  draft: EditorSnapshot | null = null;
  preview: EditPreview | null = null;
  pendingPlaylistId: string | null = null;
  request = '';
  error = '';
  private base: EditorSnapshot | null = null;
  private generation = 0;
  private api: EditorApi;
  private host: EditorHost;
  constructor(api: EditorApi, host: EditorHost) { this.api = api; this.host = host; }
  get dirty(): boolean {
    return Boolean(this.draft && this.base && (this.draft.name !== this.base.name || this.draft.tracks.length !== this.base.tracks.length || this.draft.tracks.some((track, index) => track.id !== this.base?.tracks[index]?.id)));
  }
  get canSave(): boolean { return Boolean(this.draft && this.dirty && this.draft.name.trim().length > 0 && this.draft.name.trim().length <= 200 && this.draft.tracks.length <= 500); }
  private notify(): void { this.host.dirtyChanged(this.dirty); this.host.changed(); }
  invalidatePreview(): void { this.generation++; this.preview = null; this.host.changed(); }
  resetAfterScan(): void {
    this.invalidatePreview();
    if (this.dirty) return;
    this.draft = this.base = null; this.pendingPlaylistId = null; this.request = ''; this.error = '';
    this.invalidatePreview(); this.notify();
  }
  private accept(snapshot: EditorSnapshot): void {
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
    if (this.dirty) { this.pendingPlaylistId = playlistId; this.host.navigate(); this.host.changed(); return; }
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
    this.draft = { ...this.draft, tracks: [...tracks], missingTrackCount: tracks.filter((track) => track.missing).length };
    this.error = ''; this.invalidatePreview(); this.notify();
  }
  setRequest(value: string): void {
    if (!this.host.canAct()) return;
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
  async save(): Promise<void> {
    if (!this.draft || !this.canSave || !this.host.canAct()) return;
    const draft = this.draft;
    await this.host.perform('Guardando cambios…', () => this.api.savePlaylistEdit({ editId: draft.editId, name: draft.name.trim(), trackIds: draft.tracks.map((track) => track.id) }), (snapshot) => this.accept(snapshot), this.fail);
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
