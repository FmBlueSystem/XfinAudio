/** Coordinates native close confirmation without stopping the core after Cancel. */
export class CloseFlow {
  private pending:Promise<void>|null=null;
  isClosing=false;
  readyToQuit=false;
  constructor(
    private readonly dirty:()=>boolean,
    private readonly confirmDiscard:()=>Promise<boolean>,
    private readonly shutdown:()=>Promise<void>,
    private readonly finish:()=>void,
  ) {}
  /**
   * `force` (a SIGTERM or SIGINT) skips the unsaved-changes dialog, even one already open,
   * and discards unsaved drafts; the shutdown still drains the core exactly once.
   */
  request(force=false):Promise<void> {
    if(this.readyToQuit&&!this.pending)return Promise.resolve();
    if(this.pending&&(!force||this.isClosing||this.readyToQuit))return this.pending;
    const run:Promise<void>=this.run(force).finally(()=>{if(this.pending===run)this.pending=null;});
    this.pending=run;
    return run;
  }
  private async run(force:boolean):Promise<void> {
    if(!force&&this.dirty()) {
      let confirmed=false;
      try{confirmed=await this.confirmDiscard();}catch{return;}
      if(!confirmed||this.isClosing||this.readyToQuit)return;
    }
    this.isClosing=true;
    try{await this.shutdown();}
    finally{this.readyToQuit=true;this.finish();}
  }
}
