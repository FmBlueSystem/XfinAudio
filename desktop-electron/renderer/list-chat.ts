import { AI_RECIPIENT, aiErrorMessage } from './optional-ai.js';
import { errorCode } from './errors.js';
import { SHORT_LIST_NO_CANDIDATES, alternativeCardText, extendedLine } from './short-list-notice.js';
import type { ExtendedList } from './short-list-notice.js';
import type { PrepVariant } from './model.js';
import type { AiChatAction, AiChatHistory, AiChatMessage, AiChatPeriod, AiChatPeriodKept, AiChatReplacement, AiContext, AiPayload, AiPreview, AiResult, AiSurface, OptionalAiHost } from './optional-ai.js';
import type { DetailedReview } from './generated-review.js';
export type { AiChatAction, AiChatHistory, AiChatMessage } from './optional-ai.js';
/** The conversation surface: one chat per generated review, read-only for the list. */
export const CHAT_SURFACE: AiSurface = 'chat';
/** S2's request window for one turn. */
export const CHAT_REQUEST_LIMIT = 2000;
/** S5's reply window; a stored conversation is bounded by the same per-message length. */
export const CHAT_REPLY_LIMIT = 4000;
/** S4 keeps at most 40 messages; the renderer never accepts a longer stored list than it shows. */
export const CHAT_MESSAGE_LIMIT = 200;
const CHAT_PAYLOAD_BODY_LIMIT = 64 * 1024;
const CHAT_PAYLOAD_BYTES_LIMIT = 1024 * 1024;
/** S14 accepts at most twenty proposals per reply, so the panel never renders more. */
const CHAT_ACTION_LIMIT = 20;
/** Rejected items are counted, not listed: the reply's own length bounds how many there can be. */
const CHAT_DROPPED_LIMIT = 200;
/** A position is 1..N of the list itself; the panel only bounds the payload, the core owns N. */
const CHAT_POSITION_LIMIT = 10000;
export const LIST_CHAT_PENDING = 'El asistente está leyendo la lista…';
export const LIST_CHAT_READ_AGAIN = 'El asistente volvió a leer la lista.';
export const LIST_CHAT_CANCELLED = 'Envío cancelado: la pregunta sigue en el campo para reintentarla.';
export const LIST_CHAT_TOO_LONG = 'La petición admite como máximo 2000 caracteres.';
export const LIST_CHAT_PROPOSED = 'Cambios propuestos';
export const LIST_CHAT_APPLYING = 'Aplicando el cambio propuesto…';
export const LIST_CHAT_APPLIED = 'Cambio aplicado. Puedes deshacerlo con Deshacer.';
/** S9: the switch that applies a whole reply at once, and the batch undo it offers afterwards. */
export const LIST_CHAT_AUTO = 'Aplicar los cambios automáticamente';
export const LIST_CHAT_UNDO_BATCH = 'Deshacer estos cambios';
export const LIST_CHAT_UNDOING = 'Deshaciendo estos cambios…';
/** Said when the host cannot undo at all; the same line the review panel uses. */
export const LIST_CHAT_UNDO_UNAVAILABLE = 'Actualiza la aplicación para deshacer cambios.';
/** S9: the whole reply went through. The partial form is S2's `listChatAppliedAll`. */
export const listChatAutoApplied = (applied: number): string => `Se aplicaron ${applied} cambios.`;
/** The line that explains the proposals the core refused to turn into an action. */
export const listChatDropped = (count: number): string => `Se descartaron ${count} cambios que no se pueden aplicar.`;
/** S2: the batch result, whether every shown change was applied or the batch stopped early. */
export const listChatAppliedAll = (applied: number, total: number): string => `Se aplicaron ${applied} de ${total} cambios.`;
/** Said after a proposed alternative replaced the review: the core reset the conversation with it. */
export const LIST_CHAT_VARIANT_CHANGED = 'Se cambió la alternativa. La conversación empieza de nuevo.';
export const LIST_CHAT_VARIANT_UNAVAILABLE = 'Actualiza la aplicación para cambiar de alternativa desde el asistente.';
/** S15: the line that heads the tracks a period run could not replace, with how many there are. */
export const listChatPeriodKept = (count: number): string => `Quedan ${count} fuera de época:`;
/** S15: what a period run replaced, said once after it is applied. */
export const listChatPeriodNotice = (replaced: number): string => `Se reemplazaron ${replaced} pistas.`;
/**
 * S15: one kept track, with its position, title and release year («sin año» when unknown) and
 * why it stayed: it is protected, or no track of that period mixes with its neighbours.
 */
