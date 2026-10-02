import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {readFile} from 'node:fs/promises';
const require=createRequire(import.meta.url),{validateRequest}=require('../.out/main/security.js');
test('offline host actions are reachable only through strict public IPC and native saved-delete confirmation',async()=>{
 const actions={queryLibrary:{query:{genre:'House'},sortBy:'title',descending:false,hideDuplicates:true,status:'all'},searchPlaylists:{request:'House'},comparePlaylists:{playlistIds:['1','2']},deletePlaylist:{playlistId:'1'},listDeletedPlaylists:{},restorePlaylist:{deletionId:'12345678-1234-1234-1234-123456789012'}};
 for(const [method,params] of Object.entries(actions)){assert.deepEqual(validateRequest(method,params),params);assert.throws(()=>validateRequest(method,{...params,path:'/private'}));}
 const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8'),preload=await readFile(new URL('../src/preload.ts',import.meta.url),'utf8');
 for(const method of Object.keys(actions)){assert.ok(main.includes(`case '${method}':`));assert.ok(preload.includes(`invoke('${method}'`));}
 assert.match(main,/await offline\.waitForCommit\(\)/);assert.match(main,/offline\.busy/);assert.match(main,/draftDirty.*deletePlaylist/);assert.match(main,/new OfflineHost/);assert.match(main,/preview\.trackCount/);assert.match(main,/preview\.name/);
});
test('metadata worklist export IPC allows exact bounded opaque source only',()=>{
 const source={kind:'metadata',status:'incomplete',missingField:'bpm',trackIds:['a'.repeat(64),'b'.repeat(64)]},params={source,destinationId:'12345678-1234-1234-1234-123456789012',name:'Reparar BPM'};
 assert.deepEqual(validateRequest('previewSeratoExport',params),params);
 for(const patch of [{path:'/private'},{status:'all'},{missingField:'key'},{status:'complete'},{trackIds:[]},{trackIds:['a'.repeat(64),'a'.repeat(64)]},{trackIds:['/private']},{trackIds:Array.from({length:501},(_,i)=>i.toString(16).padStart(64,'0'))}])assert.throws(()=>validateRequest('previewSeratoExport',{...params,source:{...source,...patch}}));
 const {missingField,...missing}=source;assert.throws(()=>validateRequest('previewSeratoExport',{...params,source:missing}));
});
test('generated review and persisted Prep controls use explicit validated IPC routes',async()=>{
 const reviewId='12345678-1234-1234-1234-123456789012',trackId='a'.repeat(64),actions={reviewDetails:{reviewId},reviewCompare:{reviewId,trackId},reviewRemove:{reviewId,trackId},reviewReorder:{reviewId,trackIds:[trackId]},prepSettings:{},savePrepSettings:{revision:'b'.repeat(64),requiredTrackIds:[trackId],excludedTrackIds:[],genreFocus:'House',clearUnavailable:false}};
 for(const [method,params] of Object.entries(actions)){assert.deepEqual(validateRequest(method,params),params);assert.throws(()=>validateRequest(method,{...params,command:'private'}));}
 const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8'),preload=await readFile(new URL('../src/preload.ts',import.meta.url),'utf8');for(const method of Object.keys(actions)){assert.ok(main.includes(`case '${method}':`));assert.ok(preload.includes(`invoke('${method}'`));}
});
test('legacy import uses opaque native-held preview authority and requires one app instance plus restart isolation',async()=>{
 assert.deepEqual(validateRequest('previewLegacyImport'),{});for(const method of ['applyLegacyImport','discardLegacyImport'])assert.deepEqual(validateRequest(method,{previewId:'a'.repeat(32)}),{previewId:'a'.repeat(32)});
 for(const [method,params] of [['previewLegacyImport',{source:'/old'}],['applyLegacyImport',{previewId:'a'.repeat(32),confirmed:true}],['applyLegacyImport',{previewId:'bad'}],['discardLegacyImport',{}]])assert.throws(()=>validateRequest(method,params));
 const main=await readFile(new URL('../src/main.ts',import.meta.url),'utf8'),preload=await readFile(new URL('../src/preload.ts',import.meta.url),'utf8');for(const method of ['previewLegacyImport','applyLegacyImport','discardLegacyImport']){assert.ok(main.includes(`case '${method}':`));assert.ok(preload.includes(`invoke('${method}'`));}
 assert.match(main,/requestSingleInstanceLock\(\)/);assert.match(main,/if\(ownsInstance\)app\.whenReady/);assert.match(main,/await legacy\.shutdown\(\)/);assert.match(main,/legacy\.restartRequired/);assert.match(main,/legacy\.busy/);assert.match(main,/sourceDirectory/);
});
test('restored library worklist controls wrap inside the supported narrow desktop width',async()=>{const css=await readFile(new URL('../renderer/styles.css',import.meta.url),'utf8');assert.match(css,/\.table-toolbar\s*\{[^}]*flex-wrap:\s*wrap/);});
