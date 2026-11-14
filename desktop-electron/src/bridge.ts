import {ChildProcessWithoutNullStreams, spawn} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {EventEmitter} from 'node:events';
import {StringDecoder} from 'node:string_decoder';

type Pending = {resolve:(value:any)=>void;reject:(error:Error)=>void};
/**
 * Long-running jobs the renderer cancels explicitly (`cancelCurrent`). Their lifetime
 * belongs to the cancellation contract, so no deadline may kill them mid-write.
 */
export const CANCELLABLE_JOB_METHODS:ReadonlySet<string>=new Set([
  'library.scan','library.rescan','profiles.complete','loudness.run','prep.generate','prep.select','ai.run',
]);
/** Every other request must settle inside this budget or the core is considered hung. */
export const REQUEST_TIMEOUT_MS=30000;
/** The deadline for one method: cancellable jobs have none, everything else the default. */
export function requestDeadline(method:string,defaultMs:number=REQUEST_TIMEOUT_MS):number|null {
  if(CANCELLABLE_JOB_METHODS.has(method))return null;
  return Number.isFinite(defaultMs)&&defaultMs>0?defaultMs:null;
}
export interface BridgeOptions {
  /** Overrides the per-method deadline; tests use a short one. */
  requestTimeoutMs?:number;
  /** Sink for core stderr and transport events. Never receives request parameters. */
  log?:(line:string)=>void;
}
export class PythonBridge extends EventEmitter {
  private child:ChildProcessWithoutNullStreams;
  private pending = new Map<string,Pending>();
  private buffer = '';
  private closed = false;
  private failed = false;
  private decoder = new StringDecoder('utf8');
  private exited:Promise<void>;
  private didExit = false;
  private timeoutMs:number;
  private log:(line:string)=>void;
  constructor(command:string, args:string[], env:NodeJS.ProcessEnv, options:BridgeOptions = {}) {
    super();
    this.timeoutMs=options.requestTimeoutMs??REQUEST_TIMEOUT_MS;
    this.log=options.log??((line:string)=>console.error('[core]',line));
    this.child = spawn(command,args,{env,stdio:['pipe','pipe','pipe'],windowsHide:true,shell:false});
    this.exited=new Promise(resolve=>{
      const finish=()=>{this.didExit=true;resolve();};
      this.child.once('exit',finish);this.child.once('error',finish);
    });
    this.child.stdout.on('data',(chunk:Buffer)=>this.consume(this.decoder.write(chunk)));
    this.child.stdin.on('error',(error)=>this.fail(error));
    this.child.stdout.on('error',(error)=>this.fail(error));
    this.child.stderr.on('error',(error)=>this.fail(error));
    this.child.stderr.on('data',(chunk:Buffer)=>this.log(chunk.toString().slice(0,4096).trim()));
    this.child.on('error',(error)=>this.fail(error));
    this.child.on('exit',()=>this.fail(new Error('The audio core stopped. Restart the app to reconnect.')));
  }
  request(method:string,params:Record<string,unknown> = {},id = randomUUID()):Promise<any> {
    if(this.closed) return Promise.reject(new Error('Audio core unavailable'));
    if(this.pending.size>=16) return Promise.reject(new Error('Too many pending requests'));
    return new Promise((resolve,reject)=>{
      const deadline = requestDeadline(method,this.timeoutMs);
      let timer:ReturnType<typeof setTimeout>|null=null;
      const pending:Pending={
        resolve:(value:any)=>{if(timer){clearTimeout(timer);timer=null;}resolve(value);},
        reject:(error:Error)=>{if(timer){clearTimeout(timer);timer=null;}reject(error);},
      };
      this.pending.set(id,pending);
      const frame = JSON.stringify({id,method,params})+'\n';
      if(Buffer.byteLength(frame)>65536) {this.pending.delete(id);pending.reject(new Error('Request too large'));return;}
      this.child.stdin.write(frame,error=>{if(error){this.pending.delete(id);pending.reject(error);}});
      if(deadline===null)return;
      timer=setTimeout(()=>this.expire(id,method,deadline),deadline);
      timer.unref?.();
    });
  }
  /**
   * A request without an answer is a hung core: the deadline settles that request,
   * every other waiter and the single-job slot, then kills the process so the
   * supervisor can start a healthy one.
   */
  private expire(id:string,method:string,deadline:number):void {
    const pending=this.pending.get(id);
    if(!pending)return;
    const error=Object.assign(new Error(`[core_timeout] ${method} did not answer within ${deadline} ms`),{code:'core_timeout'});
    // Method names and budgets are safe for support; request parameters never are.
    this.log(`timeout: ${method} did not answer within ${deadline} ms`);
    this.pending.delete(id);
    pending.reject(error);
    this.fail(error);
    this.child.kill('SIGKILL');
  }
  private consume(chunk:string) {
    this.buffer += chunk;
    if(Buffer.byteLength(this.buffer)>32*1024*1024) {this.fail(new Error('Core message exceeded limit'));this.child.kill();return;}
    let end:number;
    while((end=this.buffer.indexOf('\n'))>=0) {
      const line=this.buffer.slice(0,end);this.buffer=this.buffer.slice(end+1);
      if(!line.trim()) continue;
      try {
        const message=JSON.parse(line);
        if(message&&typeof message==='object'&&message.id===null&&message.ok===false) {
          // An unsolicited error frame carries no request to answer: record the
          // code only (never the payload) and keep the core alive.
          const code=typeof message.error?.code==='string'&&/^[a-z_]{1,40}$/.test(message.error.code)?message.error.code:'unknown';
          this.log(`ignored error frame with null id: ${code}`);
          continue;
        }
        if(message.event==='progress' && typeof message.jobId==='string' && this.pending.has(message.jobId)) this.emit('progress',message);
        else if(typeof message.id==='string') {
          const pending=this.pending.get(message.id);if(!pending) continue;
          this.pending.delete(message.id);
          if(message.ok===true) pending.resolve(message.result);
          else {
            const code=typeof message.error?.code==='string'&&/^[a-z_]{1,40}$/.test(message.error.code)?message.error.code:'core_error';
            const detail=typeof message.error?.message==='string'?message.error.message:'Core request failed';
            pending.reject(Object.assign(new Error(`[${code}] ${detail}`),{code}));
          }
        } else throw new Error('Invalid core frame');
      } catch(error) {this.fail(error instanceof Error?error:new Error('Invalid core response'));this.child.kill();return;}
    }
  }
  private fail(error:Error) {
    // The first failure is the one worth reporting; a kill after it (timeout, limit,
    // malformed frame) must not announce a second stop to the supervisor.
    if(this.failed)return;
    this.failed=true;this.closed=true;
    for(const item of this.pending.values())item.reject(error);
    this.pending.clear();
    this.emit('stopped',error.message);
  }
  async close():Promise<void> {
    if(this.didExit)return;
    const forced=setTimeout(()=>this.child.kill('SIGTERM'),4000);
    const hard=setTimeout(()=>this.child.kill('SIGKILL'),6000);
    try {
      if(!this.closed) {
        try {await this.request('shutdown');} catch {this.child.kill('SIGTERM');}
      } else this.child.kill('SIGTERM');
      this.child.stdin.end();
      await this.exited;
    } finally {clearTimeout(forced);clearTimeout(hard);}
  }
}
