import { errorCode, userErrorMessage } from './errors.js';
export interface PreferencesSnapshot {
  revision: string; previewVolume: number; watchLibrary: boolean; recoveryWarning: boolean; libraryLabels: string[];
  capabilities: { loudnessWriteback: boolean; providers: boolean; language: 'es' };
}
export interface PreferencesApi {
  getPreferences(): Promise<PreferencesSnapshot>;
  savePreferences(input: { revision: string; previewVolume: number; watchLibrary: boolean }): Promise<PreferencesSnapshot>;
}
export interface PreferencesHost {
  canAct(): boolean; changed(): void; dirtyChanged(dirty: boolean): void;
  applied(snapshot: PreferencesSnapshot, reason: 'load' | 'save'): void;
  perform<T>(label: string, task: () => Promise<T>, apply: (value: T, currentRoute: boolean) => void, failure: (error: unknown) => void): Promise<void>;
}
const validVolume = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
function copy(value: PreferencesSnapshot): PreferencesSnapshot {
  if (!value || !/^[a-f0-9]{64}$/.test(value.revision) || !validVolume(value.previewVolume) || typeof value.watchLibrary !== 'boolean'
    || typeof value.recoveryWarning !== 'boolean' || !Array.isArray(value.libraryLabels) || !value.libraryLabels.every((label) => typeof label === 'string')
    || typeof value.capabilities?.loudnessWriteback !== 'boolean' || typeof value.capabilities.providers !== 'boolean' || value.capabilities.language !== 'es') {
    throw Object.assign(new Error('Invalid preferences snapshot'), { code: 'settings_unavailable' });
  }
  return { revision: value.revision, previewVolume: value.previewVolume, watchLibrary: value.watchLibrary, recoveryWarning: value.recoveryWarning,
    libraryLabels: [...value.libraryLabels], capabilities: { loudnessWriteback: value.capabilities.loudnessWriteback, providers: value.capabilities.providers, language: 'es' } };
}

/** Local edits never change playback or watching; only persisted load/save snapshots reach applied(). */
export class PreferencesController {
  private draft: PreferencesSnapshot | null = null;
  private base: PreferencesSnapshot | null = null;
  private conflict = false;
  private api: PreferencesApi;
  private host: PreferencesHost;
  pending = false;
  error = '';
  constructor(api: PreferencesApi, host: PreferencesHost) { this.api = api; this.host = host; }
  get snapshot(): PreferencesSnapshot | null { return this.draft; }
  get dirty(): boolean { return Boolean(this.draft && this.base && (this.draft.previewVolume !== this.base.previewVolume || this.draft.watchLibrary !== this.base.watchLibrary)); }
  get canSave(): boolean { return !this.pending && !this.conflict && this.dirty && Boolean(this.draft && validVolume(this.draft.previewVolume) && typeof this.draft.watchLibrary === 'boolean'); }
  private notify(): void { this.host.dirtyChanged(this.dirty); this.host.changed(); }
  private accept(value: PreferencesSnapshot, reason: 'load' | 'save'): void {
    const snapshot = copy(value);
    this.base = snapshot; this.draft = copy(snapshot); this.conflict = false; this.error = '';
    this.host.applied(copy(snapshot), reason); this.notify();
  }
  private fail = (error: unknown): void => {
    if (errorCode(error) === 'stale_settings') {
      this.conflict = true;
      this.error = 'Las preferencias guardadas cambiaron. Tu borrador se conserva; descarta los cambios y actualiza para cargar la versión vigente.';
    } else this.error = userErrorMessage(error);
    this.notify();
  };
  private async run(label: string, task: () => Promise<PreferencesSnapshot>, reason: 'load' | 'save'): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    this.pending = true; this.error = ''; this.host.changed();
    try { await this.host.perform(label, task, (value) => this.accept(value, reason), this.fail); }
    catch (error) { this.fail(error); }
    finally { this.pending = false; this.notify(); }
  }
  async load(): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    if (this.dirty) { this.error = 'Tienes cambios sin guardar. Guarda el borrador o descarta los cambios antes de actualizar.'; this.notify(); return; }
    await this.run('Cargando preferencias…', () => this.api.getPreferences(), 'load');
  }
  /** Refresh folder metadata only; never accept settings revisions or apply playback. */
  async refreshLibraryLabels(): Promise<void> {
    if(this.pending||!this.host.canAct()||!this.draft||!this.base)return;
    this.pending=true;this.host.changed();
    try { await this.host.perform('Actualizando bibliotecas registradas…',()=>this.api.getPreferences(),value=>{
      const snapshot=copy(value);
      this.base={...this.base!,libraryLabels:[...snapshot.libraryLabels]};
      this.draft={...this.draft!,libraryLabels:[...snapshot.libraryLabels]};
      this.host.changed();
    },this.fail); }
    catch(error){this.fail(error);}
    finally{this.pending=false;this.host.changed();}
  }
  setVolume(value: number): void {
    if (!this.draft || this.pending || !this.host.canAct()) return;
    if (!validVolume(value)) { this.error = 'El volumen inicial debe estar entre 0 y 100 %.'; this.notify(); return; }
    this.draft = { ...this.draft, previewVolume: value }; if (!this.conflict) this.error = ''; this.notify();
  }
  setWatchLibrary(value: boolean): void {
    if (!this.draft || this.pending || !this.host.canAct()) return;
    if (typeof value !== 'boolean') { this.error = 'Elige si quieres vigilar los cambios de la biblioteca.'; this.notify(); return; }
    this.draft = { ...this.draft, watchLibrary: value }; if (!this.conflict) this.error = ''; this.notify();
  }
  async save(): Promise<void> {
    if (!this.draft || !this.canSave || !this.host.canAct()) return;
    const { revision, previewVolume, watchLibrary } = this.draft;
    await this.run('Guardando preferencias…', () => this.api.savePreferences({ revision, previewVolume, watchLibrary }), 'save');
  }
  discard(): void {
    if (!this.base || this.pending || !this.host.canAct()) return;
    this.draft = copy(this.base);
    this.error = this.conflict ? 'Borrador descartado. Pulsa Actualizar para cargar las preferencias guardadas vigentes.' : '';
    this.notify();
  }
}
