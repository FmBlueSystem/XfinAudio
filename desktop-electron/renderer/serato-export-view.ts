import type { Readiness } from './model.js';
import type { SeratoExportController } from './serato-export.js';
import { validSeratoName } from './serato-export.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `serato-export-${suffix}`; return node; };
const button = (suffix: string, caption: string, action: () => void, primary = false): HTMLButtonElement => {
  const node = identify(make('button', caption, `button ${primary ? 'primary' : 'subtle'}`), suffix);
  node.type = 'button'; node.addEventListener('click', action); return node;
};
const readiness: Record<Readiness, string> = { ready: 'Lista para exportar', needs_review: 'Revisión recomendada', blocked: 'Necesita atención' };

/** Construct once, then refresh from the app gate and controller.changed without replacing focused inputs. */
export function createSeratoExportView(root: HTMLElement, controller: SeratoExportController, host: { canAct(): boolean }): () => void {
  const setup = make('section', '', 'surface prep-form'); setup.setAttribute('aria-labelledby', 'serato-export-heading');
  const nextStep = identify(make('p', '', 'field-hint'), 'next-step'); nextStep.setAttribute('aria-live', 'polite');
  const source = identify(make('p', '', 'field-hint'), 'source');
  const nameLabel = make('label', 'Nombre del crate'); nameLabel.setAttribute('for', 'serato-export-name');
  const name = identify(make('input'), 'name'); name.maxLength = 200; name.required = true; name.autocomplete = 'off'; name.setAttribute('aria-describedby', 'serato-export-name-hint');
  name.addEventListener('input', () => controller.setName(name.value));
  const hint = identify(make('p', 'Usa un nombre breve, sin barras, dos puntos ni caracteres de control. Los nombres con muchos caracteres acentuados pueden necesitar acortarse.', 'field-hint'), 'name-hint');
  const destination = identify(make('p', '', 'field-hint'), 'destination'); destination.setAttribute('aria-live', 'polite');
  const choose = button('choose', 'Elegir carpeta _Serato_', () => { void controller.chooseDestination(); });
  const previewButton = button('preview', 'Ver vista previa', () => { void controller.requestPreview(); });
  const actions = make('div', '', 'editor-actions'); actions.append(choose, previewButton);
  setup.append(identify(make('h3', 'Exportar crate a Serato'), 'heading'), nextStep, source, nameLabel, name, hint, destination, actions,
    make('p', 'Elige la carpeta _Serato_ que contiene Subcrates. El crate se exportará directamente al destino elegido. La vista previa no escribe archivos ni modifica audio o database V2.', 'field-hint'));
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const status = identify(make('p', '', 'field-hint'), 'status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  const pending = identify(make('p', 'La exportación está en curso. Una vez iniciada la escritura no se puede cancelar; espera a que finalice y consulta el resultado.', 'review-notice'), 'pending'); pending.setAttribute('role', 'status');
  const proposal = identify(make('section', '', 'surface prep-form editor-proposal'), 'proposal'); proposal.setAttribute('aria-labelledby', 'serato-export-preview-heading');
  const assessment = make('div'); const tracks = identify(make('ol', '', 'editor-proposed-tracks'), 'tracks'); tracks.setAttribute('aria-label', 'Orden de pistas que se exportarán');
  const commit = button('commit', 'Exportar a Serato…', () => { void controller.commit(); });
  proposal.append(identify(make('h3', 'Vista previa · todavía sin exportar'), 'preview-heading'), assessment, tracks, commit,
    make('p', 'Exportar abrirá la confirmación final del sistema con este archivo y destino. Revisa los avisos antes de continuar.', 'field-hint'));
  const receipt = identify(make('section', '', 'surface prep-form editor-proposal'), 'receipt'); receipt.setAttribute('aria-labelledby', 'serato-export-receipt-heading');
  const receiptInfo = make('div'); const reveal = button('reveal', 'Mostrar crate exportado', () => { void controller.reveal(); });
  receipt.append(identify(make('h3', 'Última exportación confirmada'), 'receipt-heading'), receiptInfo, reveal);
  root.replaceChildren(setup, error, status, pending, proposal, receipt);
  let renderedPreview: SeratoExportController['preview'] | undefined; let renderedReceipt: SeratoExportController['receipt'] | undefined;
  return () => {
    const blocked = !host.canAct() || controller.pending !== null;
    source.textContent = controller.source?.kind === 'review' ? 'Origen: selección revisada actual' : controller.source?.kind === 'saved' ? 'Origen: playlist guardada completa. Los cambios sin guardar del editor no se incluyen.' : controller.source?.kind === 'metadata' ? 'Origen: lista de trabajo de metadatos para reparación. No certifica una selección lista para DJ.' : 'Elige una selección revisada, una lista de metadatos o una playlist guardada para exportar.';
    if (name.value !== controller.name) name.value = controller.name;
    name.disabled = blocked || !controller.source; name.setAttribute('aria-invalid', String(Boolean(controller.name) && !validSeratoName(controller.name)));
    destination.textContent = controller.destination ? `Destino seleccionado: ${controller.destination.label}` : 'Todavía no has elegido una carpeta de destino.';
    choose.disabled = blocked; previewButton.disabled = blocked || !controller.canPreview; commit.disabled = blocked || !controller.canCommit;
    choose.textContent = controller.destination ? 'Cambiar carpeta _Serato_' : 'Elegir carpeta _Serato_';
    const next = !controller.source ? null : !controller.destination ? choose : controller.preview ? controller.canCommit ? commit : null : previewButton;
    for (const action of [choose, previewButton, commit]) action.className = `button ${action === next && !action.disabled ? 'primary' : 'subtle'}`;
    nextStep.textContent = !controller.source ? 'Elige primero la selección que quieres exportar.' : !controller.destination ? '1. Elige la carpeta de destino.' : !controller.preview ? '2. Revisa el nombre y prepara la vista previa.' : controller.preview.blockers.length ? 'Resuelve los bloqueos antes de exportar.' : '3. Revisa la vista previa y confirma la exportación.';
    error.hidden = !controller.error; error.textContent = controller.error; status.hidden = !controller.status; status.textContent = controller.status;
    pending.hidden = controller.pending !== 'commit';
    const preview = controller.preview; proposal.hidden = !preview;
    if (preview !== renderedPreview) {
      renderedPreview = preview; assessment.replaceChildren(); tracks.replaceChildren();
      if (preview) {
        assessment.append(make('p', `Archivo: ${preview.filename}`), make('p', `Destino: ${preview.destinationLabel}`), make('p', `${preview.trackCount} pistas`), make('span', readiness[preview.readiness], `readiness-pill ${preview.readiness}`));
        assessment.append(make('p', preview.backup.required ? 'Se requiere una copia de seguridad del crate existente antes de reemplazarlo.' : 'No se requiere copia de seguridad para este archivo nuevo.', 'field-hint'));
        for (const [messages, heading, className] of [[preview.blockers, 'Bloqueos que impiden exportar', 'review-notice blocker'], [preview.warnings, 'Avisos para revisar', 'review-notice']] as const) {
          if (!messages.length) continue;
          const notice = make('section', '', className); const list = make('ul'); for (const message of messages) list.append(make('li', message)); notice.append(make('strong', heading), list); assessment.append(notice);
        }
        for (const track of preview.tracks) tracks.append(make('li', `${track.title || 'Sin título'} · ${track.artist || 'Artista desconocido'}${track.missing ? ' · Archivo no disponible' : ''}`));
      }
    }
    const result = controller.receipt; receipt.hidden = !result; reveal.disabled = blocked || !result?.validated;
    if (result !== renderedReceipt) {
      renderedReceipt = result; receiptInfo.replaceChildren();
      if (result) receiptInfo.append(make('p', `Archivo: ${result.filename}`), make('p', `Destino: ${result.destinationLabel}`), make('p', `${result.trackCount} pistas · Crate validado tras la escritura`), make('p', result.backupCreated ? 'Copia de seguridad creada.' : 'No fue necesario crear una copia de seguridad.', 'field-hint'));
    }
  };
}
