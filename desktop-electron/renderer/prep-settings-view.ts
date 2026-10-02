import type { PrepSettingsController } from './prep-settings.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = ''): HTMLElementTagNameMap[K] => { const node = document.createElement(tag); node.textContent = text; return node; };
export function createPrepSettingsView(root: HTMLElement, controller: PrepSettingsController, host: { canAct(): boolean }): () => void {
  const section = make('section'); section.className = 'prep-advanced'; section.append(make('h3', 'Controles guardados'));
  const hint = make('p', 'Guarda las pistas obligatorias, exclusiones y género para la próxima apertura. Los cambios de esta sesión no se guardan automáticamente.'); hint.className = 'field-hint';
  const status = make('p'); status.id = 'prep-settings-status'; status.setAttribute('aria-live', 'polite');
  const error = make('p'); error.id = 'prep-settings-error'; error.setAttribute('role', 'alert');
  const missing = make('p'); missing.id = 'prep-settings-unavailable';
  const label = make('label', 'Eliminar también los controles guardados que no están disponibles');
  const clear = make('input'); clear.type = 'checkbox'; clear.id = 'prep-settings-clear'; label.setAttribute('for', clear.id); clear.addEventListener('change', () => controller.setClearUnavailable(clear.checked));
  const action = (name: string, caption: string, callback: () => void): HTMLButtonElement => { const node = make('button', caption); node.type = 'button'; node.id = `prep-settings-${name}`; node.className = 'button subtle'; node.addEventListener('click', () => { if (host.canAct() && !controller.pending) callback(); }); return node; };
  const save = action('save', 'Guardar controles', () => { void controller.save(); });
  const load = action('load', 'Restaurar controles guardados', () => { void controller.load(); });
  const discard = action('discard', 'Descartar cambios de controles', () => controller.discard());
  section.append(hint, status, error, missing, clear, label, save, load, discard); root.replaceChildren(section);
  return () => {
    const blocked = !host.canAct() || controller.pending; const snapshot = controller.snapshot;
    save.disabled = blocked || !controller.canSave; load.disabled = blocked; discard.disabled = blocked || !controller.dirty;
    error.textContent = controller.error; error.hidden = !controller.error;
    status.textContent = controller.pending ? 'Actualizando controles…' : controller.dirty ? 'Cambios sin guardar para la próxima apertura.' : snapshot ? 'Controles guardados restaurados.' : 'Carga los controles guardados para restaurarlos.';
    const count = (snapshot?.unavailableRequiredCount ?? 0) + (snapshot?.unavailableExcludedCount ?? 0);
    missing.hidden = label.hidden = clear.hidden = count === 0;
    missing.textContent = `${snapshot?.unavailableRequiredCount ?? 0} obligatorias y ${snapshot?.unavailableExcludedCount ?? 0} excluidas no disponibles. Se conservan guardadas; vuelve a autorizar o escanear sus carpetas para recuperarlas.`;
    clear.checked = controller.clearUnavailable; clear.disabled = blocked;
  };
}
