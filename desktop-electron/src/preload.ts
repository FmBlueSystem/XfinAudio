// Sandboxed preloads (sandbox: true) can only require the electron built-in;
// a relative require throws before exposeInMainWorld runs. The launch guard
// lives in the unsandboxed main process via ./electron-shim.
import {contextBridge,ipcRenderer} from 'electron';
const invoke = (method:string,params?:unknown)=>ipcRenderer.invoke('xfin:action',method,params);
contextBridge.exposeInMainWorld('xfin',Object.freeze({
  previewLegacyImport:()=>invoke('previewLegacyImport'),applyLegacyImport:(params:unknown)=>invoke('applyLegacyImport',params),discardLegacyImport:(params:unknown)=>invoke('discardLegacyImport',params),
  reviewDetails:(params:unknown)=>invoke('reviewDetails',params),reviewCompare:(params:unknown)=>invoke('reviewCompare',params),reviewRemove:(params:unknown)=>invoke('reviewRemove',params),reviewReorder:(params:unknown)=>invoke('reviewReorder',params),
  prepSettings:()=>invoke('prepSettings'),savePrepSettings:(params:unknown)=>invoke('savePrepSettings',params),
  queryLibrary:(params:unknown)=>invoke('queryLibrary',params),searchPlaylists:(params:unknown)=>invoke('searchPlaylists',params),comparePlaylists:(params:unknown)=>invoke('comparePlaylists',params),
  deletePlaylist:(params:unknown)=>invoke('deletePlaylist',params),listDeletedPlaylists:()=>invoke('listDeletedPlaylists'),restorePlaylist:(params:unknown)=>invoke('restorePlaylist',params),
  getProfileStatus:()=>invoke('getProfileStatus'),completeProfiles:()=>invoke('completeProfiles'),
  getProfileSettings:()=>invoke('getProfileSettings'),saveProfileSettings:(params:unknown)=>invoke('saveProfileSettings',params),
  getAiStatus:()=>invoke('getAiStatus'),saveAiSettings:(params:unknown)=>invoke('saveAiSettings',params),
  chooseAiCredential:(params:unknown)=>invoke('chooseAiCredential',params),clearAiCredential:(params:unknown)=>invoke('clearAiCredential',params),
  prepareAiRequest:(params:unknown)=>invoke('prepareAiRequest',params),inspectAiPayload:(params:unknown)=>invoke('inspectAiPayload',params),runAiRequest:(params:unknown)=>invoke('runAiRequest',params),applyAiSuggestion:(params:unknown)=>invoke('applyAiSuggestion',params),
  revealLoudnessBackups:()=>invoke('revealLoudnessBackups'),
  getLoudnessStatus:()=>invoke('getLoudnessStatus'),saveLoudnessSettings:(params:unknown)=>invoke('saveLoudnessSettings',params),
  previewLoudness:(params:unknown)=>invoke('previewLoudness',params),runLoudness:(params:unknown)=>invoke('runLoudness',params),
  getPreferences:()=>invoke('getPreferences'),savePreferences:(params:unknown)=>invoke('savePreferences',params),
  getLibraryStatus:()=>invoke('getLibraryStatus'),rescanLibrary:()=>invoke('rescanLibrary'),
  onLibraryStatus:(callback:(value:unknown)=>void)=>{
    if(typeof callback!=='function')throw new Error('Callback required');
    const listener=(_event:Electron.IpcRendererEvent,value:unknown)=>callback(value);
    ipcRenderer.on('xfin:library-status',listener);return()=>ipcRenderer.removeListener('xfin:library-status',listener);
  },
  openLive:(params:unknown)=>invoke('openLive',params),getLiveStatus:(params:unknown)=>invoke('getLiveStatus',params),
  advanceLive:(params:unknown)=>invoke('advanceLive',params),clearLive:(params:unknown)=>invoke('clearLive',params),
  chooseSeratoDestination:()=>invoke('chooseSeratoDestination'),previewSeratoExport:(params:unknown)=>invoke('previewSeratoExport',params),
  commitSeratoExport:(params:unknown)=>invoke('commitSeratoExport',params),revealSeratoExport:(params:unknown)=>invoke('revealSeratoExport',params),
  chooseLibrary:()=>invoke('chooseLibrary'),listLibrary:()=>invoke('listLibrary'),
  getMetadataReport:()=>invoke('getMetadataReport'),
  getPrepCatalog:()=>invoke('getPrepCatalog'),selectPrepVariant:(params:unknown)=>invoke('selectPrepVariant',params),
  generatePrep:(params:unknown)=>invoke('generatePrep',params),savePlaylist:(params:unknown)=>invoke('savePlaylist',params),
  renamePlaylist:(params:unknown)=>invoke('renamePlaylist',params),duplicatePlaylist:(params:unknown)=>invoke('duplicatePlaylist',params),
  openPlaylistEditor:(params:unknown)=>invoke('openPlaylistEditor',params),previewPlaylistEdit:(params:unknown)=>invoke('previewPlaylistEdit',params),
  savePlaylistEdit:(params:unknown)=>invoke('savePlaylistEdit',params),savePlaylistImprovement:(params:unknown)=>invoke('savePlaylistImprovement',params),discardPlaylistEdit:(params:unknown)=>invoke('discardPlaylistEdit',params),
  setDraftDirty:(dirty:boolean)=>invoke('setDraftDirty',{dirty}),
  listPlaylists:()=>invoke('listPlaylists'),openPlaylist:(params:unknown)=>invoke('openPlaylist',params),
  cancelCurrent:()=>invoke('cancelCurrent'),
  onProgress:(callback:(value:unknown)=>void)=>{
    if(typeof callback!=='function')throw new Error('Callback required');
    const listener=(_event:Electron.IpcRendererEvent,value:unknown)=>callback(value);
    ipcRenderer.on('xfin:progress',listener);return()=>ipcRenderer.removeListener('xfin:progress',listener);
  },
}));