export function listChatPeriodLine(kept: AiChatPeriodKept): string {
  const year = kept.year === null ? 'sin año' : String(kept.year);
  const why = kept.reason === 'protected' ? 'protegida' : 'no hay otra de esa época que mezcle';
  return `${kept.position}. ${kept.title} (${year}) — ${why}`;
}
/** S15: what the last period change did, as the window shows it after applying it. */
export interface ListChatPeriodReport { notice: string; kept: string[] }
/** The one line each card shows for its action, in the panel's Spanish. */
export function listChatActionText(action: AiChatAction): string {
  switch (action.type) {
    case 'replace': return `Reemplazar ${action.position}. ${action.title} por ${action.replacement.title}`;
    case 'move': return `Mover ${action.position}. ${action.title} a la posición ${action.to}`;
    case 'extend': return `Ampliar la lista a ${action.to} pistas`;
    case 'remove': return `Quitar ${action.position}. ${action.title}`;
    case 'add': return `Agregar ${action.track.title} en la posición ${action.position}`;
    case 'replace_with': return `Reemplazar ${action.position}. ${action.title} por ${action.track.title}`;
    case 'reorder': return `Reordenar la lista (${action.moved} pistas cambian de lugar)`;
    case 'undo': return 'Deshacer el último cambio';
    case 'period': return `Ajustar la lista a ${action.yearMin}–${action.yearMax} (${action.outside} pistas fuera de época)`;
    default: return alternativeCardText(action.variant, action.trackCount);
  }
}
export interface ListChatApi {
  aiChatHistory(): Promise<AiChatHistory>;
  aiChatReset(): Promise<AiChatHistory>;
  prepareAiRequest(input: { surface: AiSurface; request: string; context: AiContext }): Promise<AiPreview>;
  runAiRequest(input: { previewId: string }): Promise<{ cancelled: boolean; result: AiResult | null }>;
  inspectAiPayload(input: { previewId: string }): Promise<AiPayload>;
  aiChatApply(input: { actionId: string }): Promise<{ review: DetailedReview; actions: AiChatAction[]; extended?: ExtendedList; period?: AiChatPeriod }>;
  /** Optional until the host ships it: S9's batch undo is only offered when the core can undo. */
  reviewUndo?(input: { reviewId: string }): Promise<DetailedReview>;
}
/** The panel hands the review the edit minted back to the screen, exactly like a manual edit does. */
export type ListChatHost = Pick<OptionalAiHost, 'canAct' | 'changed' | 'perform'> & {
  applied?(value: DetailedReview): void;
  /** Choosing an alternative belongs to the screen: it replaces the review, the plan and this conversation. */
  chooseVariant?(variant: PrepVariant): Promise<boolean>;
};
const uuid = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value);
const isRecord = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === 'object' && !Array.isArray(value));
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length > 0 && value.length <= max;
/** A release year inside S13's own window, 1900 to 2100; the core refuses everything else. */
const yearInRange = (value: unknown): value is number => Number.isInteger(value) && (value as number) >= 1900 && (value as number) <= 2100;
function invalid(): never { throw Object.assign(new Error('Invalid AI response'), { code: 'invalid_ai_response' }); }
/** Exact `{role, text}` pairs only: the panel renders them, so nothing else may ride along. */
function roleOf(value: unknown): AiChatMessage['role'] {
  if (value === 'user') return 'user';
  if (value === 'assistant') return 'assistant';
  return invalid();
}
function conversationCopy(value: unknown): AiChatMessage[] {
  if (!Array.isArray(value) || value.length > CHAT_MESSAGE_LIMIT) invalid();
  return value.map((item): AiChatMessage => {
    if (!isRecord(item) || Object.keys(item).sort().join(',') !== 'role,text') invalid();
    const role = roleOf(item.role);
    if (!text(item.text, CHAT_REPLY_LIMIT)) invalid();
    return { role, text: item.text };
  });
}
function previewCopy(value: unknown): AiPreview {
  if (!isRecord(value) || !uuid(value.previewId) || value.surface !== CHAT_SURFACE || value.recipient !== AI_RECIPIENT) invalid();
  if (!Array.isArray(value.disclosure) || !value.disclosure.length || value.disclosure.length > 20 || !value.disclosure.every((line) => text(line, 1000))) invalid();
  if (!text(value.requestPreview, 8000)) invalid();
  if (Object.hasOwn(value, 'firstTurn') && typeof value.firstTurn !== 'boolean') invalid();
  return { previewId: value.previewId, surface: CHAT_SURFACE, recipient: AI_RECIPIENT, disclosure: [...value.disclosure], requestPreview: value.requestPreview, ...(typeof value.firstTurn === 'boolean' ? { firstTurn: value.firstTurn } : {}) };
}
/** The candidate of a replace: public track metadata only, never a path or a track id. */
function replacementCopy(value: unknown): AiChatReplacement {
  if (!isRecord(value) || Object.keys(value).sort().join(',') !== 'artist,bpm,key,title') invalid();
  if (!text(value.title, 300) || !text(value.artist, 300)) invalid();
  if (value.bpm !== null && (typeof value.bpm !== 'number' || !Number.isFinite(value.bpm) || value.bpm <= 0 || value.bpm > 400)) invalid();
  if (value.key !== null && !text(value.key, 40)) invalid();
  return { title: value.title, artist: value.artist, bpm: value.bpm as number | null, key: value.key as string | null };
}
/**
 * One proposal, exactly one of S1's four shapes. The key set is checked whole so nothing the
 * panel never renders — a path, a track id — can ride along, and a position stays inside 1..N
 * and its bounds; the core already refused every other item before this answer existed.
 * `extend` and `use_variant` carry no position or track: they speak about the whole list.
 */
