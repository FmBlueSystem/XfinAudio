import type { Readiness, Track } from './model.js';
import { errorCode, userErrorMessage } from './errors.js';
export type SeratoExportSource = { kind: 'review'; reviewId: string } | { kind: 'saved'; playlistId: string }
  | { kind: 'metadata'; status: 'complete' | 'incomplete'; missingField: 'bpm' | 'camelot_key' | 'energy_level' | null; trackIds: string[] };
function copySource(source: SeratoExportSource): SeratoExportSource {
  if (source.kind === 'metadata') return {kind: 'metadata', status: source.status, missingField: source.missingField, trackIds: [...source.trackIds]};
  return source.kind === 'review' ? {kind: 'review', reviewId: source.reviewId} : {kind: 'saved', playlistId: source.playlistId};
}
export interface SeratoDestination { destinationId: string; label: string; }
/** One crate a split export will create or replace, as the core planned it; the parent comes first. */
export interface SeratoExportCrate { name: string; trackCount: number; action: 'create' | 'replace'; }
/** One crate file a split export wrote; the parent comes first. */
export interface SeratoExportFile { name: string; trackCount: number; }
export interface SeratoExportPreview {
  previewId: string; sourceRevision: string; filename: string; destinationLabel: string; trackCount: number;
  readiness: Readiness; warnings: string[]; blockers: string[]; canCommit: boolean;
  tracks: (Track & { missing?: boolean })[]; parentsToCreate: string[]; backup: { required: boolean };
  /** Present only for a split: every crate of the tree, parent first. */
  crates?: SeratoExportCrate[];
}
export interface SeratoExportReceipt { receiptId: string; filename: string; destinationLabel: string; trackCount: number; validated: true; backupCreated: boolean; parentsCreated: string[]; files?: SeratoExportFile[]; }
/** `%%` is Serato's nesting separator; the user reads a nested ancestor as «XfinAudio › Metadata». */
export function parentCrateLabel(name: string): string { return name.split('%%').join(' › '); }
/** A crate file name as the DJ reads it: no extension, and nesting shown as «XfinAudio › Set». */
export function crateTreeLabel(name: string): string { return parentCrateLabel(name.replace(/\.crate$/i, '')); }
/** The tramo size is a whole number of tracks; below two there is nothing to split. */
export const SPLIT_MIN_TRACKS = 2;
export const SPLIT_MAX_TRACKS = 50;
export const SPLIT_DEFAULT_TRACKS = 5;
export function validSegmentSize(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= SPLIT_MIN_TRACKS && value <= SPLIT_MAX_TRACKS;
}
/**
 * One line per crate of a split export, parent first, in the exact wording the native
 * confirmation uses; empty for today's single crate so nothing new is said.
 */
