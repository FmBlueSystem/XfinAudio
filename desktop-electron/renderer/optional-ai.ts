import { errorCode, userErrorMessage } from './errors.js';
export const AI_RECIPIENT = 'https://api.nan.builders/v1/chat/completions';
export const AI_CONNECTION_REQUEST = 'Reply with OK. XfinAudio connection test.';
export type AiSurface = 'library' | 'prep' | 'review' | 'saved' | 'editor' | 'metadata' | 'live' | 'connection';
export type AiContext = Record<string, string | number | boolean | string[]>;
export interface AiStatus { revision: string; enabled: boolean; provider: 'nan'; credentialLabel: string | null; configured: boolean; recipient: typeof AI_RECIPIENT; }
export interface AiPreview { previewId: string; surface: AiSurface; recipient: typeof AI_RECIPIENT; disclosure: string[]; requestPreview: string; }
export interface AiResult { resultId: string; surface: AiSurface; kind: 'filters' | 'intent' | 'editor_request' | 'improvement' | 'saved_selection' | 'commentary' | 'connection'; title: string; text: string; proposal: Record<string, unknown> | null; canApply: boolean; }
export interface OptionalAiApi {
  getAiStatus(): Promise<AiStatus>;
  saveAiSettings(input: { revision: string; enabled: boolean }): Promise<AiStatus>;
  chooseAiCredential(input: { revision: string }): Promise<AiStatus>;
  clearAiCredential(input: { revision: string }): Promise<AiStatus>;
  prepareAiRequest(input: { surface: AiSurface; request: string; context: AiContext }): Promise<AiPreview>;
  runAiRequest(input: { previewId: string }): Promise<{ cancelled: boolean; result: AiResult | null }>;
  applyAiSuggestion(input: { resultId: string }): Promise<{ surface: AiSurface; data: Record<string, unknown> }>;
}
export interface OptionalAiHost {
  canAct(): boolean; changed(): void; dirtyChanged(dirty: boolean): void; applied(surface: AiSurface, data: Record<string, unknown>): void;
  /** Only ask is cancellable; call cancelPending before the global cancel API, invalidate on disconnect. */
  perform<T>(label: string, task: () => Promise<T>, apply: (value: T, currentRoute: boolean) => void, failure: (error: unknown) => void): Promise<void>;
}
const kinds: Record<AiSurface, AiResult['kind']> = { library: 'filters', prep: 'intent', editor: 'editor_request', saved: 'saved_selection', review: 'commentary', metadata: 'commentary', live: 'commentary', connection: 'connection' };
const editable = new Set<AiSurface>(['library', 'prep', 'editor', 'saved']);
const JSON_LIMIT = 32000;
// The improvement preview is a local before/after render, not provider text: it carries
// up to 80 tracks per side plus the local assessment, so it is bounded well above the
// legacy 32k provider-proposal bound. Fine-grained track/public-field validation stays
// in editor.setImprovementPreview.
const IMPROVEMENT_JSON_LIMIT = 512 * 1024;
const MIN_IMPROVEMENT_TRACKS = 2;
const MAX_IMPROVEMENT_TRACKS = 80;
const HEX_ID = /^[a-f0-9]{64}$/;
const uuid = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value);
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max;
function bad(): never { throw Object.assign(new Error('Invalid AI response'), { code: 'invalid_ai_response' }); }
const isRecord = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === 'object' && !Array.isArray(value));
function recordCopy(value: unknown, limit = JSON_LIMIT): Record<string, unknown> {
  if (!isRecord(value)) bad();
  const json = JSON.stringify(value); if (!json || json.length > limit) bad();
  const copy = JSON.parse(json) as Record<string, unknown>;
  const check = (item: unknown, depth: number): void => {
    if (depth > 6) bad();
    if (typeof item === 'number' && !Number.isFinite(item)) bad();
    if (typeof item === 'string' && item.length > 8000) bad();
    if (Array.isArray(item)) { if (item.length > 500) bad(); item.forEach((child) => check(child, depth + 1)); }
    else if (isRecord(item)) { if (Object.keys(item).length > 50) bad(); for (const [key, child] of Object.entries(item)) { if (['__proto__', 'constructor', 'prototype'].includes(key)) bad(); check(child, depth + 1); } }
  };
  check(value, 0); return copy;
}
function localApplyCopy(surface: AiSurface, value: unknown, improvement = false): Record<string, unknown> {
  if (surface !== 'library') return recordCopy(value, improvement ? IMPROVEMENT_JSON_LIMIT : JSON_LIMIT);
  if (!isRecord(value)) bad();
  // Only the trusted local filter result gets a larger ID allowance; provider proposals retain their original bound.
  if (!Object.hasOwn(value, 'trackIds')) return recordCopy(value);
  const ids = value.trackIds;
  if (Object.keys(value).sort().join(',') !== 'filters,trackIds' || !Array.isArray(ids) || ids.length > 100000
    || ids.some((id) => typeof id !== 'string' || !HEX_ID.test(id)) || new Set(ids).size !== ids.length) bad();
  return { filters: recordCopy(value.filters), trackIds: [...ids] };
}
function statusCopy(value: AiStatus): AiStatus {
  if (!value || !/^[a-f0-9]{64}$/.test(value.revision) || typeof value.enabled !== 'boolean' || value.provider !== 'nan'
    || value.recipient !== AI_RECIPIENT || typeof value.configured !== 'boolean' || (value.credentialLabel !== null && (!text(value.credentialLabel, 200) || /[\\/\p{C}]/u.test(value.credentialLabel)))) bad();
  return { revision: value.revision, enabled: value.enabled, provider: 'nan', recipient: AI_RECIPIENT, configured: value.configured, credentialLabel: value.credentialLabel };
}
function contextCopy(surface: AiSurface, context: AiContext): AiContext {
  if (!Object.hasOwn(kinds, surface) || !isRecord(context)) bad();
  const keys = Object.keys(context).sort().join(',');
  if (['library', 'prep', 'metadata', 'connection'].includes(surface)) { if (keys) bad(); return {}; }
  if (surface === 'review') { if (keys !== 'reviewId' || !uuid(context.reviewId)) bad(); return { reviewId: context.reviewId }; }
  if (surface === 'editor') {
    if (keys === 'editId') { if (!uuid(context.editId)) bad(); return { editId: context.editId }; }
    // Exact improvement selector only: a partial shape is refused rather than guessed.
    if (keys !== 'draftIds,editId,includeReplacements' || !uuid(context.editId) || typeof context.includeReplacements !== 'boolean') bad();
    const draftIds = context.draftIds;
    if (!Array.isArray(draftIds) || draftIds.length < MIN_IMPROVEMENT_TRACKS || draftIds.length > MAX_IMPROVEMENT_TRACKS
      || new Set(draftIds).size !== draftIds.length || !draftIds.every((id) => HEX_ID.test(id))) bad();
    return { editId: context.editId, draftIds: [...draftIds], includeReplacements: context.includeReplacements };
  }
  if (surface === 'live') {
    if (keys !== 'revision,sessionId' || !uuid(context.sessionId) || typeof context.revision !== 'number' || !Number.isInteger(context.revision) || context.revision < 0 || context.revision > 500) bad();
    return { sessionId: context.sessionId, revision: context.revision };
  }
  if (!keys) return {};
  const ids = context.playlistIds;
  if (keys !== 'playlistIds' || !Array.isArray(ids) || !ids.length || ids.length > 200 || new Set(ids).size !== ids.length || !ids.every((id) => text(id, 200) && id.length > 0 && !/[\\/\p{C}]/u.test(id))) bad();
  return { playlistIds: [...ids] };
}
const errors: Record<string, string> = {
  ai_disabled: 'La asistencia IA está desactivada. Revisa y guarda los ajustes antes de continuar.',
  ai_unconfigured: 'Selecciona un archivo de credenciales mediante el diálogo del sistema. Seleccionarlo no comprueba la conexión.',
  stale_credential: 'La fuente de credenciales cambió. Actualiza los ajustes y prepara otra solicitud.',
  ai_credentials_unavailable: 'La fuente de credenciales no está disponible. Revisa su selección sin compartir claves aquí.',
  ai_request_failed: 'No se pudo completar la consulta al proveedor. Los datos ya enviados no se pueden recuperar.',
  stale_ai: 'El contexto o la solicitud cambió. Prepara otra vista previa y revisa de nuevo el consentimiento.',
  invalid_ai_response: 'La respuesta no cumple los límites esperados. No se ha aplicado ninguna propuesta.',
  ai_context_unavailable: 'Este contexto ya no está disponible. Vuelve a abrir la selección o pantalla de origen.',
  ai_context_too_large: 'El contexto supera el límite de esta consulta. Reduce la selección antes de continuar.',
};
export class OptionalAiController {
  private api: OptionalAiApi; private host: OptionalAiHost; private base: AiStatus | null = null; private draft: AiStatus | null = null;
  private context: AiContext | null = null; private identity = ''; private localRevision: string | number = ''; private generation = 0; private conflict = false; private appliedId = '';
  private improvement = false;
  surface: AiSurface = 'library'; request = ''; consent = false; error = ''; notice = '';
  includeReplacements = false;
  preview: AiPreview | null = null; result: AiResult | null = null;
  pending: 'load' | 'save' | 'choose' | 'clear' | 'prepare' | 'ask' | 'apply' | null = null;
  constructor(api: OptionalAiApi, host: OptionalAiHost) { this.api = api; this.host = host; }
  get snapshot(): AiStatus | null { return this.draft; }
  /** True only for the exact AI improvement selector on the editor surface. */
  get improvementEditor(): boolean { return this.surface === 'editor' && this.improvement; }
  get dirty(): boolean { return Boolean(this.base && this.draft && this.base.enabled !== this.draft.enabled); }
  get requestEditable(): boolean { return editable.has(this.surface); }
  get canSave(): boolean { return !this.pending && !this.conflict && this.dirty; }
  get canPrepare(): boolean { return !this.pending && !this.conflict && !this.dirty && Boolean(this.context && this.draft?.enabled && this.draft.configured) && (!this.requestEditable || Boolean(this.request.trim()) && this.request.length <= 2000); }
  get canAsk(): boolean { return this.canPrepare && this.consent && Boolean(this.preview); }
  get canApply(): boolean { return !this.pending && !this.dirty && !this.conflict && Boolean(this.result?.canApply && this.result.proposal && editable.has(this.result.surface) && this.result.resultId !== this.appliedId); }
  private notify(): void { this.host.dirtyChanged(this.dirty); this.host.changed(); }
  private reset(): void { this.generation++; this.preview = null; this.result = null; this.consent = false; this.appliedId = ''; }
  invalidate(): void { this.reset(); this.context = null; this.identity = ''; this.localRevision = ''; this.improvement = false; this.includeReplacements = false; this.request = ''; this.notice = ''; this.notify(); }
  cancelPending(): void { this.reset(); this.notice = 'Solicitud cancelada. Los datos ya enviados no se pueden recuperar.'; this.notify(); }
  setContext(surface: AiSurface, context: AiContext, localRevision: string | number): void {
    try {
      const copy = contextCopy(surface, context); const identity = JSON.stringify([surface, copy, localRevision]);
      if (identity === this.identity) return;
      this.reset(); this.surface = surface; this.context = copy; this.identity = identity; this.localRevision = localRevision;
      this.improvement = surface === 'editor' && Object.hasOwn(copy, 'draftIds');
      this.includeReplacements = copy.includeReplacements === true;
      this.request = surface === 'connection' ? AI_CONNECTION_REQUEST : ''; this.error = ''; this.notice = ''; this.notify();
    } catch (error) { this.invalidate(); this.fail(error); }
  }
  /**
   * Explicit user choice for the improvement selector. It invalidates the prepared
   * disclosure and its consent, updates the exact context, and notifies the host so the
   * app can regenerate the context. It never contacts the provider.
   */
  setIncludeReplacements(value: boolean): void {
    if (typeof value !== 'boolean' || this.pending || !this.host.canAct() || !this.improvement || this.includeReplacements === value) return;
    this.includeReplacements = value;
    if (this.context) { this.context = { ...this.context, includeReplacements: value }; this.identity = JSON.stringify([this.surface, this.context, this.localRevision]); }
    this.reset(); this.notice = ''; if (!this.conflict) this.error = ''; this.notify();
  }
  setRequest(value: string): void {
    if (!this.requestEditable || typeof value !== 'string' || value === this.request) return;
    this.reset(); this.request = value; this.error = value.length > 2000 ? 'La petición admite como máximo 2000 caracteres.' : ''; this.notice = ''; this.notify();
  }
  setConsent(value: boolean): void { if (typeof value !== 'boolean' || this.pending || !this.host.canAct() || !this.preview) return; this.consent = value; this.host.changed(); }
  setEnabled(value: boolean): void {
    if (!this.draft || this.pending || !this.host.canAct() || typeof value !== 'boolean' || this.draft.enabled === value) return;
    this.reset(); this.draft = { ...this.draft, enabled: value }; this.notice = ''; if (!this.conflict) this.error = ''; this.notify();
  }
  discard(): void {
    if (!this.base || this.pending || !this.host.canAct()) return;
    this.reset(); this.draft = { ...this.base }; this.error = this.conflict ? 'Borrador descartado. Pulsa Actualizar para cargar los ajustes vigentes.' : ''; this.notify();
  }
  private fail(error: unknown): void {
    const code = errorCode(error);
    if (code === 'stale_settings') { this.conflict = true; this.reset(); this.error = 'Los ajustes cambiaron. Tu borrador se conserva; descarta los cambios y actualiza antes de guardar.'; }
    else { this.error = errors[code ?? ''] ?? userErrorMessage(error); if (['stale_ai', 'stale_credential', 'ai_disabled', 'ai_unconfigured'].includes(code ?? '')) this.reset(); }
    this.notify();
  }
  private async perform<T>(kind: NonNullable<OptionalAiController['pending']>, label: string, task: () => Promise<T>, apply: (value: T) => void): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    const generation = this.generation; this.pending = kind; this.error = ''; this.host.changed();
    const failure = (error: unknown): void => { if (generation === this.generation) this.fail(error); };
    try { await this.host.perform(label, task, (value) => { if (generation === this.generation) apply(value); }, failure); }
    catch (error) { failure(error); } finally { this.pending = null; this.notify(); }
  }
  private accept(value: AiStatus): void { const copy = statusCopy(value); this.reset(); this.base = copy; this.draft = { ...copy }; this.conflict = false; this.error = ''; this.notify(); }
  async load(): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    if (this.dirty) { this.error = 'Guarda o descarta los cambios antes de actualizar los ajustes.'; this.notify(); return; }
    await this.perform('load', 'Consultando ajustes de IA…', () => this.api.getAiStatus(), (value) => this.accept(value));
  }
  async save(): Promise<void> {
    if (!this.canSave || !this.draft || !this.host.canAct()) return;
    this.reset(); const { revision, enabled } = this.draft;
    await this.perform('save', 'Guardando ajustes de IA…', () => this.api.saveAiSettings({ revision, enabled }), (value) => this.accept(value));
  }
  private async credential(kind: 'choose' | 'clear'): Promise<void> {
    if (!this.draft || this.pending || !this.host.canAct()) return;
    if (this.dirty || this.conflict) { this.error = 'Guarda o descarta los cambios de IA antes de elegir o quitar la fuente de credenciales.'; this.notify(); return; }
    const revision = this.draft.revision; this.reset(); this.notice = '';
    await this.perform(kind, kind === 'choose' ? 'Elige el archivo de credenciales en el sistema' : 'Quitando fuente de credenciales…', () => kind === 'choose' ? this.api.chooseAiCredential({ revision }) : this.api.clearAiCredential({ revision }), (value) => this.accept(value));
  }
  chooseCredential(): Promise<void> { return this.credential('choose'); }
  clearCredential(): Promise<void> { return this.credential('clear'); }
  private expectedKind(): AiResult['kind'] { return this.improvementEditor ? 'improvement' : kinds[this.surface]; }
  async prepare(): Promise<void> {
    if (!this.canPrepare || !this.context || !this.host.canAct()) return;
    this.reset(); this.notice = ''; const surface = this.surface; const context = contextCopy(surface, this.context); const request = this.requestEditable ? this.request.trim() : surface === 'connection' ? AI_CONNECTION_REQUEST : '';
    await this.perform('prepare', 'Preparando divulgación de datos…', () => this.api.prepareAiRequest({ surface, context, request }), (value) => {
      if (!value || !uuid(value.previewId) || value.surface !== surface || value.recipient !== AI_RECIPIENT || !Array.isArray(value.disclosure) || value.disclosure.length > 20 || !value.disclosure.every((line) => text(line, 1000)) || !text(value.requestPreview, 8000)) bad();
      this.preview = { ...value, disclosure: [...value.disclosure] }; this.consent = false; this.host.changed();
    });
  }
  async ask(): Promise<void> {
    if (!this.canAsk || !this.preview || !this.host.canAct()) return;
    const { previewId, surface } = this.preview; this.consent = false; this.result = null;
    this.notice = 'Confirma el envío en el diálogo del sistema. Cancelar no recupera los datos ya enviados.';
    await this.perform('ask', 'Consultando asistencia IA…', () => this.api.runAiRequest({ previewId }), (value) => {
      if (!value || typeof value.cancelled !== 'boolean') bad();
      this.preview = null;
      if (value.cancelled) { this.notice = 'Solicitud cancelada. Los datos ya enviados no se pueden recuperar.'; this.host.changed(); return; }
      const result = value.result;
      if (!result || !uuid(result.resultId) || result.surface !== surface || result.kind !== this.expectedKind() || !text(result.title, 200) || !text(result.text, 8000) || typeof result.canApply !== 'boolean') bad();
      const proposal = result.proposal === null ? null : recordCopy(result.proposal);
      this.result = { ...result, proposal, canApply: editable.has(surface) && result.canApply }; this.notice = 'Respuesta de IA recibida. Revisa la propuesta; los datos y validadores locales siguen siendo la referencia.'; this.host.changed();
    });
  }
  async applySuggestion(): Promise<void> {
    if (!this.canApply || !this.result || !this.host.canAct()) return;
    const { resultId, surface } = this.result; const improvement = this.improvementEditor;
    await this.perform('apply', 'Revisando propuesta con los validadores locales…', () => this.api.applyAiSuggestion({ resultId }), (value) => {
      if (!value || value.surface !== surface) bad(); const data = localApplyCopy(surface, value.data, improvement); this.appliedId = resultId;
      this.host.applied(surface, data);
      // The improvement preview is local staging for the editor only; the draft is untouched
      // until the user applies it there, so the notice must not claim it was applied.
      this.notice = improvement ? 'Propuesta local lista para revisar en el editor. El borrador no cambió y no se guardó nada.' : 'Propuesta aplicada al trabajo local. Guardar, exportar y reproducir requieren sus propias acciones.';
      this.host.changed();
    });
  }
}
