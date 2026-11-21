/**
 * S14a: the preview setup outlives the window.
 *
 * The app window runs in the in-memory session `xfin-offline`, so `localStorage` is empty
 * after every restart (L29). The host keeps the chosen output, pair and calibration of
 * S11-S13 in one file under the app's data folder instead. The same validator guards the
 * renderer request and the stored file, so no shape can travel one way only, and nothing
 * this module answers ever carries a path.
 */
import path from 'node:path';

export const PREVIEW_SETUP_FILE='preview-setup.json';
/** Anything larger is refused without parsing it: a setup this big is not a setup. */
export const PREVIEW_SETUP_MAX_BYTES=64*1024;
export const MAX_CALIBRATION_LABELS=16,MAX_CALIBRATION_PAIRS=32,MAX_LABEL_LENGTH=200;
const PAIR=/^\d{1,2}-\d{1,2}$/;
const ROLES:ReadonlySet<string>=new Set(['phones','room','silent','channel:1','channel:2','channel:3','channel:4']);
/** A label may not name a prototype member, or the stored object could change its shape. */
const RESERVED:ReadonlySet<string>=new Set(['__proto__','constructor','prototype']);
export interface PreviewSetupOutput {label:string|null;pair:string;}
export interface PreviewSetup {output:PreviewSetupOutput|null;calibration:Record<string,Record<string,string>>;}
export const emptyPreviewSetup=():PreviewSetup=>({output:null,calibration:{}});
const isRecord=(value:unknown):value is Record<string,unknown>=>typeof value==='object'&&value!==null&&!Array.isArray(value);
const isLabel=(value:unknown):value is string=>typeof value==='string'&&value.length>=1&&value.length<=MAX_LABEL_LENGTH;
export function validatePreviewSetup(value:unknown):PreviewSetup {
  if(!isRecord(value))throw new Error('Invalid preview setup');
  const keys=Object.keys(value);
  if(keys.length!==2||!keys.includes('output')||!keys.includes('calibration'))throw new Error('Invalid preview setup');
  return {output:readOutput(value.output),calibration:readCalibration(value.calibration)};
}
/** `null`, or exactly one label (or null) and one pair; the renderer picks both in S11 (c). */
function readOutput(value:unknown):PreviewSetupOutput|null {
  if(value===null)return null;
  if(!isRecord(value))throw new Error('Invalid preview output');
  const keys=Object.keys(value);
  if(keys.length!==2||!keys.includes('label')||!keys.includes('pair'))throw new Error('Invalid preview output');
  const {label,pair}=value;
  if(label!==null&&!isLabel(label))throw new Error('Invalid preview output label');
  if(typeof pair!=='string'||!PAIR.test(pair))throw new Error('Invalid preview output pair');
  return {label,pair};
}
/** S13 (a): one role per pair, at most 16 labels of at most 32 pairs each. */
function readCalibration(value:unknown):Record<string,Record<string,string>> {
  if(!isRecord(value))throw new Error('Invalid preview calibration');
  const labels=Object.keys(value);
  if(labels.length>MAX_CALIBRATION_LABELS)throw new Error('Too many calibrated outputs');
  const calibration:Record<string,Record<string,string>>={};
  for(const label of labels) {
    if(RESERVED.has(label)||!isLabel(label))throw new Error('Invalid calibration output label');
    const roles=value[label];
    if(!isRecord(roles))throw new Error('Invalid calibration pairs');
    const pairNames=Object.keys(roles);
    if(pairNames.length>MAX_CALIBRATION_PAIRS)throw new Error('Too many calibrated pairs');
    const calibrated:Record<string,string>={};
    for(const pair of pairNames) {
      const role=roles[pair];
      if(!PAIR.test(pair)||typeof role!=='string'||!ROLES.has(role))throw new Error('Invalid calibration role');
      calibrated[pair]=role;
    }
    calibration[label]=calibrated;
  }
  return calibration;
}
export interface PreviewSetupFs {
  stat(file:string):Promise<{size:number}>;
  readFile(file:string,encoding:'utf8'):Promise<string>;
  writeFile(file:string,data:string,options:{encoding:'utf8';mode:number}):Promise<void>;
  rename(from:string,to:string):Promise<void>;
  unlink(file:string):Promise<void>;
}
export interface PreviewSetupStore {load:()=>Promise<PreviewSetup>;save:(value:unknown)=>Promise<null>;}
/**
 * One file, written to a sibling temporary file and renamed over it with mode 0600, so a
 * reader never sees a half-written setup and nobody else can read it. Every failure of
 * `load` is the empty setup, because a lost choice is not an error the user must handle;
 * a failed `save` answers nothing and leaves the choice for this session (S14 b).
 */
export function createPreviewSetupStore({directory,fs}:{directory:string;fs:PreviewSetupFs}):PreviewSetupStore {
  const file=path.join(directory,PREVIEW_SETUP_FILE);
  let pending=0;
  return {
    load:async()=>{
      try {
        const info=await fs.stat(file);
        if(!Number.isSafeInteger(info.size)||info.size<=0||info.size>PREVIEW_SETUP_MAX_BYTES)return emptyPreviewSetup();
        const text=await fs.readFile(file,'utf8');
        if(Buffer.byteLength(text,'utf8')>PREVIEW_SETUP_MAX_BYTES)return emptyPreviewSetup();
        return validatePreviewSetup(JSON.parse(text));
      } catch {
        return emptyPreviewSetup();
      }
    },
    save:async value=>{
      // The same validator guards the request and the file, so a stored value always loads back.
      const text=JSON.stringify(validatePreviewSetup(value));
      const temporary=path.join(directory,`${PREVIEW_SETUP_FILE}.${process.pid}-${++pending}.tmp`);
      try {
        await fs.writeFile(temporary,text,{encoding:'utf8',mode:0o600});
        await fs.rename(temporary,file);
      } catch {
        // Best effort: never leave a temporary file behind, and never report a path.
        try{await fs.unlink(temporary);}catch{/* the temporary file was never created */}
      }
      return null;
    },
  };
}