export function crateTreeLines(crates: readonly SeratoExportCrate[] | undefined): string[] {
  if (!crates?.length) return [];
  return [
    `Se escribirán ${crates.length} ${crates.length === 1 ? 'crate' : 'crates'}:`,
    ...crates.map((crate) => `· «${crateTreeLabel(crate.name)}» · ${crate.trackCount} ${crate.trackCount === 1 ? 'pista' : 'pistas'} · ${crate.action === 'replace' ? 'se reemplaza' : 'se crea'}`),
  ];
}
/** The receipt names every crate a split export wrote; empty for a single crate. */
export function receiptCrateLines(files: readonly SeratoExportFile[] | undefined): string[] {
  if (!files?.length) return [];
  return [`Crates escritos: ${files.length}`, ...files.map((file) => `· «${crateTreeLabel(file.name)}» · ${file.trackCount} ${file.trackCount === 1 ? 'pista' : 'pistas'}`)];
}
/** The status after a confirmed export: a tree says how many crates were written at once. */
export function receiptNotice(receipt: { filename: string; files?: readonly SeratoExportFile[] }): string {
  const count = receipt.files?.length ?? 0;
  return count
    ? `Árbol exportado a Serato: ${count} ${count === 1 ? 'crate' : 'crates'}`
    : `Crate exportado y validado: ${receipt.filename}`;
}
/** One Spanish sentence about the ancestor crates a confirmed commit will create; empty when there are none. */
export function parentCratesLine(names: string[]): string {
  const shown = names.map(parentCrateLabel); if (!shown.length) return '';
  return shown.length === 1 ? `Se creará el crate «${shown[0]}»` : `Se crearán los crates ${shown.map((name) => `«${name}»`).join(', ')}`;
}
export interface SeratoExportApi {
  chooseSeratoDestination(): Promise<SeratoDestination | null>;
  /** Runs the same discovery as the picker with no native dialog, so the screen needs no folder step. */
  detectSeratoDestination(): Promise<SeratoDestination | null>;
  /** A generated set sends no name: the core proposes «<style> <day>-<month>» itself. */
  previewSeratoExport(input: { source: SeratoExportSource; destinationId: string; name?: string; segmentSize?: number }): Promise<SeratoExportPreview>;
  commitSeratoExport(input: { previewId: string }): Promise<SeratoExportReceipt | { cancelled: true }>;
  revealSeratoExport(input: { receiptId: string }): Promise<void>;
}
export interface SeratoExportHost {
  canAct(): boolean;
  changed(): void;
  /** Use the app-wide operation gate, without cancellation. Apply commit results even after navigation. */
  perform<T>(label: string, task: () => Promise<T>, apply: (value: T, currentRoute: boolean) => void, failure: (error: unknown) => void): Promise<void>;
}
export function validSeratoName(value: string): boolean {
  const name = value.trim();
  return Boolean(name) && name.length <= 200 && name !== '.' && name !== '..' && !/[\\/:\p{C}]/u.test(name)
    && new TextEncoder().encode(`${name}.crate`).length <= 240;
}
/** Holds only opaque capabilities. Preview never writes; only the explicit commit invokes native confirmation. */
export class SeratoExportController {
  source: SeratoExportSource | null = null;
  destination: SeratoDestination | null = null;
  /** The destination came from automatic detection, not from the manual picker. */
  destinationDetected = false;
  /** Detection ran and found nothing on the music drive; the manual choice is the way forward. */
  detectionMissed = false;
  name = '';
  /** The tramo size of this export only; null is today's single crate. */
  segmentSize: number | null = null;
  preview: SeratoExportPreview | null = null;
  receipt: SeratoExportReceipt | null = null;
  pending: 'destination' | 'detect' | 'preview' | 'commit' | 'reveal' | null = null;
  error = '';
  status = '';
  private generation = 0;
  private api: SeratoExportApi;
  private host: SeratoExportHost;
  constructor(api: SeratoExportApi, host: SeratoExportHost) { this.api = api; this.host = host; }
  get canPreview(): boolean {
    return !this.pending && Boolean(this.source && this.destination && (this.automaticName || validSeratoName(this.name)));
  }
  /** A generated set has no crate name of its own; the core names it from the style and the date. */
  get automaticName(): boolean { return this.source?.kind === 'review' && !this.name.trim(); }
  get canCommit(): boolean {
    const preview = this.preview;
    return !this.pending && Boolean(preview && preview.previewId && preview.canCommit && ['ready', 'needs_review'].includes(preview.readiness)
      && preview.blockers.length === 0 && preview.trackCount > 0 && preview.tracks.length === preview.trackCount && !preview.tracks.some((track) => track.missing));
  }
  invalidatePreview(): void { this.generation++; this.preview = null; this.host.changed(); }
  /**
   * A stopped or restarted core forgets every id it issued, so the destination and the preview
   * are useless. The source, the crate name and a published receipt stay: using the page again
   * detects the folder again instead of asking the user to find it.
   */
  forgetCore(): void {
    this.destination = null; this.destinationDetected = false; this.detectionMissed = false;
    this.error = ''; this.status = '';
    this.invalidatePreview();
  }
  setSource(source: SeratoExportSource | null, suggestedName?: string): void {
    this.source = source ? copySource(source) : null;
    // A new export starts with today's single crate; the split is never remembered.
    this.segmentSize = null;
    if (suggestedName !== undefined) this.name = suggestedName;
    this.error = '';
    if (this.pending !== 'commit') this.status = '';
    this.invalidatePreview();
    if (!this.source) { this.destinationDetected = false; this.detectionMissed = false; return; }
    // A destination the user already chose keeps winning; otherwise the screen finds it alone.
    if (this.destination) return;
    this.detectionMissed = false;
    void this.detectDestination();
  }
  setName(value: string): void {
    if (this.name === value) return;
    this.name = value; this.error = ''; this.invalidatePreview();
  }
  /** `null` means «No dividir»; anything but a whole 2-50 tracks is refused, never rounded. */
  setSegmentSize(value: number | null): void {
    // A metadata worklist is not a set: the core refuses a tramo size for it, so the choice is never held.
    if (value !== null && (!validSegmentSize(value) || this.source?.kind === 'metadata')) return;
    if (this.segmentSize === value) return;
    this.segmentSize = value; this.error = ''; this.invalidatePreview();
  }
  private async run<T>(kind: NonNullable<SeratoExportController['pending']>, label: string, task: () => Promise<T>, apply: (value: T, current: boolean) => void, failure: (error: unknown) => void): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    this.pending = kind; this.error = ''; this.host.changed();
    try { await this.host.perform(label, task, apply, failure); }
    catch (error) { failure(error); }
    finally { this.pending = null; this.host.changed(); }
  }
  private fail(error: unknown): void { this.error = userErrorMessage(error); this.host.changed(); }
  async chooseDestination(): Promise<void> {
    const generation = this.generation;
    await this.run('destination', 'Elige la carpeta _Serato_ de destino', () => this.api.chooseSeratoDestination(), (destination, current) => {
      if (!current || generation !== this.generation || !destination) return;
      if (destination.destinationId === this.destination?.destinationId && destination.label === this.destination.label) return;
      this.destination = { destinationId: destination.destinationId, label: destination.label };
      this.destinationDetected = false; this.detectionMissed = false;
      this.status = ''; this.invalidatePreview();
    }, (error) => { if (generation === this.generation) this.fail(error); });
  }
  /** Automatic detection is the first step whenever a source is opened; it never shows a dialog. */
  async detectDestination(): Promise<void> {
    // An older bridge without the action keeps the choose-first flow instead of failing the screen.
    if (typeof this.api.detectSeratoDestination !== 'function' || this.destination) return;
    const generation = this.generation;
    // A search result belongs to the controller, not to a route: opening the export screen
    // navigates right after setSource, so route currency cannot decide whether it applies.
    await this.run('detect', 'Buscando la carpeta _Serato_ del disco de música…', () => this.api.detectSeratoDestination(), (destination) => {
      if (generation !== this.generation || this.destination) return;
      if (!destination) { this.detectionMissed = true; this.destinationDetected = false; this.host.changed(); return; }
      this.destination = { destinationId: destination.destinationId, label: destination.label };
      this.destinationDetected = true; this.detectionMissed = false;
      this.status = this.automaticName
        ? 'Carpeta _Serato_ detectada automáticamente. El nombre del crate se propone solo, con el estilo y la fecha del día.'
        : 'Carpeta _Serato_ detectada automáticamente en el disco de música.';
      this.invalidatePreview();
    }, (error) => { if (generation === this.generation) this.fail(error); });
  }
  async requestPreview(): Promise<void> {
    if (!this.canPreview || !this.source || !this.destination || !this.host.canAct()) return;
    this.invalidatePreview(); this.status = '';
    const generation = this.generation;
    const input: { source: SeratoExportSource; destinationId: string; name?: string; segmentSize?: number } = {
      source: copySource(this.source),
      destinationId: this.destination.destinationId,
    };
    // An empty name is not sent at all: the core owns the automatic name and its collision suffix.
    if (!this.automaticName) input.name = this.name.trim();
    // No split sends no size at all, so today's single crate keeps the same request.
    if (this.segmentSize !== null) input.segmentSize = this.segmentSize;
    await this.run('preview', 'Preparando vista previa de Serato…', () => this.api.previewSeratoExport(input), (preview, current) => {
      if (!current || generation !== this.generation) return;
      this.preview = preview; this.status = 'Vista previa preparada. Revisa las pistas y los avisos antes de exportar.'; this.host.changed();
    }, (error) => {
      if (generation !== this.generation) return;
      if (errorCode(error) !== 'unknown_destination') { this.fail(error); return; }
      // The core forgot the id and the host's single re-detection found nothing: this is the
      // honest not-found path, never the "choose a valid folder" refusal.
      this.destination = null; this.destinationDetected = false; this.detectionMissed = true;
      this.error = ''; this.status = ''; this.invalidatePreview();
    });
  }
  async commit(): Promise<void> {
    if (!this.canCommit || !this.preview || !this.host.canAct()) return;
    const previewId = this.preview.previewId;
    this.status = 'Confirma la exportación en el diálogo del sistema. Una vez iniciada, espera a que finalice.';
    await this.run('commit', 'Confirmando exportación a Serato…', () => this.api.commitSeratoExport({ previewId }), (result) => {
      if ('cancelled' in result) { this.status = 'Exportación cancelada antes de escribir. Puedes revisar la vista previa y volver a confirmar.'; return; }
      // Publication may already have finished; navigation or a different selection must never discard its receipt.
      this.receipt = result; this.status = receiptNotice(result);
      // The split belongs to the export that just finished, never to the next one.
      this.segmentSize = null; this.invalidatePreview();
    }, (error) => {
      // Serato DJ was open and nothing was written: the same preview can be confirmed once it is closed (S13).
      if (errorCode(error) === 'serato_running') { this.status = ''; this.fail(error); return; }
      this.invalidatePreview(); this.status = 'No se pudo confirmar el resultado de la exportación.'; this.fail(error);
    });
  }
  async reveal(): Promise<void> {
    if (!this.receipt?.validated) return;
    const receiptId = this.receipt.receiptId;
    await this.run('reveal', 'Mostrando el crate exportado…', () => this.api.revealSeratoExport({ receiptId }), () => {}, (error) => this.fail(error));
  }
}
