import type { GeneratedReviewController, ReviewEvidence } from './generated-review.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', cls = ''): HTMLElementTagNameMap[K] => { const node = document.createElement(tag); node.textContent = text; node.className = cls; return node; };
const score = (value: number | null): string => value === null ? 'Sin dato' : value.toLocaleString('es', { maximumFractionDigits: 3 });
const readiness = { ready: 'Lista para revisar', needs_review: 'Revisión recomendada', blocked: 'Necesita atención' };
function checks(value: ReviewEvidence): HTMLElement {
  const list = make('ul'); for (const check of value.readinessChecks) list.append(make('li', `${check.label} · ${readiness[check.status]}: ${check.detail}`)); return list;
}
export function createGeneratedReviewView(root: HTMLElement, controller: GeneratedReviewController, host: { canAct(): boolean }): () => void {
  const section = make('section', '', 'surface prep-form'); section.id = 'generated-review-controls';
  const alert = make('p', '', 'review-notice blocker'); alert.id = 'review-error'; alert.setAttribute('role', 'alert');
  const summary = make('p', '', 'field-hint'); summary.id = 'review-readiness-summary';
  const notices = make('div', '', 'review-notice'); notices.id = 'review-readiness-notices';
  const label = make('label', 'Ajustar una pista'); label.setAttribute('for', 'review-selected-track');
  const selected = make('select'); selected.id = 'review-selected-track';
  let selectedId = ''; let selectedIndex = 0; let renderedTracks = ''; let requestedTrackId = ''; let comparisonTrackId = '';
  const button = (caption: string, action: () => void): HTMLButtonElement => {
    const node = make('button', caption, 'button subtle'); node.type = 'button';
    node.addEventListener('click', () => { if (!node.disabled && host.canAct() && !controller.pending) action(); }); return node;
  };
  const compare = button('Comparar reemplazo', () => { requestedTrackId = selectedId; void controller.compare(selectedId); });
  const remove = button('Retirar y completar', () => { void controller.remove(selectedId); });
  const up = button('Subir', () => { void controller.move(selectedId, -1); });
  const down = button('Bajar', () => { void controller.move(selectedId, 1); });
  const controls = make('div', '', 'editor-actions'); controls.append(compare, remove, up, down);
  const evidence = make('details'); evidence.id = 'review-evidence';
  const evidenceBody = make('div');
  const load = button('Cargar evidencia local', () => { void controller.load(); }); load.id = 'review-load-evidence';
  evidence.append(make('summary', 'Por qué esta selección'), load, evidenceBody);
  const preview = make('section', '', 'review-notice'); preview.id = 'review-replacement-comparison'; preview.setAttribute('aria-live', 'polite');
  section.append(alert, summary, notices, label, selected, controls,
    make('p', 'Comparar no modifica la selección. Retirar busca un reemplazo; si no existe, acorta la selección. Subir o bajar recalcula las transiciones. El audio permanece intacto.', 'field-hint'), preview, evidence);
  root.replaceChildren(section);
  let renderedDetails: ReviewEvidence | null | undefined; let renderedComparison: GeneratedReviewController['comparison'] | undefined;
  const render = (): void => {
    root.hidden = !controller.editable;
    if (!controller.editable || !controller.snapshot) { selectedId = ''; return; }
    const blocked = !host.canAct() || controller.pending;
    const details = controller.details; const tracks = controller.snapshot.tracks;
    const currentIndex = tracks.findIndex(track => track.id === selectedId);
    selectedIndex = currentIndex >= 0 ? currentIndex : Math.min(selectedIndex, Math.max(0, tracks.length - 1));
    selectedId = tracks[selectedIndex]?.id ?? '';
    const trackKey = JSON.stringify(tracks.map(track => [track.id, track.title, track.artist]));
    if (trackKey !== renderedTracks) {
      renderedTracks = trackKey; selected.replaceChildren();
      for (const [index, track] of tracks.entries()) { const option = make('option', `${index + 1}. ${track.title} · ${track.artist}`); option.value = track.id; selected.append(option); }
    }
    selected.value = selectedId; selected.disabled = blocked || !tracks.length;
    const protectedIds = new Set(details?.protectedTrackIds ?? []); const protectedTrack = protectedIds.has(selectedId);
    compare.id = `review-compare-${selectedIndex}`; remove.id = `review-remove-${selectedIndex}`;
    compare.disabled = remove.disabled = blocked || !selectedId || protectedTrack;
    for (const [move, direction] of [[up, -1], [down, 1]] as const) {
      move.id = `review-move-${selectedIndex}-${direction}`;
      move.disabled = compare.disabled || selectedIndex + direction < 0 || selectedIndex + direction >= tracks.length || protectedIds.has(tracks[selectedIndex + direction]?.id);
    }
    alert.hidden = !controller.error; alert.textContent = controller.error;
    summary.textContent = `${readiness[controller.snapshot.readiness]} · ${controller.snapshot.warnings.length} avisos · ${controller.snapshot.blockers.length} bloqueos`;
    load.hidden = Boolean(details); load.disabled = blocked;
    if (details !== renderedDetails) {
      renderedDetails = details; evidenceBody.replaceChildren(); notices.replaceChildren();
      const actionable = details?.readinessChecks.filter(check => check.status !== 'ready') ?? []; notices.hidden = !actionable.length;
      if (details) {
        if (actionable.length) notices.append(checks({ ...details, readinessChecks: actionable }));
        const facts = make('pre', details.engineFacts, 'review-engine-facts'); facts.id = 'review-engine-facts'; evidenceBody.append(make('p', details.readinessSummary), facts, make('h4', 'Comprobaciones de preparación'), checks(details));
        const table = make('table'); table.id = 'review-transition-evidence'; const head = make('tr');
        for (const name of ['Transición', 'Total', 'Compatibilidad', 'Mezclabilidad', 'Componentes', 'Explicaciones y avisos']) head.append(make('th', name));
        const thead = make('thead'); thead.append(head); table.append(thead); const body = make('tbody');
        for (const item of details.transitions) { const row = make('tr'); for (const value of [String(item.index), score(item.totalScore), score(item.compatibilityScore), score(item.mixabilityScore), Object.entries(item.components).map(([key, value]) => `${key}: ${score(value)}`).join(' · '), [...item.explanations, ...item.warnings].join('; ')]) row.append(make('td', value)); body.append(row); }
        table.append(body); const scroll = make('div', '', 'table-scroll'); scroll.append(table); evidenceBody.append(scroll);
      }
    }
    const comparison = controller.comparison;
    if (comparison !== renderedComparison) {
      renderedComparison = comparison; comparisonTrackId = requestedTrackId; preview.replaceChildren();
      if (comparison) {
        preview.append(make('h4', comparison.replacement ? `Reemplazo propuesto: ${comparison.replacement.title} · ${comparison.replacement.artist}` : 'Sin reemplazo elegible'), make('p', comparison.message));
        for (const [caption, value] of [['Original', comparison.original], ['Propuesto', comparison.proposed]] as const) preview.append(make('h4', `${caption} · puntuación ${score(value.qualityScore)}`), make('p', value.readinessSummary), checks(value));
      }
    }
    preview.hidden = !comparison || comparisonTrackId !== selectedId;
  };
  selected.addEventListener('change', () => { selectedId = selected.value; render(); });
  return render;
}
