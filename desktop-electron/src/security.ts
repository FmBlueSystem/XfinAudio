import path from 'node:path';
import {REVIEW_CONTROL_FIELDS,validateReviewControlRequest} from './review-security';
import {OFFLINE_FIELDS,validateOfflineRequest} from './offline-security';

export const APP_URL = 'xfin-app://ui/index.html';
export const CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; media-src xfin-audio:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'";
export function isTrustedSender(url: string): boolean { return url === APP_URL || url.startsWith(APP_URL + '#'); }
export function assertTrackId(id: unknown): asserts id is string {
  if (typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id)) throw new Error('Invalid track identity');
}
export function assetPath(raw: string, root: string): string {
  const url = new URL(raw);
  if (url.protocol !== 'xfin-app:' || url.host !== 'ui' || url.search || url.hash) throw new Error('Asset denied');
  const relative = decodeURIComponent(url.pathname).replace(/^\//, '');
  if (!/^[a-zA-Z0-9_/-]+\.(html|css|js)$/.test(relative) || relative.split('/').includes('..')) throw new Error('Asset denied');
  const target = path.resolve(root, relative);
  if (!target.startsWith(path.resolve(root) + path.sep)) throw new Error('Asset denied');
  return target;
}
export function parseRange(header: string | null, size: number): {start:number;end:number;status:number} {
  if (!Number.isSafeInteger(size) || size < 0) throw new Error('Invalid size');
  if (!header) return {start:0,end:size-1,status:200};
  const match = /^bytes=(\d*)-(\d*)$/.exec(header);
  if (!match || (!match[1] && !match[2]) || size === 0) throw new Error('Unsatisfiable range');
  const left = match[1] ? Number(match[1]) : null;
  const right = match[2] ? Number(match[2]) : null;
  if ((left !== null && !Number.isSafeInteger(left)) || (right !== null && !Number.isSafeInteger(right))) throw new Error('Invalid range');
  const start = left === null ? Math.max(0, size - (right ?? 0)) : left;
  const end = left === null || right === null ? size-1 : Math.min(right,size-1);
  if (start < 0 || start >= size || end < start) throw new Error('Unsatisfiable range');
  return {start,end,status:206};
}
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
export function validateRequest(method:string, value:unknown): Record<string,unknown> {
  const fields:Record<string,string[]> = {
    ...OFFLINE_FIELDS,...REVIEW_CONTROL_FIELDS,
    previewLegacyImport:[],applyLegacyImport:['previewId'],discardLegacyImport:['previewId'],
    getProfileStatus:[],completeProfiles:[],getProfileSettings:[],saveProfileSettings:['revision','spectralCohesion'],
    getAiStatus:[],saveAiSettings:['revision','enabled'],chooseAiCredential:['revision'],clearAiCredential:['revision'],prepareAiRequest:['surface','request','context'],runAiRequest:['previewId'],applyAiSuggestion:['resultId'],
    getLoudnessStatus:[],revealLoudnessBackups:[],saveLoudnessSettings:['revision','enabled','targetLufs','toleranceLu'],previewLoudness:['trackIds','force'],runLoudness:['previewId'],
    getPreferences:[],savePreferences:['revision','previewVolume','watchLibrary'],getLibraryStatus:[],rescanLibrary:[],
    openLive:['reviewId'],getLiveStatus:['sessionId'],advanceLive:['sessionId','revision','trackId'],clearLive:['sessionId'],
    chooseSeratoDestination:[],previewSeratoExport:['source','destinationId','name'],commitSeratoExport:['previewId'],revealSeratoExport:['receiptId'],
    chooseLibrary:[],listLibrary:[],getMetadataReport:[],getPrepCatalog:[],selectPrepVariant:['planId','variant'],
    generatePrep:['targetTrackCount','name','strategy','targetMinutes','slotRole','genreFocus','startTrackId','endTrackId','requiredTrackIds','excludedTrackIds'],
    savePlaylist:['name','reviewId'],listPlaylists:[],renamePlaylist:['playlistId','name'],duplicatePlaylist:['playlistId'],openPlaylistEditor:['playlistId'],
    previewPlaylistEdit:['editId','trackIds','request'],savePlaylistEdit:['editId','name','trackIds'],discardPlaylistEdit:['editId'],setDraftDirty:['dirty'],openPlaylist:['playlistId'],cancelCurrent:[],
  };
  if (!Object.hasOwn(fields,method)) throw new Error('Unsupported action');
  if (value === undefined) value = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid parameters');
  const params = value as Record<string,unknown>;
  if (Object.keys(params).some(key=>!fields[method].includes(key))) throw new Error('Unexpected parameter');
  if (method === 'generatePrep' && (!Number.isInteger(params.targetTrackCount) || Number(params.targetTrackCount)<2 || Number(params.targetTrackCount)>100)) throw new Error('Choose 2–100 tracks');
  if(method === 'generatePrep') validatePrepIntent(params);
  if(method === 'selectPrepVariant' && (typeof params.planId !== 'string' || !uuid.test(params.planId) || typeof params.variant!=='string' || !['safe','balanced','adventurous'].includes(params.variant))) throw new Error('Invalid Prep plan or variant');
  if(method==='savePreferences'&&(typeof params.revision!=='string'||!/^[a-f0-9]{64}$/.test(params.revision)||typeof params.previewVolume!=='number'||!Number.isFinite(params.previewVolume)||params.previewVolume<0||params.previewVolume>1||typeof params.watchLibrary!=='boolean'))throw new Error('Invalid preferences');
  if(method==='saveProfileSettings'&&(typeof params.revision!=='string'||!/^[a-f0-9]{64}$/.test(params.revision)||typeof params.spectralCohesion!=='number'||!Number.isFinite(params.spectralCohesion)||params.spectralCohesion<0||params.spectralCohesion>1))throw new Error('Invalid profile preferences');
  if(['applyLegacyImport','discardLegacyImport'].includes(method)&&(typeof params.previewId!=='string'||!/^[a-f0-9]{32}$/.test(params.previewId)))throw new Error('Invalid legacy import preview');
  validateReviewControlRequest(method,params);
  validateOfflineRequest(method,params);
  validateAiRequest(method,params);
  validateLoudnessRequest(method,params);
  validateEditorRequest(method,params);
  validateSeratoRequest(method,params);
  validateLiveRequest(method,params);
  if ('name' in params && (typeof params.name !== 'string' || !params.name.trim() || params.name.length>200 || /[\x00-\x1f]/.test(params.name))) throw new Error('Invalid name');
  if (method === 'savePlaylist' && (typeof params.name !== 'string' || typeof params.reviewId !== 'string' || !uuid.test(params.reviewId))) throw new Error('Invalid review');
  if (['openPlaylist','openPlaylistEditor','renamePlaylist','duplicatePlaylist'].includes(method) && (typeof params.playlistId !== 'string' || !/^[1-9]\d{0,14}$/.test(params.playlistId))) throw new Error('Invalid playlist');
  return params;
}

function validatePrepIntent(params:Record<string,unknown>):void {
  if('strategy' in params && (typeof params.strategy!=='string'||!/^[a-z][a-z0-9_]{0,49}$/.test(params.strategy)))throw new Error('Invalid strategy');
  if('targetMinutes' in params && (typeof params.targetMinutes!=='number'||!Number.isFinite(params.targetMinutes)||params.targetMinutes<=0||params.targetMinutes>600))throw new Error('Choose a duration greater than zero and at most 600 minutes');
  if('slotRole' in params && params.slotRole!==null && (typeof params.slotRole!=='string'||!['warmup','peak_time','chill'].includes(params.slotRole)))throw new Error('Invalid slot role');
  if('genreFocus' in params && (typeof params.genreFocus!=='string'||params.genreFocus.length>100||/[\x00-\x1f]/.test(params.genreFocus)))throw new Error('Invalid genre');
  for(const name of ['startTrackId','endTrackId'])if(name in params)assertTrackId(params[name]);
  for(const name of ['requiredTrackIds','excludedTrackIds']) {
    if(!(name in params))continue;
    const ids=params[name];
    if(!Array.isArray(ids)||ids.length>100||new Set(ids).size!==ids.length)throw new Error('Invalid track selection');
    ids.forEach(assertTrackId);
  }
  const required=(params.requiredTrackIds??[]) as string[];
  const excluded=(params.excludedTrackIds??[]) as string[];
  if(required.some(id=>excluded.includes(id))||excluded.includes(String(params.startTrackId))||excluded.includes(String(params.endTrackId)))throw new Error('Required tracks cannot be excluded');
  const protectedIds=new Set([...required,...(params.startTrackId?[String(params.startTrackId)]:[]),...(params.endTrackId?[String(params.endTrackId)]:[])]);
  if(protectedIds.size>Number(params.targetTrackCount))throw new Error('The requested count must include every required track');
  if(params.startTrackId&&params.startTrackId===params.endTrackId)throw new Error('Opening and closing tracks must differ');
}

function validateEditorRequest(method:string,params:Record<string,unknown>):void {
  if(['previewPlaylistEdit','savePlaylistEdit','discardPlaylistEdit'].includes(method) && (typeof params.editId!=='string'||!uuid.test(params.editId)))throw new Error('Invalid edit session');
  if(['renamePlaylist','savePlaylistEdit'].includes(method) && typeof params.name!=='string')throw new Error('A playlist name is required');
  if(['previewPlaylistEdit','savePlaylistEdit'].includes(method)) {
    if(!Array.isArray(params.trackIds)||params.trackIds.length>500)throw new Error('Choose at most 500 track references');
    params.trackIds.forEach(assertTrackId);
  }
  if(method==='previewPlaylistEdit' && (typeof params.request!=='string'||!params.request.trim()||params.request.length>2000||/[\x00-\x1f]/.test(params.request)))throw new Error('Invalid edit request');
  if(method==='setDraftDirty' && typeof params.dirty!=='boolean')throw new Error('Invalid draft state');
}

function validateSeratoRequest(method:string,params:Record<string,unknown>):void {
  const validToken=(value:unknown)=>typeof value==='string'&&uuid.test(value);
  if(method==='commitSeratoExport'&&!validToken(params.previewId))throw new Error('Invalid export preview');
  if(method==='revealSeratoExport'&&!validToken(params.receiptId))throw new Error('Invalid export receipt');
  if(method!=='previewSeratoExport')return;
  if(!validToken(params.destinationId))throw new Error('Invalid Serato destination');
  const source=params.source;
  if(!source||typeof source!=='object'||Array.isArray(source))throw new Error('Invalid export source');
  const item=source as Record<string,unknown>;
  const fields=item.kind==='review'?['kind','reviewId']:item.kind==='saved'?['kind','playlistId']:item.kind==='metadata'?['kind','status','missingField','trackIds']:[];
  if(!fields.length||Object.keys(item).length!==fields.length||Object.keys(item).some(key=>!fields.includes(key)))throw new Error('Invalid export source');
  if(item.kind==='metadata'){
    if(!['complete','incomplete'].includes(String(item.status))||(item.missingField!==null&&!['bpm','camelot_key','energy_level'].includes(String(item.missingField)))||(item.status==='complete'&&item.missingField!==null)||!Array.isArray(item.trackIds)||item.trackIds.length<1||item.trackIds.length>500||new Set(item.trackIds).size!==item.trackIds.length)throw new Error('Invalid metadata worklist');
    item.trackIds.forEach(assertTrackId);
  }else if(item.kind==='review'?!validToken(item.reviewId):typeof item.playlistId!=='string'||!/^[1-9]\d{0,14}$/.test(item.playlistId))throw new Error('Invalid export source');
  const name=params.name;
  if(typeof name!=='string'||!name.trim()||['.','..'].includes(name.trim())||name.length>200||/[\/\\:\p{C}]/u.test(name)||Buffer.byteLength(name.trim()+'.crate','utf8')>240)throw new Error('Invalid crate name');
}

function validateLiveRequest(method:string,params:Record<string,unknown>):void {
  if(!['openLive','getLiveStatus','advanceLive','clearLive'].includes(method))return;
  const value=method==='openLive'?params.reviewId:params.sessionId;
  if(typeof value!=='string'||!uuid.test(value))throw new Error('Invalid Live identity');
  if(method==='advanceLive') {
    assertTrackId(params.trackId);
    if(!Number.isInteger(params.revision)||Number(params.revision)<0||Number(params.revision)>500)throw new Error('Invalid Live revision');
  }
}

function validateLoudnessRequest(method:string,params:Record<string,unknown>):void {
  if(method==='saveLoudnessSettings') {
    if(typeof params.revision!=='string'||!/^[a-f0-9]{64}$/.test(params.revision)||typeof params.enabled!=='boolean'||
      typeof params.targetLufs!=='number'||!Number.isFinite(params.targetLufs)||params.targetLufs< -30||params.targetLufs>0||
      typeof params.toleranceLu!=='number'||!Number.isFinite(params.toleranceLu)||params.toleranceLu<0||params.toleranceLu>10)throw new Error('Invalid loudness settings');
  }
  if(method==='runLoudness'&&(typeof params.previewId!=='string'||!uuid.test(params.previewId)))throw new Error('Invalid loudness preview');
  if(method==='previewLoudness') {
    if(!Array.isArray(params.trackIds)||params.trackIds.length<1||params.trackIds.length>500||new Set(params.trackIds).size!==params.trackIds.length||typeof params.force!=='boolean'||(params.force&&params.trackIds.length!==1))throw new Error('Invalid loudness scope');
    params.trackIds.forEach(assertTrackId);
  }
}

function validateAiRequest(method:string,params:Record<string,unknown>):void {
  if(['saveAiSettings','chooseAiCredential','clearAiCredential'].includes(method)&&(typeof params.revision!=='string'||!/^[a-f0-9]{64}$/.test(params.revision)))throw new Error('Invalid settings revision');
  if(method==='saveAiSettings'&&typeof params.enabled!=='boolean')throw new Error('Invalid optional AI setting');
  if(method==='runAiRequest'&&(typeof params.previewId!=='string'||!uuid.test(params.previewId)))throw new Error('Invalid AI preview');
  if(method==='applyAiSuggestion'&&(typeof params.resultId!=='string'||!uuid.test(params.resultId)))throw new Error('Invalid AI result');
  if(method!=='prepareAiRequest')return;
  const {surface,request,context}=params;
  if(typeof surface!=='string'||!['library','prep','review','saved','editor','metadata','live','connection'].includes(surface)||typeof request!=='string'||request.length>2000||request.includes('\0')||!context||typeof context!=='object'||Array.isArray(context))throw new Error('Invalid AI request');
  const item=context as Record<string,unknown>,keys=Object.keys(item).sort().join(',');
  const token=(value:unknown)=>typeof value==='string'&&uuid.test(value);
  if(['library','prep','metadata','connection'].includes(surface)&&keys)throw new Error('Unexpected AI context');
  if(surface==='review'&&(keys!=='reviewId'||!token(item.reviewId)))throw new Error('Invalid review context');
  if(surface==='editor'&&(keys!=='editId'||!token(item.editId)))throw new Error('Invalid editor context');
  if(surface==='live'&&(keys!=='revision,sessionId'||!token(item.sessionId)||!Number.isInteger(item.revision)||Number(item.revision)<0||Number(item.revision)>500))throw new Error('Invalid Live context');
  if(surface==='saved'&&keys){const ids=item.playlistIds;if(keys!=='playlistIds'||!Array.isArray(ids)||ids.length<1||ids.length>200||new Set(ids).size!==ids.length||ids.some(id=>typeof id!=='string'||!/^[1-9]\d{0,14}$/.test(id)))throw new Error('Invalid saved-set scope');}
  if(['library','prep','editor','saved'].includes(surface)?!request.trim():request!==(surface==='connection'?'Reply with OK. XfinAudio connection test.':''))throw new Error('Invalid request text for this surface');
}
