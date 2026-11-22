import type { GeneratedReviewController, ReviewEvidence } from './generated-review.js';
import { localizeReviewNotice } from './workflow.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', cls = ''): HTMLElementTagNameMap[K] => { const node = document.createElement(tag); node.textContent = text; node.className = cls; return node; };
const score = (value: number | null): string => value === null ? 'Sin dato' : value.toLocaleString('es', { maximumFractionDigits: 3 });
const readiness = { ready: 'Lista para revisar', needs_review: 'Revisión recomendada', blocked: 'Necesita atención' };
function checks(value: ReviewEvidence): HTMLElement {
  const list = make('ul'); for (const check of value.readinessChecks) list.append(make('li', `${check.label} · ${readiness[check.status]}: ${localizeReviewNotice(check.detail)}`)); return list;
}
export function createGeneratedReviewView(root: HTMLElement, controller: GeneratedReviewController, host: { canAct(): boolean }): () => void {
  const section = make('section', '', 'surface prep-form'); section.id = 'generated-review-controls';
  const alert = make('p', '', 'review-notice blocker'); alert.id = 'review-error'; alert.setAttribute('role', 'alert');
  const summary = make('p', '', 'field-hint'); summary.id = 'review-readiness-summary';
  const notices = make('div', '', 'review-notice'); notices.id = 'review-readiness-notices';
  const label = make('label', 'Ajustar una pista'); label.setAttribute('for', 'review-selected-track');
  const selected = make('select'); selected.id = 'review-selected-track';
  let selectedId = ''; let selectedIndex = 0; let followIndex = -1; let positionedIndex = -1; let renderedTracks = ''; let requestedTrackId = ''; let comparisonTrackId = '';
  const button = (caption: string, action: () => void): HTMLButtonElement => {
    const node = make('button', caption, 'button subtle'); node.type = 'button';
    node.addEventListener('click', () => { if (!node.disabled && host.canAct() && !controller.pending) action(); }); return node;
  };
  const compare = button('Comparar reemplazo', () => { requestedTrackId = selectedId; void controller.compare(selectedId); });
  const remove = button('Retirar y completar', () => { void controller.remove(selectedId); });
  // A repeated track shares one id: the row index tells the controller which copy moves,
  // and followIndex keeps that copy selected once the new order arrives.
  const up = button('Subir', () => { followIndex = selectedIndex - 1; void controller.move(selectedId, -1, selectedIndex); });
  const down = button('Bajar', () => { followIndex = selectedIndex + 1; void controller.move(selectedId, 1, selectedIndex); });
  const positionLabel = make('label', 'Posición'); positionLabel.setAttribute('for', 'review-position');
  const position = make('input'); position.type = 'number'; position.id = 'review-position'; position.min = '1'; position.step = '1';
  const positionMove = button('Mover', () => { followIndex = Number(position.value) - 1; void controller.moveTo(selectedId, Number(position.value), selectedIndex); });
  const undo = button('Deshacer', () => { void controller.undo(); }); undo.id = 'review-undo';
  const redo = button('Rehacer', () => { void controller.redo(); }); redo.id = 'review-redo';
  const historyStatus = make('p', '', 'field-hint'); historyStatus.id = 'review-history-status';
  historyStatus.setAttribute('role', 'status');
  const controls = make('div', '', 'editor-actions');
  controls.append(compare, remove, up, down, positionLabel, position, positionMove, undo, redo);
  const evidence = make('details'); evidence.id = 'review-evidence';
  const evidenceBody = make('div');
  const load = button('Cargar evidencia local', () => { void controller.load(); }); load.id = 'review-load-evidence';
  evidence.append(make('summary', 'Por qué esta selección'), load, evidenceBody);
  const preview = make('section', '', 'review-notice'); preview.id = 'review-replacement-comparison'; preview.setAttribute('aria-live', 'polite');
  const previewBody = make('div');
  const use = button('Usar este reemplazo', () => { void controller.replace(); }); use.id = 'review-use-replacement'; use.hidden = true;
  preview.append(previewBody, use);
  section.append(alert, summary, notices, label, selected, controls, historyStatus,
    make('p', 'Comparar no modifica la selección. Usar este reemplazo aplica el reemplazo que mostró la comparación. Retirar busca un reemplazo; si no existe, acorta la selección. Subir o bajar recalcula las transiciones; Posición mueve la pista a esa posición en un solo paso. Deshacer y rehacer restauran la selección anterior sin tocar el audio.', 'field-hint'), preview, evidence);
  root.replaceChildren(section);
  let renderedDetails: ReviewEvidence | null | undefined; let renderedComparison: GeneratedReviewController['comparison'] | undefined;
  const render = (): void => {
    root.hidden = !controller.editable;
    if (!controller.editable || !controller.snapshot) { selectedId = ''; return; }
    const blocked = !host.canAct() || controller.pending;
    const details = controller.details; const tracks = controller.snapshot.tracks;
    if (tracks[selectedIndex]?.id !== selectedId) {
      const followed = tracks[followIndex]?.id === selectedId ? followIndex : tracks.findIndex(track => track.id === selectedId);
      followIndex = -1;
      selectedIndex = followed >= 0 ? followed : Math.min(selectedIndex, Math.max(0, tracks.length - 1));
    }
    selectedId = tracks[selectedIndex]?.id ?? '';
    const trackKey = JSON.stringify(tracks.map(track => [track.id, track.title, track.artist]));
    if (trackKey !== renderedTracks) {
      renderedTracks = trackKey; selected.replaceChildren();
      for (const [index, track] of tracks.entries()) { const option = make('option', `${index + 1}. ${track.title} · ${track.artist}`); option.value = track.id; selected.append(option); }
    }
    selected.value = selectedId; selected.selectedIndex = selectedIndex; selected.disabled = blocked || !tracks.length;
    const protectedIds = new Set(details?.protectedTrackIds ?? []); const protectedTrack = protectedIds.has(selectedId);
    compare.id = `review-compare-${selectedIndex}`; remove.id = `review-remove-${selectedIndex}`;
    compare.disabled = remove.disabled = blocked || !selectedId || protectedTrack;
    for (const [move, direction] of [[up, -1], [down, 1]] as const) {
      move.id = `review-move-${selectedIndex}-${direction}`;
      move.disabled = compare.disabled || selectedIndex + direction < 0 || selectedIndex + direction >= tracks.length || protectedIds.has(tracks[selectedIndex + direction]?.id);
    }
    positionMove.id = `review-position-move-${selectedIndex}`;
    position.disabled = blocked || !tracks.length;
    position.max = String(Math.max(1, tracks.length));
    positionMove.disabled = compare.disabled || !tracks.length;
    // The typed position is only seeded when the selection changes, never while it is being edited.
    if (selectedIndex !== positionedIndex) { positionedIndex = selectedIndex; position.value = String(selectedIndex + 1); }
    alert.hidden = !controller.error; alert.textContent = controller.error;
    historyStatus.hidden = !controller.status; historyStatus.textContent = controller.status ?? '';
    undo.disabled = blocked || !controller.canUndo; redo.disabled = blocked || !controller.canRedo;
    summary.textContent = `${readiness[controller.snapshot.readiness]} · ${controller.snapshot.warnings.length} avisos · ${controller.snapshot.blockers.length} bloqueos`;
    load.hidden = Boolean(details); load.disabled = blocked;
    if (details !== renderedDetails) {
      renderedDetails = details; evidenceBody.replaceChildren(); notices.replaceChildren();
      const actionable = details?.readinessChecks.filter(check => check.status !== 'ready') ?? []; notices.hidden = !actionable.length;
      if (details) {
        if (actionable.length) notices.append(checks({ ...details, readinessChecks: actionable }));
        const facts = make('pre', details.engineFacts, 'review-engine-facts'); facts.id = 'review-engine-facts'; evidenceBody.append(make('p', localizeReviewNotice(details.readinessSummary)), facts, make('h4', 'Comprobaciones de preparación'), checks(details));
        const table = make('table'); table.id = 'review-transition-evidence'; const head = make('tr');
        for (const name of ['Transición', 'Total', 'Compatibilidad', 'Mezclabilidad', 'Componentes', 'Explicaciones y avisos']) head.append(make('th', name));
        const thead = make('thead'); thead.append(head); table.append(thead); const body = make('tbody');
        for (const item of details.transitions) { const row = make('tr'); for (const value of [String(item.index), score(item.totalScore), score(item.compatibilityScore), score(item.mixabilityScore), Object.entries(item.components).map(([key, value]) => `${key}: ${score(value)}`).join(' · '), [...item.explanations, ...item.warnings].map(localizeReviewNotice).join('; ')]) row.append(make('td', value)); body.append(row); }
        table.append(body); const scroll = make('div', '', 'table-scroll'); scroll.append(table); evidenceBody.append(scroll);
      }
    }
    const comparison = controller.comparison;
    if (comparison !== renderedComparison) {
      renderedComparison = comparison; comparisonTrackId = requestedTrackId; previewBody.replaceChildren();
      if (comparison) {
        previewBody.append(make('h4', comparison.replacement ? `Reemplazo propuesto: ${comparison.replacement.title} · ${comparison.replacement.artist}` : 'Sin reemplazo elegible'), make('p', comparison.message));
        for (const [caption, value] of [['Original', comparison.original], ['Propuesto', comparison.proposed]] as const) previewBody.append(make('h4', `${caption} · puntuación ${score(value.qualityScore)}`), make('p', value.readinessSummary), checks(value));
      }
    }
    const comparable = Boolean(comparison?.replacement) && comparisonTrackId === selectedId;
    use.hidden = !comparable; use.disabled = blocked || !comparable;
    preview.hidden = !comparison || comparisonTrackId !== selectedId;
  };
  selected.addEventListener('change', () => {
    const tracks = controller.snapshot?.tracks ?? []; const row = selected.selectedIndex;
    selectedId = selected.value; followIndex = -1;
    selectedIndex = Number.isInteger(row) && tracks[row]?.id === selectedId ? row : tracks.findIndex(track => track.id === selectedId);
    render();
  });
  return render;
}
