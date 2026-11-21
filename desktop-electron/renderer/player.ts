import { audioUrl, formatDuration } from './model.js';
import type { Track } from './model.js';

/** S11 (d): the chosen preview output prepares the graph before any playback. */
export interface PreviewRoute { prepare(element: HTMLAudioElement): Promise<boolean>; readonly message: string; }

/** One audio element survives every page change; never create per-row players. */
export function createPlayer(onStateChange: () => void, preview: PreviewRoute | null = null) {
  const element = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const audio = element<HTMLAudioElement>('audio-player');
  const toggle = element<HTMLButtonElement>('player-toggle');
  const seek = element<HTMLInputElement>('player-seek');
  let current: Track | null = null;
  let revision = 0;
  const volume = element<HTMLInputElement>('player-volume');
  let volumeTouched = false;
  let initialVolumeApplied = false;
  // S11 (a): the host lets this page read `xfin-audio:` across origins, so Web Audio can
  // take the audio; without the attribute the source node stays silent.
  audio.crossOrigin = 'anonymous';
  audio.volume = 0.7;
  volume.value = '0.7';
  const status = (message: string) => { element('player-status').textContent = message; };
  const syncClock = () => {
    seek.disabled = !Number.isFinite(audio.duration) || audio.duration <= 0;
    seek.max = seek.disabled ? '100' : String(audio.duration);
    seek.value = String(Number.isFinite(audio.currentTime) ? audio.currentTime : 0);
    element('player-current').textContent = formatDuration(audio.currentTime);
    element('player-duration').textContent = formatDuration(audio.duration);
  };
  const sync = () => {
    toggle.disabled = current === null;
    toggle.textContent = audio.paused ? '▶' : 'Ⅱ';
    toggle.setAttribute('aria-label', audio.paused ? 'Reproducir' : 'Pausar');
    syncClock();
    onStateChange();
  };
  const play = async () => {
    const expected = revision;
    try { await audio.play(); }
    catch (error) {
      if (expected === revision && !(error instanceof DOMException && error.name === 'AbortError')) {
        status('No se pudo reproducir esta pista. Comprueba que el archivo siga disponible.');
        element('player-artist').textContent = 'No se pudo reproducir · Prueba otra pista';
      }
    }
    if (expected === revision) sync();
  };
  const select = async (track: Track) => {
    // S11 (d)(e): with a chosen output the graph is prepared first, and an output that is
    // gone refuses the playback instead of falling back to another one.
    if (preview && !(await preview.prepare(audio))) {
      revision += 1;
      audio.pause();
      status(preview.message);
      return;
    }
    if (current?.id === track.id) {
      if (audio.paused) await play(); else audio.pause();
      return;
    }
    revision += 1;
    audio.pause();
    current = track;
    audio.src = audioUrl(track.id);
    element('player-title').textContent = track.title || 'Sin título';
    element('player-artist').textContent = track.artist || 'Artista desconocido';
    status(`Preescucha: ${track.title}`);
    audio.load();
    sync();
    await play();
  };
  toggle.addEventListener('click', () => { if (current) void select(current); });
  seek.addEventListener('input', () => {
    if (!seek.disabled) audio.currentTime = Math.min(audio.duration, Math.max(0, Number(seek.value)));
    sync();
  });
  volume.addEventListener('input', () => {
    const value = Number(volume.value);
    if (!Number.isFinite(value)) return;
    volumeTouched = true;
    audio.volume = Math.min(1, Math.max(0, value));
  });
  for (const event of ['play', 'pause', 'ended', 'loadedmetadata', 'durationchange']) audio.addEventListener(event, sync);
  audio.addEventListener('timeupdate', syncClock);
  audio.addEventListener('error', () => {
    if (current) {
      status('El archivo no está disponible o su formato no se puede reproducir');
      element('player-artist').textContent = 'Archivo no disponible o formato no compatible';
    }
    sync();
  });
  return {
    select,
    applyPreferencesVolume(value: number, reason: 'load' | 'save'): void {
      if (!Number.isFinite(value) || value < 0 || value > 1) return;
      if (reason === 'load') {
        if (initialVolumeApplied) return;
        initialVolumeApplied = true;
        if (volumeTouched) return;
      } else initialVolumeApplied = true;
      audio.volume = value;
      volume.value = String(value);
    },
    isPlaying: (id: string) => current?.id === id && !audio.paused,
    stopIfMissing(ids: Set<string>) {
      if (current && !ids.has(current.id)) {
        revision += 1;
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
        current = null;
        element('player-title').textContent = 'Tu próxima conexión';
        element('player-artist').textContent = 'Selecciona una pista para escuchar';
        sync();
      }
    },
  };
}
