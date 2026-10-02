import { formatDuration } from './model.js';
import type { Track } from './model.js';
import { LiveElapsedClock } from './live.js';
import type { LiveController, LiveSnapshot } from './live.js';
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `live-${suffix}`; return node; };
const button = (caption: string, action: () => void, primary = false): HTMLButtonElement => {
  const node = make('button', caption, `button ${primary ? 'primary' : 'subtle'}`); node.type = 'button'; node.addEventListener('click', action); return node;
};
export interface LiveViewHost { canAct(): boolean; isConnected?(): boolean; play(track: Track): void; }
export interface LiveView { render(): void; dispose(): void; }

export function createLiveView(root: HTMLElement, controller: LiveController, host: LiveViewHost): LiveView {
  const clock = new LiveElapsedClock(); let disposed = false;
  const canAct = (): boolean => host.canAct() && !controller.pending;
  const canUse = (snapshot: LiveSnapshot): boolean => canAct() && controller.valid && controller.snapshot === snapshot;
  const empty = identify(make('section', 'Abre Live desde una selección revisada completamente lista. No se generan sugerencias alternativas si la selección no está disponible.', 'surface empty-state'), 'empty');
  const error = identify(make('p', '', 'review-notice blocker'), 'error'); error.setAttribute('role', 'alert');
  const unavailable = identify(make('p', '', 'review-notice blocker'), 'unavailable'); unavailable.setAttribute('role', 'status');
  const content = identify(make('div'), 'content');
  const summary = make('section', '', 'surface prep-form'); summary.setAttribute('aria-labelledby', 'live-current-heading');
  const currentTitle = identify(make('h3'), 'current-heading'); currentTitle.setAttribute('aria-live', 'polite');
  const currentDetails = make('p', '', 'field-hint'); const elapsed = identify(make('strong', '', 'numeric'), 'elapsed');
  const timeLabel = make('p', 'Tiempo desde la última marca manual: '); timeLabel.append(elapsed);
  const currentPreview = identify(button('Preescuchar pista actual', () => { const snapshot = controller.snapshot; if (snapshot && canUse(snapshot)) host.play(snapshot.current); }), 'current-preview');
  currentPreview.setAttribute('aria-label', 'Preescuchar pista actual');
  const refresh = identify(button('Actualizar estado', () => { if (canAct() && controller.snapshot) void controller.refresh(); }), 'refresh');
  const clear = identify(button('Finalizar y limpiar Live', () => { if (canAct() && controller.snapshot) void controller.clear(); }), 'clear');
  const actions = make('div', '', 'editor-actions'); actions.append(currentPreview, refresh, clear);
  summary.append(make('span', 'PISTA MARCADA COMO ACTUAL', 'eyebrow'), currentTitle, currentDetails, timeLabel, actions,
    make('p', 'Live es una guía manual. El tiempo y el historial reflejan tus marcas, no la reproducción detectada. Preescuchar y marcar la siguiente pista son acciones separadas; no se controlan decks de Serato.', 'field-hint'));
  const choices = make('section', '', 'surface prep-form editor-proposal'); choices.setAttribute('aria-labelledby', 'live-candidates-heading');
  const complete = identify(make('p', '', 'field-hint'), 'complete');
  const candidates = identify(make('ol', '', 'editor-proposed-tracks'), 'candidates'); candidates.setAttribute('aria-label', 'Siguientes pistas clasificadas por el motor');
  choices.append(identify(make('h3', 'Siguientes pistas recomendadas'), 'candidates-heading'), complete, candidates);
  const historySection = make('section', '', 'surface prep-form editor-proposal'); historySection.setAttribute('aria-labelledby', 'live-history-heading');
  const history = identify(make('ol', '', 'editor-proposed-tracks'), 'history'); const historyEmpty = make('p', 'Todavía no has marcado un cambio de pista.', 'field-hint');
  historySection.append(identify(make('h3', 'Historial de marcas manuales'), 'history-heading'), historyEmpty, history);
  content.append(summary, choices, historySection); root.replaceChildren(empty, error, unavailable, content);
  let rendered: LiveSnapshot | null | undefined; let candidateButtons: HTMLButtonElement[] = [];
  const updateElapsed = (): void => {
    if (disposed) return;
    const connected = (host.isConnected ? host.isConnected() : host.canAct()) && controller.valid;
    elapsed.textContent = formatDuration(clock.read(controller.snapshot, connected));
  };
  let timer: ReturnType<typeof globalThis.setInterval> | null = null;
  const stopTimer = (): void => { if (timer !== null) globalThis.clearInterval(timer); timer = null; };
  return {
    render(): void {
      if (disposed) return;
      const snapshot = controller.snapshot; const blocked = !canAct(); const connected = host.isConnected ? host.isConnected() : host.canAct();
      empty.hidden = Boolean(snapshot); content.hidden = !snapshot;
      error.hidden = !controller.error; error.textContent = controller.error;
      unavailable.hidden = connected && (!snapshot || controller.valid);
      unavailable.textContent = !connected ? 'Servicio local desconectado. El tiempo está pausado y esta sesión ya no está disponible; reinicia XfinAudio para continuar.' : 'La sesión mostrada no está vigente. Actualiza el estado o vuelve a abrir Live desde una selección revisada y lista.';
      refresh.disabled = clear.disabled = blocked || !snapshot;
      currentPreview.disabled = blocked || !snapshot || !controller.valid;
      if (snapshot !== rendered) {
        rendered = snapshot; candidates.replaceChildren(); history.replaceChildren(); candidateButtons = [];
        if (snapshot) {
          currentTitle.textContent = `${snapshot.current.title || 'Sin título'} · ${snapshot.current.artist || 'Artista desconocido'}`;
          currentDetails.textContent = `${snapshot.current.bpm ?? '—'} BPM · ${snapshot.current.key || '—'} · Energía ${snapshot.current.energy ?? '—'}`;
          complete.textContent = snapshot.state === 'complete' ? 'Selección completada: no hay más pistas por marcar. La pista final sigue como actual hasta que limpies Live.' : snapshot.candidates.length ? 'Clasificación real de la selección aplicada. Revisa los avisos antes de marcar una pista.' : 'No hay opciones elegibles en la selección actual. No se añade ninguna pista de reserva.';
          for (const [index, candidate] of snapshot.candidates.entries()) {
            const row = make('li'); row.append(make('strong', `${index + 1}. ${candidate.track.title || 'Sin título'} · ${candidate.track.artist || 'Artista desconocido'}`), make('p', `Puntuación del motor: ${Number.isFinite(candidate.score) ? candidate.score.toLocaleString('es', { maximumFractionDigits: 2 }) : '—'}`, 'field-hint'));
            const alerts = make('ul'); for (const alert of candidate.alerts) alerts.append(make('li', alert)); row.append(alerts);
            const preview = button('Preescuchar', () => { if (canUse(snapshot)) host.play(candidate.track); }); preview.dataset.livePreview = candidate.track.id; preview.setAttribute('aria-label', `Preescuchar opción ${index + 1}: ${candidate.track.title}`);
            const next = button('Marcar como siguiente', () => { if (canUse(snapshot) && snapshot.state === 'active') void controller.advance(candidate.track.id); }, true); next.dataset.liveNext = candidate.track.id; next.setAttribute('aria-label', `Marcar como siguiente: ${candidate.track.title}`);
            const controls = make('div', '', 'editor-actions'); controls.append(preview, next); candidateButtons.push(preview, next); row.append(controls); candidates.append(row);
          }
          for (const entry of snapshot.history) {
            const date = new Date(entry.startedAt); const time = Number.isNaN(date.getTime()) ? 'Hora no disponible' : date.toLocaleString('es');
            history.append(make('li', `${entry.track.title || 'Sin título'} · ${entry.track.artist || 'Artista desconocido'} · Inicio marcado: ${time}`));
          }
          historyEmpty.hidden = snapshot.history.length > 0;
        }
      }
      for (const control of candidateButtons) control.disabled = blocked || !controller.valid || (Boolean(control.dataset.liveNext) && snapshot?.state !== 'active');
      updateElapsed();
      if (snapshot && connected && controller.valid) { if (timer === null) timer = globalThis.setInterval(updateElapsed, 500); }
      else stopTimer();
    },
    dispose(): void { disposed = true; stopTimer(); },
  };
}
