import type { LoudnessController, LoudnessTrack } from './loudness.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `loudness-${suffix}`; return node; };
const metric = (value: number | null): string => value === null ? '—' : value.toFixed(1).replace('-', '−');
const stateLabels: Record<LoudnessTrack['state'], string> = { unmeasured: 'Sin medición', measured: 'Medición completa', too_short: 'Medición parcial: menos de 60 s', unmeasurable: 'No medible', transient_failure: 'Fallo temporal', unsupported: 'No compatible' };
export function createLoudnessView(root: HTMLElement, controller: LoudnessController, host: { canAct(): boolean }): () => void {
  const canAct = (): boolean => host.canAct() && !controller.pending;
  const section = make('section', '', 'surface prep-form'); section.setAttribute('aria-labelledby', 'loudness-heading');
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const availability = identify(make('p', '', 'review-notice'), 'availability'); availability.setAttribute('role', 'status');
  const stale = identify(make('p', 'Datos desactualizados. Actualiza el estado antes de seleccionar pistas o analizar.', 'review-notice'), 'stale');
  const dirty = identify(make('p', '', 'field-hint'), 'dirty'); dirty.setAttribute('aria-live', 'polite');
  const settings = make('fieldset'); settings.append(make('legend', 'Ajustes de sonoridad'));
  const enabled = identify(make('input'), 'enabled'); enabled.type = 'checkbox'; enabled.setAttribute('aria-describedby', 'loudness-warning');
  const enabledLabel = make('label', 'Activar análisis de sonoridad y escritura automática de etiquetas'); enabledLabel.setAttribute('for', enabled.id);
  const warning = identify(make('p', 'Este único ajuste activa el análisis y la escritura automática de etiquetas de sonoridad: reemplaza los comentarios existentes. Antes de ejecutar se revisan las pistas y las copias de seguridad y se pide confirmación en el diálogo del sistema. Guardar los ajustes no inicia el análisis ni la preescucha.', 'review-notice'), 'warning');
  const numeric = (id: string, label: string, min: string, max: string): HTMLInputElement => {
    const input = identify(make('input'), id); input.type = 'number'; input.min = min; input.max = max; input.step = '0.5';
    const caption = make('label', label); caption.setAttribute('for', input.id); settings.append(caption, input); return input;
  };
  settings.append(enabled, enabledLabel, warning);
  const target = numeric('target', 'Objetivo de sonoridad (−30 a 0 LUFS)', '-30', '0');
  const tolerance = numeric('tolerance', 'Tolerancia (0 a 10 LU)', '0', '10');
  enabled.addEventListener('change', () => { if (canAct()) controller.setEnabled(enabled.checked); });
  target.addEventListener('change', () => { if (canAct()) controller.setTarget(target.value.trim() ? Number(target.value) : NaN); });
  tolerance.addEventListener('change', () => { if (canAct()) controller.setTolerance(tolerance.value.trim() ? Number(tolerance.value) : NaN); });
  const action = (id: string, caption: string, callback: () => void, primary = false): HTMLButtonElement => {
    const button = identify(make('button', caption, `button ${primary ? 'primary' : 'subtle'}`), id); button.type = 'button';
    button.addEventListener('click', () => { if (canAct() && !button.disabled) callback(); }); return button;
  };
  const save = action('save', 'Guardar ajustes', () => { void controller.save(); }, true);
  const discard = action('discard', 'Descartar cambios', () => controller.discard());
  const refresh = action('refresh', 'Actualizar', () => { void controller.load(); });
  const settingsActions = make('div', '', 'editor-actions'); settingsActions.append(save, discard, refresh);
  const scope = make('section'); scope.setAttribute('aria-labelledby', 'loudness-scope-heading');
  const selection = identify(make('p', '', 'field-hint'), 'selection'); selection.setAttribute('aria-live', 'polite');
  const selectPage = action('select-page', 'Añadir esta página a la selección', () => controller.selectPage());
  const selectAll = action('select-all', 'Seleccionar toda la biblioteca', () => controller.selectAll());
  const clear = action('clear', 'Quitar selección', () => controller.clearSelection());
  const scopeActions = make('div', '', 'editor-actions'); scopeActions.append(selectPage, selectAll, clear);
  const table = make('table'); table.append(make('caption', 'Sonoridad de las pistas de la biblioteca'));
  const head = make('thead'); const headings = make('tr');
  for (const caption of ['Seleccionar', 'Pista', 'Estado y avisos', 'LUFS', 'LRA (LU)', 'Pico real (dBTP)', 'Acción']) { const th = make('th', caption); th.setAttribute('scope', 'col'); headings.append(th); }
  head.append(headings); const rows = identify(make('tbody'), 'rows'); table.append(head, rows);
  const pageLabel = identify(make('span'), 'page'); pageLabel.setAttribute('aria-live', 'polite');
  const previous = action('previous', 'Página anterior', () => controller.setPage(controller.page - 1));
  const next = action('next', 'Página siguiente', () => controller.setPage(controller.page + 1));
  const pages = make('div', '', 'editor-actions'); pages.append(previous, pageLabel, next);
  const request = action('preview', 'Preparar vista previa de las pistas seleccionadas', () => { void controller.requestPreview(); }, true);
  scope.append(identify(make('h3', 'Elegir pistas'), 'scope-heading'), make('p', 'Selecciona explícitamente hasta 500 pistas. Cada página muestra como máximo 100; cambiar de página conserva la selección. Si se supera el límite, no se recorta la selección.', 'field-hint'), selection, scopeActions, table, pages, request);
  const previewSection = identify(make('section'), 'preview-section'); previewSection.setAttribute('aria-labelledby', 'loudness-preview-heading');
  const previewSummary = identify(make('p'), 'preview-summary'); const previewTracks = identify(make('ol'), 'preview-tracks');
  let previewPage = 0; let lastPreview = controller.preview;
  const previewPageLabel = make('span'); previewPageLabel.setAttribute('aria-live', 'polite');
  const previewPrevious = action('preview-previous', 'Vista previa: página anterior', () => { previewPage--; render(); });
  const previewNext = action('preview-next', 'Vista previa: página siguiente', () => { previewPage++; render(); });
  const previewPages = make('div', '', 'editor-actions'); previewPages.append(previewPrevious, previewPageLabel, previewNext);
  const run = action('run', 'Analizar y escribir etiquetas…', () => { void controller.run(); }, true);
  previewSection.append(identify(make('h3', 'Vista previa de sonoridad'), 'preview-heading'), previewSummary,
    make('p', 'Esta vista previa no escribe archivos. Se reemplazarán los comentarios al guardar nuevas etiquetas. Al continuar, revisa y confirma las pistas exactas y la copia de seguridad en el diálogo del sistema.', 'review-notice'), previewTracks, previewPages, run);
  const pending = identify(make('p', 'Confirma en el diálogo del sistema y espera el resultado. Cancelar detiene lo pendiente; una escritura en curso debe terminar antes de salir.', 'review-notice'), 'pending'); pending.setAttribute('role', 'status');
  const result = identify(make('p', '', 'review-notice'), 'result'); result.setAttribute('role', 'status');
  const resultWarning = identify(make('p', '', 'review-notice blocker'), 'result-warning'); resultWarning.setAttribute('role', 'alert');
  const revealBackups = action('reveal-backups', 'Mostrar copias de seguridad', () => { void controller.revealBackups(); });
  const backupNotice = identify(make('p', '', 'field-hint'), 'backup-notice'); backupNotice.setAttribute('role', 'status');
  section.append(identify(make('h3', 'Sonoridad'), 'heading'), error, availability, stale, settings, dirty, settingsActions, scope, previewSection, pending, result, resultWarning, revealBackups, backupNotice); root.replaceChildren(section);
  let renderedTracks: LoudnessTrack[] | undefined; let renderedPage = -1;
  let rowControls: { id: string; checkbox: HTMLInputElement; reanalyze: HTMLButtonElement }[] = [];
  function render(): void {
    const snapshot = controller.snapshot; const blocked = !canAct(); const selectionBlocked = blocked || !snapshot || !controller.statusFresh;
    error.textContent = controller.error; error.hidden = !controller.error;
    availability.textContent = !snapshot ? 'Carga el estado de sonoridad para consultar el motor y las pistas.' : !snapshot.available
      ? snapshot.reason === 'missing_engine' ? 'El motor de sonoridad no está instalado o no está disponible.' : 'El motor de sonoridad no superó la comprobación. El análisis no está disponible.'
      : snapshot.enabled ? 'Motor de sonoridad disponible. El análisis requiere una selección y confirmación explícitas.' : 'Sonoridad desactivada: no se analiza ni se escriben etiquetas.';
    stale.hidden = !snapshot || controller.statusFresh; dirty.textContent = controller.dirty ? 'Ajustes sin guardar. Tu borrador se conserva al cambiar de pantalla.' : 'Sin ajustes pendientes.';
    enabled.disabled = target.disabled = tolerance.disabled = blocked || !snapshot;
    if (snapshot) { enabled.checked = snapshot.enabled; if (target.value !== String(snapshot.targetLufs)) target.value = String(snapshot.targetLufs); if (tolerance.value !== String(snapshot.toleranceLu)) tolerance.value = String(snapshot.toleranceLu); }
    save.disabled = blocked || !controller.canSave; discard.disabled = blocked || !controller.dirty; refresh.disabled = blocked;
    selectPage.disabled = selectAll.disabled = selectionBlocked || !snapshot?.totalTracks; clear.disabled = selectionBlocked || !controller.selectedIds.length;
    selection.textContent = `${controller.selectedIds.length} de ${snapshot?.totalTracks ?? 0} pistas seleccionadas (máximo 500).`;
    previous.disabled = selectionBlocked || controller.page === 0; next.disabled = selectionBlocked || controller.page + 1 >= controller.pageCount;
    pageLabel.textContent = `Página ${controller.page + 1} de ${controller.pageCount}`; request.disabled = blocked || !controller.canPreview;
    if (renderedTracks !== snapshot?.tracks || renderedPage !== controller.page) {
      renderedTracks = snapshot?.tracks; renderedPage = controller.page; rows.replaceChildren(); rowControls = [];
      for (const entry of controller.visibleTracks) {
        const row = make('tr'); const checkbox = make('input'); checkbox.type = 'checkbox'; checkbox.setAttribute('aria-label', `Seleccionar ${entry.track.title}, ${entry.track.artist}`);
        checkbox.addEventListener('change', () => { if (canAct() && !checkbox.disabled) controller.toggleTrack(entry.track.id, checkbox.checked); });
        const chosen = make('td'); chosen.append(checkbox); const title = make('td', `${entry.track.title} · ${entry.track.artist}`);
        const description = entry.state === 'measured' && !entry.complete ? 'Medición incompleta' : stateLabels[entry.state];
        const hasMetrics = entry.complete || entry.state === 'too_short';
        const peakWarning = hasMetrics && entry.truePeak !== null ? entry.truePeak >= 0 ? ' · Riesgo de recorte (pico ≥0 dBTP)' : entry.truePeak > -1 ? ' · Poco margen (pico >−1 dBTP)' : '' : '';
        const reanalyze = action(`reanalyze-${entry.track.id}`, 'Reanalizar', () => { void controller.reanalyze(entry.track.id); }); reanalyze.setAttribute('aria-label', `Preparar vista previa de reanálisis de ${entry.track.title}`);
        const last = make('td'); last.append(reanalyze); row.append(chosen, title, make('td', description + peakWarning), make('td', hasMetrics ? metric(entry.lufs) : '—'),
          make('td', entry.state === 'too_short' ? 'No estable (<60 s)' : entry.complete ? metric(entry.lra) : '—'), make('td', hasMetrics ? metric(entry.truePeak) : '—'), last);
        rows.append(row); rowControls.push({ id: entry.track.id, checkbox, reanalyze });
      }
    }
    const selected = new Set(controller.selectedIds);
    for (const row of rowControls) { row.checkbox.checked = selected.has(row.id); row.checkbox.disabled = selectionBlocked; row.reanalyze.disabled = selectionBlocked || controller.dirty || !snapshot?.enabled || !snapshot.available; }
    const preview = controller.preview; if (preview !== lastPreview) { lastPreview = preview; previewPage = 0; }
    previewSection.hidden = !preview; previewTracks.replaceChildren();
    const previewCount = Math.max(1, Math.ceil((preview?.trackCount ?? 0) / 100));
    previewPrevious.disabled = blocked || !preview || previewPage === 0; previewNext.disabled = blocked || !preview || previewPage + 1 >= previewCount;
    previewPageLabel.textContent = `Página ${previewPage + 1} de ${previewCount}`;
    if (preview) {
      previewSummary.textContent = `${preview.force ? 'Reanálisis' : 'Análisis'} de ${preview.trackCount} pistas. Espacio previsto para copias de seguridad: ${preview.backupBytes} bytes.`;
      previewTracks.start = previewPage * 100 + 1; for (const track of preview.tracks.slice(previewPage * 100, previewPage * 100 + 100)) previewTracks.append(make('li', `${track.title} · ${track.artist}`));
    }
    run.disabled = blocked || !controller.canRun; pending.hidden = controller.pending !== 'run'; result.hidden = !controller.result;
    resultWarning.hidden = !controller.result?.warning; resultWarning.textContent = controller.result?.warning ?? '';
    revealBackups.disabled = blocked || !controller.canRevealBackups; backupNotice.textContent = controller.backupNotice; backupNotice.hidden = !controller.backupNotice;
    if (controller.result) { const value = controller.result; result.textContent = `Última ejecución ${value.cancelled ? 'cancelada' : 'finalizada'}: ${value.changedCount} escrituras completadas, ${value.unchangedCount} sin cambios, ${value.failureCount} fallidas, ${value.backupCount} copias de seguridad. Las escrituras ya completadas se conservan.`; }
  }
  return render;
}
