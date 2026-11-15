import { AI_RECIPIENT, aiErrorMessage } from './optional-ai.js';
import type { AiChatHistory, AiChatMessage, AiContext, AiPayload, AiPreview, AiResult, AiSurface, OptionalAiHost } from './optional-ai.js';
export type { AiChatHistory, AiChatMessage } from './optional-ai.js';
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
export const LIST_CHAT_PENDING = 'El asistente está leyendo la lista…';
export const LIST_CHAT_READ_AGAIN = 'El asistente volvió a leer la lista.';
export const LIST_CHAT_CANCELLED = 'Envío cancelado: la pregunta sigue en el campo para reintentarla.';
export const LIST_CHAT_TOO_LONG = 'La petición admite como máximo 2000 caracteres.';
export interface ListChatApi {
  aiChatHistory(): Promise<AiChatHistory>;
  aiChatReset(): Promise<AiChatHistory>;
  prepareAiRequest(input: { surface: AiSurface; request: string; context: AiContext }): Promise<AiPreview>;
  runAiRequest(input: { previewId: string }): Promise<{ cancelled: boolean; result: AiResult | null }>;
  inspectAiPayload(input: { previewId: string }): Promise<AiPayload>;
}
export type ListChatHost = Pick<OptionalAiHost, 'canAct' | 'changed' | 'perform'>;
const uuid = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value);
const isRecord = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === 'object' && !Array.isArray(value));
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length > 0 && value.length <= max;
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
/**
 * One conversation with the assistant about the generated review (S7). It only reads: every
 * turn prepares the `chat` selector for the current review, sends the typed question and stores
 * the conversation the core returns. The native dialog and its first-turn consent belong to the
 * host, so this controller never ticks a per-send consent, and a failed or cancelled turn keeps
 * the question in the box.
 */
export class ListChatController {
  private api: ListChatApi; private host: ListChatHost; private review = ''; private generation = 0;
  messages: AiChatMessage[] = []; request = ''; error = ''; notice = ''; loaded = false;
  preview: AiPreview | null = null; payload: AiPayload | null = null;
  /** Index of the reply the assistant announced it had re-read the list for; null when none. */
  readAgain: number | null = null;
  pending: 'load' | 'send' | 'reset' | 'inspect' | null = null;
  constructor(api: ListChatApi, host: ListChatHost) { this.api = api; this.host = host; }
  get reviewId(): string { return this.review; }
  get pendingText(): string {
    switch (this.pending) {
      case 'send': return LIST_CHAT_PENDING;
      case 'load': return 'Cargando la conversación…';
      case 'reset': return 'Empezando una conversación nueva…';
      case 'inspect': return 'Recuperando el envío exacto…';
      default: return '';
    }
  }
  get canSend(): boolean {
    return !this.pending && this.host.canAct() && this.review !== '' && this.request.trim().length > 0 && this.request.length <= CHAT_REQUEST_LIMIT;
  }
  get canReset(): boolean { return !this.pending && this.host.canAct() && this.review !== ''; }
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
    this.error = ''; this.notice = ''; this.loaded = false;
    this.host.changed();
  }
  setRequest(value: string): void {
    if (this.pending || typeof value !== 'string' || value === this.request) return;
    this.request = value;
    this.error = value.length > CHAT_REQUEST_LIMIT ? LIST_CHAT_TOO_LONG : '';
    this.notice = '';
    this.host.changed();
  }
  private fail(error: unknown): void { this.error = aiErrorMessage(error); this.host.changed(); }
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
      this.messages = conversationCopy(value?.conversation); this.loaded = true;
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
    this.messages = messages; this.request = ''; this.notice = '';
    const last = messages.at(-1);
    this.readAgain = result.listChanged && last?.role === 'assistant' ? messages.length - 1 : null;
  }
  /** Starts a new conversation: the core forgets the stored one and the panel empties. */
  async newConversation(): Promise<void> {
    if (!this.canReset) return;
    await this.perform('reset', 'Empezando una conversación nueva…', () => this.api.aiChatReset(), (value) => {
      this.messages = conversationCopy(value?.conversation); this.loaded = true;
      this.request = ''; this.readAgain = null; this.preview = null; this.payload = null; this.error = ''; this.notice = '';
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
