import type { SeratoDestination, SeratoExportHost, SeratoExportSource } from './serato-export.js';

/** The receipt main returns after a validated crate write; the renderer only handles its opaque id. */
export interface SeratoQuickReceipt { receiptId: string; filename: string; destinationLabel: string; trackCount: number; validated: true; backupCreated: boolean; }
/** What one quick export answered: a receipt, a block, a missing destination, or a native cancellation. */
export type SeratoQuickResult =
  | { status: 'exported'; receipt: SeratoQuickReceipt }
  | { status: 'cancelled' }
  | { status: 'blocked'; filename: string; blockers: string[] }
  | { status: 'needs_destination' };
export interface SeratoQuickExportApi {
  /** A generated set sends no name: the core proposes «<style> <day>-<month>» itself. */
  quickSeratoExport(input: { source: SeratoExportSource; name?: string }): Promise<SeratoQuickResult>;
  chooseSeratoDestination(): Promise<SeratoDestination | null>;
  revealSeratoExport(input: { receiptId: string }): Promise<void>;
}
/** The one Spanish explanation of a missing Serato folder, shared with the export page (S3). */
export const SERATO_NOT_FOUND_MESSAGE = 'No se encontró la carpeta _Serato_ en el disco de música. Abre Serato una vez con ese disco conectado para crearla; después podrás elegir la carpeta manualmente.';
/** A bridge without the operation keeps the page flow instead of failing the export button. */
export function quickExportAvailable(api: { quickSeratoExport?: unknown } | undefined): boolean {
  return typeof api?.quickSeratoExport === 'function';
}
function copySource(source: SeratoExportSource): SeratoExportSource {
  if (source.kind === 'metadata') return { kind: 'metadata', status: source.status, missingField: source.missingField, trackIds: [...source.trackIds] };
  return source.kind === 'review' ? { kind: 'review', reviewId: source.reviewId } : { kind: 'saved', playlistId: source.playlistId };
}
function crateName(filename: string): string { return filename.replace(/\.crate$/i, ''); }
/**
 * One click runs destination detection, preview and the native confirmation in main and
 * stays on the current screen. It never carries a path, a destination or a confirmation
 * flag: the receipt is the only proof of a write.
 */
