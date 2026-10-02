import type { SeratoExportSource } from './serato-export.js';
export type MetadataField = 'bpm' | 'camelot_key' | 'energy_level';
export interface MetadataTrack {
  readonly id: string;
  readonly title: string;
  readonly artist: string;
  readonly releaseYear: number | null;
  readonly missingFields: readonly MetadataField[];
  readonly explanation: string;
  readonly locked: boolean;
  readonly priority: number;
}
export interface MetadataReport {
  readonly totalTracks: number;
  readonly completeCount: number;
  readonly incompleteCount: number;
  readonly gaps: Readonly<Record<MetadataField, number>>;
  readonly yearCoverage: { readonly withReleaseYear: number; readonly withoutReleaseYear: number };
  readonly tracks: readonly MetadataTrack[];
  readonly repairPlan: string;
  readonly readOnly: true;
}

const prefix = 'metadata-worklist-';
const labels: Record<MetadataField, string> = { bpm: 'BPM', camelot_key: 'Tonalidad', energy_level: 'Energía' };
const pageSize = 100;
const selectionHint = 'Selecciona una pista para consultar su explicación.';
function element<K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = '', suffix = ''): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.textContent = text;
  node.className = className;
  if (suffix) node.id = prefix + suffix;
  return node;
}
function button(text: string, suffix = ''): HTMLButtonElement {
  const node = element('button', text, 'button subtle', suffix);
  node.type = 'button';
  return node;
}
function label(text: string, suffix: string): HTMLLabelElement {
  const node = element('label', text, 'sr-only');
  node.setAttribute('for', prefix + suffix);
  return node;
}
const searchText = (text: string): string => text.normalize('NFKC').toLocaleLowerCase('es');

