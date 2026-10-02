import path from 'node:path';
import {lstat,realpath} from 'node:fs/promises';
/** Reveal only the fixed app-owned recovery directory, never a renderer-provided path. */
export async function revealLoudnessBackups(dataDir:string,reveal:(filename:string)=>void):Promise<{found:boolean}> {
  const folder=path.join(dataDir,'loudness-backups');
  let info;
  try{info=await lstat(folder);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return {found:false};throw error;}
  if(!info.isDirectory()||info.isSymbolicLink()||await realpath(folder)!==folder)throw new Error('[loudness_unavailable] Recovery directory unavailable');
  reveal(folder);return {found:true};
}
