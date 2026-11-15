import {
  EMPTY_GENRE_LABEL, GENRE_BUSY, GENRE_LOAD_FAILED, GENRE_UNAVAILABLE_META, clearedGenreMessage,
  filterGenres, genreFocusCountLabel, genreGroupHeading, genreOptionLabel, genreResultMessage,
  sameGenre, selectedGenreMessage, unavailableGenreLabel, validateGenreCatalog,
} from './genre-picker.js';
import type { GenreCatalog, GenreOption, GenreRequest } from './genre-picker.js';
import { nextActiveIndex } from './track-search.js';

export interface GenrePickerHost {
  canAct(): boolean;
  catalog(input: GenreRequest): Promise<GenreCatalog>;
}
export interface GenrePickerView { sync(): void; }

const element = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
};

/**
 * Accessible combobox for the preferred genre. It only writes the chosen genre into the
 * hidden #prep-genre input, so PrepFields, buildPrepInput and genreFocus stay unchanged; the
 * groups, their order and the availability of a restored genre all come from the read-only
 * core method, never from a ranking recomputed here.
 */
export function createGenrePickerView(host: GenrePickerHost): GenrePickerView {
  const input = element<HTMLInputElement>('prep-genre-search');
  const list = element<HTMLUListElement>('prep-genre-results');
  const status = element<HTMLElement>('prep-genre-status');
  const selection = element<HTMLElement>('prep-genre-selection');
  const chosenLabel = element<HTMLElement>('prep-genre-selected-label');
  const chosenMeta = element<HTMLElement>('prep-genre-selected-meta');
  const clear = element<HTMLButtonElement>('prep-genre-clear');
  const hidden = element<HTMLInputElement>('prep-genre');
  const seed = element<HTMLInputElement>('prep-start');
  let catalog: GenreCatalog | null = null;
  let loadedSeed: string | null = null;
  let loadedGenre: string | null = null;
  let loading = false;
  let open = false;
  let active = -1;
  const options: HTMLElement[] = [];
  const values: string[] = [];

  const announce = (text: string): void => { status.textContent = text; };
  const seedId = (): string => seed.value.trim();
  const storedGenre = (): string => hidden.value.trim();
  const stale = (): boolean => catalog === null || loadedSeed !== seedId() || loadedGenre !== storedGenre();
  const findOption = (value: string): GenreOption | undefined => {
    for (const group of catalog?.groups ?? []) for (const option of group.genres) if (sameGenre(option.name, value)) return option;
    return undefined;
  };
  const close = (): void => {
    open = false; active = -1; options.length = 0; values.length = 0;
    list.replaceChildren(); list.hidden = true;
    input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant');
  };
  const highlight = (): void => {
    options.forEach((option, index) => option.setAttribute('aria-selected', index === active ? 'true' : 'false'));
    if (active >= 0 && options[active]) input.setAttribute('aria-activedescendant', options[active].id);
    else input.removeAttribute('aria-activedescendant');
  };
  const renderSelection = (announcement?: string): void => {
    const value = storedGenre();
    clear.hidden = !value;
    if (!value) {
      selection.setAttribute('data-state', 'empty');
      chosenLabel.textContent = EMPTY_GENRE_LABEL; chosenMeta.textContent = '';
    } else {
      const option = findOption(value);
      const unavailable = option === undefined && catalog !== null && loadedGenre === value && !catalog.genreAvailable;
      selection.setAttribute('data-state', option ? 'chosen' : unavailable ? 'unavailable' : 'chosen');
      chosenLabel.textContent = option ? option.name : unavailable ? unavailableGenreLabel(value) : value;
      chosenMeta.textContent = option ? genreFocusCountLabel(option.count) : unavailable ? GENRE_UNAVAILABLE_META : '';
    }
    if (announcement) announce(announcement);
  };
  const renderOptions = (query: string): void => {
    const groups = filterGenres(catalog?.groups ?? [], query);
    const rows: HTMLElement[] = [];
    options.length = 0; values.length = 0;
    let index = 0;
    for (const group of groups) {
      if (catalog && catalog.seedTitle !== null) {
        const heading = make('li', genreGroupHeading(group, catalog.seedTitle), 'genre-group-heading');
        heading.setAttribute('role', 'presentation');
        rows.push(heading);
      }
      for (const option of group.genres) {
        const item = make('li', '', 'track-result');
        item.id = `prep-genre-option-${index++}`;
        item.setAttribute('role', 'option');
        item.append(make('span', genreOptionLabel(option), 'track-result-title'));
        item.addEventListener('click', () => choose(option.name));
        options.push(item); values.push(option.name); rows.push(item);
      }
    }
    list.replaceChildren(...rows);
    list.hidden = rows.length === 0;
    input.setAttribute('aria-expanded', rows.length ? 'true' : 'false');
    open = rows.length > 0;
    active = options.length ? 0 : -1;
    highlight();
    announce(genreResultMessage(query, options.length));
  };
  const notify = (): void => {
    // The Prep form owns its own draft state: the same input/change pair a typed value used
    // to send keeps `prepSettings.edited()`, the summaries and the AI context in step.
    hidden.dispatchEvent(new Event('input'));
    hidden.dispatchEvent(new Event('change'));
  };
  const choose = (name: string): void => {
    hidden.value = name; input.value = '';
    close();
    renderSelection(selectedGenreMessage(name));
    notify();
  };
  const load = async (): Promise<void> => {
    if (loading || !host.canAct()) return;
    const currentSeed = seedId(); const currentGenre = storedGenre();
    const request: GenreRequest = {};
    if (currentSeed) request.startTrackId = currentSeed;
    if (currentGenre) request.genre = currentGenre;
    loading = true;
    try {
      catalog = validateGenreCatalog(await host.catalog(request));
      loadedSeed = currentSeed; loadedGenre = currentGenre;
      renderSelection();
    } catch {
      catalog = null; loadedSeed = currentSeed; loadedGenre = currentGenre;
      renderSelection(); close(); announce(GENRE_LOAD_FAILED);
    } finally { loading = false; }
    if (open && catalog) renderOptions(input.value);
  };
  const show = (): void => {
    if (!host.canAct()) { close(); announce(GENRE_BUSY); return; }
    open = true;
    if (stale()) { void load(); return; }
    renderOptions(input.value);
  };

  input.addEventListener('click', show);
  input.addEventListener('focus', show);
  input.addEventListener('input', show);
  input.addEventListener('keydown', (event) => {
    const key = (event as KeyboardEvent).key;
    if (key === 'ArrowDown' || key === 'ArrowUp') {
      event.preventDefault();
      if (!open || options.length === 0) { show(); return; }
      active = nextActiveIndex(active, key === 'ArrowDown' ? 1 : -1, options.length);
      highlight();
      return;
    }
    if (key === 'Enter') {
      const choice = values[active];
      if (choice === undefined) return;
      event.preventDefault(); choose(choice); return;
    }
    if (key === 'Escape' && open) { event.preventDefault(); close(); }
  });
  // A pointer press inside the list must not blur the input before the click selects.
  list.addEventListener('mousedown', (event) => event.preventDefault());
  input.addEventListener('blur', () => close());
  clear.addEventListener('click', () => {
    hidden.value = ''; input.value = '';
    close();
    renderSelection(clearedGenreMessage());
    notify();
    input.focus();
  });
  close();
  renderSelection();

  return {
    sync: () => {
      renderSelection();
      if (host.canAct() && stale()) void load();
    },
  };
}
