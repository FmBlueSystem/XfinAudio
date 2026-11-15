import type { GenreCatalog, GenreRequest } from './genre-picker.js';
import { validateGenreCatalog } from './genre-picker.js';
import { errorCode, userErrorMessage } from './errors.js';
export interface PrepSelections { requiredTrackIds: string[]; excludedTrackIds: string[]; genreFocus: string; }
export type PrepSlotRole = 'warmup' | 'peak_time' | 'chill';
/** The Prep form the core accepted in the last successful generation. */
export interface PrepFormSnapshot { targetTrackCount: number | null; targetMinutes: number | null; strategy: string | null; slotRole: PrepSlotRole | null; name: string | null; startTrackId: string | null; endTrackId: string | null; }
export const EMPTY_PREP_FORM: PrepFormSnapshot = { targetTrackCount: null, targetMinutes: null, strategy: null, slotRole: null, name: null, startTrackId: null, endTrackId: null };
export interface PrepSettingsSnapshot extends PrepSelections { revision: string; unavailableRequiredCount: number; unavailableExcludedCount: number; lastForm: PrepFormSnapshot; }
export interface PrepSettingsApi { prepSettings(): Promise<PrepSettingsSnapshot>; savePrepSettings(input: PrepSelections & { revision: string; clearUnavailable: boolean }): Promise<PrepSettingsSnapshot>; prepGenres?(input: GenreRequest): Promise<unknown>; }
interface Host { canAct(): boolean; read(): PrepSelections; restore(value: PrepSelections): void; remembered(value: PrepFormSnapshot): void; changed(): void; saved(): void; perform<T>(label: string, task: () => Promise<T>, apply: (value: T) => void, failure: (error: unknown) => void): Promise<void>; }
const copy = (value: PrepSelections): PrepSelections => ({ requiredTrackIds: [...value.requiredTrackIds], excludedTrackIds: [...value.excludedTrackIds], genreFocus: value.genreFocus });
const key = (value: PrepSelections): string => JSON.stringify({ ...copy(value), requiredTrackIds: [...value.requiredTrackIds].sort(), excludedTrackIds: [...value.excludedTrackIds].sort() });
const invalid = (): never => { throw Object.assign(new Error('Invalid preferences'), { code: 'settings_unavailable' }); };
const digest = (value: unknown): boolean => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
function validatePrepForm(value: unknown): PrepFormSnapshot {
  // Additive section: a payload without it leaves the form untouched instead of
  // failing the whole load, like the other additive settings sections.
  if (value === undefined || value === null) return { ...EMPTY_PREP_FORM };
  if (typeof value !== 'object' || Array.isArray(value)) return invalid();
  const form = value as Record<string, unknown>;
  const set = (field: keyof PrepFormSnapshot): boolean => form[field] !== null && form[field] !== undefined;
  const check = (field: keyof PrepFormSnapshot, accepted: (item: unknown) => boolean): void => { if (set(field) && !accepted(form[field])) invalid(); };
  check('targetTrackCount', (item) => Number.isInteger(item) && Number(item) >= 2 && Number(item) <= 100);
  check('targetMinutes', (item) => typeof item === 'number' && Number.isFinite(item) && item > 0 && item <= 600);
  check('strategy', (item) => typeof item === 'string' && /^[a-z][a-z0-9_]{0,49}$/.test(item));
  check('slotRole', (item) => typeof item === 'string' && ['warmup', 'peak_time', 'chill'].includes(item));
  check('name', (item) => typeof item === 'string' && item.length <= 200 && !/[\x00-\x1f]/.test(item));
  check('startTrackId', digest); check('endTrackId', digest);
  const pick = <K extends keyof PrepFormSnapshot>(field: K): PrepFormSnapshot[K] => (set(field) ? form[field] : null) as PrepFormSnapshot[K];
  return { targetTrackCount: pick('targetTrackCount'), targetMinutes: pick('targetMinutes'), strategy: pick('strategy'), slotRole: pick('slotRole'), name: pick('name'), startTrackId: pick('startTrackId'), endTrackId: pick('endTrackId') };
}
function validate(value: PrepSettingsSnapshot): PrepSettingsSnapshot {
  const lists = [value.requiredTrackIds, value.excludedTrackIds];
  if (!/^[a-f0-9]{64}$/.test(value.revision) || typeof value.genreFocus !== 'string' || value.genreFocus.length > 100 || lists.some(list => !Array.isArray(list) || list.length > 100 || list.some(id => typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id))) || [value.unavailableRequiredCount, value.unavailableExcludedCount].some(count => !Number.isInteger(count) || count < 0)) invalid();
  return { ...value, ...copy(value), lastForm: validatePrepForm(value.lastForm) };
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
      const snapshot = validate(value);
      this.snapshot = snapshot; this.conflict = false;
      if (this.editVersion === version) { this.host.restore(copy(snapshot)); if (!save) this.host.remembered(snapshot.lastForm); this.clearUnavailable = false; this.editedBeforeLoad = false; }
      if (save) this.host.saved();
    }, fail); } catch (error) { fail(error); }
    finally { this.pending = false; this.host.changed(); }
  }
  async load(): Promise<void> { await this.run(false); }
  async save(): Promise<void> { await this.run(true); }
  /** The read-only genre catalog. It is not persisted state, so it never touches the snapshot. */
  async genres(input: GenreRequest): Promise<GenreCatalog> {
    if (typeof this.api.prepGenres !== 'function') throw Object.assign(new Error('Genre catalog unavailable'), { code: 'genres_unavailable' });
    return validateGenreCatalog(await this.api.prepGenres(input));
  }
  discard(): void { if (this.pending || !this.host.canAct()) return; this.host.restore(this.snapshot ? copy(this.snapshot) : { requiredTrackIds: [], excludedTrackIds: [], genreFocus: '' }); this.clearUnavailable = false; this.editedBeforeLoad = false; this.editVersion++; this.error = this.conflict ? 'Actualiza para cargar los controles guardados vigentes.' : ''; this.host.changed(); }
}
