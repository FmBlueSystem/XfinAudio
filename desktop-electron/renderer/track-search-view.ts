import {
  clearedTrackMessage, nextActiveIndex, searchResultMessage, searchTracks, selectedTrackMessage,
  trackChoiceArtist, trackChoiceLabel, trackChoiceMeta, trackChoiceTitle, unavailableTrackLabel,
} from './track-search.js';
import type { Track } from './model.js';

export interface TrackSearchHost { changed(): void; }
export interface TrackSearchView {
  setLibrary(tracks: Track[]): void;
  setSelected(id: string): void;
  sync(): void;
}

const element = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};

/**
 * Accessible combobox for the opening track. It only writes the chosen opaque id into the
 * hidden #prep-start input, so PrepFields, buildPrepInput and startTrackId stay unchanged.
 */
export function createTrackSearchView(host: TrackSearchHost): TrackSearchView {
  const input = element<HTMLInputElement>('prep-start-search');
  const list = element<HTMLUListElement>('prep-start-results');
  const status = element<HTMLElement>('prep-start-status');
  const selection = element<HTMLElement>('prep-start-selection');
  const chosenLabel = element<HTMLElement>('prep-start-selected-label');
  const chosenMeta = element<HTMLElement>('prep-start-selected-meta');
  const clear = element<HTMLButtonElement>('prep-start-clear');
  const hidden = element<HTMLInputElement>('prep-start');
  let tracks: Track[] = [];
  let results: Track[] = [];
  let options: HTMLElement[] = [];
  let active = -1;

  const announce = (text: string): void => { status.textContent = text; };
  const close = (): void => {
    active = -1; results = []; options = [];
    list.replaceChildren(); list.hidden = true;
    input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant');
  };
  const highlight = (): void => {
    options.forEach((option, index) => option.setAttribute('aria-selected', index === active ? 'true' : 'false'));
    if (active >= 0 && options[active]) input.setAttribute('aria-activedescendant', options[active].id);
    else input.removeAttribute('aria-activedescendant');
  };
  const renderSelection = (announcement?: string): void => {
    const id = hidden.value;
    const track = id ? tracks.find((item) => item.id === id) : undefined;
    clear.hidden = !id;
    if (!id) {
      selection.setAttribute('data-state', 'empty');
      chosenLabel.textContent = 'Sin preferencia'; chosenMeta.textContent = '';
    } else {
      selection.setAttribute('data-state', track ? 'chosen' : 'unavailable');
      chosenLabel.textContent = track ? trackChoiceLabel(track) : unavailableTrackLabel(id);
      chosenMeta.textContent = track ? trackChoiceMeta(track) : 'Ya no está en la biblioteca.';
    }
    if (announcement) announce(announcement);
  };
  const choose = (id: string): void => {
    const track = tracks.find((item) => item.id === id);
    hidden.value = id; input.value = '';
    close();
    renderSelection(selectedTrackMessage(track ? trackChoiceLabel(track) : unavailableTrackLabel(id)));
    host.changed();
  };
  const open = (): void => {
    const query = input.value;
    const found = searchTracks(tracks, query);
    results = found.results; active = results.length ? 0 : -1;
    options = results.map((track, index) => {
      const item = make('li', '', 'track-result');
      item.id = `prep-start-option-${index}`;
      item.setAttribute('role', 'option');
      item.append(make('span', trackChoiceTitle(track), 'track-result-title'), make('span', trackChoiceArtist(track), 'track-result-artist'), make('span', trackChoiceMeta(track), 'track-result-meta'));
      item.addEventListener('click', () => choose(track.id));
      return item;
    });
    list.replaceChildren(...options);
    list.hidden = options.length === 0;
    input.setAttribute('aria-expanded', options.length ? 'true' : 'false');
    highlight();
    announce(searchResultMessage(query, results.length, found.total));
  };

  input.addEventListener('input', () => { open(); host.changed(); });
  input.addEventListener('keydown', (event) => {
    const key = (event as KeyboardEvent).key;
    if (key === 'ArrowDown' || key === 'ArrowUp') {
      event.preventDefault();
      if (list.hidden || results.length === 0) open();
      else { active = nextActiveIndex(active, key === 'ArrowDown' ? 1 : -1, results.length); highlight(); }
      return;
    }
    if (key === 'Enter') {
      const choice = results[active];
      if (!choice) return;
      event.preventDefault(); choose(choice.id); return;
    }
    if (key === 'Escape' && !list.hidden) { event.preventDefault(); close(); }
  });
  // A pointer press inside the list must not blur the input before the click selects.
  list.addEventListener('mousedown', (event) => event.preventDefault());
  input.addEventListener('blur', () => close());
  clear.addEventListener('click', () => {
    hidden.value = ''; input.value = ''; close();
    renderSelection(clearedTrackMessage()); host.changed(); input.focus();
  });
  close();
  renderSelection();

  return {
    setLibrary: (library) => { tracks = library; renderSelection(); if (!list.hidden) open(); },
    setSelected: (id) => { hidden.value = id; input.value = ''; close(); renderSelection(); },
    sync: () => { renderSelection(); },
  };
}
