/** S5 presentation of the follow-Serato section; the controller owns polling and identity. */
import type { Track } from './model.js';
import { transitionQuality } from './review-facts.js';
import { followKey } from './live-follow.js';
import type { LiveFollowAnswer, LiveFollowController, LiveFollowPlaying } from './live-follow.js';

const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `live-follow-${suffix}`; return node; };
const button = (caption: string, action: () => void): HTMLButtonElement => {
  const node = make('button', caption, 'button subtle'); node.type = 'button'; node.addEventListener('click', action); return node;
};
const number = (value: number | null | undefined): string => typeof value === 'number' && Number.isFinite(value) ? String(value) : '—';

export interface LiveFollowViewHost { play(track: Track): void; }
export interface LiveFollowView { render(): void; dispose(): void; }

/** «Deck 1: Título — Artista · 124 BPM · 8A», with «Actual» on the newest library track. */
export function playingLine(entry: LiveFollowPlaying, current: boolean): string {
  return `Deck ${entry.deck}: ${entry.title || 'Sin título'} — ${entry.artist || 'Artista desconocido'} · ${number(entry.bpm)} BPM · ${entry.key || '—'}${current ? ' · Actual' : ''}`;
}

export function createLiveFollowView(root: HTMLElement, controller: LiveFollowController, host: LiveFollowViewHost): LiveFollowView {
  let disposed = false; let drawn = '';
  const section = make('section', '', 'surface prep-form live-follow');
  section.setAttribute('aria-labelledby', 'live-follow-heading');
  const toggle = make('label', '', 'live-follow-toggle');
  const switchControl = document.createElement('input');
  switchControl.type = 'checkbox'; switchControl.id = 'live-follow-switch'; switchControl.checked = controller.following;
  switchControl.addEventListener('change', () => { controller.setFollowing(switchControl.checked === true); });
  toggle.append(switchControl, make('span', 'Seguir lo que suena en Serato'));
  const message = identify(make('p', '', 'field-hint'), 'message'); message.setAttribute('role', 'status');
  const playingBlock = make('section', '', 'live-follow-block');
  const playingList = identify(make('ol', '', 'editor-proposed-tracks'), 'playing');
  playingList.setAttribute('aria-label', 'Pistas sonando en Serato');
  playingBlock.append(identify(make('h4', 'Sonando en Serato'), 'playing-heading'), playingList);
  const suggestionsBlock = make('section', '', 'live-follow-block editor-proposal');
  const suggestionsList = identify(make('ol', '', 'editor-proposed-tracks'), 'suggestions');
  suggestionsList.setAttribute('aria-label', 'Sugerencias para lo que suena en Serato');
  suggestionsBlock.append(identify(make('h4', 'Qué poner después'), 'suggestions-heading'), suggestionsList);
  section.append(identify(make('h3', 'Seguir a Serato'), 'heading'), toggle, message, playingBlock, suggestionsBlock,
    identify(make('p', 'Solo lectura: XfinAudio no controla Serato ni modifica su historial.', 'field-hint'), 'readonly'));
  root.replaceChildren(section);

  const rebuild = (answer: LiveFollowAnswer | null): void => {
    playingList.replaceChildren(); suggestionsList.replaceChildren();
    playingBlock.hidden = !answer || answer.playing.length === 0;
    suggestionsBlock.hidden = !answer || answer.suggestions.length === 0;
    if (!answer) return;
    // S3's `current` is the newest open entry in the library; the same entry is the one marked.
    let currentIndex = -1;
    answer.playing.forEach((entry, index) => { if (entry.inLibrary) currentIndex = index; });
    for (const [index, entry] of answer.playing.entries()) {
      const row = make('li', playingLine(entry, index === currentIndex), index === currentIndex ? 'live-follow-current' : '');
      playingList.append(row);
    }
    for (const suggestion of answer.suggestions) {
      const row = make('li');
      row.append(make('strong', `${suggestion.title || 'Sin título'} · ${suggestion.artist || 'Artista desconocido'}`));
      const quality = transitionQuality(suggestion.score);
      const facts = make('p', '', 'field-hint');
      facts.append(make('span', `${number(suggestion.bpm)} BPM · ${suggestion.key || '—'} · Energía ${number(suggestion.energy)} · `),
        make('span', quality.text, `transition-quality ${quality.tone}`));
      const controls = make('div', '', 'editor-actions');
      const preview = button('Preescuchar', () => { host.play(suggestion); });
      preview.dataset.liveFollowPreview = suggestion.id;
      preview.setAttribute('aria-label', `Preescuchar ${suggestion.title || 'la pista sugerida'}`);
      controls.append(preview);
      row.append(facts, controls); suggestionsList.append(row);
    }
  };

  return {
    render(): void {
      if (disposed) return;
      switchControl.checked = controller.following;
      const line = controller.message;
      message.hidden = !line; message.textContent = line;
      const key = followKey(controller.answer, controller.reason);
      // The redraw follows the playing tracks only: a new answer with the same decks keeps
      // every list node, so a switch or a scroll is never reset by the three-second poll.
      if (key === drawn) return;
      drawn = key;
      rebuild(controller.answer);
    },
    dispose(): void { disposed = true; },
  };
}