function actionCopy(value: unknown): AiChatAction {
  if (!isRecord(value) || !uuid(value.actionId) || !text(value.reason, 200)) invalid();
  const actionId = value.actionId; const reason = value.reason; const keys = Object.keys(value).sort().join(',');
  if (value.type === 'replace' || value.type === 'move') {
    if (!text(value.title, 300) || !text(value.artist, 300)) invalid();
    if (!Number.isInteger(value.position) || (value.position as number) < 1 || (value.position as number) > CHAT_POSITION_LIMIT) invalid();
    const position = value.position as number;
    const base = { actionId, position, title: value.title, artist: value.artist, reason };
    if (value.type === 'replace') {
      if (keys !== 'actionId,artist,position,reason,replacement,title,type') invalid();
      return { ...base, type: 'replace', replacement: replacementCopy(value.replacement) };
    }
    if (keys !== 'actionId,artist,position,reason,title,to,type') invalid();
    if (!Number.isInteger(value.to) || (value.to as number) < 1 || (value.to as number) > CHAT_POSITION_LIMIT || value.to === position) invalid();
    return { ...base, type: 'move', to: value.to as number };
  }
  // S4 accepts at most one of each per reply; the count is bounded like a requested list.
  if (value.type === 'extend') {
    if (keys !== 'actionId,reason,to,type') invalid();
    if (!Number.isInteger(value.to) || (value.to as number) < 2 || (value.to as number) > 100) invalid();
    return { actionId, type: 'extend', to: value.to as number, reason };
  }
  if (value.type === 'use_variant') {
    if (keys !== 'actionId,reason,trackCount,type,variant') invalid();
    if (!['safe', 'balanced', 'adventurous'].includes(value.variant as string)) invalid();
    if (!Number.isInteger(value.trackCount) || (value.trackCount as number) < 1 || (value.trackCount as number) > 100) invalid();
    return { actionId, type: 'use_variant', variant: value.variant as PrepVariant, trackCount: value.trackCount as number, reason };
  }
  // S5's new tools: one position of the list for drop/add/swap, the whole list for reorder,
  // and undo, which speaks about the last review step. `add` may address the position after
  // the last track, so its bound is the panel's position window, not N itself.
  if (value.type === 'remove') {
    if (keys !== 'actionId,artist,position,reason,title,type') invalid();
    if (!text(value.title, 300) || !text(value.artist, 300)) invalid();
    if (!Number.isInteger(value.position) || (value.position as number) < 1 || (value.position as number) > CHAT_POSITION_LIMIT) invalid();
    return { actionId, type: 'remove', position: value.position as number, title: value.title, artist: value.artist, reason };
  }
  if (value.type === 'add') {
    if (keys !== 'actionId,position,reason,track,type') invalid();
    if (!Number.isInteger(value.position) || (value.position as number) < 1 || (value.position as number) > CHAT_POSITION_LIMIT) invalid();
    return { actionId, type: 'add', position: value.position as number, track: replacementCopy(value.track), reason };
  }
  if (value.type === 'replace_with') {
    if (keys !== 'actionId,artist,position,reason,title,track,type') invalid();
    if (!text(value.title, 300) || !text(value.artist, 300)) invalid();
    if (!Number.isInteger(value.position) || (value.position as number) < 1 || (value.position as number) > CHAT_POSITION_LIMIT) invalid();
    return { actionId, type: 'replace_with', position: value.position as number, title: value.title, artist: value.artist, track: replacementCopy(value.track), reason };
  }
  if (value.type === 'reorder') {
    if (keys !== 'actionId,moved,reason,type') invalid();
    // A permutation that leaves every track in place changes nothing, so it is not a reorder.
    if (!Number.isInteger(value.moved) || (value.moved as number) < 1 || (value.moved as number) > 100) invalid();
    return { actionId, type: 'reorder', moved: value.moved as number, reason };
  }
  if (value.type === 'undo') {
    if (keys !== 'actionId,reason,type') invalid();
    return { actionId, type: 'undo', reason };
  }
  // S14's period change speaks about the whole list: a year range and the count of the
  // unprotected tracks the current list has outside it, which the core drops when it is 0.
  if (value.type === 'period') {
    if (keys !== 'actionId,outside,reason,type,yearMax,yearMin') invalid();
    if (!yearInRange(value.yearMin) || !yearInRange(value.yearMax) || value.yearMin > value.yearMax) invalid();
    if (!Number.isInteger(value.outside) || (value.outside as number) < 0 || (value.outside as number) > 100) invalid();
    return { actionId, type: 'period', yearMin: value.yearMin, yearMax: value.yearMax, outside: value.outside as number, reason };
  }
  return invalid();
}
function actionsCopy(value: unknown): AiChatAction[] {
  if (!Array.isArray(value) || value.length > CHAT_ACTION_LIMIT) invalid();
  const actions = value.map(actionCopy);
  if (new Set(actions.map((action) => action.actionId)).size !== actions.length) invalid();
  return actions;
}
/** The `extended` field S1 adds to an answer that grew the list: three exact counts, nothing else. */function extendedCopy(value: unknown): ExtendedList {
  if (!isRecord(value) || Object.keys(value).sort().join(',') !== 'added,outsideGenre,requested') invalid();
  for (const key of ['requested', 'added', 'outsideGenre'] as const) {
    if (!Number.isInteger(value[key]) || (value[key] as number) < 0) invalid();
  }
  return value as unknown as ExtendedList;
}
/** S13's period result: what the run replaced and the tracks it could not, position and metadata only. */
function periodCopy(value: unknown): AiChatPeriod {
  if (!isRecord(value) || Object.keys(value).sort().join(',') !== 'kept,replaced,yearMax,yearMin') invalid();
  if (!yearInRange(value.yearMin) || !yearInRange(value.yearMax) || value.yearMin > value.yearMax) invalid();
  if (!Number.isInteger(value.replaced) || (value.replaced as number) < 0 || (value.replaced as number) > 100) invalid();
  if (!Array.isArray(value.kept) || value.kept.length > 100) invalid();
  const kept = value.kept.map((item): AiChatPeriodKept => {
    if (!isRecord(item) || Object.keys(item).sort().join(',') !== 'position,reason,title,year') invalid();
    if (!Number.isInteger(item.position) || (item.position as number) < 1 || (item.position as number) > CHAT_POSITION_LIMIT) invalid();
    if (!text(item.title, 300)) invalid();
    if (item.year !== null && !yearInRange(item.year)) invalid();
    if (item.reason !== 'protected' && item.reason !== 'no_candidate') invalid();
    return { position: item.position as number, title: item.title, year: item.year as number | null, reason: item.reason };
  });
  return { yearMin: value.yearMin, yearMax: value.yearMax, replaced: value.replaced as number, kept };
}
/** The review an applied action minted: the same payload a manual edit answers, which the screen sets as its own. */
function reviewCopy(value: unknown): DetailedReview {
  if (!isRecord(value) || !uuid(value.reviewId)) invalid();
  if (!Array.isArray(value.tracks) || value.tracks.length > 500) invalid();
  if (typeof value.name !== 'string' || value.name.length > 200 || !['safe', 'balanced', 'adventurous', 'saved'].includes(value.variant as string)) invalid();
  if (!['ready', 'needs_review', 'blocked'].includes(value.readiness as string)) invalid();
  for (const key of ['warnings', 'blockers'] as const) {
    const lines = value[key];
    if (!Array.isArray(lines) || lines.length > 200 || !lines.every((line) => text(line, 400))) invalid();
  }
  for (const track of value.tracks) {
    if (!isRecord(track) || !text(track.id, 200) || !text(track.title, 400) || (track.artist !== '' && !text(track.artist, 400))) invalid();
  }
  return value as unknown as DetailedReview;
}
/**
 * One conversation with the assistant about the generated review (S7). The list is never changed
 * by asking: every turn prepares the `chat` selector for the current review, sends the typed
 * question and stores the conversation and the proposals the core returns. A proposal is applied
 * when the user clicks its «Aplicar» card (S5), or — while S9's switch is on — as the reply
 * arrives; either way the core applies it, the native dialog and its first-turn permission belong
 * to the host, and a failed or cancelled turn keeps the question in the box.
 */
