import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {validateRequest}=require('../.out/main/security.js');
const editId='12345678-1234-1234-1234-123456789abc',track='a'.repeat(64);
test('saved editor exposes bounded named operations, never filesystem paths',()=>{
 assert.deepEqual(validateRequest('renamePlaylist',{playlistId:'1',name:'Warm up'}),{playlistId:'1',name:'Warm up'});
 for(const method of ['duplicatePlaylist','openPlaylistEditor'])assert.deepEqual(validateRequest(method,{playlistId:'1'}),{playlistId:'1'});
 assert.deepEqual(validateRequest('savePlaylistEdit',{editId,name:'Set',trackIds:[track,track]}),{editId,name:'Set',trackIds:[track,track]});
 assert.deepEqual(validateRequest('previewPlaylistEdit',{editId,trackIds:[track],request:'sube la energía'}),{editId,trackIds:[track],request:'sube la energía'});
 assert.deepEqual(validateRequest('discardPlaylistEdit',{editId}),{editId});
 assert.deepEqual(validateRequest('setDraftDirty',{dirty:true}),{dirty:true});
});
test('editor rejects unknown fields, oversized orders, invalid identities and ambiguous dirty state',()=>{
 for(const params of [{editId:'../x',name:'Set',trackIds:[track]},{editId,name:'Set',trackIds:Array(501).fill(track)},{editId,name:'Set',trackIds:['/etc/passwd']},{editId,name:'Set',trackIds:[track],path:'/tmp/file'},{editId,trackIds:[track]}])assert.throws(()=>validateRequest('savePlaylistEdit',params));
 for(const params of [{editId,trackIds:[track],request:''},{editId,trackIds:[track],request:'x'.repeat(2001)}])assert.throws(()=>validateRequest('previewPlaylistEdit',params));
 for(const dirty of ['true',1,null])assert.throws(()=>validateRequest('setDraftDirty',{dirty}));
 assert.throws(()=>validateRequest('renamePlaylist',{playlistId:'1'}));
 assert.throws(()=>validateRequest('duplicatePlaylist',{playlistId:'0'}));
});
