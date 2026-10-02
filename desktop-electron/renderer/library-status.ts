export interface LibraryStatus {
  revision: number;
  changeState: 'restored' | 'clean' | 'changed';
  watchState: 'starting' | 'active' | 'disabled' | 'unavailable' | 'paused';
  rootCount: number; watchedCount: number;
}
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `library-status-${suffix}`; return node; };
/** Separate read-only projections: watcher availability never rewrites the last observed change state. */
export function createLibraryStatusView(root: HTMLElement, host: { canAct(): boolean; rescan(): void }): (status: LibraryStatus | null) => void {
  const banner = identify(make('section'), 'banner'); banner.className = 'surface prep-form'; banner.setAttribute('aria-live', 'polite'); banner.setAttribute('aria-labelledby', 'library-status-heading');
  const changes = identify(make('p'), 'changes'); const watch = identify(make('p'), 'watch'); const counts = identify(make('p'), 'counts'); counts.className = 'field-hint';
  const rescan = identify(make('button', 'Volver a escanear bibliotecas'), 'rescan'); rescan.type = 'button'; rescan.className = 'button subtle';
  let current: LibraryStatus | null = null;
  rescan.addEventListener('click', () => { if (host.canAct() && current && current.rootCount > 0) host.rescan(); });
  banner.append(identify(make('h3', 'Estado de la biblioteca'), 'heading'), changes, watch, counts, rescan); root.replaceChildren(banner);
  return (status): void => {
    current = status; rescan.disabled = !host.canAct() || !status || status.rootCount === 0;
    if (!status) { changes.textContent = 'Estado de la biblioteca no disponible.'; watch.textContent = ''; counts.textContent = ''; return; }
    changes.textContent = ({
      restored: 'Biblioteca restaurada tras reiniciar. Todavía no se ha verificado de nuevo después del reinicio.',
      clean: status.rootCount ? 'Escaneo completado. No se han detectado cambios desde el último escaneo.' : 'No hay carpetas autorizadas para verificar. Elige una carpeta de música para empezar.',
      changed: 'Se han detectado cambios en la biblioteca. Vuelve a escanear para revisar los archivos y actualizar la selección.',
    })[status.changeState];
    watch.textContent = ({
      starting: 'Iniciando la vigilancia automática de cambios…',
      active: `Vigilancia activa en ${status.watchedCount} de ${status.rootCount} carpetas.`,
      disabled: 'Vigilancia automática desactivada. Puedes volver a escanear manualmente.',
      unavailable: 'No se pueden vigilar automáticamente los cambios futuros. Vuelve a escanear manualmente para comprobarlos.',
      paused: 'Vigilancia temporalmente en pausa. El estado del último escaneo se conserva.',
    })[status.watchState];
    watch.className = status.watchState === 'unavailable' ? 'review-notice' : 'field-hint';
    counts.textContent = `${status.rootCount} ${status.rootCount === 1 ? 'carpeta registrada' : 'carpetas registradas'} · ${status.watchedCount} vigiladas`;
  };
}
