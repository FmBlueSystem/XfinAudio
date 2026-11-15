import {
  nextActiveIndex, searchResultMessage, searchTracks, trackChoiceArtist, trackChoiceLabel, trackChoiceMeta, trackChoiceTitle, unavailableTrackLabel,
} from './track-search.js';
import {
  chooseIds, chosenMessage, chipRemoveLabel, clearedMessage, emptyChoiceLabel, pickerChoice, pickerChoices, removeId, removedMessage,
} from './track-picker.js';
import type { TrackPickerChoice, TrackPickerKind } from './track-picker.js';
import type { Track } from './model.js';

export interface TrackPickerConfig { id: string; kind: TrackPickerKind; multiple: boolean; changed(): void; }
export interface TrackPickerView {
  setLibrary(tracks: Track[]): void;
  setSelected(ids: string[]): void;
  sync(): void;
}

const element = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};

/**
 * The opening-track combobox mounted for the closing, required and excluded tracks: typing
 * filters by title, artist, genre and BPM, arrows and Enter or a click choose, and every chosen
 * track is a chip with «Quitar». It only writes the chosen opaque ids into the existing
 * #prep-end, #prep-required or #prep-excluded select, so PrepFields, buildPrepInput, the saved
 * controls and the remembered form keep reading unchanged values.
 */
export function createTrackPicker(config: TrackPickerConfig): TrackPickerView {
  const select = element<HTMLSelectElement>(`prep-${config.id}`);
  const input = element<HTMLInputElement>(`prep-${config.id}-search`);
  const chips = element<HTMLElement>(`prep-${config.id}-chips`);
  const list = element<HTMLUListElement>(`prep-${config.id}-results`);
  const status = element<HTMLElement>(`prep-${config.id}-status`);
  let tracks: Track[] = [];
  let results: Track[] = [];
  let options: HTMLElement[] = [];
  let active = -1;

  const announce = (text: string): void => { status.textContent = text; };
  const carriers = (): HTMLOptionElement[] => Array.from(select.options ?? []);
  /** The select is the value carrier, so every choice is read back from it. */
  const readIds = (): string[] => {
    const ids = Array.from(select.selectedOptions ?? [], (item) => item.value).filter(Boolean);
    for (const item of carriers()) if (item.selected && item.value && !ids.includes(item.value)) ids.push(item.value);
    return config.multiple ? ids : ids.slice(0, 1);
  };
  /** A chosen id is added to the carrier; one that left the library stays explicit and blocks. */
  const ensureOption = (id: string): void => {
    if (carriers().some((item) => item.value === id)) return;
    const track = tracks.find((item) => item.id === id);
    const added = make('option', track ? trackChoiceLabel(track) : unavailableTrackLabel(id));
    added.value = id;
    if (!track) added.disabled = true;
    select.append(added);
  };
  const writeIds = (ids: string[]): void => {
    for (const id of ids) if (id) ensureOption(id);
    const keep = new Set(ids.filter(Boolean));
    for (const item of carriers()) item.selected = keep.has(item.value);
    if (!config.multiple) select.value = ids.find(Boolean) ?? '';
  };
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
  const chip = (choice: TrackPickerChoice): HTMLElement => {
    const item = make('li', '', 'track-chip');
    item.setAttribute('data-state', choice.available ? 'chosen' : 'unavailable');
    const body = make('span', '', 'track-chip-body');
    body.append(make('span', choice.label, 'track-chip-label'), make('span', choice.meta, 'track-chip-meta'));
    const remove = make('button', 'Quitar', 'text-button');
    remove.type = 'button';
    remove.setAttribute('aria-label', chipRemoveLabel(choice.label));
    remove.addEventListener('click', () => {
      if (select.disabled) return;
      const remaining = removeId(readIds(), choice.id);
      writeIds(remaining);
      renderChips(remaining.length ? removedMessage(choice.label) : clearedMessage(config.kind));
      input.focus();
      config.changed();
    });
    item.append(body, remove);
    return item;
  };
  const renderChips = (announcement?: string): void => {
    const chosen = pickerChoices(readIds(), tracks);
    chips.replaceChildren(...(chosen.length ? chosen.map(chip) : [make('li', emptyChoiceLabel(config.kind), 'track-chip-empty')]));
    if (announcement) announce(announcement);
  };
  const choose = (id: string): void => {
    if (select.disabled) return;
    writeIds(chooseIds(readIds(), id, config.multiple));
    input.value = ''; close();
    renderChips(chosenMessage(config.kind, pickerChoice(id, tracks).label));
    config.changed();
  };
  const open = (): void => {
    const query = input.value;
    const found = searchTracks(tracks, query);
    results = found.results; active = results.length ? 0 : -1;
    options = results.map((track, index) => {
      const item = make('li', '', 'track-result');
      item.id = `prep-${config.id}-option-${index}`;
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

  input.addEventListener('input', () => open());
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
  close();
  renderChips();

  return {
    setLibrary: (library) => { tracks = library; renderChips(); if (!list.hidden) open(); },
    setSelected: (ids) => { writeIds(config.multiple ? ids : ids.slice(0, 1)); renderChips(); },
    sync: () => renderChips(),
  };
}
