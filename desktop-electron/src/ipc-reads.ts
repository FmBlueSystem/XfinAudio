/** The exact refusal every action outside the whitelist keeps while the host is occupied. */
export const BUSY_MESSAGE='[busy] Another task is still running';
/**
 * Read-only actions that may still be dispatched while an exclusive task holds the host.
 *
 * The audio core runs a single job worker: `JsonlServer.process_line` answers only
 * `track.resolve` and `prep.catalog` inline while a job is active and refuses every
 * other method with `busy`. A read therefore belongs here only when this process can
 * answer it without that worker: `getLibraryStatus` reads the cached native watcher
 * status and `getPrepCatalog` is the core's inline catalog lookup. Admitting any other
 * read would only move the same refusal from this boundary to the core.
 */
export const READ_ONLY_ACTIONS:ReadonlySet<string>=new Set(['getLibraryStatus','getPrepCatalog']);
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
