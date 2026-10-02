import type { Track } from './model.js';
export interface ProfileStatus {
  state:'idle'|'complete'|'partial'|'cancelled'|'unavailable';
  totalTracks:number;readyCount:number;spectralReadyCount:number;danceabilityReadyCount:number;edgeReadyCount:number;pendingCount:number;failedCount:number;
}
/** completeCount/incompleteCount retain library metadata meanings; status owns profile readiness. */
export interface ProfileResult {cancelled:boolean;status:ProfileStatus;tracks:Track[];completeCount:number;incompleteCount:number;}
export interface ProfilesApi {getProfileStatus():Promise<ProfileStatus>;completeProfiles():Promise<ProfileResult>;}
const keys=['totalTracks','readyCount','spectralReadyCount','danceabilityReadyCount','edgeReadyCount','pendingCount','failedCount'] as const;
export function profileStatus(value:ProfileStatus):ProfileStatus {
  const invalid=():never=>{throw Object.assign(new Error('Invalid profile summary'),{code:'profiles_unavailable'});};
  if(!value||!['idle','complete','partial','cancelled','unavailable'].includes(value.state))return invalid();
  for(const key of keys)if(!Number.isSafeInteger(value[key])||value[key]<0||value[key]>100000||value[key]>value.totalTracks)return invalid();
  if(value.readyCount+value.pendingCount!==value.totalTracks||(['spectralReadyCount','danceabilityReadyCount','edgeReadyCount'] as const).some(key=>value[key]<value.readyCount)
    ||(value.state==='complete'&&value.pendingCount!==0))return invalid();
  return {state:value.state,...Object.fromEntries(keys.map(key=>[key,value[key]]))} as ProfileStatus;
}
export const profileStageNames:Record<string,string>={spectral:'perfil espectral',danceability:'bailabilidad',edge:'perfiles de entrada y salida'};
export function profileSummary(status:ProfileStatus|null,stale:boolean,pending:boolean):string {
  if(stale)return 'La biblioteca cambió. Vuelve a escanear para actualizar los perfiles.';
  if(!status)return pending?'Completando perfiles locales…':'Perfiles todavía sin consultar.';
  const label={idle:'Perfiles pendientes',complete:'Perfiles completos',partial:'Perfiles parciales',cancelled:'Análisis de perfiles cancelado',unavailable:'Perfiles no disponibles'}[status.state];
  return `${label}: ${status.readyCount} de ${status.totalTracks} pistas completas · ${status.pendingCount} pendientes · ${status.failedCount} fallidas. Espectral ${status.spectralReadyCount} · bailabilidad ${status.danceabilityReadyCount} · entrada/salida ${status.edgeReadyCount}.${pending?' Análisis en curso…':''}`;
}
export function createProfilesView(root:HTMLElement,host:{canAct():boolean;retry():void}):(status:ProfileStatus|null,stale:boolean,pending:boolean,error:string)=>void {
  const section=document.createElement('section');section.className='surface review-notice';section.setAttribute('aria-label','Perfiles locales');
  const summary=document.createElement('p');summary.id='profiles-summary';summary.setAttribute('role','status');
  const hint=document.createElement('p');hint.className='field-hint';hint.textContent='Análisis local de solo lectura para las estrategias existentes. Los metadatos siguen disponibles; no escribe etiquetas ni inicia reproducción.';
  const failure=document.createElement('p');failure.id='profiles-error';failure.setAttribute('role','alert');
  const retry=document.createElement('button');retry.id='profiles-retry';retry.type='button';retry.className='button subtle';retry.textContent='Completar / reintentar perfiles';retry.addEventListener('click',()=>{if(!retry.disabled&&host.canAct())host.retry();});
  section.append(summary,hint,failure,retry);root.replaceChildren(section);
  return(status,stale,pending,error)=>{summary.textContent=profileSummary(status,stale,pending);failure.textContent=error;failure.hidden=!error;retry.disabled=!host.canAct()||pending||stale||status?.totalTracks===0||status?.state==='complete';};
}
