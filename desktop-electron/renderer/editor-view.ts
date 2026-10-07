import { formatDuration } from './model.js';
import type { Readiness } from './model.js';
import type { EditorTrack, SavedPlaylistEditor } from './editor.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, id: string): T => { node.id = `editor-${id}`; return node; };
const button = (id: string, label: string, action: () => void, primary = false): HTMLButtonElement => {
  const node = identify(make('button', label, `button ${primary ? 'primary' : 'subtle'}`), id);
  node.type = 'button'; node.addEventListener('click', action); return node;
};
const readiness: Record<Readiness, string> = { ready: 'Lista para revisar', needs_review: 'Revisión recomendada', blocked: 'Necesita atención' };

export function createEditorView(root: HTMLElement, editor: SavedPlaylistEditor, host: { canAct(): boolean; play(track: EditorTrack): void; improvement(): { available: boolean; hint: string }; openImprovement(): void; improvementApplied(): void }): () => void {
  const empty = make('div', 'Abre una playlist guardada con «Editar» para empezar.', 'surface empty-state');
  const content = make('div');
  const summary = make('section', '', 'surface editor-summary');
  const label = make('label', 'Nombre de la playlist'); label.setAttribute('for', 'editor-name');
  const name = identify(make('input'), 'name'); name.maxLength = 200; name.required = true;
  name.addEventListener('input', () => editor.rename(name.value));
  const dirty = identify(make('p', '', 'editor-dirty'), 'dirty'); dirty.setAttribute('aria-live', 'polite');
  const count = make('p', '', 'field-hint');
  const save = button('save', 'Guardar cambios', () => { void editor.save(); }, true);
  const discard = button('discard', 'Descartar cambios', () => { void editor.discard(); });
  const actions = make('div', '', 'editor-actions'); actions.append(save, discard);
  // Discoverability without authority: this only reveals the existing AI panel and moves
  // focus to its instruction. It never prepares, authorizes, or contacts the provider.
  const improve = button('improve', 'Mejorar con IA…', () => host.openImprovement());
  const improveHint = identify(make('p', '', 'field-hint'), 'improve-hint');
  summary.append(label, name, dirty, count, actions, improve, improveHint, make('p', 'Guardar actualiza esta playlist local. Descartar recupera la versión guardada. El audio no se modifica.', 'field-hint'));
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const switching = identify(make('section', '', 'review-notice'), 'switch'); switching.setAttribute('aria-labelledby', 'editor-switch-title');
  switching.append(identify(make('h3', 'Tienes cambios sin guardar'), 'switch-title'), make('p', 'Para abrir otra playlist, decide qué hacer con este borrador.'));
  const cancelSwitch = button('switch-cancel', 'Cancelar · seguir editando', () => editor.cancelSwitch());
  const discardSwitch = button('switch-discard', 'Descartar y abrir otra playlist', () => { void editor.confirmSwitch(); });
  const switchActions = make('div', '', 'editor-actions'); switchActions.append(cancelSwitch, discardSwitch); switching.append(switchActions);
  const missing = make('p', '', 'review-notice');
  const tableWrap = make('div', '', 'table-card editor-table');
  const tableScroll = make('div', '', 'table-scroll'); tableWrap.append(tableScroll);
  const noTracks = make('p', 'El borrador está vacío. Puedes descartarlo o guardar la playlist sin pistas.', 'inline-empty');
  const form = make('form', '', 'surface editor-command');
  const commandLabel = make('label', 'Cambio en lenguaje natural'); commandLabel.setAttribute('for', 'editor-request');
  const request = identify(make('input'), 'request'); request.maxLength = 500; request.placeholder = 'Por ejemplo: acorta a 10 temas'; request.setAttribute('aria-describedby', 'editor-request-hint');
  request.addEventListener('input', () => editor.setRequest(request.value));
  const previewButton = button('preview', 'Ver propuesta', () => {}); previewButton.type = 'submit';
  form.addEventListener('submit', (event) => { event.preventDefault(); void editor.requestPreview(); });
  form.append(make('h3', 'Propón un cambio antes de aplicarlo'), commandLabel, request, identify(make('p', 'Prueba «acorta a 10 temas» o «sube la energía». El motor local evalúa tu petición; revisar una propuesta no cambia el borrador.', 'field-hint'), 'request-hint'), previewButton);
  const proposal = identify(make('section', '', 'surface editor-proposal'), 'proposal');
  const assessment = make('div'); const proposedTracks = identify(make('ol', '', 'editor-proposed-tracks'), 'proposal-tracks');
  const apply = button('apply', 'Aplicar al borrador', () => editor.applyPreview(), true);
  proposal.append(make('h3', 'Propuesta sin aplicar'), assessment, proposedTracks, apply, make('p', 'Aplicar cambia solo el borrador. Después, usa Guardar cambios para conservarlo.', 'field-hint'));
  const improvementSection = identify(make('section', '', 'surface editor-improvement'), 'improvement');
  const improvementBlocked = identify(make('p', '', 'review-notice blocker'), 'improvement-blocked'); improvementBlocked.setAttribute('role', 'alert');
  const improvementAssessment = make('div');
  const improvementBefore = identify(make('ol', '', 'editor-improvement-list'), 'improvement-before');
  const improvementAfter = identify(make('ol', '', 'editor-improvement-list'), 'improvement-after');
  const improvementCounts = identify(make('p', '', 'field-hint'), 'improvement-counts');
  // Read-only until the user clicks: rendering the proposal never changes the draft.
  const improvementApply = button('improvement-apply', 'Aplicar mejora al borrador', () => { if (editor.applyImprovementPreview()) host.improvementApplied(); }, true);
  improvementSection.append(make('h3', 'Mejora con IA (sin aplicar)'), improvementBlocked, improvementAssessment,
    make('span', 'ANTES', 'eyebrow'), improvementBefore, make('span', 'DESPUÉS', 'eyebrow'), improvementAfter, improvementCounts,
    improvementApply, make('p', 'Aplicarla cambia solo el borrador. Después, usa Guardar mejora para conservarla en la playlist.', 'field-hint'));
  content.append(switching, error, summary, missing, tableWrap, noTracks, form, proposal, improvementSection); root.replaceChildren(empty, content);
  root.addEventListener('keydown', (event) => { if (event.key === 'Escape' && editor.pendingPlaylistId) editor.cancelSwitch(); });
  const rowControls = new Map<string, HTMLButtonElement>();
  const focusRow = (id: string, index: number): void => {
    const preferred = rowControls.get(`${id}-${index}`);
    const fallback = rowControls.get(`remove-${index}`) ?? name;
    (preferred && !preferred.disabled ? preferred : fallback).focus();
  };
  let renderedTracks: EditorTrack[] | undefined; let renderedBusy: boolean | undefined; let previousPending: string | null = null;
  return () => {
    const draft = editor.draft; const blocked = !host.canAct();
    empty.hidden = Boolean(draft); content.hidden = !draft;
    error.hidden = !editor.error; error.textContent = editor.error;
    if (!draft) return;
    if (name.value !== draft.name) name.value = draft.name;
    if (request.value !== editor.request) request.value = editor.request;
    name.disabled = request.disabled = blocked;
    // The improvement CTA and its reason are decided by the app from the exact draft
    // bounds and the presence of the dedicated save bridge.
    const improvementStatus = host.improvement();
    improve.disabled = blocked || !improvementStatus.available;
    improveHint.textContent = improvementStatus.hint; improveHint.hidden = improvementStatus.available;
    dirty.textContent = editor.dirty ? 'Cambios sin guardar' : 'Sin cambios pendientes';
    count.textContent = `${draft.tracks.length} pistas · ${formatDuration(draft.tracks.reduce((total, track) => total + (track.duration ?? 0), 0))}`;
    save.disabled = blocked || !editor.canSave; discard.disabled = blocked || (!editor.dirty && !editor.error);
    // Once the draft holds the exact bound improvement order, saving is a distinct,
    // deliberate action; any manual edit revokes the binding and restores this label.
    save.textContent = editor.improvementBound ? 'Guardar mejora' : 'Guardar cambios';
    previewButton.disabled = blocked || !editor.request.trim() || editor.request.length > 500 || draft.tracks.length < 2 || draft.tracks.length > 500;
    switching.hidden = !editor.pendingPlaylistId; cancelSwitch.disabled = discardSwitch.disabled = blocked;
    if (editor.pendingPlaylistId && editor.pendingPlaylistId !== previousPending) cancelSwitch.focus();
    previousPending = editor.pendingPlaylistId;
    const missingCount = draft.tracks.filter((track) => track.missing).length;
    missing.hidden = missingCount === 0; missing.textContent = `${missingCount} ${missingCount === 1 ? 'archivo no disponible' : 'archivos no disponibles'}. Sus posiciones se conservan hasta que decidas quitarlos del borrador.`;
    noTracks.hidden = draft.tracks.length !== 0; tableWrap.hidden = draft.tracks.length === 0;
    if (renderedTracks !== draft.tracks || renderedBusy !== blocked) {
      renderedTracks = draft.tracks; renderedBusy = blocked; rowControls.clear();
      const table = make('table'); table.setAttribute('aria-label', 'Orden de pistas del borrador');
      const head = make('thead'); const headers = make('tr');
      for (const title of ['#', 'PISTA / ARTISTA', 'METADATOS', 'ESTADO', 'ACCIONES']) { const th = make('th', title); th.scope = 'col'; headers.append(th); }
      head.append(headers); const body = make('tbody');
      draft.tracks.forEach((track, index) => {
        const row = make('tr'); row.dataset.editorIndex = String(index);
        const title = make('td', '', 'track-name'); title.append(make('strong', track.title || 'Sin título'), make('span', track.artist || 'Artista desconocido'));
        const state = make('td', track.missing ? 'Archivo no disponible' : 'Disponible', track.missing ? 'editor-missing' : 'muted');
        const controls = make('td'); const group = make('div', '', 'editor-row-actions');
        for (const [id, caption, action, disabled] of [
          ['up', 'Subir', () => { editor.move(index, -1); focusRow(index === 1 ? 'down' : 'up', index - 1); }, index === 0], ['down', 'Bajar', () => { editor.move(index, 1); focusRow(index === draft.tracks.length - 2 ? 'up' : 'down', index + 1); }, index === draft.tracks.length - 1],
          ['remove', 'Quitar', () => { editor.remove(index); focusRow('remove', Math.min(index, (editor.draft?.tracks.length ?? 1) - 1)); }, false], ['listen', 'Escuchar', () => host.play(track), track.missing],
        ] as const) {
          const control = button(`${id}-${index}`, caption, action); control.disabled = blocked || disabled;
          control.setAttribute('aria-label', `${caption} ${index + 1}: ${track.title || 'Sin título'}`); rowControls.set(`${id}-${index}`, control); group.append(control);
        }
        controls.append(group); row.append(make('td', String(index + 1), 'track-index'), title, make('td', `${track.bpm ?? '—'} BPM · ${track.key || '—'} · Energía ${track.energy ?? '—'}`), state, controls); body.append(row);
      });
      table.append(head, body); tableScroll.replaceChildren(table);
    }
    const preview = editor.preview; proposal.hidden = !preview;
    assessment.replaceChildren(); proposedTracks.replaceChildren(); apply.disabled = blocked || !preview || preview.assessment.readiness === 'blocked';
    if (preview) {
      const result = preview.assessment;
      assessment.append(make('p', result.description), make('span', readiness[result.readiness], `readiness-pill ${result.readiness}`), make('p', `Puntuación del motor: ${Number.isFinite(result.qualityScore) ? result.qualityScore.toLocaleString('es', { maximumFractionDigits: 2 }) : '—'} · ${preview.tracks.length} pistas`, 'field-hint'));
      const warnings = make('ul'); for (const warning of result.warnings) warnings.append(make('li', warning)); assessment.append(warnings);
      preview.tracks.forEach((track, index) => proposedTracks.append(make('li', `${index + 1}. ${track.title || 'Sin título'} · ${track.artist || 'Artista desconocido'}${track.missing ? ' · Archivo no disponible' : ''}`)));
    }
    const improvement = editor.improvement;
    improvementSection.hidden = !improvement;
    improvementApply.disabled = blocked || !improvement || improvement.assessment.readiness === 'blocked';
    if (improvement) {
      const result = improvement.assessment;
      const isBlocked = result.readiness === 'blocked';
      improvementBlocked.hidden = !isBlocked;
      improvementBlocked.textContent = isBlocked ? 'La propuesta está bloqueada: revisa las advertencias; no puede aplicarse al borrador.' : '';
      improvementAssessment.replaceChildren(); improvementBefore.replaceChildren(); improvementAfter.replaceChildren();
      improvementAssessment.append(make('p', result.description), make('span', readiness[result.readiness], `readiness-pill ${result.readiness}`), make('p', `Puntuación del motor: ${Number.isFinite(result.qualityScore) ? result.qualityScore.toLocaleString('es', { maximumFractionDigits: 2 }) : '—'} · ${improvement.after.length} pistas`, 'field-hint'));
      const warnings = make('ul'); for (const warning of result.warnings) warnings.append(make('li', warning)); improvementAssessment.append(warnings);
      // Positions are matched by track id so a reorder is visible in the DESPUÉS list itself.
      // No marker means unchanged, or no previous match at all (added track).
      const previousPositions = new Map(improvement.before.map((track, index) => [track.id, index]));
      const line = (track: EditorTrack, index: number, marker = ''): HTMLLIElement => make('li', `${index + 1}. ${track.title || 'Sin título'} · ${track.artist || 'Artista desconocido'}${track.missing ? ' · Archivo no disponible' : ''}${marker}`);
      improvement.before.forEach((track, index) => improvementBefore.append(line(track, index)));
      let moved = 0;
      improvement.after.forEach((track, index) => {
        const previous = previousPositions.get(track.id);
        if (previous === undefined || previous === index) { improvementAfter.append(line(track, index)); return; }
        moved += 1;
        improvementAfter.append(line(track, index, ` · #${previous + 1} → #${index + 1}`));
      });
      const added = improvement.addedIds.length; const removed = improvement.removedIds.length;
      improvementCounts.textContent = `${added} ${added === 1 ? 'pista añadida' : 'pistas añadidas'} · ${removed} ${removed === 1 ? 'pista quitada' : 'pistas quitadas'}${moved ? ` · ${moved} ${moved === 1 ? 'movida' : 'movidas'}` : ''}`;
    }
  };
}
