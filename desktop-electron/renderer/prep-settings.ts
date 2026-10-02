import { errorCode, userErrorMessage } from './errors.js';
export interface PrepSelections { requiredTrackIds: string[]; excludedTrackIds: string[]; genreFocus: string; }
export interface PrepSettingsSnapshot extends PrepSelections { revision: string; unavailableRequiredCount: number; unavailableExcludedCount: number; }
export interface PrepSettingsApi { prepSettings(): Promise<PrepSettingsSnapshot>; savePrepSettings(input: PrepSelections & { revision: string; clearUnavailable: boolean }): Promise<PrepSettingsSnapshot>; }
interface Host { canAct(): boolean; read(): PrepSelections; restore(value: PrepSelections): void; changed(): void; saved(): void; perform<T>(label: string, task: () => Promise<T>, apply: (value: T) => void, failure: (error: unknown) => void): Promise<void>; }
const copy = (value: PrepSelections): PrepSelections => ({ requiredTrackIds: [...value.requiredTrackIds], excludedTrackIds: [...value.excludedTrackIds], genreFocus: value.genreFocus });
const key = (value: PrepSelections): string => JSON.stringify({ ...copy(value), requiredTrackIds: [...value.requiredTrackIds].sort(), excludedTrackIds: [...value.excludedTrackIds].sort() });
function validate(value: PrepSettingsSnapshot): PrepSettingsSnapshot {
  const lists = [value.requiredTrackIds, value.excludedTrackIds];
  if (!/^[a-f0-9]{64}$/.test(value.revision) || typeof value.genreFocus !== 'string' || value.genreFocus.length > 100 || lists.some(list => !Array.isArray(list) || list.length > 100 || list.some(id => typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id))) || [value.unavailableRequiredCount, value.unavailableExcludedCount].some(count => !Number.isInteger(count) || count < 0)) throw Object.assign(new Error('Invalid preferences'), { code: 'settings_unavailable' });
  return { ...value, ...copy(value) };
}
export class PrepSettingsController {
  snapshot: PrepSettingsSnapshot | null = null;
  pending = false;
  error = '';
  clearUnavailable = false;
  private conflict = false;
  private editVersion = 0;
  private libraryVersion = 0;
  private editedBeforeLoad = false;
  constructor(private api: PrepSettingsApi, private host: Host) {}
  get dirty(): boolean { return this.clearUnavailable || (this.snapshot ? key(this.host.read()) !== key(this.snapshot) : this.editedBeforeLoad); }
  get canSave(): boolean { return Boolean(this.snapshot) && this.dirty && !this.pending && !this.conflict; }
  libraryChanged(): void { const dirty = this.dirty; this.libraryVersion++; if (!dirty) { this.snapshot = null; this.editedBeforeLoad = false; this.clearUnavailable = false; this.conflict = false; } this.host.changed(); }
  edited(): void { this.editVersion++; this.editedBeforeLoad = true; if (!this.conflict) this.error = ''; this.host.changed(); }
  setClearUnavailable(value: boolean): void { if (!this.pending && this.host.canAct()) { this.clearUnavailable = value; this.edited(); } }
  private async run(save: boolean): Promise<void> {
    if (this.pending || !this.host.canAct() || (save && !this.canSave)) return;
    if (!save && this.dirty) { this.error = 'Conservamos tus cambios. Guarda o descarta antes de restaurar los controles.'; this.host.changed(); return; }
    const version = this.editVersion; const libraryVersion = this.libraryVersion;
    const input = { ...copy(this.host.read()), revision: this.snapshot?.revision ?? '', clearUnavailable: this.clearUnavailable };
    this.pending = true; this.error = ''; this.host.changed();
    const fail = (error: unknown): void => { this.conflict = errorCode(error) === 'stale_settings'; this.error = userErrorMessage(error); };
    try { await this.host.perform(save ? 'Guardando controles de preparación…' : 'Restaurando controles guardados…', () => save ? this.api.savePrepSettings(input) : this.api.prepSettings(), value => {
      if (libraryVersion !== this.libraryVersion) return;
      this.snapshot = validate(value); this.conflict = false;
      if (this.editVersion === version) { this.host.restore(copy(this.snapshot)); this.clearUnavailable = false; this.editedBeforeLoad = false; }
      if (save) this.host.saved();
    }, fail); } catch (error) { fail(error); }
    finally { this.pending = false; this.host.changed(); }
  }
  async load(): Promise<void> { await this.run(false); }
  async save(): Promise<void> { await this.run(true); }
  discard(): void { if (this.pending || !this.host.canAct()) return; this.host.restore(this.snapshot ? copy(this.snapshot) : { requiredTrackIds: [], excludedTrackIds: [], genreFocus: '' }); this.clearUnavailable = false; this.editedBeforeLoad = false; this.editVersion++; this.error = this.conflict ? 'Actualiza para cargar los controles guardados vigentes.' : ''; this.host.changed(); }
}
