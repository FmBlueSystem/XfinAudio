import type { Readiness, Track } from './model.js';
import { userErrorMessage } from './errors.js';
export type SeratoExportSource = { kind: 'review'; reviewId: string } | { kind: 'saved'; playlistId: string }
  | { kind: 'metadata'; status: 'complete' | 'incomplete'; missingField: 'bpm' | 'camelot_key' | 'energy_level' | null; trackIds: string[] };
function copySource(source: SeratoExportSource): SeratoExportSource {
  if (source.kind === 'metadata') return {kind: 'metadata', status: source.status, missingField: source.missingField, trackIds: [...source.trackIds]};
  return source.kind === 'review' ? {kind: 'review', reviewId: source.reviewId} : {kind: 'saved', playlistId: source.playlistId};
}
export interface SeratoDestination { destinationId: string; label: string; }
export interface SeratoExportPreview {
  previewId: string; sourceRevision: string; filename: string; destinationLabel: string; trackCount: number;
  readiness: Readiness; warnings: string[]; blockers: string[]; canCommit: boolean;
  tracks: (Track & { missing?: boolean })[]; backup: { required: boolean };
}
export interface SeratoExportReceipt { receiptId: string; filename: string; destinationLabel: string; trackCount: number; validated: true; backupCreated: boolean; }
export interface SeratoExportApi {
  chooseSeratoDestination(): Promise<SeratoDestination | null>;
  previewSeratoExport(input: { source: SeratoExportSource; destinationId: string; name: string }): Promise<SeratoExportPreview>;
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
  name = '';
  preview: SeratoExportPreview | null = null;
  receipt: SeratoExportReceipt | null = null;
  pending: 'destination' | 'preview' | 'commit' | 'reveal' | null = null;
  error = '';
  status = '';
  private generation = 0;
  private api: SeratoExportApi;
  private host: SeratoExportHost;
  constructor(api: SeratoExportApi, host: SeratoExportHost) { this.api = api; this.host = host; }
  get canPreview(): boolean { return !this.pending && Boolean(this.source && this.destination && validSeratoName(this.name)); }
  get canCommit(): boolean {
    const preview = this.preview;
    return !this.pending && Boolean(preview && preview.previewId && preview.canCommit && ['ready', 'needs_review'].includes(preview.readiness)
      && preview.blockers.length === 0 && preview.trackCount > 0 && preview.tracks.length === preview.trackCount && !preview.tracks.some((track) => track.missing));
  }
  invalidatePreview(): void { this.generation++; this.preview = null; this.host.changed(); }
  setSource(source: SeratoExportSource | null, suggestedName?: string): void {
    this.source = source ? copySource(source) : null;
    if (suggestedName !== undefined) this.name = suggestedName;
    this.error = '';
    if (this.pending !== 'commit') this.status = '';
    this.invalidatePreview();
  }
  setName(value: string): void {
    if (this.name === value) return;
    this.name = value; this.error = ''; this.invalidatePreview();
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
      this.status = ''; this.invalidatePreview();
    }, (error) => { if (generation === this.generation) this.fail(error); });
  }
  async requestPreview(): Promise<void> {
    if (!this.canPreview || !this.source || !this.destination || !this.host.canAct()) return;
    this.invalidatePreview(); this.status = '';
    const generation = this.generation;
    const input = { source: copySource(this.source), destinationId: this.destination.destinationId, name: this.name.trim() };
    await this.run('preview', 'Preparando vista previa de Serato…', () => this.api.previewSeratoExport(input), (preview, current) => {
      if (!current || generation !== this.generation) return;
      this.preview = preview; this.status = 'Vista previa preparada. Revisa las pistas y los avisos antes de exportar.'; this.host.changed();
    }, (error) => { if (generation === this.generation) this.fail(error); });
  }
  async commit(): Promise<void> {
    if (!this.canCommit || !this.preview || !this.host.canAct()) return;
    const previewId = this.preview.previewId;
    this.status = 'Confirma la exportación en el diálogo del sistema. Una vez iniciada, espera a que finalice.';
    await this.run('commit', 'Confirmando exportación a Serato…', () => this.api.commitSeratoExport({ previewId }), (result) => {
      if ('cancelled' in result) { this.status = 'Exportación cancelada antes de escribir. Puedes revisar la vista previa y volver a confirmar.'; return; }
      // Publication may already have finished; navigation or a different selection must never discard its receipt.
      this.receipt = result; this.status = `Crate exportado y validado: ${result.filename}`; this.invalidatePreview();
    }, (error) => { this.invalidatePreview(); this.status = 'No se pudo confirmar el resultado de la exportación.'; this.fail(error); });
  }
  async reveal(): Promise<void> {
    if (!this.receipt?.validated) return;
    const receiptId = this.receipt.receiptId;
    await this.run('reveal', 'Mostrando el crate exportado…', () => this.api.revealSeratoExport({ receiptId }), () => {}, (error) => this.fail(error));
  }
}
