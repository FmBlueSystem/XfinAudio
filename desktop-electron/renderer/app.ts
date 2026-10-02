import {LegacyImportController} from './legacy-import.js';
import type {LegacyImportApi} from './legacy-import.js';
import {createLegacyImportView} from './legacy-import-view.js';
import {GeneratedReviewController} from './generated-review.js';
import type {GeneratedReviewApi} from './generated-review.js';
import {createGeneratedReviewView} from './generated-review-view.js';
import {PrepSettingsController} from './prep-settings.js';
import type {PrepSettingsApi} from './prep-settings.js';
import {createPrepSettingsView} from './prep-settings-view.js';
import {OfflineBrowseView} from './offline-browse.js';
import type {OfflineBrowseApi} from './offline-browse.js';
import {createProfilesView,profileStatus,profileStageNames} from './profiles.js';
import type {ProfilesApi,ProfileStatus} from './profiles.js';
import {ProfileSettingsController,createProfileSettingsView} from './profile-settings.js';
import type {ProfileSettingsApi} from './profile-settings.js';
import { OptionalAiController } from './optional-ai.js';
import type { OptionalAiApi, AiSurface, AiContext } from './optional-ai.js';
import { createOptionalAiView } from './optional-ai-view.js';
import { PreferencesController } from './preferences.js';
import { LoudnessController } from './loudness.js';
import type { LoudnessApi } from './loudness.js';
import { createLoudnessView } from './loudness-view.js';
import type { PreferencesApi } from './preferences.js';
import { createPreferencesView } from './preferences-view.js';
import { createLibraryStatusView } from './library-status.js';
import type { LibraryStatus } from './library-status.js';
import { LiveController } from './live.js';
import { createLiveView } from './live-view.js';
import { SeratoExportController } from './serato-export.js';
import type { SeratoExportSource } from './serato-export.js';
import { createSeratoExportView } from './serato-export-view.js';
import { errorCode,userErrorMessage } from './errors.js';
import { SavedPlaylistEditor } from './editor.js';
import { createEditorView } from './editor-view.js';
import { buildPrepInput, canSaveReview, filterTracks, formatDuration, hasPrepMetadata, isCoreFailure, normalizePrepName, OperationGate } from './model.js';
import type { LibraryResult, MetadataFilter, PlaylistSummary, PrepFields, PrepStrategy, PrepVariant, PrepVariantSummary, Readiness, ReviewResult, Route as ExistingRoute, Track, XfinApi } from './model.js';
import { renderMetadataPanel } from './metadata.js';
import type { MetadataReport } from './metadata.js';
import { createPlayer } from './player.js';

type Route = ExistingRoute | 'preferences' | 'loudness' | 'ai';
type AppApi = XfinApi & LegacyImportApi & GeneratedReviewApi & PrepSettingsApi & OfflineBrowseApi & ProfilesApi & ProfileSettingsApi & PreferencesApi & LoudnessApi & OptionalAiApi & { getLibraryStatus(): Promise<LibraryStatus>; rescanLibrary(): Promise<LibraryResult>; onLibraryStatus(callback: (status: LibraryStatus) => void): () => void; };
declare global { interface Window { xfin: AppApi; } }
const api = window.xfin;
let coreAvailable = Boolean(api);
let restartRequired=false;
let renderLegacyImport=():void=>{};
let coreFailure = api ? '' : 'Abre XfinAudio desde su aplicación de escritorio';
const element = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;
const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = '') => {
  const node = document.createElement(tag);
  node.textContent = text;
  node.className = className;
  return node;
};
const gate = new OperationGate();
let route: Route = 'library';
let routeRevision = 0;
let library: Track[] = [];
let offlineLibrary:Track[]|null=null;
let libraryWorklist:SeratoExportSource|null=null;
let offline:OfflineBrowseView|undefined;
let libraryStatus: LibraryStatus | null = null;
let libraryGeneration = 0;
let profilesSnapshot:ProfileStatus|null=null;
let profilesStale=false;
let profilesError='';
let profileAutoPending:number|null=null;
let profileBootstrapPending=typeof api?.getProfileStatus==='function';
let profileSettingsAttempted=false;
let profileSettingsDirty=false;
let prepSettingsDirty=false;
let prepSettings:PrepSettingsController|undefined;
let prepSettingsBootstrapPending=typeof api?.prepSettings==='function'&&typeof api?.savePrepSettings==='function';
let renderPrepSettings=():void=>{};
let renderGeneratedReview=():void=>{};
const prepSettingsAvailable=():boolean=>typeof api?.prepSettings==='function'&&typeof api?.savePrepSettings==='function';
let renderProfiles=():void=>{};
let renderProfileSettings=():void=>{};
const profilesAvailable=():boolean=>typeof api?.getProfileStatus==='function'&&typeof api?.completeProfiles==='function';
const profileSettingsAvailable=():boolean=>typeof api?.getProfileSettings==='function'&&typeof api?.saveProfileSettings==='function';
let libraryBootstrapped = false;
let preferencesBootstrapPending = typeof api?.getPreferences === 'function' && typeof api?.savePreferences === 'function';
let statusBootstrapPending = Boolean(api?.getLibraryStatus);
let editorDirty = false;
let preferencesDirty = false;
let loudnessDirty = false;
let aiDirty = false;
let ai: OptionalAiController | undefined;
let renderAi = (): void => {};
let aiContextKey = '';
let deferredAiApply: (() => void) | null = null;
let aiLibraryFilter: Set<string> | null = null;
let aiFilterRevision = 0;
const aiSavedScope = new Set<string>();
let aiSavedSelection: { ids: string[]; names: string[]; comparison: string } | null = null;
let metadataReport: MetadataReport | null = null;
let review: ReviewResult | null = null;
let strategies: PrepStrategy[] = [];
let catalogLoaded = false;
let prepPlan: { id: string; variants: PrepVariantSummary[] } | null = null;
const variantNames: Record<PrepVariant, string> = { safe: 'Segura', balanced: 'Equilibrada', adventurous: 'Aventurera' };
const readinessNames: Record<Readiness, string> = { ready: 'Lista para revisar', needs_review: 'Revisión recomendada', blocked: 'Necesita atención' };
let playlists: PlaylistSummary[] = [];
let playlistsLoaded = false;
let activeKind = '';
let activeJobId = '';
let cancellable = false;
const titles: Record<Route, string> = { library: 'Biblioteca', metadata: 'Metadatos', prep: 'Preparar sesión', review: 'Revisar selección', playlists: 'Playlists guardadas', editor: 'Editar playlist', serato: 'Exportar a Serato', live: 'Asistente Live', preferences: 'Preferencias', loudness: 'Sonoridad', ai: 'IA opcional' };
const player = createPlayer(() => {
  document.querySelectorAll<HTMLButtonElement>('[data-track-id]').forEach((button) => {
    const playing = player.isPlaying(button.dataset.trackId ?? '');
    button.textContent = playing ? 'Ⅱ' : '▶';
    button.setAttribute('aria-label', `${playing ? 'Pausar' : 'Escuchar'} ${button.dataset.trackTitle ?? 'pista'}`);
    button.closest('tr')?.classList.toggle('playing', playing);
  });
});

let renderLive = (): void => {};
let live: LiveController;
let renderSerato = (): void => {};
let serato: SeratoExportController;
let renderEditor = (): void => {};
const editor = new SavedPlaylistEditor(api, {
  canAct: () => coreAvailable && !gate.busy,
  changed: () => { renderEditor(); syncAiContext(); },
  dirtyChanged: (dirty) => {
    serato?.invalidatePreview();
    editorDirty = dirty;
    syncDraftDirty();
  },
  navigate: () => navigate('editor', false),
  perform: (label, task, apply, failure) => perform('editor', label, task, (result, current) => {
    apply(result, current);
    showStatus(label.startsWith('Guardando') ? 'Cambios guardados' : 'Editor actualizado', 'Los cambios solo se conservan al pulsar Guardar cambios');
  }, false, failure),
});
renderEditor = createEditorView(element('editor-container'), editor, {
  canAct: () => coreAvailable && !gate.busy,
  play: (track) => { void player.select(track).catch(() => showStatus('No se puede abrir esta pista', 'Comprueba que el archivo siga disponible', true)); },
});
renderEditor();

