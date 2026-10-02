import {ChildProcessWithoutNullStreams, spawn} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {EventEmitter} from 'node:events';
import {StringDecoder} from 'node:string_decoder';

type Pending = {resolve:(value:any)=>void;reject:(error:Error)=>void};
export class PythonBridge extends EventEmitter {
  private child:ChildProcessWithoutNullStreams;
  private pending = new Map<string,Pending>();
  private buffer = '';
  private closed = false;
  private decoder = new StringDecoder('utf8');
  private exited:Promise<void>;
  private didExit = false;
  constructor(command:string, args:string[], env:NodeJS.ProcessEnv) {
    super();
    this.child = spawn(command,args,{env,stdio:['pipe','pipe','pipe'],windowsHide:true,shell:false});
    this.exited=new Promise(resolve=>{
      const finish=()=>{this.didExit=true;resolve();};
      this.child.once('exit',finish);this.child.once('error',finish);
    });
    this.child.stdout.on('data',(chunk:Buffer)=>this.consume(this.decoder.write(chunk)));
    this.child.stdin.on('error',(error)=>this.fail(error));
    this.child.stdout.on('error',(error)=>this.fail(error));
    this.child.stderr.on('error',(error)=>this.fail(error));
    this.child.stderr.on('data',(chunk:Buffer)=>console.error('[core]',chunk.toString().slice(0,4096).trim()));
    this.child.on('error',(error)=>this.fail(error));
    this.child.on('exit',()=>this.fail(new Error('The audio core stopped. Restart the app to reconnect.')));
  }
  request(method:string,params:Record<string,unknown> = {},id = randomUUID()):Promise<any> {
    if(this.closed) return Promise.reject(new Error('Audio core unavailable'));
    if(this.pending.size>=16) return Promise.reject(new Error('Too many pending requests'));
    return new Promise((resolve,reject)=>{
      this.pending.set(id,{resolve,reject});
      const frame = JSON.stringify({id,method,params})+'\n';
      if(Buffer.byteLength(frame)>65536) {this.pending.delete(id);reject(new Error('Request too large'));return;}
      this.child.stdin.write(frame,error=>{if(error){this.pending.delete(id);reject(error);}});
    });
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
  private fail(error:Error) {this.closed=true;for(const item of this.pending.values())item.reject(error);this.pending.clear();this.emit('stopped',error.message);}
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
