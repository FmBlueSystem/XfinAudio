import type { GeneratedReviewController, ReviewEvidence } from './generated-review.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', cls = ''): HTMLElementTagNameMap[K] => { const node = document.createElement(tag); node.textContent = text; node.className = cls; return node; };
const score = (value: number | null): string => value === null ? 'Sin dato' : value.toLocaleString('es', { maximumFractionDigits: 3 });
function checks(value: ReviewEvidence): HTMLElement {
  const list = make('ul'); for (const check of value.readinessChecks) list.append(make('li', `${check.label} · ${check.status}: ${check.detail}`)); return list;
}
export function createGeneratedReviewView(root: HTMLElement, controller: GeneratedReviewController, host: { canAct(): boolean }): () => void {
  return () => {
    root.replaceChildren(); root.hidden = !controller.editable;
    if (!controller.editable || !controller.snapshot) return;
    const blocked = !host.canAct() || controller.pending;
    const section = make('section', '', 'surface'); section.id = 'generated-review-controls';
    section.append(make('h3', 'Revisión local del motor'), make('p', 'Compara sin modificar. Retirar busca un reemplazo elegible; si no existe, acorta la selección. Reordenar recalcula las transiciones. Las pistas de audio permanecen intactas.', 'field-hint'));
    if (controller.error) { const alert = make('p', controller.error, 'review-notice blocker'); alert.setAttribute('role', 'alert'); section.append(alert); }
    const button = (caption: string, id: string, action: () => void): HTMLButtonElement => { const node = make('button', caption, 'button subtle'); node.type = 'button'; node.id = id; node.disabled = blocked; node.addEventListener('click', () => { if (host.canAct() && !controller.pending) action(); }); return node; };
    const details = controller.details;
    if (details) {
      const facts = make('pre', details.engineFacts, 'review-engine-facts'); facts.id = 'review-engine-facts'; section.append(facts, make('h4', 'Comprobaciones de preparación'), checks(details));
      const table = make('table'); table.id = 'review-transition-evidence'; const head = make('tr');
      for (const name of ['Transición', 'Total', 'Compatibilidad', 'Mezclabilidad', 'Componentes', 'Explicaciones y avisos']) head.append(make('th', name));
      const thead = make('thead'); thead.append(head); table.append(thead); const body = make('tbody');
      for (const item of details.transitions) { const row = make('tr'); for (const value of [String(item.index), score(item.totalScore), score(item.compatibilityScore), score(item.mixabilityScore), Object.entries(item.components).map(([key, value]) => `${key}: ${score(value)}`).join(' · '), [...item.explanations, ...item.warnings].join('; ')]) row.append(make('td', value)); body.append(row); }
      table.append(body); const scroll = make('div', '', 'table-scroll'); scroll.append(table); section.append(scroll);
    } else section.append(button('Cargar evidencia local', 'review-load-evidence', () => { void controller.load(); }));
    const controls = make('ol'); const tracks = controller.snapshot.tracks; const protectedIds = new Set(details?.protectedTrackIds ?? []);
    tracks.forEach((track, index) => {
      const row = make('li'); row.append(make('span', `${track.title} · ${track.artist} `));
      const compare = button('Comparar reemplazo', `review-compare-${index}`, () => { void controller.compare(track.id); });
      const remove = button('Retirar y completar', `review-remove-${index}`, () => { void controller.remove(track.id); });
      compare.disabled ||= protectedIds.has(track.id); remove.disabled ||= protectedIds.has(track.id);
      row.append(compare, remove);
      for (const direction of [-1, 1] as const) { const move = button(direction === -1 ? 'Subir' : 'Bajar', `review-move-${index}-${direction}`, () => { void controller.move(track.id, direction); }); move.disabled ||= index + direction < 0 || index + direction >= tracks.length || protectedIds.has(track.id) || protectedIds.has(tracks[index + direction]?.id); row.append(move); }
      controls.append(row);
    }); section.append(make('h4', 'Editar selección generada'), controls);
    const comparison = controller.comparison;
    if (comparison) { const preview = make('section', '', 'review-notice'); preview.id = 'review-replacement-comparison'; preview.setAttribute('aria-live', 'polite'); preview.append(make('h4', comparison.replacement ? `Reemplazo propuesto: ${comparison.replacement.title} · ${comparison.replacement.artist}` : 'Sin reemplazo elegible'), make('p', comparison.message));
      for (const [label, value] of [['Original', comparison.original], ['Propuesto', comparison.proposed]] as const) preview.append(make('h4', `${label} · puntuación ${score(value.qualityScore)}`), make('p', value.readinessSummary), checks(value)); section.append(preview); }
    root.append(section);
  };
}