/** Render only the supplied, read-only domain projection; the caller owns loading and playback. */
export function renderMetadataPanel(container: HTMLElement, report: MetadataReport, onPreview?: (id: string) => void, onExport?: (source: SeratoExportSource) => void): void {
  const summary = element('div', '', 'stats-grid');
  for (const [suffix, title, value] of [
    ['total', 'Total de pistas', report.totalTracks], ['complete', 'Completas', report.completeCount],
    ['incomplete', 'Pendientes', report.incompleteCount], ['year', 'Con año', report.yearCoverage.withReleaseYear],
  ] as const) {
    const card = element('div', '', 'stat-card');
    card.append(element('span', title), element('strong', String(value), 'numeric', suffix));
    if (suffix === 'year') card.append(element('small', `Sin año: ${report.yearCoverage.withoutReleaseYear}. El año es informativo.`));
    summary.append(card);
  }
  const notice = element('div', '', 'review-notice');
  notice.append(element('strong', 'Asistente local · solo lectura'), element('p', 'No se infieren valores ni se escriben etiquetas. Corrige los datos con una fuente verificada en tu editor y vuelve a escanear.'));
  notice.append(element('p', Object.entries(labels).map(([field, title]) => `${title}: ${report.gaps[field as MetadataField]}`).join(' · ')));

  const card = element('section', '', 'table-card');
  card.setAttribute('aria-label', 'Pistas con metadatos pendientes');
  const toolbar = element('div', '', 'table-toolbar metadata-toolbar');
  const search = element('input', '', '', 'search');
  search.type = 'search';
  search.placeholder = 'Buscar pista o artista';
  const field = element('select', '', '', 'field');
  for (const [value, title] of [['all', 'Todos los datos faltantes'], ...Object.entries(labels)]) {
    const option = element('option', title);
    option.value = value;
    field.append(option);
  }
  field.value = 'all';
  toolbar.append(label('Buscar pista o artista', 'search'), search, label('Dato faltante', 'field'), field);
  const count = element('p', '', 'muted', 'count');
  count.setAttribute('role', 'status');
  count.setAttribute('aria-live', 'polite');
  toolbar.append(count);
  const exportButton = button('Exportar lista a Serato', 'export-serato');
  const exportHint = element('p', 'Lista de reparación de metadatos, no una certificación DJ. Máximo 500 pistas; se revisa el destino y se confirma antes de escribir.', 'muted', 'export-hint');
  if (onExport) toolbar.append(exportButton, exportHint);

  const scroll = element('div', '', 'table-scroll');
  scroll.tabIndex = 0;
  scroll.setAttribute('role', 'region');
  scroll.setAttribute('aria-label', 'Tabla de pistas pendientes');
  const table = element('table');
  table.append(element('caption', 'Pistas con datos obligatorios pendientes, ordenadas por prioridad', 'sr-only'));
  const head = element('thead');
  const headers = element('tr');
  for (const title of ['Prioridad', 'Pista', 'Año', 'Datos faltantes', 'Bloqueo', ...(onPreview ? ['Escuchar'] : [])]) {
    const header = element('th', title);
    header.scope = 'col';
    headers.append(header);
  }
  head.append(headers);
  const body = element('tbody');
  table.append(head, body);
  scroll.append(table);
  const empty = element('p', '', 'inline-empty');
  const pagination = element('div', '', 'table-toolbar metadata-toolbar');
  const previous = button('Anterior', 'previous');
  const next = button('Siguiente', 'next');
  previous.setAttribute('aria-label', 'Página anterior de pistas pendientes');
  next.setAttribute('aria-label', 'Página siguiente de pistas pendientes');
  const pageLabel = element('span', '', 'muted', 'page');
  pagination.append(previous, pageLabel, next);
  card.append(toolbar, scroll, empty, pagination);

  const details = element('section', '', 'surface prep-form metadata-details');
  details.setAttribute('aria-labelledby', prefix + 'detail-heading');
  const selectedTitle = element('p', '', 'muted', 'selected-title');
  const explanation = element('p', selectionHint, 'metadata-guidance', 'explanation');
  explanation.setAttribute('aria-live', 'polite');
  details.append(element('h3', 'Explicación de la pista', '', 'detail-heading'), selectedTitle, explanation);
  const plan = element('section', '', 'surface prep-form metadata-details');
  plan.setAttribute('aria-labelledby', prefix + 'plan-heading');
  plan.append(element('h3', 'Plan de reparación · solo lectura', '', 'plan-heading'), element('p', report.repairPlan, 'metadata-guidance', 'plan'));

  const tracks = [...report.tracks].sort((a, b) => a.priority - b.priority);
  let filtered = tracks;
  let page = 0;
  let selectionButtons: HTMLButtonElement[] = [];
  function renderPage(): void {
    body.replaceChildren();
    selectionButtons = [];
    selectedTitle.textContent = '';
    explanation.textContent = selectionHint;
    const start = page * pageSize;
    for (const track of filtered.slice(start, start + pageSize)) {
      const row = element('tr');
      row.dataset.metadataTrackId = track.id;
      const name = element('td', '', 'track-name');
      const select = button(track.title);
      select.className = 'text-button';
      select.setAttribute('aria-label', `Ver explicación: ${track.title}`);
      select.setAttribute('aria-controls', explanation.id);
      select.setAttribute('aria-pressed', 'false');
      select.addEventListener('click', () => {
        for (const item of selectionButtons) item.setAttribute('aria-pressed', String(item === select));
        selectedTitle.textContent = `${track.title} · ${track.artist || 'Artista no indicado'}`;
        explanation.textContent = track.explanation;
      });
      selectionButtons.push(select);
      name.append(select, element('span', track.artist || 'Artista no indicado'));
      row.append(element('td', String(track.priority), 'numeric'), name, element('td', track.releaseYear === null ? '—' : String(track.releaseYear), 'numeric'));
      row.append(element('td', track.missingFields.map((field) => labels[field]).join(', ')), element('td', track.locked ? 'Bloqueada' : 'Sin bloqueo'));
      if (onPreview) {
        const previewCell = element('td');
        const preview = button('Escuchar');
        preview.setAttribute('aria-label', `Escuchar: ${track.title}`);
        preview.addEventListener('click', () => onPreview(track.id));
        previewCell.append(preview);
        row.append(previewCell);
      }
      body.append(row);
    }
    const total = filtered.length;
    exportButton.disabled = total === 0 || total > 500;
    count.textContent = total ? `${start + 1}–${Math.min(start + pageSize, total)} de ${total} pistas` : '0 pistas';
    pageLabel.textContent = `Página ${page + 1} de ${Math.max(1, Math.ceil(total / pageSize))}`;
    previous.disabled = page === 0;
    next.disabled = start + pageSize >= total;
    scroll.hidden = total === 0;
    empty.hidden = total > 0;
    empty.textContent = !report.totalTracks ? 'No hay pistas en la biblioteca.' : !tracks.length ? 'No hay datos obligatorios pendientes. El año de publicación es informativo.' : 'Ninguna pista coincide con los filtros.';
  }
  function filter(): void {
    const query = searchText(search.value.trim());
    filtered = tracks.filter((track) => (field.value === 'all' || track.missingFields.includes(field.value as MetadataField)) && searchText(`${track.title} ${track.artist}`).includes(query));
    page = 0;
    renderPage();
  }
  exportButton.addEventListener('click', () => {
    if (!onExport || exportButton.disabled) return;
    onExport({kind: 'metadata', status: 'incomplete', missingField: field.value === 'all' ? null : field.value as MetadataField, trackIds: filtered.map(track => track.id)});
  });
  search.addEventListener('input', filter);
  field.addEventListener('change', filter);
  previous.addEventListener('click', () => { if (page > 0) { page--; renderPage(); } });
  next.addEventListener('click', () => { if ((page + 1) * pageSize < filtered.length) { page++; renderPage(); } });
  renderPage();
  container.replaceChildren(summary, notice, card, details, plan);
}
