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
  request():Promise<void> {
    if(this.pending)return this.pending;
    if(this.readyToQuit)return Promise.resolve();
    this.pending=this.run().finally(()=>{this.pending=null;});
    return this.pending;
  }
  private async run():Promise<void> {
    if(this.dirty()) {
      let confirmed=false;
      try{confirmed=await this.confirmDiscard();}catch{return;}
      if(!confirmed)return;
    }
    this.isClosing=true;
    try{await this.shutdown();}
    finally{this.readyToQuit=true;this.finish();}
  }
}
