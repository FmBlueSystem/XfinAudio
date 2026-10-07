/** The exact refusal every action outside the whitelist keeps while the host is occupied. */
export const BUSY_MESSAGE='[busy] Another task is still running';
/**
 * Read actions this process may still dispatch while an exclusive task holds the host,
 * mapped to the core query each one sends.
 *
 * The audio core runs a single job worker, but `JsonlServer.process_line` answers the
 * genuinely read-only queries inline. Every entry here is answered by an owned
 * connection-per-call or an in-memory snapshot, so it cannot write state, control the
 * running job, read credentials, or observe another operation's partial work. A read
 * whose core query is not in that inline set stays refused rather than moving the same
 * refusal from this boundary to the core.
 */
export const READ_ONLY_CORE:Readonly<Record<string,string>>={
  listLibrary:'library.list',listPlaylists:'playlist.list',openPlaylist:'playlist.open',
  getMetadataReport:'metadata.report',getPreferences:'settings.get',prepSettings:'prep.settings.get',
  getPrepCatalog:'prep.catalog',getProfileStatus:'profiles.status',getProfileSettings:'profiles.settings.get',
  getLoudnessStatus:'loudness.status',getAiStatus:'ai.status',getLiveStatus:'live.status',
  queryLibrary:'library.query',searchPlaylists:'playlist.search',comparePlaylists:'playlist.compare',
  listDeletedPlaylists:'playlist.deleted.list',
};
/** Reads answered locally from a cache or in-memory snapshot, with no core query at all. */
export const LOCAL_READ_ACTIONS:ReadonlySet<string>=new Set(['getLibraryStatus']);
/** Every action admitted while the host is occupied; these two sets are the whole whitelist. */
export const READ_ONLY_ACTIONS:ReadonlySet<string>=new Set([...Object.keys(READ_ONLY_CORE),...LOCAL_READ_ACTIONS]);
/** Core methods the single worker answers inline, so the shared request may forward them during a job. */
export const INLINE_CORE_METHODS:ReadonlySet<string>=new Set([...Object.values(READ_ONLY_CORE),'track.resolve']);
/** Local draft bookkeeping and cancellation already run during an exclusive task. */
export const ALWAYS_ALLOWED_ACTIONS:ReadonlySet<string>=new Set(['setDraftDirty','cancelCurrent']);
/** Every host side exclusive source; a pending core job counts as one. */
export interface HostActivity{legacy:boolean;offline:boolean;profiles:boolean;serato:boolean;optionalAi:boolean;loudness:boolean;library:boolean;dialog:boolean;job:boolean;}
export function exclusiveInFlight(activity:HostActivity):boolean {
  return activity.legacy||activity.offline||activity.profiles||activity.serato||activity.optionalAi||activity.loudness||activity.library||activity.dialog||activity.job;
}
export function isAllowedWhileBusy(method:string):boolean {
  return READ_ONLY_ACTIONS.has(method)||ALWAYS_ALLOWED_ACTIONS.has(method);
}
/** Fail-closed: an action outside the whitelist is refused while the host is occupied. */
export function assertDispatchable(method:string,activity:HostActivity):void {
  if(exclusiveInFlight(activity)&&!isAllowedWhileBusy(method))throw new Error(BUSY_MESSAGE);
}