export class ListChatController {
  private api: ListChatApi; private host: ListChatHost; private review = ''; private generation = 0;
  messages: AiChatMessage[] = []; request = ''; error = ''; notice = ''; loaded = false;
  preview: AiPreview | null = null; payload: AiPayload | null = null;
  /** The changes the last reply still proposes; applying one hands the minted review to the screen. */
  actions: AiChatAction[] = [];
  /** How many items of the last reply the core refused to turn into an action. */
  droppedActions = 0;
  /** Index of the reply the assistant announced it had re-read the list for; null when none. */
  readAgain: number | null = null;
  pending: 'load' | 'send' | 'reset' | 'inspect' | 'apply' | 'undo' | null = null;
  /**
   * S9: with this on a reply's changes are applied as they arrive, exactly like «Aplicar todo».
   * It is on by default and lives as long as the app is open, not as long as one conversation.
   */
  autoApply = true;
  /** S9: what the last automatic batch applied and how many steps undo it; null hides the undo. */
  autoBatch: { count: number; notice: string; texts: string[] } | null = null;
  /** S15: what the last period change did, as the window reports it; null hides the report. */
  period: ListChatPeriodReport | null = null;
  /** True while the chat itself applies a batch or undoes one, so its own edits never retire it. */
  private inBatch = false;
  /** True while the chat hands a review it minted to the screen: that is not another edit. */
  private selfEdit = false;
  constructor(api: ListChatApi, host: ListChatHost) { this.api = api; this.host = host; }
  get reviewId(): string { return this.review; }
  get pendingText(): string {
    switch (this.pending) {
      case 'send': return LIST_CHAT_PENDING;
      case 'load': return 'Cargando la conversación…';
      case 'reset': return 'Empezando una conversación nueva…';
      case 'inspect': return 'Recuperando el envío exacto…';
      case 'apply': return LIST_CHAT_APPLYING;
      case 'undo': return LIST_CHAT_UNDOING;
      default: return '';
    }
  }
  get canSend(): boolean {
    return !this.pending && this.host.canAct() && this.review !== '' && this.request.trim().length > 0 && this.request.length <= CHAT_REQUEST_LIMIT;
  }
  get canReset(): boolean { return !this.pending && this.host.canAct() && this.review !== ''; }
  /** Every card shares the panel's state: nothing is applied while anything is running. */
  get applyEnabled(): boolean { return !this.pending && this.host.canAct() && this.review !== ''; }
  /** S2: a batch only exists with two or more proposed changes. */
  get canApplyAll(): boolean { return this.applyEnabled && this.actions.length >= 2; }
  /** S9: the batch undo is offered while its steps are the last thing that changed the list. */
  get canUndoBatch(): boolean { return !this.pending && this.host.canAct() && this.review !== '' && this.autoBatch !== null; }
  get requestEditable(): boolean { return !this.pending && this.host.canAct() && this.review !== ''; }
  /**
   * Publishes the review the conversation belongs to. Another review is another conversation
   * (the core discards it with the generated list), so the transcript is dropped and read again
   * on demand; the question the user is typing survives.
   */
  setReview(value: string | null): void {
    const next = uuid(value) ? value : '';
    if (next === this.review) return;
    this.generation++;
    this.review = next; this.messages = []; this.preview = null; this.payload = null; this.readAgain = null;
    this.actions = []; this.droppedActions = 0; this.autoBatch = null; this.period = null;
    this.error = ''; this.notice = ''; this.loaded = false;
    this.host.changed();
  }
  /** S9: the switch itself, kept as long as the app is open and across conversations. */
  setAutoApply(value: boolean): void {
    if (typeof value !== 'boolean' || value === this.autoApply) return;
    this.autoApply = value;
    this.host.changed();
  }
  /**
   * S9: the list was edited outside this batch — a manual edit or the review's own undo — so the
   * batch no longer reverts only its own steps and its undo goes away.
   */
  reviewReplaced(): void {
    if (this.selfEdit || !this.autoBatch) return;
    this.autoBatch = null;
    this.host.changed();
  }
  setRequest(value: string): void {
    if (this.pending || typeof value !== 'string' || value === this.request) return;
    this.request = value;
    this.error = value.length > CHAT_REQUEST_LIMIT ? LIST_CHAT_TOO_LONG : '';
    this.notice = '';
    this.host.changed();
  }
  private fail(error: unknown): void {
    const code = errorCode(error);
    // A list with nothing left to add is an answer, not a failure: S3 says the same line here.
    if (code === 'no_candidates') { this.error = ''; this.notice = SHORT_LIST_NO_CANDIDATES; this.host.changed(); return; }
    this.error = aiErrorMessage(error);
    // The core no longer holds these proposals (or the list they belong to), so a retry can only
    // fail again: the cards go instead of staying as a promise the app cannot keep.
    if (code === 'stale_ai') { this.actions = []; this.droppedActions = 0; }
    this.host.changed();
  }
  private async perform<T>(kind: NonNullable<ListChatController['pending']>, label: string, task: () => Promise<T>, apply: (value: T) => void): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    const generation = this.generation; this.pending = kind; this.error = ''; this.notice = ''; this.host.changed();
    const failure = (error: unknown): void => { if (generation === this.generation) this.fail(error); };
    try { await this.host.perform(label, task, (value) => { if (generation === this.generation) apply(value); }, failure); }
    catch (error) { failure(error); }
    finally { this.pending = null; this.host.changed(); }
  }
  /** Reads the stored conversation once per review, on the panel's first open. */
  async load(): Promise<void> {
    if (this.pending || !this.host.canAct() || !this.review || this.loaded) return;
    await this.perform('load', 'Cargando la conversación…', () => this.api.aiChatHistory(), (value) => {
      this.messages = conversationCopy(value?.conversation);
      this.actions = actionsCopy(value?.actions); this.droppedActions = 0;
      this.loaded = true;
    });
  }
  /** One turn: prepare the exact `chat` selector, then run the prepared preview. */
  async send(): Promise<void> {
    if (!this.canSend) return;
    const message = this.request.trim(); const reviewId = this.review;
    await this.perform('send', LIST_CHAT_PENDING, async () => {
      const preview = previewCopy(await this.api.prepareAiRequest({ surface: CHAT_SURFACE, request: message, context: { reviewId } }));
      return { preview, answer: await this.api.runAiRequest({ previewId: preview.previewId }) };
    }, (value) => this.accept(value.preview, value.answer));
    await this.autoApplyReply();
  }
  private accept(preview: AiPreview, answer: { cancelled: boolean; result: AiResult | null } | null): void {
    if (!answer || typeof answer.cancelled !== 'boolean') invalid();
    // The disclosure of the turn that was sent stays available beside its answer.
    this.preview = preview;
    if (answer.cancelled) { this.notice = LIST_CHAT_CANCELLED; return; }
    const result = answer.result;
    if (!result || !uuid(result.resultId) || result.surface !== CHAT_SURFACE || result.kind !== 'chat') invalid();
    if (!text(result.title, 200) || !text(result.text, CHAT_REPLY_LIMIT) || result.proposal !== null || result.canApply !== false || typeof result.listChanged !== 'boolean') invalid();
    const messages = conversationCopy(result.conversation);
    const actions = actionsCopy(result.actions);
    const droppedActions = result.droppedActions;
    if (!Number.isInteger(droppedActions) || (droppedActions as number) < 0 || (droppedActions as number) > CHAT_DROPPED_LIMIT) invalid();
    this.messages = messages; this.actions = actions; this.droppedActions = droppedActions as number;
    this.request = ''; this.notice = ''; this.period = null;
    const last = messages.at(-1);
    this.readAgain = result.listChanged && last?.role === 'assistant' ? messages.length - 1 : null;
  }
  /**
   * Applies one proposal through the core, which does it as a normal edit: the review it mints is
   * handed to the screen, the cards are redrawn from its answer and the panel says it can be undone.
   * The new reviewId is adopted before the hand-off so this conversation is not mistaken for another.
   * An extension reports its own counts instead of the generic line, and a proposed alternative is
   * the screen's choice, never an apply in the core.
   */
  async apply(actionId: string): Promise<void> {
    if (!this.applyEnabled) return;
    const action = this.actions.find((item) => item.actionId === actionId);
    if (!action) return;
    await this.applyAction(action);
  }
  /**
   * S2: applies the shown changes one after another in that order, stops at the first failure
   * and reports how many of them were applied. A proposed alternative is the screen's own
   * choice, never a batch edit, so the batch stops before it instead of guessing.
   */
  async applyAll(): Promise<void> {
    if (!this.canApplyAll) return;
    const batch = [...this.actions];
    let applied = 0;
    for (const action of batch) {
      if (action.type === 'use_variant') break;
      if (!(await this.applyAction(action))) break;
      applied++;
    }
    this.notice = listChatAppliedAll(applied, batch.length);
    this.host.changed();
  }
  /** One proposal through the core; true only when the core answered with the new review. */
  private async applyAction(action: AiChatAction): Promise<boolean> {
    if (this.pending || !this.host.canAct()) return false;
    if (action.type === 'use_variant') { await this.applyVariant(action.variant); return false; }
    const extend = action.type === 'extend';
    const period = action.type === 'period';
    let applied = false;
    await this.perform('apply', LIST_CHAT_APPLYING, () => this.api.aiChatApply({ actionId: action.actionId }), (value) => {
      const review = reviewCopy(value?.review);
      const actions = actionsCopy(value?.actions);
      const extended = extend && value && Object.hasOwn(value, 'extended') ? extendedCopy(value.extended) : null;
      // S15: the period answer carries what it replaced and the tracks it could not, which the
      // window reports beside the cards; it outlives its own batch step so the report still shows.
      const replaced = period && value && Object.hasOwn(value, 'period') ? periodCopy(value.period) : null;
      this.actions = actions; this.droppedActions = 0;
      this.notice = extended ? extendedLine(extended) : replaced ? listChatPeriodNotice(replaced.replaced) : LIST_CHAT_APPLIED; this.error = '';
      if (period) this.period = replaced ? { notice: listChatPeriodNotice(replaced.replaced), kept: replaced.kept.map(listChatPeriodLine) } : null;
      // A single click is another way of editing the list, so it retires an earlier batch undo.
      if (!this.inBatch) this.autoBatch = null;
      this.handOff(review);
      applied = true;
    });
    return applied;
  }
  /**
   * S9: a reply's changes are applied at once, in order, exactly as «Aplicar todo» does: the batch
   * stops at the first failure and everything that was applied is listed with one undo for the
   * whole batch. A proposed alternative is the screen's own choice, so it is never applied here;
   * it stays as a card with «Aplicar».
   */
  private async autoApplyReply(): Promise<void> {
    if (!this.autoApply || !this.applyEnabled) return;
    const batch = this.actions.filter((action) => action.type !== 'use_variant');
    if (batch.length === 0) return;
    let applied = 0; const texts: string[] = [];
    this.inBatch = true;
    try {
      for (const action of batch) {
        if (!(await this.applyAction(action))) break;
        applied++; texts.push(listChatActionText(action));
      }
    } finally { this.inBatch = false; }
    // Nothing went through: the error and the untouched cards already tell the whole story.
    if (applied === 0) return;
    const notice = applied === batch.length ? listChatAutoApplied(applied) : listChatAppliedAll(applied, batch.length);
    this.autoBatch = { count: applied, notice, texts };
    this.notice = notice;
    this.host.changed();
  }
  /**
   * S9: reverts the last automatic batch by undoing its own steps, newest first, one review at a
   * time. The button belongs to that batch, so it goes before the first step and a failed step
   * leaves the list, the error and the rest of the conversation exactly as they were.
   */
  async undoBatch(): Promise<void> {
    const batch = this.autoBatch;
    if (!batch || !this.canUndoBatch) return;
    const undo = this.api.reviewUndo;
    if (!undo) { this.error = LIST_CHAT_UNDO_UNAVAILABLE; this.host.changed(); return; }
    this.autoBatch = null;
    this.inBatch = true;
    try {
      for (let step = 0; step < batch.count; step++) {
        const reviewId = this.review;
        let undone = false;
        await this.perform('undo', LIST_CHAT_UNDOING, () => undo({ reviewId }), (value) => {
          this.handOff(reviewCopy(value));
          this.notice = ''; this.error = '';
          undone = true;
        });
        if (!undone) break;
      }
    } finally { this.inBatch = false; }
    this.host.changed();
  }
  /** Hands a minted review to the screen without letting that hand-off retire this chat's batch. */
  private handOff(review: DetailedReview): void {
    this.review = review.reviewId;
    this.selfEdit = true;
    try { this.host.applied?.(review); } finally { this.selfEdit = false; }
  }
  /**
   * A proposed alternative is chosen by the screen, which owns the plan, the discard question and
   * the new conversation: the core reports it as `stale_ai` because it is no longer its decision.
   * The note is set after that reset so it is not mistaken for the conversation it replaced.
   */
  private async applyVariant(variant: PrepVariant): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    const choose = this.host.chooseVariant;
    if (!choose) { this.error = LIST_CHAT_VARIANT_UNAVAILABLE; this.host.changed(); return; }
    this.pending = 'apply'; this.error = ''; this.notice = ''; this.host.changed();
    let chosen = false;
    try { chosen = await choose(variant); }
    catch (error) { this.error = aiErrorMessage(error); }
    finally { this.pending = null; }
    if (chosen) { this.notice = LIST_CHAT_VARIANT_CHANGED; this.actions = []; this.droppedActions = 0; }
    this.host.changed();
  }
  /** Starts a new conversation: the core forgets the stored one and the panel empties. */
  async newConversation(): Promise<void> {
    if (!this.canReset) return;
    await this.perform('reset', 'Empezando una conversación nueva…', () => this.api.aiChatReset(), (value) => {
      this.messages = conversationCopy(value?.conversation);
      this.actions = actionsCopy(value?.actions); this.droppedActions = 0;
      this.loaded = true;
      this.request = ''; this.readAgain = null; this.preview = null; this.payload = null; this.error = ''; this.notice = '';
      this.period = null;
    });
  }
  /** Read-only inspection of the exact body the last prepared turn would send. */
  async inspectPayload(): Promise<void> {
    if (!this.host.canAct() || this.pending || !this.preview) return;
    const previewId = this.preview.previewId;
    await this.perform('inspect', 'Recuperando el envío exacto…', () => this.api.inspectAiPayload({ previewId }), (value) => {
      if (!value || value.previewId !== previewId || value.surface !== CHAT_SURFACE || value.recipient !== AI_RECIPIENT) invalid();
      if (typeof value.request !== 'string' || value.request.length > 8000 || !text(value.body, CHAT_PAYLOAD_BODY_LIMIT)) invalid();
      if (typeof value.truncated !== 'boolean' || !Number.isInteger(value.bytes) || value.bytes < 0 || value.bytes > CHAT_PAYLOAD_BYTES_LIMIT) invalid();
      this.payload = { previewId: value.previewId, surface: CHAT_SURFACE, recipient: AI_RECIPIENT, request: value.request, body: value.body, bytes: value.bytes, truncated: value.truncated };
    });
  }
}
