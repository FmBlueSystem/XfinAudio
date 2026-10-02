import type { PreferencesController } from './preferences.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `preferences-${suffix}`; return node; };
export function createPreferencesView(root: HTMLElement, controller: PreferencesController, host: { canAct(): boolean }): () => void {
  const canAct = (): boolean => host.canAct() && !controller.pending;
  const section = make('section', '', 'surface prep-form'); section.setAttribute('aria-labelledby', 'preferences-heading');
  const empty = identify(make('p', 'Carga las preferencias guardadas para revisar los ajustes.', 'field-hint'), 'empty');
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const recovery = identify(make('p', 'Se han recuperado preferencias con valores seguros. Revisa estos ajustes antes de guardar.', 'review-notice'), 'recovery'); recovery.setAttribute('role', 'status');
  const dirty = identify(make('p', '', 'field-hint'), 'dirty'); dirty.setAttribute('aria-live', 'polite');
  const controls = identify(make('div'), 'controls');
  const volumeLabel = make('label', 'Volumen inicial de preescucha'); volumeLabel.setAttribute('for', 'preferences-volume');
  const volume = identify(make('input'), 'volume'); volume.type = 'range'; volume.min = '0'; volume.max = '1'; volume.step = '0.01'; volume.setAttribute('aria-describedby', 'preferences-volume-hint preferences-volume-level');
  const level = identify(make('output'), 'volume-level'); level.setAttribute('for', 'preferences-volume');
  const volumeHint = identify(make('p', 'Define el nivel inicial al abrir XfinAudio. El volumen del reproductor del pie cambia solo en esta sesión. Editar aquí no lo modifica; Guardar aplica el nivel elegido sin iniciar la reproducción.', 'field-hint'), 'volume-hint');
  const watch = identify(make('input'), 'watch'); watch.type = 'checkbox'; watch.setAttribute('aria-describedby', 'preferences-watch-hint');
  const watchLabel = make('label', 'Vigilar cambios en las carpetas de la biblioteca'); watchLabel.setAttribute('for', 'preferences-watch');
  const watchHint = identify(make('p', 'La vigilancia avisa de cambios en las carpetas ya autorizadas. No modifica las pistas ni sustituye un nuevo escaneo. Solo se cambia al guardar.', 'field-hint'), 'watch-hint');
  volume.addEventListener('input', () => { if (canAct()) controller.setVolume(Number(volume.value)); });
  watch.addEventListener('change', () => { if (canAct()) controller.setWatchLibrary(watch.checked); });
  controls.append(volumeLabel, volume, level, volumeHint, watch, watchLabel, watchHint);
  const action = (id: string, caption: string, callback: () => void, primary = false): HTMLButtonElement => {
    const node = identify(make('button', caption, `button ${primary ? 'primary' : 'subtle'}`), id); node.type = 'button'; node.addEventListener('click', () => { if (canAct()) callback(); }); return node;
  };
  const save = action('save', 'Guardar preferencias', () => { void controller.save(); }, true);
  const discard = action('discard', 'Descartar cambios', () => controller.discard());
  const refresh = action('refresh', 'Actualizar', () => { void controller.load(); });
  const actions = make('div', '', 'editor-actions'); actions.append(save, discard, refresh);
  const labels = identify(make('ul'), 'libraries'); const labelsSection = make('section'); labelsSection.setAttribute('aria-labelledby', 'preferences-libraries-heading');
  labelsSection.append(identify(make('h3', 'Bibliotecas registradas'), 'libraries-heading'), labels);
  const capabilities = make('p', 'La escritura de etiquetas por sonoridad y los proveedores siguen en pausa. No se leen ni importan credenciales. La interfaz está en español.', 'field-hint');
  section.append(identify(make('h3', 'Preferencias locales'), 'heading'), empty, error, recovery, controls, dirty, actions, labelsSection, capabilities); root.replaceChildren(section);
  let renderedLabels: string | undefined;
  return () => {
    const snapshot = controller.snapshot; const blocked = !canAct();
    empty.hidden = Boolean(snapshot); controls.hidden = !snapshot; labelsSection.hidden = !snapshot;
    error.hidden = !controller.error; error.textContent = controller.error; recovery.hidden = !snapshot?.recoveryWarning;
    dirty.textContent = controller.dirty ? 'Cambios sin guardar. Se conservan al cambiar de pantalla.' : 'Sin cambios pendientes.';
    save.disabled = blocked || !controller.canSave; discard.disabled = blocked || !controller.dirty; refresh.disabled = blocked;
    volume.disabled = watch.disabled = blocked || !snapshot;
    if (!snapshot) return;
    capabilities.textContent = `${snapshot.capabilities.loudnessWriteback ? 'Configura el análisis y la escritura automática de etiquetas en Sonoridad; allí se comprueba el motor y se confirma cada ejecución.' : 'La escritura de etiquetas por sonoridad sigue en pausa.'} ${snapshot.capabilities.providers ? 'IA opcional permite configurar una fuente y realizar consultas con consentimiento y confirmación explícitos. Revisa cada envío en esa pantalla.' : 'Los proveedores siguen en pausa. No se leen ni importan credenciales.'} La interfaz está en español.`;
    if (volume.value !== String(snapshot.previewVolume)) volume.value = String(snapshot.previewVolume);
    watch.checked = snapshot.watchLibrary; level.textContent = `${Math.round(snapshot.previewVolume * 100)} %`; volume.setAttribute('aria-valuetext', level.textContent);
    const fingerprint = JSON.stringify(snapshot.libraryLabels);
    if (fingerprint !== renderedLabels) { renderedLabels = fingerprint; labels.replaceChildren(); for (const label of snapshot.libraryLabels) labels.append(make('li', label)); if (!snapshot.libraryLabels.length) labels.append(make('li', 'Todavía no hay bibliotecas registradas.')); }
  };
}