serato = new SeratoExportController(api, {
  canAct: () => coreAvailable && !gate.busy && !(editor.dirty && serato.source?.kind === 'saved' && serato.source.playlistId === editor.draft?.id),
  changed: () => renderSerato(),
  perform: (label, task, apply, failure) => perform('serato', label, task, (result, current) => { apply(result, current); showStatus('Serato', serato.status || 'Operación completada'); }, false, failure),
});
renderSerato = createSeratoExportView(element('serato-container'), serato, { canAct: () => coreAvailable && !gate.busy && !(editor.dirty && serato.source?.kind === 'saved' && serato.source.playlistId === editor.draft?.id) });
renderSerato();
live = new LiveController(api, {
  canAct: () => coreAvailable && !gate.busy,
  changed: () => { renderLive(); syncAiContext(); },
  perform: (label, task, apply, failure) => perform('live', label, task, (result, current) => { apply(result, current); showStatus('Guía Live actualizada', 'Las marcas son manuales y no controlan la reproducción de Serato'); }, false, failure),
});
const liveView = createLiveView(element('live-container'), live, {
  canAct: () => coreAvailable && !gate.busy,
  isConnected: () => coreAvailable,
  play: track => { void player.select(track).catch(() => showStatus('No se puede abrir esta pista', 'Comprueba que siga disponible', true)); },
});
renderLive = liveView.render;
renderLive();
window.addEventListener('beforeunload', () => liveView.dispose(), { once: true });
let renderPreferences = (): void => {};
const preferencesAvailable = (): boolean => typeof api?.getPreferences === 'function' && typeof api?.savePreferences === 'function';
const preferences = new PreferencesController(api, {
  canAct: () => coreAvailable && !gate.busy && preferencesAvailable(),
  changed: () => renderPreferences(),
  dirtyChanged: (dirty) => { preferencesDirty = dirty; syncDraftDirty(); },
  applied: (snapshot, reason) => player.applyPreferencesVolume(snapshot.previewVolume, reason),
  perform: (label, task, apply, failure) => perform('preferences', label, task, (result, current) => {
    apply(result, current); showStatus(label.startsWith('Guardando') ? 'Preferencias guardadas' : 'Preferencias actualizadas');
  }, false, failure),
});
renderPreferences = createPreferencesView(element('preferences-container'), preferences, { canAct: () => coreAvailable && !gate.busy && preferencesAvailable() });
const profileSettings=new ProfileSettingsController(api,{
  canAct:()=>coreAvailable&&!gate.busy&&profileSettingsAvailable(),changed:()=>renderProfileSettings(),
  dirtyChanged:dirty=>{profileSettingsDirty=dirty;syncDraftDirty();},
  applied:()=>{libraryGeneration++;invalidateAiSource();editor.invalidatePreview();serato.invalidatePreview();invalidatePrep();},
  perform:(label,task,apply,failure)=>perform('profile-settings',label,task,value=>{apply(value);showStatus('Cohesión espectral actualizada');},false,failure),
});
renderProfileSettings=createProfileSettingsView(element('profile-settings-container'),profileSettings,{canAct:()=>coreAvailable&&!gate.busy&&profileSettingsAvailable()});
let renderLoudness = (): void => {};
const loudnessAvailable = (): boolean => ['getLoudnessStatus', 'saveLoudnessSettings', 'previewLoudness', 'runLoudness'].every((key) => typeof api?.[key as keyof AppApi] === 'function');
const loudness = new LoudnessController(api, {
  canAct: () => coreAvailable && !gate.busy && loudnessAvailable(),
  changed: () => renderLoudness(),
  dirtyChanged: (dirty) => { loudnessDirty = dirty; syncDraftDirty(); },
  applied: (snapshot, reason) => {
    if (reason === 'save') { serato.invalidatePreview(); invalidatePrep(); }
    if (reason === 'run' && loudness.result && (!loudness.result.cancelled || loudness.result.changedCount + loudness.result.unchangedCount + loudness.result.failureCount + loudness.result.backupCount > 0)) {
      libraryGeneration++; metadataReport = null; editor.invalidatePreview(); serato.invalidatePreview(); invalidatePrep();
      if (!loudness.result.warning) applyLibrary({ tracks: snapshot.tracks.map((entry) => entry.track), count: snapshot.totalTracks });
    }
  },
  perform: async (label, task, apply, failure) => {
    const isRun = loudness.pending === 'run';
    if ((isRun || loudness.pending === 'preview') && (editorDirty || preferencesDirty)) {
      const error = { code: 'dirty_draft' }; failure(error); showStatus('Hay cambios sin guardar', userErrorMessage(error), true); return;
    }
    if (isRun) player.stopIfMissing(new Set());
    await perform(isRun ? 'loudness' : 'loudness-settings', label, task, (result, current) => {
      apply(result, current);
      if (isRun && loudness.result) {
        const receipt = loudness.result;
        showStatus(receipt.warning ? 'Sonoridad finalizada con aviso' : receipt.cancelled ? 'Sonoridad cancelada' : 'Sonoridad finalizada', `${receipt.changedCount} escrituras completadas · ${receipt.unchangedCount} sin cambios · ${receipt.failureCount} fallidas · ${receipt.backupCount} copias. Las escrituras ya completadas se conservan con sus copias de seguridad.${receipt.warning ? ` ${receipt.warning}` : ''}`, Boolean(receipt.warning));
      } else showStatus(label.startsWith('Guardando') ? 'Ajustes de sonoridad guardados' : 'Sonoridad actualizada');
    }, isRun, failure);
  },
});
renderLoudness = createLoudnessView(element('loudness-container'), loudness, { canAct: () => coreAvailable && !gate.busy && loudnessAvailable() });
const aiAvailable = (): boolean => ['getAiStatus', 'saveAiSettings', 'chooseAiCredential', 'clearAiCredential', 'prepareAiRequest', 'runAiRequest', 'applyAiSuggestion'].every((key) => typeof api?.[key as keyof AppApi] === 'function');
ai = new OptionalAiController(api, {
  canAct: () => coreAvailable && !gate.busy && aiAvailable(),
  changed: () => renderAi(),
  dirtyChanged: (dirty) => { aiDirty = dirty; syncDraftDirty(); },
  applied: (surface, data) => {
    const change = planAiApply(surface, data); const context = aiContextKey;
    deferredAiApply = () => { if (context === aiContextKey) change(); };
  },
  perform: (label, task, apply, failure) => perform(ai?.pending === 'ask' ? 'ai' : ai?.pending === 'apply' ? 'ai-apply' : 'ai-settings', label, task, (value, current) => {
    apply(value, current); showStatus('Asistencia IA', ai?.notice || 'Operación local completada; cada consulta requiere consentimiento');
  }, ai?.pending === 'ask', failure),
});
renderAi = createOptionalAiView(element('optional-ai-container'), ai, { canAct: () => coreAvailable && !gate.busy && aiAvailable() });
renderAi();
function invalidateAiSource(): void { aiContextKey = ''; deferredAiApply = null; ai?.invalidate(); }
function prepFields(): PrepFields {
  const value = (id: string): string => element<HTMLInputElement | HTMLSelectElement>(`prep-${id}`).value;
  const selected = (id: string): string[] => Array.from(element<HTMLSelectElement>(`prep-${id}`).selectedOptions ?? [], (option) => option.value);
  return { name: value('name'), count: value('count'), strategy: value('strategy'), minutes: value('minutes'), role: value('role'), genre: value('genre'), start: value('start'), end: value('end'), required: selected('required'), excluded: selected('excluded') };
}
function syncAiContext(): void {
  if (!ai) return;
  const panel = element<HTMLDetailsElement>('ai-panel');
  let surface: AiSurface | null = null; let context: AiContext = {}; let revision: unknown = libraryGeneration;
  if (route === 'library') { surface = 'library'; revision = [libraryGeneration, library.length, element<HTMLInputElement>('library-search').value, element<HTMLSelectElement>('metadata-filter').value, aiFilterRevision]; }
  else if (route === 'prep') { surface = 'prep'; revision = [libraryGeneration, prepFields()]; }
  else if (route === 'metadata') surface = 'metadata';
  else if (route === 'review' && review?.reviewId) { surface = 'review'; context = { reviewId: review.reviewId }; revision = [libraryGeneration, review.reviewId]; }
  else if (route === 'editor' && editor.draft) { surface = 'editor'; context = { editId: editor.draft.editId }; revision = [libraryGeneration, editor.draft.editId, editor.draft.revision, editor.draft.name, editor.draft.tracks.map((track) => track.id), editor.request]; }
  else if (route === 'live' && live?.valid && live.snapshot) { surface = 'live'; context = { sessionId: live.snapshot.sessionId, revision: live.snapshot.revision }; revision = [libraryGeneration, live.snapshot.sessionId, live.snapshot.revision]; }
  else if (route === 'playlists' && (aiSavedScope.size > 0 || playlists.length <= 200)) {
    surface = 'saved'; context = aiSavedScope.size ? { playlistIds: [...aiSavedScope] } : {};
    revision = [libraryGeneration, playlists.map((item) => [item.id, item.name, item.trackCount, item.createdAt]), [...aiSavedScope]];
  } else if (route === 'ai') { surface = 'connection'; revision = 'synthetic'; }
  panel.hidden = !aiAvailable() || !surface;
  if (!coreAvailable) return;
  if (!surface) { if (aiContextKey) invalidateAiSource(); return; }
  const identity = JSON.stringify([surface, context, revision]);
  if (identity !== aiContextKey) { aiContextKey = identity; ai.setContext(surface, context, JSON.stringify(revision)); }
  renderAi();
}
function loadAiIfOpen(): boolean {
  if (!ai || !coreAvailable || gate.busy || !aiAvailable() || ai.snapshot || ai.pending || ai.dirty || element('ai-panel').hidden || !element<HTMLDetailsElement>('ai-panel').open) return false;
  void ai.load(); return true;
}
function planAiApply(surface: AiSurface, data: Record<string, unknown>): () => void {
  const invalid = (): never => { throw Object.assign(new Error('Invalid local suggestion'), { code: 'invalid_ai_response' }); };
  if (surface === 'library') {
    const ids = data.trackIds; const known = new Set(library.map((track) => track.id));
    if (!Array.isArray(ids) || ids.length > 100000 || ids.some((id) => typeof id !== 'string' || !known.has(id)) || new Set(ids).size !== ids.length) return invalid();
    return () => { aiLibraryFilter = new Set(ids as string[]); aiFilterRevision++; renderLibrary(); };
  }
  if (surface === 'prep') {
    const fields = prepFields(); const scalar: Record<string, keyof PrepFields> = { name: 'name', targetTrackCount: 'count', strategy: 'strategy', targetMinutes: 'minutes', slotRole: 'role', genreFocus: 'genre', startTrackId: 'start', endTrackId: 'end' };
    for (const [key, value] of Object.entries(data)) {
      if (key === 'requiredTrackIds' || key === 'excludedTrackIds') {
        if (!Array.isArray(value) || value.some((id) => typeof id !== 'string')) return invalid();
        const field = key === 'requiredTrackIds' ? 'required' : 'excluded';
        fields[field] = [...new Set([...fields[field], ...value as string[]])];
      }
      else if (scalar[key]) {
        if (value !== null && typeof value !== 'string' && typeof value !== 'number') return invalid();
        const field = scalar[key];
        // Match the original confirmed_intent: local hard boundaries win over AI suggestions.
        if ((field === 'start' || field === 'end') && fields[field]) continue;
        (fields[field] as string) = value === null ? '' : String(value);
      }
      else return invalid();
    }
    buildPrepInput(fields, library, strategies);
    return () => {
      for (const key of ['name', 'count', 'strategy', 'minutes', 'role', 'genre', 'start', 'end'] as const) element<HTMLInputElement | HTMLSelectElement>(`prep-${key}`).value = fields[key];
      for (const key of ['required', 'excluded'] as const) for (const option of element<HTMLSelectElement>(`prep-${key}`).options) option.selected = fields[key].includes(option.value);
      renderStrategyHint(); syncAiContext();
    };
  }
  if (surface === 'editor') {
    if (!editor.draft || typeof data.request !== 'string' || !data.request.trim() || data.request.length > 500) return invalid();
    const request = data.request; return () => editor.setRequest(request);
  }
  if (surface === 'saved') {
    const ids = data.playlistIds; const names = data.names;
    if (!['find', 'compare'].includes(String(data.action)) || !Array.isArray(ids) || ids.length > 200 || ids.some((id) => typeof id !== 'string' || !playlists.some((item) => item.id === id))
      || !Array.isArray(names) || names.length > 200 || names.some((name) => typeof name !== 'string' || name.length > 200) || typeof data.comparison !== 'string' || data.comparison.length > 8000) return invalid();
    const comparison = data.comparison;
    return () => { aiSavedSelection = { ids: [...ids] as string[], names: [...names] as string[], comparison }; renderPlaylists(); };
  }
  return invalid();
}
const renderLibraryStatus = createLibraryStatusView(element('library-status-container'), { canAct: () => coreAvailable && !gate.busy && Boolean(api?.rescanLibrary), rescan: () => scan(true) });
if(['reviewDetails','reviewCompare','reviewRemove','reviewReorder'].every(key=>typeof api?.[key as keyof AppApi]==='function')){
  const generatedReview=new GeneratedReviewController(api,{
    current:()=>review,canAct:()=>coreAvailable&&!gate.busy,changed:()=>renderGeneratedReview(),
    applied:value=>{if(review?.reviewId!==value.reviewId){if(serato.source?.kind==='review')serato.setSource(null);live.invalidate();invalidateAiSource();prepPlan=null;}review=value;renderVariants();renderReview();},
    perform:(label,task,apply,failure)=>perform('review-edit',label,task,value=>{apply(value);showStatus('Revisión local actualizada');},false,failure),
  });
  renderGeneratedReview=createGeneratedReviewView(element('generated-review-container'),generatedReview,{canAct:()=>coreAvailable&&!gate.busy});
}
if(prepSettingsAvailable()){
  prepSettings=new PrepSettingsController(api,{
    canAct:()=>coreAvailable&&!gate.busy,
    read:()=>{const fields=prepFields();return {requiredTrackIds:fields.required,excludedTrackIds:fields.excluded,genreFocus:fields.genre};},
    restore:value=>{for(const [key,ids] of [['required',value.requiredTrackIds],['excluded',value.excludedTrackIds]] as const)for(const option of element<HTMLSelectElement>(`prep-${key}`).options??[])option.selected=ids.includes(option.value);element<HTMLInputElement>('prep-genre').value=value.genreFocus;invalidatePrep();},
    changed:()=>{prepSettingsDirty=prepSettings?.dirty??false;renderPrepSettings();syncDraftDirty();},saved:()=>{invalidateAiSource();invalidatePrep();},
    perform:(label,task,apply,failure)=>perform('prep-settings',label,task,value=>{apply(value);showStatus('Controles de preparación actualizados');},false,failure),
  });
  renderPrepSettings=createPrepSettingsView(element('prep-settings-container'),prepSettings,{canAct:()=>coreAvailable&&!gate.busy});
}
const legacyCanAct=():boolean=>coreAvailable&&!gate.busy&&!editorDirty&&!preferencesDirty&&!profileSettingsDirty&&!prepSettingsDirty&&!loudnessDirty&&!aiDirty;
if(['previewLegacyImport','applyLegacyImport','discardLegacyImport'].every(key=>typeof api?.[key as keyof AppApi]==='function')){
  const legacyImport=new LegacyImportController(api,{canAct:legacyCanAct,changed:()=>renderLegacyImport(),applied:()=>freezeAfterLegacy(),
    perform:async(label,task,apply,failure)=>{const committing=label.startsWith('Importando');if(committing)player.stopIfMissing(new Set());await perform(committing?'legacy-import':'legacy-preview',label,task,value=>{apply(value);if(!restartRequired)showStatus(value.cancelled?'Importación cancelada':'Vista previa de datos actualizada','No se importa nada hasta la confirmación del sistema');},false,failure);},
  });
  renderLegacyImport=createLegacyImportView(element('legacy-import-container'),legacyImport,{canAct:legacyCanAct});renderLegacyImport();
}
if(typeof api?.queryLibrary==='function'&&typeof api?.searchPlaylists==='function')offline=new OfflineBrowseView(element('offline-library-container'),element('offline-saved-container'),api,{
  canAct:()=>coreAvailable&&!gate.busy,canDelete:()=>!editorDirty&&!preferencesDirty&&!profileSettingsDirty&&!prepSettingsDirty&&!loudnessDirty&&!aiDirty,
  perform:(label,task,apply)=>perform('offline',label,task,apply),
  libraryChanged:tracks=>{offlineLibrary=tracks;renderLibrary();},savedChanged:()=>renderPlaylists(),
  deleted:id=>{playlists=playlists.filter(item=>item.id!==id);if(editor.draft?.id===id)editor.resetAfterScan();if(review?.savedPlaylistId===id){review=null;renderReview();}serato.invalidatePreview();invalidateAiSource();aiSavedSelection=null;renderPlaylists();},
  restored:playlist=>{playlists=[playlist,...playlists.filter(item=>item.id!==playlist.id)];invalidateAiSource();aiSavedSelection=null;renderPlaylists();},
});
const drawProfiles=createProfilesView(element('profiles-container'),{canAct:()=>coreAvailable&&!gate.busy&&profilesAvailable(),retry:()=>{void completeProfiles();}});
renderProfiles=()=>drawProfiles(profilesSnapshot,profilesStale,activeKind==='profiles',profilesError);
renderPreferences(); renderProfileSettings(); renderLoudness(); renderProfiles(); renderLibraryStatus(libraryStatus);
function freezeAfterLegacy(reason='legacy_restart_required'):void{
  if(!restartRequired||reason==='legacy_recovery_required')coreFailure=reason==='legacy_recovery_required'?'Cierra XfinAudio y revisa el estado del perfil y sus copias antes de continuar. No se realizarán otras operaciones.':'Cierra y vuelve a abrir XfinAudio. Después, selecciona explícitamente tus carpetas musicales y vuelve a escanearlas.';
  restartRequired=true;coreAvailable=false;profileAutoPending=null;player.stopIfMissing(new Set());invalidateAiSource();editor.invalidatePreview();serato.invalidatePreview();loudness.invalidateContext();invalidatePrep();showStatus('Reinicio necesario',coreFailure,true);syncControls();
}
function syncDraftDirty(): void {
  renderLegacyImport();
  if (api?.setDraftDirty) void api.setDraftDirty(editorDirty || preferencesDirty || profileSettingsDirty || prepSettingsDirty || loudnessDirty || aiDirty).catch(() => showStatus('No se pudo proteger el cierre del borrador', 'Guarda tus cambios antes de cerrar XfinAudio', true));
}
function acceptLibraryStatus(status: LibraryStatus): void {
  if (!Number.isSafeInteger(status.revision) || status.revision < 0 || (libraryStatus && status.revision <= libraryStatus.revision)) return;
  libraryStatus = status;
  if (status.changeState === 'changed' && coreAvailable) {
    profilesStale=true;profileAutoPending=null;offline?.invalidateLibrary();offline?.invalidateSaved();
    if(activeKind==='profiles'&&!gate.cancelled){gate.requestCancel();void api.cancelCurrent().catch(()=>{profilesError=userErrorMessage({code:'profiles_unavailable'});renderProfiles();});}
    libraryGeneration++;
    loudness.invalidateContext();
    invalidateAiSource();
    aiLibraryFilter = null; aiFilterRevision++; aiSavedSelection = null;
    metadataReport = null;
    editor.invalidatePreview();
    serato.invalidatePreview();
    invalidatePrep();
    renderLibrary();
    element('saved-ai-selection').hidden = true;
  }
  renderProfiles();
  renderLibraryStatus(libraryStatus);
}
function loadLibraryStatus(): Promise<void> {
  return perform('library-status', 'Consultando estado de la biblioteca…', () => api.getLibraryStatus(), acceptLibraryStatus);
}
function continueIdleWork(kind: string): void {
  if (!coreAvailable || gate.busy) return;
  if(profileAutoPending!==null){const generation=profileAutoPending;profileAutoPending=null;if(generation===libraryGeneration&&!profilesStale){void completeProfiles();return;}}
  if (libraryBootstrapped && preferencesBootstrapPending) { preferencesBootstrapPending = false; void preferences.load(); return; }
  if (libraryBootstrapped && statusBootstrapPending) { statusBootstrapPending = false; void loadLibraryStatus(); return; }
  if(libraryBootstrapped&&profileBootstrapPending){profileBootstrapPending=false;void loadProfiles();return;}
  if(libraryBootstrapped&&prepSettingsBootstrapPending&&prepSettings&&!prepSettings.pending&&!prepSettings.dirty&&kind!=='prep-settings'){prepSettingsBootstrapPending=false;void prepSettings.load();return;}
  if(route==='preferences'&&kind!=='profile-settings'&&!profileSettingsAttempted&&profileSettingsAvailable()){profileSettingsAttempted=true;void profileSettings.load();return;}
  if (route === 'playlists' && !playlistsLoaded && kind !== 'playlists') { void loadPlaylists(); return; }
  if (route === 'metadata' && !metadataReport && kind !== 'metadata') { void loadMetadata(); return; }
  if (route === 'preferences' && kind !== 'preferences' && !preferences.snapshot && !preferences.pending && preferencesAvailable()) { void preferences.load(); return; }
  if (route === 'loudness' && kind !== 'loudness-settings' && kind !== 'loudness' && !loudness.statusFresh && !loudness.dirty && !loudness.pending && loudnessAvailable()) { void loudness.load(); return; }
  if (kind !== 'ai-settings' && kind !== 'ai' && kind !== 'ai-apply' && loadAiIfOpen()) return;
  if (kind.startsWith('ai')||kind==='offline') return;
  if (route === 'metadata' && kind !== 'metadata') void loadMetadata();
  if (route === 'playlists' && kind !== 'playlists') void loadPlaylists();
}
function canStartLive(): boolean { return Boolean(review?.reviewId && review.variant !== 'saved' && review.readiness === 'ready' && !review.blockers.length); }

