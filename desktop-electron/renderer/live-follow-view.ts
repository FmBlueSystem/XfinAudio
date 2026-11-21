/** S5 presentation of the follow-Serato section; the controller owns polling and identity. */
import type { Track } from './model.js';
import { transitionQuality } from './review-facts.js';
import { deckOf, followKey } from './live-follow.js';
import type { LiveFollowAnswer, LiveFollowController, LiveFollowPlaying } from './live-follow.js';

const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};
const identify = <T extends HTMLElement>(node: T, suffix: string): T => { node.id = `live-follow-${suffix}`; return node; };
const button = (caption: string, action: () => void): HTMLButtonElement => {
  const node = make('button', caption, 'button subtle'); node.type = 'button'; node.addEventListener('click', action); return node;
};
const number = (value: number | null | undefined): string => typeof value === 'number' && Number.isFinite(value) ? String(value) : '—';

export interface LiveFollowViewHost { play(track: Track): void; /** S9: the bridge, so a row can ask for its own file; absent until the host ships `dragTrack`. */ api?: LiveFollowDragApi; }
export interface LiveFollowDragApi { dragTrack?(input: { trackId: string }): unknown; }
export interface LiveFollowView { render(): void; dispose(): void; }

/** S8: the columns of «Qué poner después», in the order the user reads them. */
const SUGGESTION_COLUMNS = ['#', 'Título', 'Artista', 'BPM', 'Tonalidad', 'Energía', 'Mezcla', 'Escuchar'] as const;
const DRAG_HINT = 'Arrastra una fila a un deck o a un crate de Serato.';

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
  // S10: while a deck is chosen, «Automático» goes back to the newest open entry.
  const automatic = identify(button('Automático', () => { controller.chooseDeck(null); }), 'automatic');
  automatic.hidden = true;
  const playingBlock = make('section', '', 'live-follow-block');
  const playingList = identify(make('ol', '', 'editor-proposed-tracks'), 'playing');
  playingList.setAttribute('aria-label', 'Pistas sonando en Serato');
  playingBlock.append(identify(make('h4', 'Sonando en Serato'), 'playing-heading'), playingList);
  const suggestionsBlock = make('section', '', 'live-follow-block editor-proposal');
  // S8: the suggestions are a table; S9 makes each row the handle of its own audio file.
  const suggestionsTable = identify(make('table', '', 'live-follow-suggestions'), 'suggestions');
  suggestionsTable.setAttribute('aria-label', 'Sugerencias para lo que suena en Serato');
  const suggestionsHead = make('thead'); const suggestionHeaders = make('tr');
  for (const caption of SUGGESTION_COLUMNS) { const th = make('th', caption); th.scope = 'col'; suggestionHeaders.append(th); }
  suggestionsHead.append(suggestionHeaders);
  const suggestionsBody = identify(make('tbody'), 'suggestion-rows');
  suggestionsTable.append(suggestionsHead, suggestionsBody);
  const suggestionsScroll = make('div', '', 'table-scroll'); suggestionsScroll.append(suggestionsTable);
  const suggestionsHeading = identify(make('h4', 'Qué poner después'), 'suggestions-heading');
  suggestionsBlock.append(suggestionsHeading, suggestionsScroll,
    identify(make('p', DRAG_HINT, 'field-hint'), 'drag-hint'));
  section.append(identify(make('h3', 'Seguir a Serato'), 'heading'), toggle, message, automatic, playingBlock, suggestionsBlock,
    identify(make('p', 'Solo lectura: XfinAudio no controla Serato ni modifica su historial.', 'field-hint'), 'readonly'));
  root.replaceChildren(section);

  const rebuild = (answer: LiveFollowAnswer | null): void => {
    playingList.replaceChildren(); suggestionsBody.replaceChildren();
    playingBlock.hidden = !answer || answer.playing.length === 0;
    suggestionsBlock.hidden = !answer || answer.suggestions.length === 0;
    if (!answer) return;
    // S9: no bridge action means no draggable row: the table stays readable and inert.
    const dragTrack = typeof host.api?.dragTrack === 'function' ? host.api.dragTrack : null;
    // S10: the marked line is the deck the answer calls current, else the deck the user chose,
    // and without a choice the newest playing entry that is in the library (S7 e).
    const chosen = controller.chosenDeck;
    const target = chosen ?? deckOf(answer.currentDeck);
    let currentIndex = target === null ? -1 : answer.playing.findIndex((entry) => deckOf(entry.deck) === target);
    if (currentIndex < 0 && chosen === null) currentIndex = answer.playing.findIndex((entry) => entry.inLibrary);
    // S10: each line is a button that asks for its own deck.
    for (const [index, entry] of answer.playing.entries()) {
      const current = index === currentIndex;
      const row = make('li', '', current ? 'live-follow-current' : '');
      const line = button(playingLine(entry, current), () => { controller.chooseDeck(entry.deck); });
      line.className = `live-follow-deck${current ? ' is-current' : ''}`;
      line.dataset.liveFollowDeck = deckOf(entry.deck) ?? String(entry.deck ?? '');
      if (current) line.setAttribute('aria-current', 'true');
      row.append(line);
      playingList.append(row);
    }
    // S10: the heading names the track the suggestions are for.
    const title = answer.current ? answer.current.title || 'Sin título' : '';
    suggestionsHeading.textContent = title ? `Qué poner después de ${title}` : 'Qué poner después';
    for (const [index, suggestion] of answer.suggestions.entries()) {
      const quality = transitionQuality(suggestion.score);
      const row = make('tr');
      row.dataset.liveFollowSuggestion = suggestion.id;
      row.draggable = dragTrack !== null;
      // The row is the drag handle: the browser drag is cancelled, so the host alone starts
      // the native drag and the track path never reaches the renderer.
      if (dragTrack) row.addEventListener('dragstart', (event) => {
        event.preventDefault();
        void dragTrack({ trackId: suggestion.id });
      });
      row.append(
        make('td', String(index + 1), 'track-index'),
        make('td', suggestion.title || 'Sin título'),
        make('td', suggestion.artist || 'Artista desconocido'),
        make('td', number(suggestion.bpm), 'numeric'),
        make('td', suggestion.key || '—'),
        make('td', number(suggestion.energy), 'numeric'),
        make('td', quality.text, `transition-quality ${quality.tone}`),
      );
      const action = make('td');
      const preview = button('Preescuchar', () => { host.play(suggestion); });
      preview.dataset.liveFollowPreview = suggestion.id;
      preview.setAttribute('aria-label', `Preescuchar ${suggestion.title || 'la pista sugerida'}`);
      action.append(preview);
      row.append(action); suggestionsBody.append(row);
    }
  };

  return {
    render(): void {
      if (disposed) return;
      switchControl.checked = controller.following;
      automatic.hidden = controller.chosenDeck === null;
      const line = controller.message;
      message.hidden = !line; message.textContent = line;
      const key = followKey(controller.answer, controller.reason, controller.chosenDeck);
      // The redraw follows the playing tracks and the chosen deck only: a new answer with the
      // same decks keeps every list node, so a switch or a scroll is never reset by the poll.
      if (key === drawn) return;
      drawn = key;
      rebuild(controller.answer);
    },
    dispose(): void { disposed = true; },
  };
}
