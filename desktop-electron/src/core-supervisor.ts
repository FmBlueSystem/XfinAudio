/**
 * Supervised audio core: when the process dies it is replaced after a bounded
 * delay, and after the retry cap the app keeps its existing "restart the app"
 * message instead of respawning forever.
 */
export const RESTART_DELAYS_MS:readonly number[]=[1000,3000,9000];
export const MAX_CORE_RESTARTS=RESTART_DELAYS_MS.length;
/** A replacement core that stays up this long restores the whole retry budget. */
export const STABLE_CORE_MS=60000;
export interface StoppableCore{on(event:'stopped',listener:(message:string)=>void):unknown;}
export interface CoreSupervisorOptions<T extends StoppableCore>{
  create:()=>T;
  delays?:readonly number[];
  stabilityMs?:number;
  onStarted?:(core:T,attempt:number)=>void;
  onStopped?:(message:string)=>void;
  onRestart?:(attempt:number,delayMs:number)=>void;
  onExhausted?:(restarts:number,message:string)=>void;
}
export class CoreSupervisor<T extends StoppableCore>{
  private value:T|null=null;
  private restarts=0;
  private closed=false;
  private restartTimer:ReturnType<typeof setTimeout>|null=null;
  private stabilityTimer:ReturnType<typeof setTimeout>|null=null;
  constructor(private readonly options:CoreSupervisorOptions<T>){}
  get core():T {if(!this.value)throw new Error('Core supervisor has not started');return this.value;}
  get restartCount():number {return this.restarts;}
  /** Create and wire the first core. */
  start():T {const core=this.adopt();this.options.onStarted?.(core,0);return core;}
  /** Stop supervising: nothing is created after this call, the live core is closed by its owner. */
  shutdown():void {this.closed=true;this.clearTimers();}
  private adopt():T {
    const core=this.options.create();
    this.value=core;
    core.on('stopped',(message:string)=>this.handleStopped(core,message)); 
    this.armStability();
    return core;
  }
  private handleStopped(core:T,message:string):void {
    if(core!==this.value)return; // a replaced core's late exit never restarts anything
    if(this.restartTimer!==null)return; // one stop already scheduled the only restart for this core
    this.clearTimers();
    this.options.onStopped?.(message);
    if(this.closed)return;
    const delays=this.options.delays??RESTART_DELAYS_MS;
    if(this.restarts>=delays.length){this.options.onExhausted?.(this.restarts,message);return;}
    const delay=delays[this.restarts];
    this.restarts+=1;
    this.options.onRestart?.(this.restarts,delay);
    this.restartTimer=setTimeout(()=>{
      this.restartTimer=null;
      if(this.closed)return;
      const next=this.adopt();
      this.options.onStarted?.(next,this.restarts);
    },delay);
    this.restartTimer.unref?.();
  }
  private armStability():void {
    this.clearTimers();
    const ms=this.options.stabilityMs??STABLE_CORE_MS;
    if(!Number.isFinite(ms)||ms<=0)return;
    this.stabilityTimer=setTimeout(()=>{this.stabilityTimer=null;this.restarts=0;},ms);
    this.stabilityTimer.unref?.();
  }
  private clearTimers():void {
    if(this.restartTimer){clearTimeout(this.restartTimer);this.restartTimer=null;}
    if(this.stabilityTimer){clearTimeout(this.stabilityTimer);this.stabilityTimer=null;}
  }
}
