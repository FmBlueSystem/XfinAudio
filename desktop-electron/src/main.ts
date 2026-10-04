import {app,BrowserWindow,dialog,ipcMain,protocol,session,shell} from 'electron';
import path from 'node:path';
import {readFile} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import {PythonBridge} from './bridge';
import {coreEnvironment} from './core-environment';
import {APP_URL,CSP,assetPath,isTrustedSender,validateRequest} from './security';
import {audioResponse} from './audio';
import {configureStorage} from './storage';
import {CloseFlow} from './close-flow';
import {SeratoHost} from './serato-host';
import {revealLoudnessBackups} from './loudness-backups';
import {OptionalAiHost} from './optional-ai-host';
import {LoudnessHost} from './loudness-host';
import {LegacyImportHost} from './legacy-import-host';
import {OfflineHost} from './offline-host';
import {ProfilesHost,profileProgress} from './profiles-host';
import {LibraryHost} from './library-host';
import {LibraryWatch} from './library-watch';
import {createNativeWatchFactory} from './native-watch';
app.setName('XfinAudio Next');
const dataDir=configureStorage(app,process.env.XFIN_DATA_DIR);
const ownsInstance=app.requestSingleInstanceLock();
if(!ownsInstance)app.quit();
protocol.registerSchemesAsPrivileged([
  {scheme:'xfin-app',privileges:{standard:true,secure:true,supportFetchAPI:true}},
  {scheme:'xfin-audio',privileges:{standard:true,secure:true,stream:true,supportFetchAPI:true}},
]);
let window:BrowserWindow|null=null;
let core:PythonBridge;
let current:{id:string;method:string}|null=null;
let draftDirty=false;
let dialogOpen=false;
const libraryHost=new LibraryHost(new LibraryWatch(createNativeWatchFactory(dataDir),status=>{
  if(window&&!window.isDestroyed())window.webContents.send('xfin:library-status',status);
}),run);
const closeFlow=new CloseFlow(
  ()=>draftDirty,
  async()=>{
    const options:Electron.MessageBoxOptions={type:'warning',buttons:['Seguir editando','Descartar y salir'],defaultId:0,cancelId:0,title:'Cambios sin guardar',message:'Hay cambios sin guardar',detail:'Si sales ahora perderás los cambios del borrador. Tus playlists guardadas no se modificarán.'};
    const result=window?await dialog.showMessageBox(window,options):await dialog.showMessageBox(options);
    return result.response===1;
  },
  async()=>{await legacy.shutdown();await profiles.shutdown();await optionalAi.shutdown();await loudness.shutdown();await libraryHost.close();await serato.waitForCommit();await offline.waitForCommit();await core?.close();},
  ()=>app.quit(),
);
const serato=new SeratoHost({
  request:run,
  choose:async()=>{
    const selected=await dialog.showOpenDialog(window!,{title:'Elige la carpeta _Serato_ que contiene Subcrates',properties:['openDirectory']});
    return selected.canceled||selected.filePaths.length!==1?null:selected.filePaths[0];
  },
  confirm:async summary=>{
    const detail=[`Destino: ${path.join(summary.destinationPath,'Subcrates',summary.filename)}`,`${summary.trackCount} pistas en el orden revisado`,summary.backup.required?'Se reemplazará el crate existente y se conservará una copia de seguridad.':'Se creará un crate nuevo.',...summary.warnings].join('\n\n');
    const result=await dialog.showMessageBox(window!,{type:'warning',title:'Confirmar exportación a Serato',message:`¿Exportar ${summary.filename}?`,detail,buttons:['Cancelar','Exportar a Serato'],defaultId:0,cancelId:0,noLink:true});
    return result.response===1;
  },
  reveal:filename=>shell.showItemInFolder(filename),
  isClosing:()=>closeFlow.isClosing,
});
const loudness=new LoudnessHost({
  request:run,
  confirm:async summary=>{
    const detail=[`${summary.trackCount} pistas seleccionadas`,...summary.folders,`Copias de seguridad: ${summary.backupDirectory}`,`Espacio estimado para copias: ${Math.ceil(summary.backupBytes/1024/1024)} MiB`,'El análisis escribirá automáticamente etiquetas de sonoridad y reemplazará los comentarios existentes. No cambia las muestras de audio.'].join('\n\n');
    const result=await dialog.showMessageBox(window!,{type:'warning',title:'Confirmar sonoridad y escritura',message:'¿Analizar y actualizar las pistas seleccionadas?',detail,buttons:['Cancelar','Analizar y actualizar etiquetas'],defaultId:0,cancelId:0,noLink:true});
    return result.response===1;
  },
  cancel:()=>current?.method==='loudness.run'?core.request('cancel',{jobId:current.id}):Promise.resolve({cancelled:false}),
  isClosing:()=>closeFlow.isClosing,
});
const optionalAi=new OptionalAiHost({
  request:run,
  choose:async()=>{const result=await dialog.showOpenDialog(window!,{title:'Selecciona el archivo de credenciales de Nan Builders (no se leerá hasta una petición confirmada)',properties:['openFile','showHiddenFiles']});return result.canceled||result.filePaths.length!==1?null:result.filePaths[0];},
  confirm:async summary=>{
    const detail=[`Destinatario: ${summary.recipient}`,...summary.disclosure,summary.requestPreview,'La petición puede generar consumo en tu proveedor. Cancelar después del envío descarta la respuesta; no puede recuperar los datos ya enviados.'].filter(Boolean).join('\n\n');
    const result=await dialog.showMessageBox(window!,{type:'warning',title:'Confirmar solicitud opcional a Nan Builders',message:'¿Enviar solo esta solicitud?',detail,buttons:['Cancelar','Enviar esta solicitud'],defaultId:0,cancelId:0,noLink:true});return result.response===1;
  },
  cancel:()=>current?.method==='ai.run'?core.request('cancel',{jobId:current.id}):Promise.resolve({cancelled:false}),
  isClosing:()=>closeFlow.isClosing,
});
const legacy=new LegacyImportHost({
  request:run,isClosing:()=>closeFlow.isClosing,canStart:()=>!draftDirty&&!current&&!dialogOpen&&!libraryHost.busy&&!serato.busy&&!optionalAi.busy&&!loudness.busy&&!profiles.busy&&!offline.busy,
  chooseDirectory:async()=>{const selected=await dialog.showOpenDialog(window!,{title:'Elige la carpeta de datos de XfinAudio anterior, con la aplicación cerrada',properties:['openDirectory']});return selected.canceled||selected.filePaths.length!==1?null:selected.filePaths[0];},
  confirm:async preview=>{const detail=[`Origen: ${preview.sourceDirectory}`,`${preview.playlistCount} playlists · ${preview.trackCount} registros · ${preview.referenceCount} referencias`,
    'Cierra la aplicación anterior y deja que finalice sus escrituras antes de continuar. Solo se admite el esquema compatible actual y un perfil nuevo vacío de XfinAudio.',
    'La carpeta original queda intacta y se conserva una copia de respaldo. Solo se importan volumen inicial y cohesión espectral de las preferencias; IA, vigilancia y sonoridad permanecen desactivadas.',
    'Después de importar debes cerrar y volver a abrir XfinAudio. Selecciona explícitamente tus carpetas de música y vuelve a escanear para autorizar sus pistas.'].join('\n\n');
    const result=await dialog.showMessageBox(window!,{type:'warning',title:'Confirmar importación de datos anteriores',message:'¿Importar estos datos en el perfil nuevo?',detail,buttons:['Cancelar','Importar y reiniciar después'],defaultId:0,cancelId:0,noLink:true});return result.response===1;},
});
const offline=new OfflineHost({request:run,isClosing:()=>closeFlow.isClosing,confirm:async preview=>{
  const result=await dialog.showMessageBox(window!,{type:'warning',title:'Eliminar playlist guardada',message:`¿Eliminar «${preview.name}»?`,detail:`${preview.trackCount} pistas en la playlist guardada. Se conservará una copia recuperable en los datos de XfinAudio. No se borrarán archivos de música.`,buttons:['Cancelar','Eliminar playlist'],defaultId:0,cancelId:0,noLink:true});return result.response===1;
}});
const profiles=new ProfilesHost({request:run,cancel:()=>current?.method==='profiles.complete'?core.request('cancel',{jobId:current.id}):Promise.resolve({cancelled:false}),isClosing:()=>closeFlow.isClosing});
const editSnapshot=(value:any)=>({...value,id:String(value.id)});
const summaries=(items:any[])=>items.map(item=>({id:String(item.id),name:item.name,trackCount:item.trackCount,createdAt:item.updatedAt}));
async function run(method:string,params:Record<string,unknown>={}) {
  if(current)throw new Error('Another task is still running');
  const id=randomUUID();current={id,method};
  window?.webContents.send('xfin:progress',{jobId:id,operation:method,phase:'started',message:'Procesando…'});
  try{return await core.request(method,params,id);}finally{if(current?.id===id)current=null;}
}
async function action(method:string,raw:unknown) {
  const params=validateRequest(method,raw);
  if((legacy.busy||offline.busy||profiles.busy||serato.busy||optionalAi.busy||loudness.busy||libraryHost.busy||dialogOpen||current)&&!['setDraftDirty','cancelCurrent','getLibraryStatus'].includes(method))throw new Error('[busy] Another task is still running');
  if(legacy.restartRequired&&method!=='setDraftDirty')throw new Error('[legacy_restart_required] Restart required after import');
  if(closeFlow.isClosing&&method!=='setDraftDirty')throw new Error('La aplicación se está cerrando');
  if(draftDirty&&method==='deletePlaylist')throw new Error('[dirty_saved_draft] Save or discard drafts before deletion');
  if(draftDirty&&['previewLoudness','runLoudness'].includes(method))throw new Error('[dirty_draft] Save or discard drafts before loudness writes');
  switch(method) {
    case 'previewLegacyImport':return legacy.preview();
    case 'applyLegacyImport':try{return await legacy.apply(params.previewId as string);}finally{if(legacy.restartRequired)await libraryHost.close();}
    case 'discardLegacyImport':return legacy.discard(params.previewId as string);
    case 'reviewDetails':return run('review.details',params);
    case 'reviewCompare':return run('review.compare',params);
    case 'reviewRemove':return run('review.remove',params);
    case 'reviewReorder':return run('review.reorder',params);
    case 'prepSettings':return run('prep.settings.get');
    case 'savePrepSettings':return run('prep.settings.update',params);
    case 'queryLibrary':return offline.query(params);
    case 'searchPlaylists':return offline.search(params.request as string);
    case 'comparePlaylists':return offline.compare(params.playlistIds as string[]);
    case 'deletePlaylist':return offline.delete(params.playlistId as string);
    case 'listDeletedPlaylists':return offline.deleted();
    case 'restorePlaylist':return offline.restore(params.deletionId as string);
    case 'getProfileStatus':return run('profiles.status');
    case 'completeProfiles':return profiles.complete();
    case 'getProfileSettings':return run('profiles.settings.get');
    case 'saveProfileSettings':return run('profiles.settings.update',params);
    case 'getAiStatus':return run('ai.status');
    case 'saveAiSettings':return run('ai.settings.update',params);
    case 'chooseAiCredential':return optionalAi.choose(params);
    case 'clearAiCredential':return run('ai.credential.set',{revision:params.revision,path:null});
    case 'prepareAiRequest':return optionalAi.prepare(params);
    case 'runAiRequest':return optionalAi.ask(params.previewId as string);
    case 'applyAiSuggestion':return run('ai.apply',params);
    case 'revealLoudnessBackups':return revealLoudnessBackups(dataDir,filename=>shell.showItemInFolder(filename));
    case 'getLoudnessStatus':return run('loudness.status');
    case 'saveLoudnessSettings':return run('loudness.settings.update',params);
    case 'previewLoudness':return loudness.preview(params);
    case 'runLoudness':return loudness.run(params.previewId as string);
    case 'getPreferences':return run('settings.get');
    case 'savePreferences':return libraryHost.savePreferences(params);
    case 'getLibraryStatus':return libraryHost.status;
    case 'rescanLibrary':return libraryHost.rescan();
    case 'openLive':return run('live.open',params);
    case 'getLiveStatus':return run('live.status',params);
    case 'advanceLive':return run('live.next',params);
    case 'clearLive':return run('live.clear',params);
    case 'chooseSeratoDestination':return serato.choose();
    case 'previewSeratoExport':return serato.preview(params);
    case 'commitSeratoExport':return serato.commit(params.previewId as string);
    case 'revealSeratoExport':return serato.reveal(params.receiptId as string);
    case 'setDraftDirty':draftDirty=params.dirty as boolean;return {dirty:draftDirty};
    case 'renamePlaylist':return summaries([await run('playlist.rename',{...params,playlistId:Number(params.playlistId)})])[0];
    case 'duplicatePlaylist':return summaries([await run('playlist.duplicate',{playlistId:Number(params.playlistId)})])[0];
    case 'openPlaylistEditor':return editSnapshot(await run('playlist.edit.open',{playlistId:Number(params.playlistId)}));
    case 'previewPlaylistEdit':return run('playlist.edit.preview',params);
    case 'savePlaylistEdit':return editSnapshot(await run('playlist.edit.save',params));
    case 'discardPlaylistEdit':return editSnapshot(await run('playlist.edit.discard',params));
    case 'chooseLibrary': {
      if(dialogOpen||current)throw new Error('Another task is still running');
      dialogOpen=true;
      try {
        const selected=await dialog.showOpenDialog(window!,{title:'Elige una carpeta de música',properties:['openDirectory']});
        if(selected.canceled||selected.filePaths.length!==1)return null;
        return await libraryHost.scan(selected.filePaths[0]);
      }finally{dialogOpen=false;}
    }
    case 'listLibrary': {const result=await core.request('library.list');return {...result,count:result.tracks.length};}
    case 'getMetadataReport':return run('metadata.report');
    case 'getPrepCatalog':return core.request('prep.catalog');
    case 'selectPrepVariant':return run('prep.select',params);
    case 'generatePrep':return run('prep.generate',params);
    case 'savePlaylist':return summaries([await run('playlist.save',params)])[0];
    case 'listPlaylists':return summaries((await core.request('playlist.list')).playlists);
    case 'openPlaylist': {
      const result=await run('playlist.open',{playlistId:Number(params.playlistId)});
      return {...result,savedPlaylistId:String(result.id),reviewId:'',variant:'saved',canSave:false,warnings:result.missingTrackCount?[`${result.missingTrackCount} pistas no disponibles`]:[],blockers:[],readiness:'needs_review'};
    }
    case 'cancelCurrent':if(profiles.busy)return profiles.cancel();if(optionalAi.asking)return optionalAi.cancel();if(loudness.busy)return loudness.cancel();return current&&['library.scan','library.rescan','prep.generate','prep.select'].includes(current.method)?core.request('cancel',{jobId:current.id}):{cancelled:false};
    default:throw new Error('Unsupported action');
  }
}
async function start() {
  const repoRoot=path.resolve(__dirname,'../../..');
  const env=coreEnvironment(process.env);
  let executable=path.join(process.resourcesPath,'core','xfinaudio-core');
  let args=['--data-dir',dataDir];
  if(!app.isPackaged){
    executable=process.env.XFIN_PYTHON??path.join(repoRoot,'.venv-headless','bin','python');
    args=['-m','xfinaudio.headless',...args];env.PYTHONPATH=path.join(repoRoot,'src');
  }
  core=new PythonBridge(executable,args,env);
  const isolated=session.fromPartition('xfin-offline');
  isolated.setPermissionRequestHandler((_contents,_permission,callback)=>callback(false));
  isolated.setPermissionCheckHandler(()=>false);
  isolated.webRequest.onBeforeRequest((details,callback)=>{
    const url=new URL(details.url);callback({cancel:!['xfin-app:','xfin-audio:'].includes(url.protocol)});
  });
  isolated.on('will-download',(event)=>event.preventDefault());
  const rendererRoot=path.resolve(__dirname,'../renderer');
  isolated.protocol.handle('xfin-app',async request=>{
    try{
      if(request.method!=='GET')return new Response(null,{status:405});
      const filename=assetPath(request.url,rendererRoot);
      const mime=filename.endsWith('.html')?'text/html':filename.endsWith('.css')?'text/css':'text/javascript';
      return new Response(await readFile(filename),{headers:{'Content-Type':mime,'Content-Security-Policy':CSP,'X-Content-Type-Options':'nosniff'}});
    }catch{return new Response(null,{status:404});}
  });
  isolated.protocol.handle('xfin-audio',request=>legacy.restartRequired||legacy.busy?new Response(null,{status:409}):audioResponse(request,id=>core.request('track.resolve',{trackId:id}))); 
  window=new BrowserWindow({width:1440,height:940,minWidth:900,minHeight:650,backgroundColor:'#10151b',show:false,webPreferences:{
    preload:path.join(__dirname,'preload.js'),session:isolated,nodeIntegration:false,contextIsolation:true,sandbox:true,
    webSecurity:true,allowRunningInsecureContent:false,webviewTag:false,devTools:!app.isPackaged,
  }});
  window.removeMenu();
  window.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  window.webContents.on('will-navigate',(event)=>event.preventDefault());
  window.webContents.on('will-attach-webview',(event)=>event.preventDefault());
  ipcMain.handle('xfin:action',(event,method,params)=>{
    if(event.sender!==window?.webContents||!event.senderFrame||event.senderFrame!==window.webContents.mainFrame||!isTrustedSender(event.senderFrame.url))throw new Error('Untrusted caller');
    return action(method,params);
  });
  core.on('progress',message=>{
    const job=current;
    if(!job||message.jobId!==job.id)return;
    const data=message.data??{};
    if(job.method==='profiles.complete'){const progress=profileProgress(data);if(progress)window?.webContents.send('xfin:progress',{jobId:message.jobId,operation:job.method,...progress,current:progress.processedCount,total:progress.totalCount});return;}
    if(job.method==='loudness.run'&&data.phase==='loudness_write'&&Array.isArray(data.trackIds)&&data.trackIds.length<=2){
      for(const trackId of data.trackIds)if(typeof trackId==='string'&&/^[a-f0-9]{64}$/.test(trackId))void core.request('track.resolve',{trackId}).then(track=>libraryHost.suppressPaths([track.path],5000)).catch(error=>console.error('Owned-write observation suppression unavailable',error));
      return;
    }
    window?.webContents.send('xfin:progress',{jobId:message.jobId,operation:job.method,phase:data.phase,current:data.processedCount,total:data.totalCount,message:data.fileName??data.message??data.phase});
  });
  core.on('stopped',message=>{void libraryHost.close();if(window&&!window.isDestroyed())window.webContents.send('xfin:progress',{jobId:'',operation:'core',phase:'error',message});});
  window.once('ready-to-show',()=>window?.show());
  window.on('close',event=>{if(!closeFlow.readyToQuit){event.preventDefault();void closeFlow.request().catch(error=>console.error(error));}});
  window.on('closed',()=>{window=null;});
  await libraryHost.initialize();
  await window.loadURL(APP_URL);
}
app.on('before-quit',event=>{
  if(closeFlow.readyToQuit)return;
  event.preventDefault();
  void closeFlow.request().catch(error=>console.error(error));
});
app.on('window-all-closed',()=>app.quit());
app.on('second-instance',()=>{if(window){if(window.isMinimized())window.restore();window.focus();}});
if(ownsInstance)app.whenReady().then(start).catch(error=>{console.error(error);app.quit();});
