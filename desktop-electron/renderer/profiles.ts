import type { Track } from './model.js';
export interface ProfileStatus {
  state:'idle'|'complete'|'partial'|'cancelled'|'unavailable';
  totalTracks:number;readyCount:number;spectralReadyCount:number;danceabilityReadyCount:number;edgeReadyCount:number;
  spectralPendingCount:number;danceabilityPendingCount:number;edgePendingCount:number;
  edgeNotApplicableCount:number;
  pendingCount:number;failedCount:number;estimatedRemainingSeconds:number|null;
}
/** completeCount/incompleteCount retain library metadata meanings; status owns profile readiness. */
export interface ProfileResult {cancelled:boolean;status:ProfileStatus;tracks:Track[];completeCount:number;incompleteCount:number;}
export interface ProfilesApi {getProfileStatus():Promise<ProfileStatus>;completeProfiles():Promise<ProfileResult>;}
const keys=['totalTracks','readyCount','spectralReadyCount','danceabilityReadyCount','edgeReadyCount','spectralPendingCount','danceabilityPendingCount','edgePendingCount','edgeNotApplicableCount','pendingCount','failedCount'] as const;
/** The edge stage ignores tracks shorter than this, so they never reach its windows. */
const minEdgeTrackSeconds=65;
export function profileStatus(value:ProfileStatus):ProfileStatus {
  const invalid=():never=>{throw Object.assign(new Error('Invalid profile summary'),{code:'profiles_unavailable'});};
  if(!value||!['idle','complete','partial','cancelled','unavailable'].includes(value.state))return invalid();
  // Older cores do not send the not-applicable count; zero keeps their meaning exact.
  const status:ProfileStatus={...value,edgeNotApplicableCount:value.edgeNotApplicableCount??0};
  for(const key of keys)if(!Number.isSafeInteger(status[key])||status[key]<0||status[key]>100000||status[key]>status.totalTracks)return invalid();
  // Per-analysis readiness and pending are two halves of the same total, never a guess.
  if(status.readyCount+status.pendingCount!==status.totalTracks
    ||status.spectralReadyCount<status.readyCount||status.spectralReadyCount+status.spectralPendingCount!==status.totalTracks
    ||status.danceabilityReadyCount<status.readyCount||status.danceabilityReadyCount+status.danceabilityPendingCount!==status.totalTracks
    // A short track is complete without an edge profile, so ready + not applicable + pending is the library.
    ||status.edgeReadyCount+status.edgeNotApplicableCount+status.edgePendingCount!==status.totalTracks
    ||(status.state==='complete'&&status.pendingCount!==0))return invalid();
  const remaining=status.estimatedRemainingSeconds;
  if(remaining!==null&&(!Number.isSafeInteger(remaining)||remaining<0||remaining>315360000||(status.pendingCount===0&&remaining!==0)))return invalid();
  return {state:status.state,...Object.fromEntries(keys.map(key=>[key,status[key]])),estimatedRemainingSeconds:remaining} as ProfileStatus;
}
/** Spanish phrasing for tracks whose edge windows do not apply; empty when there are none. */
export function profileShortTracksLabel(count:number|undefined):string {
  if(typeof count!=='number'||!Number.isSafeInteger(count)||count<=0)return '';
  return `${count} no aplican (menos de ${minEdgeTrackSeconds} s)`;
}
export const profileStageNames:Record<string,string>={spectral:'perfil espectral',danceability:'bailabilidad',edge:'bordes de entrada y salida'};
/** Spanish rounding of a measured estimate; nothing is claimed without one. */
export function profileEta(seconds:number|null|undefined):string {
  if(typeof seconds!=='number'||!Number.isSafeInteger(seconds)||seconds<=0)return '';
  if(seconds<60)return 'Falta menos de un minuto';
  const minutes=Math.round(seconds/60);
  if(minutes<60)return `Faltan unos ${minutes} min`;
  const hours=Math.floor(minutes/60),rest=minutes%60;
  return `${hours===1?'Falta':'Faltan unas'} ${hours} h${rest?` ${rest} min`:''}`;
}
export function profileSummary(status:ProfileStatus|null,stale:boolean,pending:boolean,remaining:number|null=null):string {
  if(stale)return 'La biblioteca cambió. Vuelve a escanear para actualizar los perfiles.';
  if(!status)return pending?'Completando perfiles locales…':'Perfiles todavía sin consultar.';
  const label={idle:'Perfiles pendientes',complete:'Perfiles completos',partial:'Perfiles parciales',cancelled:'Análisis de perfiles cancelado',unavailable:'Perfiles no disponibles'}[status.state];
  const perStage=`Pendientes por análisis: espectral ${status.spectralPendingCount} · bailabilidad ${status.danceabilityPendingCount} · bordes ${status.edgePendingCount}.`;
  // Short tracks are complete without edges, so they are named apart from the pending work.
  const shortTracks=profileShortTracksLabel(status.edgeNotApplicableCount);
  // A running job reports its own measurement; the stored status is the last one it published.
  const eta=profileEta(remaining??status.estimatedRemainingSeconds);
  return `${label}: ${status.readyCount} de ${status.totalTracks} pistas completas · ${status.pendingCount} pendientes · ${status.failedCount} fallidas. ${perStage}${shortTracks?` ${shortTracks}.`:''}${eta?` ${eta}.`:''}${pending?' Análisis en curso…':''}`;
}
export function createProfilesView(root:HTMLElement,host:{canAct():boolean;retry():void;rescanAndComplete():void}):(status:ProfileStatus|null,stale:boolean,pending:boolean,error:string,remaining?:number|null)=>void {
  const section=document.createElement('section');section.className='surface review-notice';section.setAttribute('aria-label','Perfiles locales');
  const summary=document.createElement('p');summary.id='profiles-summary';summary.setAttribute('role','status');
  const hint=document.createElement('p');hint.className='field-hint';hint.textContent='Análisis local de solo lectura para las estrategias existentes. Los metadatos siguen disponibles; no escribe etiquetas ni inicia reproducción.';
  const failure=document.createElement('p');failure.id='profiles-error';failure.setAttribute('role','alert');
  const retry=document.createElement('button');retry.id='profiles-retry';retry.type='button';retry.className='button subtle';retry.textContent='Completar / reintentar perfiles';retry.addEventListener('click',()=>{if(!retry.disabled&&host.canAct())host.retry();});
  // S1: a stale library still has one forward path, the rescan whose completion chains step 2/2.
  const rescan=document.createElement('button');rescan.id='profiles-rescan';rescan.type='button';rescan.className='button';rescan.textContent='Reescanear y completar perfiles';rescan.hidden=true;
  rescan.addEventListener('click',()=>{if(!rescan.disabled&&host.canAct())host.rescanAndComplete();});
  section.append(summary,hint,failure,retry,rescan);root.replaceChildren(section);
  return(status,stale,pending,error,remaining=null)=>{const canAct=host.canAct();
    summary.textContent=profileSummary(status,stale,pending,remaining);failure.textContent=error;failure.hidden=!error;
    retry.disabled=!canAct||pending||stale||status?.totalTracks===0||status?.state==='complete';
    rescan.hidden=!stale;rescan.disabled=!canAct||pending;};
}
