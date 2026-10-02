import {open,realpath} from 'node:fs/promises';
import {constants} from 'node:fs';
import {Readable} from 'node:stream';
import {assertTrackId,parseRange} from './security';
type Source={path:string;mime:string;identity:{device:string;inode:string;size:string;mtimeNs:string}};
type Resolver=(id:string)=>Promise<Source>;
export async function audioResponse(request:Request,resolve:Resolver):Promise<Response> {
  const url = new URL(request.url);
  if(url.protocol!=='xfin-audio:'||url.host!=='track'||url.search||url.hash||!['GET','HEAD'].includes(request.method))return new Response(null,{status:403});
  const id=url.pathname.slice(1);
  try{assertTrackId(id);}catch{return new Response(null,{status:403});}
  try {
    const source=await resolve(id);
    const canonical=await realpath(source.path);
    if(canonical!==source.path)return new Response(null,{status:403});
    const file=await open(canonical,constants.O_RDONLY|constants.O_NOFOLLOW);
    const identity=await file.stat({bigint:true});
    const stat=await file.stat();
    const stillCanonical=await realpath(source.path).catch(()=>null);
    if(stillCanonical!==canonical||identity.dev!==BigInt(source.identity.device)||identity.ino!==BigInt(source.identity.inode)||identity.size!==BigInt(source.identity.size)||identity.mtimeNs!==BigInt(source.identity.mtimeNs)){await file.close();return new Response(null,{status:403});}
    if(!stat.isFile()){await file.close();return new Response(null,{status:404});}
    let range;
    try{range=parseRange(request.headers.get('range'),stat.size);}
    catch{await file.close();return new Response(null,{status:416,headers:{'Content-Range':`bytes */${stat.size}`}});}
    const headers:Record<string,string>={
      'Content-Type':source.mime,'Accept-Ranges':'bytes','Content-Length':String(Math.max(0,range.end-range.start+1)),
      'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Access-Control-Allow-Origin':'xfin-app://ui',
    };
    if(range.status===206)headers['Content-Range']=`bytes ${range.start}-${range.end}/${stat.size}`;
    if(request.method==='HEAD'||stat.size===0){await file.close();return new Response(null,{status:range.status,headers});}
    const stream=file.createReadStream({start:range.start,end:range.end,autoClose:true});
    return new Response(Readable.toWeb(stream) as ReadableStream,{status:range.status,headers});
  }catch{return new Response(null,{status:404});}
}
