import {open,realpath} from 'node:fs/promises';
import {constants} from 'node:fs';
import {Readable} from 'node:stream';
import {APP_ORIGIN,assertTrackId,parseRange} from './security';
type Source={path:string;mime:string;identity:{device:string;inode:string;size:string;mtimeNs:string}};
type Resolver=(id:string)=>Promise<Source>;
/** S11a: the app page reads audio into Web Audio, so every answer, errors included, names its origin and never `*`. */
const headers=(extra:Record<string,string>={}):Record<string,string>=>({'Access-Control-Allow-Origin':APP_ORIGIN,...extra});
export async function audioResponse(request:Request,resolve:Resolver):Promise<Response> {
  const url = new URL(request.url);
  if(url.protocol!=='xfin-audio:'||url.host!=='track'||url.search||url.hash||!['GET','HEAD'].includes(request.method))return new Response(null,{status:403,headers:headers()});
  const id=url.pathname.slice(1);
  try{assertTrackId(id);}catch{return new Response(null,{status:403,headers:headers()});}
  try {
    const source=await resolve(id);
    const canonical=await realpath(source.path);
    if(canonical!==source.path)return new Response(null,{status:403,headers:headers()});
    const file=await open(canonical,constants.O_RDONLY|constants.O_NOFOLLOW);
    const identity=await file.stat({bigint:true});
    const stat=await file.stat();
    const stillCanonical=await realpath(source.path).catch(()=>null);
    if(stillCanonical!==canonical||identity.dev!==BigInt(source.identity.device)||identity.ino!==BigInt(source.identity.inode)||identity.size!==BigInt(source.identity.size)||identity.mtimeNs!==BigInt(source.identity.mtimeNs)){await file.close();return new Response(null,{status:403,headers:headers()});}
    if(!stat.isFile()){await file.close();return new Response(null,{status:404,headers:headers()});}
    let range;
    try{range=parseRange(request.headers.get('range'),stat.size);}
    catch{await file.close();return new Response(null,{status:416,headers:headers({'Content-Range':`bytes */${stat.size}`})});}
    const answer=headers({
      'Content-Type':source.mime,'Accept-Ranges':'bytes','Content-Length':String(Math.max(0,range.end-range.start+1)),
      'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
    });
    if(range.status===206)answer['Content-Range']=`bytes ${range.start}-${range.end}/${stat.size}`;
    if(request.method==='HEAD'||stat.size===0){await file.close();return new Response(null,{status:range.status,headers:answer});}
    const stream=file.createReadStream({start:range.start,end:range.end,autoClose:true});
    return new Response(Readable.toWeb(stream) as ReadableStream,{status:range.status,headers:answer});
  }catch{return new Response(null,{status:404,headers:headers()});}
}