function openSerato(source: SeratoExportSource, name: string): void {
  if (!coreAvailable || gate.busy) return;
  if (source.kind === 'saved' && editor.dirty && editor.draft?.id === source.playlistId) {
    showStatus('Tienes un borrador sin guardar', 'Guarda o descarta los cambios del editor antes de exportar esta playlist', true); navigate('editor', false); return;
  }
  serato.setSource(source, name); navigate('serato', false);
}

function showStatus(label: string, detail = '', error = false): void {
  if(restartRequired){label='Reinicio necesario';detail=coreFailure;error=true;}
  else if (!coreAvailable) {
    label = 'Servicio local desconectado';
    detail = coreFailure || 'Reinicia XfinAudio para volver a conectar con tu biblioteca';
    error = true;
  }
  element('operation-status').hidden = false;
  element('operation-status').classList.toggle('is-error', error);
  element('operation-label').textContent = label;
  element('operation-detail').textContent = detail;
}
function canSave(): boolean {
  return canSaveReview(review);
}
function syncControls(): void {
  document.querySelectorAll<HTMLButtonElement>('[data-track-id]').forEach((button) => { button.disabled = !coreAvailable || (activeKind === 'loudness'||activeKind.startsWith('legacy')); });
  document.querySelectorAll<HTMLButtonElement>('[data-mutation]').forEach((button) => { button.disabled = gate.busy || !coreAvailable; });
  document.querySelectorAll<HTMLInputElement | HTMLSelectElement>('[data-prep-control]').forEach((control) => { control.disabled = gate.busy || !coreAvailable; });
  element<HTMLSelectElement>('prep-strategy').disabled = gate.busy || !coreAvailable || !catalogLoaded;
  element<HTMLButtonElement>('export-library-worklist').disabled=gate.busy||!coreAvailable||!libraryWorklist||libraryStatus?.changeState==='changed';
  element<HTMLButtonElement>('generate-prep').disabled = gate.busy || !coreAvailable || library.length < 2;
  element<HTMLButtonElement>('start-live').disabled = gate.busy || !coreAvailable || !canStartLive();
  element<HTMLButtonElement>('export-review').disabled = gate.busy || !coreAvailable || !review || !(review.reviewId || review.savedPlaylistId);
  element<HTMLButtonElement>('save-playlist').disabled = gate.busy || !coreAvailable || !canSave();
  element<HTMLButtonElement>('cancel-operation').hidden = !gate.busy || !cancellable || !coreAvailable;
  element<HTMLButtonElement>('cancel-operation').disabled = gate.cancelled;
  element('cancel-operation').textContent = gate.cancelled ? 'Cancelando…' : 'Cancelar';
  renderEditor();
  renderSerato();
  renderLive();
  renderPreferences();
  renderProfileSettings();renderProfiles();renderGeneratedReview();renderPrepSettings();renderLegacyImport();offline?.sync();
  renderLoudness();
  syncAiContext(); renderAi();
  renderLibraryStatus(libraryStatus);
  element('prep-availability').textContent = library.length ? `${library.length} pistas en la biblioteca · ${library.filter(hasPrepMetadata).length} con metadatos completos` : 'Añade una carpeta de música para empezar';
}
function navigate(next: Route, load = true): void {
  route = next;
  routeRevision += 1;
  document.querySelectorAll<HTMLElement>('.page-panel').forEach((panel) => { panel.hidden = panel.id !== `page-${next}`; });
  document.querySelectorAll<HTMLButtonElement>('.nav-item').forEach((button) => {
    const selected = button.dataset.route === next;
    button.classList.toggle('active', selected);
    if (selected) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  element('page-title').textContent = titles[next];
  document.title = `XfinAudio · ${titles[next]}`;
  editor.invalidatePreview();
  if(next==='prep'&&load&&!gate.busy&&prepSettings&&!prepSettings.snapshot&&!prepSettings.pending&&!prepSettings.dirty){prepSettingsBootstrapPending=false;void prepSettings.load();}
  if (next === 'ai') element<HTMLDetailsElement>('ai-panel').open = true;
  syncAiContext();
  if (next === 'preferences' && load && !gate.busy && !preferences.snapshot && preferencesAvailable()) void preferences.load();
  if(next==='preferences'&&load&&!gate.busy&&!profileSettings.snapshot&&profileSettingsAvailable()){profileSettingsAttempted=true;void profileSettings.load();}
  if (next === 'loudness' && load && !gate.busy && !loudness.statusFresh && !loudness.dirty && loudnessAvailable()) void loudness.load();
  if (next === 'metadata' && load && !gate.busy) void loadMetadata();
  if (next === 'playlists' && load && !gate.busy) void loadPlaylists();
  if (load) loadAiIfOpen();
}
function renderTable(target: string, tracks: Track[]): void {
  const table = make('table');
  table.setAttribute('aria-label', target === 'library-table' ? 'Pistas de la biblioteca' : 'Pistas de la selección');
  const head = make('thead');
  const headers = make('tr');
  for (const title of ['#', 'PISTA / ARTISTA', 'BPM', 'TONALIDAD', 'ENERGÍA', 'DURACIÓN', 'ESCUCHAR']) {
    const th = make('th', title);
    th.scope = 'col';
    headers.append(th);
  }
  head.append(headers);
  const body = make('tbody');
  tracks.forEach((track, index) => {
    const row = make('tr');
    row.append(make('td', String(index + 1).padStart(2, '0'), 'track-index'));
    const name = make('td', '', 'track-name');
    name.append(make('strong', track.title || 'Sin título'), make('span', track.artist || 'Artista desconocido'));
    row.append(name, make('td', track.bpm === null ? '—' : String(track.bpm), 'numeric'));
    const key = make('td');
    key.append(make('span', track.key || '—', track.key ? 'key-pill' : 'muted'));
    row.append(key);
    const energy = make('td');
    energy.append(make('span', track.energy === null ? '—' : String(track.energy), 'energy-value'));
    row.append(energy, make('td', formatDuration(track.duration), 'numeric muted'));
    const action = make('td');
    const button = make('button', player.isPlaying(track.id) ? 'Ⅱ' : '▶', 'track-play');
    button.type = 'button';
    button.dataset.trackId = track.id;
    button.dataset.trackTitle = track.title;
    button.setAttribute('aria-label', `Escuchar ${track.title}`);
    button.addEventListener('click', () => { if (coreAvailable && activeKind !== 'loudness'&&!activeKind.startsWith('legacy')) void player.select(track).catch(() => showStatus('No se puede abrir esta pista', 'Su identificador no es válido', true)); });
    action.append(button);
    row.append(action);
    body.append(row);
  });
  table.append(head, body);
  element(target).replaceChildren(table);
}
function renderLibrary(): void {
  const complete = library.filter(hasPrepMetadata).length;
  for (const id of ['library-total', 'nav-library-count']) element(id).textContent = String(library.length);
  element('library-ready').textContent = String(complete);
  element('library-incomplete').textContent = String(library.length - complete);
  const browsed=offlineLibrary??library;
  const visible = filterTracks(aiLibraryFilter ? browsed.filter((track) => aiLibraryFilter!.has(track.id)) : browsed, element<HTMLInputElement>('library-search').value, element<HTMLSelectElement>('metadata-filter').value as MetadataFilter);
  const metadataFilter=element<HTMLSelectElement>('metadata-filter').value;
  libraryWorklist=['ready','incomplete'].includes(metadataFilter)&&visible.length>0&&visible.length<=500?{kind:'metadata',status:metadataFilter==='ready'?'complete':'incomplete',missingField:null,trackIds:visible.map(track=>track.id)}:null;
  renderTable('library-table', visible);
  element('library-table').hidden = library.length === 0;
  element('library-empty').hidden = library.length > 0;
  element('library-no-results').hidden = library.length === 0 || visible.length > 0;
  element('ai-library-filter').hidden = aiLibraryFilter === null;
  element('ai-library-filter-notice').textContent = aiLibraryFilter ? `Filtro local de IA: ${aiLibraryFilter.size} coincidencias. La biblioteca completa sigue disponible para preparar sesiones.` : '';
  element('library-visible-count').textContent = `${visible.length} ${visible.length === 1 ? 'pista' : 'pistas'}`;
  syncControls();
}
function applyLibrary(result: LibraryResult): void {
  const controlsDirty=prepSettings?.dirty??false;prepSettings?.libraryChanged();if(prepSettings&&!controlsDirty)prepSettingsBootstrapPending=true;
  library = result.tracks;
  offline?.invalidateLibrary();offline?.invalidateSaved();
  aiLibraryFilter = null; aiFilterRevision++;
  metadataReport = null;
  player.stopIfMissing(new Set(library.map((track) => track.id)));
  renderTrackChoices();
  renderLibrary();
}
function option(value: string, label: string): HTMLOptionElement {
  const node = make('option', label); node.value = value; return node;
}
function renderTrackChoices(): void {
  for (const id of ['start', 'end', 'required', 'excluded']) {
    const select = element<HTMLSelectElement>(`prep-${id}`);
    const selected=new Set(Array.from(select.selectedOptions??[],item=>item.value));const scalar=id==='start'||id==='end';if(scalar&&select.value)selected.add(select.value);
    select.replaceChildren();
    if(scalar)select.append(option('', 'Sin preferencia'));
    for(const track of library){const item=option(track.id,`${track.title||'Sin título'} · ${track.artist||'Artista desconocido'}`);item.selected=selected.has(track.id);select.append(item);}
    if(!scalar&&prepSettingsDirty)for(const value of selected)if(!library.some(track=>track.id===value)){const missing=option(value,`No disponible: ${value.slice(0,8)}`);missing.disabled=true;missing.selected=true;select.append(missing);}
    if(scalar)select.value=library.some(track=>selected.has(track.id))?[...selected][0]:'';
  }
}
function renderStrategyHint(): void {
  const strategy = strategies.find((item) => item.name === element<HTMLSelectElement>('prep-strategy').value);
  element('strategy-hint').textContent = strategy ? `${strategy.description}${strategy.requiresVibeMetadata ? ' Requiere metadatos vibe existentes; los datos ausentes no se inventan.' : ''}` : 'Sin preferencia: se conserva la estrategia predeterminada del motor.';
}
async function loadCatalog(): Promise<void> {
  element('catalog-retry').hidden = true;
  element('strategy-hint').textContent = 'Cargando estrategias del motor local…';
  syncControls();
  try {
    if (!api.getPrepCatalog) throw new Error('Catálogo no disponible');
    const result = await api.getPrepCatalog();
    if (!coreAvailable) return;
    strategies = result.strategies;
    catalogLoaded = true;
    element<HTMLSelectElement>('prep-strategy').replaceChildren(option('', 'Predeterminada del motor'), ...strategies.map((strategy) => option(strategy.name, strategy.displayName)));
    renderStrategyHint();
  } catch {
    if (coreAvailable) {
      element('strategy-hint').textContent = 'No se pudo cargar el catálogo. Puedes usar la estrategia predeterminada o volver a intentar.';
      element('catalog-retry').hidden = false;
    }
  }
  syncControls();
}
function invalidatePrep(options: { preserveLive?: boolean } = {}): void {
  if (!options.preserveLive) live.invalidate();
  if (serato.source?.kind === 'review') serato.setSource(null);
  prepPlan = null;
  review = null;
  renderVariants();
  renderReview();
}
function renderVariants(): void {
  const container = element('prep-variants');
  container.replaceChildren();
  element('variant-comparison').hidden = prepPlan === null;
  if (!prepPlan) return;
  const plan = prepPlan;
  for (const variant of plan.variants) {
    const card = make('article', '', 'surface prep-variant');
    const readiness = make('span', readinessNames[variant.readiness], `readiness-pill ${variant.readiness}`);
    card.append(make('h3', variantNames[variant.name]), make('p', variant.description), readiness);
    card.append(make('p', `${variant.trackCount} pistas · ${variant.warnings.length} avisos · ${variant.blockers.length} bloqueos`));
    card.append(make('p', `Puntuación del motor: ${Number.isFinite(variant.qualityScore) ? variant.qualityScore.toLocaleString('es', { maximumFractionDigits: 2 }) : '—'}`, 'field-hint'));
    const button = make('button', review?.variant === variant.name ? 'Volver a revisar' : 'Revisar alternativa', 'button subtle full-width');
    button.type = 'button'; button.dataset.mutation = ''; button.dataset.variant = variant.name;
    button.setAttribute('aria-label', `Revisar alternativa ${variantNames[variant.name].toLocaleLowerCase('es')}`);
    button.setAttribute('aria-pressed', String(review?.variant === variant.name));
    button.addEventListener('click', () => {
      if (gate.busy || !coreAvailable || prepPlan !== plan) return;
      if (serato.source?.kind === 'review') serato.setSource(null);
      live.invalidate();
      review = null;
      renderReview();
      void perform('select', 'Abriendo la alternativa para revisión…', () => api.selectPrepVariant({ planId: plan.id, variant: variant.name }), (result, currentRoute) => {
        if (prepPlan !== plan) return;
        review = result;
        renderVariants();
        renderReview();
        showStatus('Alternativa preparada para revisar', 'Comprueba las pistas, los avisos y el estado antes de guardar');
        if (currentRoute) navigate('review', false);
      }, true);
    });
    card.append(button);
    container.append(card);
  }
  syncControls();
}
function renderReview(): void {
  element('review-empty').hidden = review !== null;
  element('review-content').hidden = review === null;
  if (!review) { renderGeneratedReview();syncControls(); return; }
  element('review-name').textContent = review.name || 'Selección equilibrada';
  element('review-track-count').textContent = `${review.tracks.length} pistas · ${formatDuration(review.tracks.reduce((total, track) => total + (track.duration ?? 0), 0))}`;
  element('review-variant').textContent = review.variant === 'saved' ? 'PLAYLIST GUARDADA' : `SELECCIÓN ${variantNames[review.variant].toLocaleUpperCase('es')}`;
  const readiness = element('review-readiness');
  readiness.textContent = readinessNames[review.readiness];
  readiness.className = `readiness-pill ${review.readiness}`;
  const notices = element('review-alerts');
  notices.replaceChildren();
  for (const [messages, category] of [[review.blockers, 'blocker'], [review.warnings, 'warning']] as const) {
    if (!messages.length) continue;
    const notice = make('section', '', `review-notice ${category}`);
    notice.append(make('strong', category === 'blocker' ? 'Antes de guardar' : 'Ten en cuenta'));
    const list = make('ul');
    for (const message of messages) list.append(make('li', message));
    notice.append(list);
    notices.append(notice);
  }
  renderTable('review-table', review.tracks);
  element<HTMLInputElement>('save-name').value = review.name || 'Mi sesión';
  element('save-form').hidden = review.variant === 'saved' || review.canSave === false;
  element('save-hint').textContent = review.blockers.length ? 'Resuelve los bloqueos antes de guardar esta selección' : 'Escucha y revisa los avisos; después guarda tu selección';
  syncControls();
}

function renderPlaylistActions(card: HTMLElement, playlist: PlaylistSummary): void {
  const actions = make('div', '', 'playlist-actions');
  const renameForm = make('form', '', 'playlist-rename'); renameForm.id = `playlist-rename-${playlist.id}`; renameForm.hidden = true;
  const label = make('label', 'Nuevo nombre'); label.setAttribute('for', `playlist-name-${playlist.id}`);
  const input = make('input'); input.id = `playlist-name-${playlist.id}`; input.value = playlist.name; input.maxLength = 200; input.required = true;
  const save = make('button', 'Guardar nombre', 'button primary'); save.type = 'submit'; save.dataset.mutation = '';
  const cancel = make('button', 'Cancelar', 'button subtle'); cancel.type = 'button'; cancel.addEventListener('click', () => { renameForm.hidden = true; });
  renameForm.append(label, input, save, cancel);
  renameForm.addEventListener('submit', (event) => {
    event.preventDefault();
    if (gate.busy || !coreAvailable) return;
    const name = input.value.trim();
    if (!name || name.length > 200) { showStatus('Revisa el nombre', 'Usa entre 1 y 200 caracteres', true); return; }
    void perform('playlists', 'Renombrando playlist…', () => api.renamePlaylist({ playlistId: playlist.id, name }), (result) => {
      playlists = playlists.map((item) => item.id === result.id ? result : item);offline?.invalidateSaved();
      renderPlaylists(); showStatus('Playlist renombrada', result.name);
    });
  });
  for (const [caption, action] of [
    ['Exportar a Serato', () => { openSerato({ kind: 'saved', playlistId: playlist.id }, playlist.name); }],
    ['Editar', () => { void editor.open(playlist.id); }],
    ['Renombrar', () => {
      if (editor.draft?.id === playlist.id) { void editor.open(playlist.id).then(() => element<HTMLInputElement>('editor-name').focus()); return; }
      renameForm.hidden = !renameForm.hidden; if (!renameForm.hidden) input.focus();
    }],
    ['Duplicar', () => { void perform('playlists', 'Duplicando playlist guardada…', () => api.duplicatePlaylist({ playlistId: playlist.id }), (result) => {
      playlists = [result, ...playlists.filter((item) => item.id !== result.id)]; offline?.invalidateSaved();renderPlaylists(); showStatus('Playlist duplicada', result.name);
    }); }],
  ] as const) {
    const control = make('button', caption, 'button subtle'); control.type = 'button'; control.dataset.mutation = '';
    control.setAttribute('aria-label', `${caption}: ${playlist.name}`);
    control.addEventListener('click', () => { if (!gate.busy && coreAvailable) action(); }); actions.append(control);
  }
  card.append(actions, renameForm);
}

function renderPlaylists(): void {
  for (const id of aiSavedScope) if (!playlists.some((item) => item.id === id)) aiSavedScope.delete(id);
  const suggestion = element('saved-ai-selection'); suggestion.replaceChildren(); suggestion.hidden = !aiSavedSelection;
  if (aiSavedSelection) { suggestion.append(make('h3', 'Selección local sugerida por IA'), make('p', aiSavedSelection.comparison)); const names = make('ul'); for (const name of aiSavedSelection.names) names.append(make('li', name)); suggestion.append(names); }
  offline?.beginPlaylistRender(playlists);
  const container = element('playlists-list');
  container.replaceChildren();
  element('playlists-empty').hidden = playlists.length > 0;
  for (const playlist of playlists) {
    if(offline&&!offline.matches(playlist.id))continue;
    const card = make('article', '', 'surface playlist-card');
    if (aiAvailable()) {
      const scope = make('input'); scope.type = 'checkbox'; scope.checked = aiSavedScope.has(playlist.id); scope.id = `ai-saved-scope-${playlist.id}`; scope.disabled = gate.busy || !coreAvailable;
      const label = make('label', 'Incluir en la consulta de IA'); label.setAttribute('for', scope.id);
      scope.addEventListener('change', () => { if (gate.busy || !coreAvailable) return; if (scope.checked && aiSavedScope.size >= 200) { scope.checked = false; showStatus('Consulta de IA demasiado grande', 'Selecciona como máximo 200 playlists', true); return; } if (scope.checked) aiSavedScope.add(playlist.id); else aiSavedScope.delete(playlist.id); syncAiContext(); });
      card.append(scope, label);
    }
    if (aiSavedSelection?.ids.includes(playlist.id)) card.append(make('p', 'Incluida en la propuesta local de IA', 'review-notice'));
    card.append(make('div', '♫', 'playlist-art'), make('span', 'PLAYLIST LOCAL', 'eyebrow'), make('h3', playlist.name));
    const date = new Date(playlist.createdAt);
    card.append(make('p', `${playlist.trackCount} pistas${Number.isNaN(date.getTime()) ? '' : ` · ${date.toLocaleDateString('es', { day: 'numeric', month: 'short' })}`}`));
    const button = make('button', 'Abrir playlist →', 'button subtle');
    button.dataset.mutation = '';
    button.addEventListener('click', () => {
      if (gate.busy || !coreAvailable) return;
      invalidatePrep();
      void perform('open', 'Abriendo playlist…', () => api.openPlaylist({ playlistId: playlist.id }), (result, currentRoute) => {
      review = result;
      renderReview();
      showStatus('Playlist abierta', result.name);
      if (currentRoute) navigate('review', false);
    }); });
    card.append(button);
    renderPlaylistActions(card, playlist);offline?.addPlaylistActions(card,playlist);
    container.append(card);
  }
  syncControls();
}
async function perform<T>(kind: string, label: string, task: () => Promise<T>, apply: (value: T, currentRoute: boolean) => void, canCancel = false, failure?: (error: unknown) => void): Promise<void> {
  if (!coreAvailable) return;
  const token = gate.begin(routeRevision);
  if (!token) return;
  const sourceGeneration = libraryGeneration;
  activeKind = kind;
  activeJobId = '';
  cancellable = canCancel;
  showStatus(label);
  const progress = element<HTMLProgressElement>('operation-progress');
  progress.hidden = !canCancel;
  progress.removeAttribute('value');
  syncControls();
  try {
    const result = await task();
    // No new operation can start before this token finishes. Cancellation must not discard a write receipt.
    const terminalLegacy=kind==='legacy-import'&&activeKind==='legacy-import'&&gate.busy;
    const terminalProfiles=kind==='profiles'&&activeKind==='profiles'&&gate.busy;
    const terminalLoudness = kind === 'loudness' && activeKind === 'loudness' && gate.busy;
    if ((gate.isCurrent(token) || terminalLoudness || terminalProfiles || terminalLegacy) && (coreAvailable || kind === 'serato' || terminalLoudness || terminalLegacy)) {
      if (sourceGeneration !== libraryGeneration && ['prep', 'select', 'open', 'metadata','profiles'].includes(kind)) showStatus('La biblioteca cambió', 'Vuelve a escanear antes de preparar una nueva selección');
      else apply(result, token.routeRevision === routeRevision);
    }
  } catch (error) {
    const code=errorCode(error);if(code==='legacy_restart_required'||code==='legacy_recovery_required')freezeAfterLegacy(code);
    if (!gate.cancelled || kind === 'loudness' || kind === 'profiles') {
      failure?.(error);
      console.error('Local operation failed', error);
      showStatus('No se pudo completar la operación', userErrorMessage(error), true);
    }
  } finally {
    if (gate.cancelled) {
      if (kind === 'scan') {
        try { applyLibrary(await api.listLibrary()); }
        catch { showStatus('Escaneo cancelado', 'No se pudo actualizar la biblioteca; vuelve a elegir la carpeta para sincronizarla', true); }
      }
      if (kind !== 'loudness' && kind !== 'profiles' && !element('operation-status').classList.contains('is-error')) showStatus('Operación cancelada', kind === 'ai' ? 'Los datos ya enviados no se pueden recuperar.' : kind === 'scan' ? 'Se conservan las pistas leídas hasta la cancelación' : 'Puedes volver a intentarlo cuando quieras');
    }
    gate.finish(token);
    const localApply = deferredAiApply; deferredAiApply = null;
    if (kind === 'ai-apply' && coreAvailable && localApply) localApply();
    activeKind = '';
    activeJobId = '';
    progress.hidden = true;
    syncControls();
    if (kind === 'library') libraryBootstrapped = true;
    continueIdleWork(kind);
  }
}
function loadMetadata(): Promise<void> {
  return perform('metadata', 'Revisando metadatos…', () => api.getMetadataReport(), (result) => {
    metadataReport = result;const reportGeneration=libraryGeneration;
    renderMetadataPanel(element('metadata-report-container'), metadataReport, (id) => {
      const track = library.find((item) => item.id === id);
      if (track && coreAvailable && activeKind !== 'loudness'&&!activeKind.startsWith('legacy')) void player.select(track).catch(() => showStatus('No se puede abrir esta pista', 'Comprueba que siga disponible en tu biblioteca', true));
    },source=>{if(metadataReport===result&&reportGeneration===libraryGeneration)openSerato(source,'Revisión de metadatos');});
    showStatus('Metadatos actualizados', `${result.incompleteCount} pistas requieren revisión · no se han escrito etiquetas`);
  });
}
function loadPlaylists(): Promise<void> {
  return perform('playlists', 'Cargando playlists…', () => api.listPlaylists(), (result) => {
    playlistsLoaded = true;
    playlists = result;offline?.invalidateSaved();
    renderPlaylists();
    showStatus('Playlists actualizadas', `${result.length} guardadas en este equipo`);
  });
}
function loadProfiles():Promise<void>{
  return perform('profile-status','Consultando perfiles locales…',()=>api.getProfileStatus(),value=>{profilesSnapshot=profileStatus(value);profilesError='';renderProfiles();},false,error=>{profilesError=userErrorMessage(error);renderProfiles();});
}
async function completeProfiles():Promise<void>{
  if(!coreAvailable||gate.busy||!profilesAvailable()||profilesStale)return;
  if(editor.dirty){showStatus('Tienes un borrador sin guardar','Guarda o descarta los cambios del editor antes de completar perfiles',true);navigate('editor',false);return;}
  editor.resetAfterScan();libraryGeneration++;invalidateAiSource();metadataReport=null;loudness.invalidateContext();serato.invalidatePreview();invalidatePrep();
  profilesError='';const ids=new Set(library.map(track=>track.id));
  await perform('profiles','Completando perfiles locales…',()=>api.completeProfiles(),result=>{
    const summary=profileStatus(result.status);
    if(typeof result.cancelled!=='boolean'||!Array.isArray(result.tracks)||result.tracks.length!==ids.size||new Set(result.tracks.map(track=>track.id)).size!==ids.size||result.tracks.some(track=>!ids.has(track.id))||summary.totalTracks!==ids.size||result.completeCount!==result.tracks.filter(hasPrepMetadata).length||result.incompleteCount!==result.tracks.length-result.completeCount)throw Object.assign(new Error('Invalid profile result'),{code:'profiles_unavailable'});
    profilesSnapshot=summary;applyLibrary({tracks:result.tracks,count:result.tracks.length});
    showStatus(result.cancelled?'Perfiles cancelados':summary.state==='complete'?'Perfiles completados':'Perfiles pendientes',`${summary.readyCount} de ${summary.totalTracks} pistas completas; los metadatos siguen disponibles`);
  },true,error=>{profilesError=userErrorMessage(error);renderProfiles();});
}
function scan(registered = false): void {
  if (gate.busy || !coreAvailable || (registered && (!api.rescanLibrary || !libraryStatus?.rootCount))) return;
  if (editor.dirty) { showStatus('Tienes un borrador sin guardar', 'Guarda o descarta los cambios del editor antes de cambiar la biblioteca', true); navigate('editor', false); return; }
  profileAutoPending=null;profilesSnapshot=null;profilesStale=false;profilesError='';
  editor.resetAfterScan();
  libraryGeneration++; invalidateAiSource();
  aiLibraryFilter = null; aiFilterRevision++; aiSavedSelection = null;
  loudness.invalidateContext();
  serato.invalidatePreview();
  invalidatePrep();
  void perform('scan', registered ? 'Volviendo a escanear bibliotecas…' : 'Elige tu carpeta de música', () => registered ? api.rescanLibrary() : api.chooseLibrary(), (result) => {
    if (!result) { showStatus('Selección de carpeta cancelada'); return; }
    applyLibrary(result);
    if(!result.cancelled&&profilesAvailable()){profilesStale=libraryStatus?.changeState==='changed';profileAutoPending=libraryGeneration;}
    showStatus(result.cancelled?'Escaneo cancelado':'Biblioteca actualizada', `${library.length} pistas disponibles`);
  }, true);
}
for (const button of document.querySelectorAll<HTMLButtonElement>('[data-route]')) button.addEventListener('click', () => navigate(button.dataset.route as Route));
element('export-library-worklist').addEventListener('click',()=>{if(libraryWorklist&&libraryStatus?.changeState!=='changed')openSerato(libraryWorklist,libraryWorklist.kind==='metadata'&&libraryWorklist.status==='complete'?'Metadatos completos':'Metadatos pendientes');});
element('choose-library').addEventListener('click', () => scan());
element('choose-library-empty').addEventListener('click', () => scan());
element('library-search').addEventListener('input', renderLibrary);
element('clear-ai-library-filter').addEventListener('click', () => { aiLibraryFilter = null; aiFilterRevision++; renderLibrary(); });
element('ai-panel').addEventListener('toggle', () => { syncAiContext(); loadAiIfOpen(); });
for (const id of ['name', 'count', 'strategy', 'minutes', 'role', 'genre', 'start', 'end', 'required', 'excluded']) for (const event of ['input', 'change']) element(`prep-${id}`).addEventListener(event,()=>{if(['required','excluded','genre'].includes(id))prepSettings?.edited();syncAiContext();});
element('metadata-filter').addEventListener('change', renderLibrary);
element('prep-strategy').addEventListener('change', renderStrategyHint);
element('catalog-retry').addEventListener('click', () => { void loadCatalog(); });
element('refresh-metadata').addEventListener('click', () => { void loadMetadata(); });
element('refresh-playlists').addEventListener('click', () => { void loadPlaylists(); });
element('prep-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (gate.busy) return;
  const name = normalizePrepName(element<HTMLInputElement>('prep-name').value);
  const value = (id: string) => element<HTMLInputElement | HTMLSelectElement>(`prep-${id}`).value;
  const selected = (id: string) => Array.from(element<HTMLSelectElement>(`prep-${id}`).selectedOptions ?? [], (option) => option.value);
  let input;
  try {
    input = buildPrepInput({ count: value('count'), name, strategy: value('strategy'), minutes: value('minutes'), role: value('role'), genre: value('genre'), start: value('start'), end: value('end'), required: selected('required'), excluded: selected('excluded') }, library, strategies);
  } catch (error) { showStatus('Revisa la configuración de la sesión', error instanceof Error ? error.message : String(error), true); return; }
  invalidatePrep();
  void perform('prep', 'Preparando alternativas para tu sesión…', () => api.generatePrep(input), (result, currentRoute) => {
    review = result;
    prepPlan = result.planId && result.variants ? { id: result.planId, variants: result.variants } : null;
    renderVariants();
    renderReview();
    showStatus('Selección preparada', 'Compara las alternativas y revisa las pistas antes de guardar');
    if (currentRoute) navigate('review', false);
  }, true);
});
element('start-live').addEventListener('click', () => {
  if (!coreAvailable || gate.busy || !canStartLive() || !review) return;
  void live.start(review.reviewId); navigate('live', false);
});
element('export-review').addEventListener('click', () => {
  if (!review) return;
  if (review.savedPlaylistId) openSerato({ kind: 'saved', playlistId: review.savedPlaylistId }, review.name);
  else if (review.reviewId) openSerato({ kind: 'review', reviewId: review.reviewId }, review.name);
});
element('save-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (gate.busy || !canSave() || !review) return;
  const name = element<HTMLInputElement>('save-name').value.trim();
  if (!name) { showStatus('Ponle un nombre a la playlist', 'El nombre no puede quedar vacío', true); return; }
  const candidate = review;
  void perform('save', 'Guardando playlist…', () => api.savePlaylist({ name, reviewId: candidate.reviewId }), (result, currentRoute) => {
    review = { ...candidate, name: result.name, savedPlaylistId: result.id, canSave: false };
    serato.invalidatePreview();
    playlists = [result, ...playlists.filter((playlist) => playlist.id !== result.id)];offline?.invalidateSaved();
    renderReview();
    renderPlaylists();
    showStatus('Playlist guardada', result.name);
    if (currentRoute) navigate('playlists', false);
  });
});
element('cancel-operation').addEventListener('click', () => {
  if (!gate.busy || !cancellable || gate.cancelled) return;
  if (activeKind === 'ai') ai?.cancelPending();
  gate.requestCancel();
  if (activeKind !== 'ai') invalidatePrep();
  syncControls();
  element('operation-detail').textContent = activeKind === 'ai' ? 'Solicitud cancelada. Los datos ya enviados no se pueden recuperar.' : activeKind === 'loudness' ? 'Cancelando lo pendiente. Las etiquetas ya escritas se conservan con sus copias; espera a que termine cualquier escritura en curso…' : 'Esperando a que termine la operación en curso…';
  void api.cancelCurrent().catch(() => showStatus('No se pudo solicitar la cancelación', 'Espera a que termine la operación antes de intentarlo de nuevo', true));
});
if (api) {
  if (api.onLibraryStatus) {
    const unsubscribeStatus = api.onLibraryStatus(acceptLibraryStatus);
    window.addEventListener('beforeunload', unsubscribeStatus, { once: true });
  }
  const unsubscribe = api.onProgress((event) => {
    if (isCoreFailure(event)) {
      coreAvailable = false;profileAutoPending=null;profilesError=userErrorMessage({code:'profiles_unavailable'});
      invalidateAiSource();
      loudness.invalidateContext();
      editor.invalidatePreview();
      serato.invalidatePreview();
      live.invalidate({ preserveSnapshot: true });
      invalidatePrep({ preserveLive: true });
      console.error('Local core stopped', event.message);
      coreFailure = userErrorMessage({ code: 'core_stopped' });
      showStatus('Servicio local desconectado', coreFailure, true);
      element('operation-progress').hidden = true;
      syncControls();
      return;
    }
    if (!coreAvailable) return;
    if (!gate.busy || gate.cancelled || !cancellable) return;
    if (event.phase !== activeKind && event.operation !== activeKind) return;
    if (activeJobId && event.jobId !== activeJobId) return;
    activeJobId = event.jobId;
    const progress = element<HTMLProgressElement>('operation-progress');
    progress.hidden = false;
    if (event.total && event.total > 0 && event.current !== undefined) {
      progress.max = event.total;
      progress.value = Math.min(event.total, Math.max(0, event.current));
    } else progress.removeAttribute('value');
    element('operation-label').textContent = activeKind==='profiles'?`Completando ${profileStageNames[event.stage??'']??'perfiles locales'}…`:activeKind === 'scan' ? 'Leyendo metadatos…' : activeKind === 'loudness' ? 'Analizando sonoridad y escribiendo etiquetas…' : activeKind === 'ai' ? 'Consultando asistencia IA…' : 'Preparando selección…';
    element('operation-detail').textContent = [event.current !== undefined ? `${event.current}${event.total ? ` / ${event.total}` : ''}` : '', activeKind==='profiles'?'Análisis local de solo lectura':event.message ?? ''].filter(Boolean).join(' · ');
  });
  window.addEventListener('beforeunload', unsubscribe, { once: true });
  void loadCatalog();
  void perform('library', 'Cargando biblioteca…', () => api.listLibrary(), (result) => {
    applyLibrary(result);
    element('operation-status').hidden = true;
  });
} else {
  showStatus('El servicio local no está disponible', 'Abre XfinAudio desde su aplicación de escritorio', true);
  syncControls();
}
