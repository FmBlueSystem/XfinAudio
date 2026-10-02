import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,rm,stat,symlink,unlink,realpath} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {audioResponse}=require('../.out/main/audio.js');
const url='xfin-audio://track/'+ 'a'.repeat(64);
test('authorized audio serves streamed bytes, suffix ranges, HEAD and 416', async()=>{
 const dir=await realpath(await mkdtemp(join(tmpdir(),'xfin-audio-')));const path=dir+'/audio.flac';await writeFile(path,'0123456789');
 const identity=await stat(path,{bigint:true});
 const resolver=async()=>({path,mime:'audio/flac',identity:{device:String(identity.dev),inode:String(identity.ino),size:String(identity.size),mtimeNs:String(identity.mtimeNs)}});
 try{
  const all=await audioResponse(new Request(url),resolver);assert.equal(all.status,200);assert.equal(await all.text(),'0123456789');
  const partial=await audioResponse(new Request(url,{headers:{range:'bytes=2-5'}}),resolver);assert.equal(partial.status,206);assert.equal(partial.headers.get('content-range'),'bytes 2-5/10');assert.equal(await partial.text(),'2345');
  const suffix=await audioResponse(new Request(url,{headers:{range:'bytes=-3'}}),resolver);assert.equal(await suffix.text(),'789');
  const head=await audioResponse(new Request(url,{method:'HEAD'}),resolver);assert.equal(head.headers.get('content-length'),'10');assert.equal(await head.text(),'');
  const bad=await audioResponse(new Request(url,{headers:{range:'bytes=10-'}}),resolver);assert.equal(bad.status,416);assert.equal(bad.headers.get('content-range'),'bytes */10');
 }finally{await rm(dir,{recursive:true});}
});
test('unknown identities and arbitrary paths are never opened', async()=>{
 let calls=0;const resolver=async()=>{calls++;throw new Error('unknown track');};
 for(const address of ['xfin-audio://track/../../etc/passwd','file:///etc/passwd',url+'?path=/etc/passwd'])assert.equal((await audioResponse(new Request(address),resolver)).status,403);
 assert.equal(calls,0);assert.equal((await audioResponse(new Request(url),resolver)).status,404);
});

test('rejects a file replaced after authorization with a symlink or different inode',async()=>{
 const dir=await realpath(await mkdtemp(join(tmpdir(),'xfin-race-')));const path=dir+'/track.flac';const outside=dir+'/private.txt';
 await writeFile(path,'SAFE');await writeFile(outside,'OUTSIDE');const original=await stat(path,{bigint:true});
 const identity={path,mime:'audio/flac',identity:{device:String(original.dev),inode:String(original.ino),size:String(original.size),mtimeNs:String(original.mtimeNs)}};
 try{
  const replaced=await audioResponse(new Request(url),async()=>{await unlink(path);await symlink(outside,path);return identity;});
  assert.notEqual(replaced.status,200);assert.equal(await replaced.text(),'');
  await unlink(path);await writeFile(path,'DIFFERENT');
  const swapped=await audioResponse(new Request(url),async()=>identity);assert.equal(swapped.status,403);
 }finally{await rm(dir,{recursive:true});}
});