export class SeratoQuickExportController {
  request: { source: SeratoExportSource; name: string } | null = null;
  notice = '';
  detail = '';
  tone: 'success' | 'blocked' | 'quiet' = 'quiet';
  blockers: string[] = [];
  receipt: SeratoQuickReceipt | null = null;
  needsDestination = false;
  pending: 'export' | 'choose' | 'reveal' | null = null;
  private api: SeratoQuickExportApi;
  private host: SeratoExportHost;
  constructor(api: SeratoQuickExportApi, host: SeratoExportHost) { this.api = api; this.host = host; }
  private async run(kind: NonNullable<SeratoQuickExportController['pending']>, label: string, task: () => Promise<unknown>, apply: (value: unknown) => void): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    this.pending = kind; this.host.changed();
    try {
      // The result belongs to the controller, not to a route: the user stays where they were,
      // and a receipt must survive any navigation that happened while the dialog was open.
      await this.host.perform(label, task, (value) => { apply(value); this.host.changed(); }, () => { this.clearResult(); this.host.changed(); });
    } catch { this.clearResult(); }
    finally { this.pending = null; this.host.changed(); }
  }
  private clearResult(): void {
    this.notice = ''; this.detail = ''; this.blockers = []; this.receipt = null;
    this.needsDestination = false; this.tone = 'quiet';
  }
  /** A stopped core voids the ids behind a notice; the export request survives so the button still works. */
  forgetCore(): void {
    this.clearResult(); this.host.changed();
  }
  async export(source: SeratoExportSource, name: string): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    this.request = { source: copySource(source), name };
    this.clearResult();
    const request = this.request;
    const input: { source: SeratoExportSource; name?: string } = { source: copySource(request.source) };
    // An empty name is not sent at all: the core owns the automatic name and its collision suffix.
    if (request.name.trim()) input.name = request.name;
    await this.run('export', 'Exportando a Serato…', () => this.api.quickSeratoExport(input), (value) => this.apply(value as SeratoQuickResult));
  }
  /** The notice offers this after a miss; a valid choice continues to the same confirmation. */
  async chooseDestination(): Promise<void> {
    const request = this.request;
    if (!request || this.pending || !this.host.canAct()) return;
    let chosen: SeratoDestination | null = null;
    await this.run('choose', 'Elige la carpeta _Serato_ de destino', () => this.api.chooseSeratoDestination(), (value) => { chosen = (value as SeratoDestination | null) ?? null; });
    if (chosen) await this.export(request.source, request.name);
  }
  async reveal(): Promise<void> {
    const receipt = this.receipt;
    if (!receipt?.validated) return;
    await this.run('reveal', 'Mostrando el crate exportado…', () => this.api.revealSeratoExport({ receiptId: receipt.receiptId }), () => {});
  }
  private apply(result: SeratoQuickResult): void {
    if (!result || typeof result !== 'object' || !['exported', 'cancelled', 'blocked', 'needs_destination'].includes(String(result.status))) throw Object.assign(new Error('Invalid export result'), { code: 'invalid_params' });
    if (result.status === 'exported') {
      const receipt = result.receipt;
      if (!receipt || typeof receipt.receiptId !== 'string' || !receipt.receiptId || receipt.validated !== true || typeof receipt.filename !== 'string' || !receipt.filename
        || typeof receipt.destinationLabel !== 'string' || typeof receipt.trackCount !== 'number' || !Number.isFinite(receipt.trackCount)) throw Object.assign(new Error('Invalid export result'), { code: 'invalid_params' });
      this.receipt = receipt; this.needsDestination = false; this.blockers = []; this.tone = 'success';
      this.notice = `Crate «${crateName(receipt.filename)}» exportado a Serato`;
      this.detail = `${receipt.filename} · ${receipt.destinationLabel} · ${receipt.trackCount} ${receipt.trackCount === 1 ? 'pista' : 'pistas'}`;
      return;
    }
    if (result.status === 'blocked') {
      this.blockers = (Array.isArray(result.blockers) ? result.blockers : []).filter((message) => typeof message === 'string');
      this.tone = 'blocked';
      this.notice = 'No se exportó nada: la selección no está lista';
      this.detail = this.blockers.length ? 'Bloqueos que impiden exportar:' : 'La vista previa no permite exportar esta selección. Revisa «Opciones de exportación».';
      return;
    }
    if (result.status === 'needs_destination') {
      this.needsDestination = true; this.tone = 'blocked';
      this.notice = 'No se encontró la carpeta _Serato_ de destino';
      this.detail = SERATO_NOT_FOUND_MESSAGE;
      return;
    }
    this.tone = 'quiet'; this.notice = 'Exportación cancelada'; this.detail = 'No se escribió nada.';
  }
}
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `serato-quick-export-${suffix}`; return node; };
const button = (suffix: string, caption: string, action: () => void, className = 'button subtle'): HTMLButtonElement => {
  const node = identify(make('button', caption, className), suffix);
  node.type = 'button'; node.addEventListener('click', action); return node;
};
/** Notice and its three actions; construction is one-time, rendering never starts an operation. */
export function createSeratoQuickExportView(root: HTMLElement, controller: SeratoQuickExportController, host: { canAct(): boolean }, advanced: (source: SeratoExportSource, name: string) => void): () => void {
  const section = make('section', '', 'operation-status'); section.id = 'serato-quick-export';
  section.setAttribute('role', 'status'); section.setAttribute('aria-live', 'polite'); section.setAttribute('aria-atomic', 'true');
  const copy = make('div', '', 'status-copy');
  const notice = identify(make('strong'), 'notice'); const detail = identify(make('span'), 'detail');
  copy.append(notice, detail);
  const blockers = identify(make('ul'), 'blockers');
  const reveal = button('reveal', 'Mostrar en Finder', () => { void controller.reveal(); });
  const choose = button('choose', 'Elegir carpeta', () => { void controller.chooseDestination(); });
  const options = button('advanced', 'Opciones de exportación', () => { const request = controller.request; if (request) advanced(request.source, request.name); }, 'text-button');
  section.append(copy, blockers, reveal, choose, options);
  root.replaceChildren(section);
  return () => {
    const blocked = !host.canAct() || controller.pending !== null;
    section.hidden = !controller.notice && controller.blockers.length === 0;
    section.classList.toggle('is-error', controller.tone === 'blocked');
    notice.textContent = controller.notice;
    detail.textContent = controller.detail;
    blockers.hidden = controller.blockers.length === 0;
    blockers.replaceChildren(...controller.blockers.map((message) => make('li', message)));
    reveal.hidden = controller.receipt === null; reveal.disabled = blocked || controller.receipt === null;
    choose.hidden = !controller.needsDestination; choose.disabled = blocked;
    options.hidden = controller.request === null; options.disabled = blocked;
  };
}
