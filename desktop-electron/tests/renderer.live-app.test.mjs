import test from 'node:test';import assert from 'node:assert/strict';
class Element extends EventTarget {
 constructor(tag='div'){super();this.tagName=tag;}textContent='';value='';disabled=false;hidden=false;dataset={};children=[];attrs={};classes=new Set();
 classList={toggle:(k,v)=>v?this.classes.add(k):this.classes.delete(k),contains:k=>this.classes.has(k)};
 setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}append(...n){this.children.push(...n);}replaceChildren(...n){this.children=n;}closest(){return null;}focus(){}set innerHTML(_){throw new Error('Unsafe HTML');}
}
const tick=()=>new Promise(r=>setImmediate(r));const all=n=>[n,...n.children.flatMap(all)];const click=n=>{assert.ok(n);n.dispatchEvent(new Event('click'));};let sequence=0;
async function fixture(overrides={}) {
 const previous=[globalThis.document,globalThis.window],elements=new Map(),get=id=>{const dynamic=[...elements.values()].flatMap(all).find(n=>n.id===id);if(dynamic)return dynamic;if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 const routes=['library','live','review'].map(route=>Object.assign(new Element('button'),{dataset:{route}}));
 const tracks=['a','b','c'].map(id=>({id:id.repeat(64),title:id,artist:'Artist',bpm:120,key:'8A',energy:5,duration:60}));
 const review={reviewId:'review',tracks,warnings:[],blockers:[],name:'Ready',variant:'balanced',readiness:'ready'};
 let state={sessionId:'session',revision:0,sourceReviewId:'review',state:'active',current:tracks[0],history:[],candidates:[{track:tracks[1],score:.98,alerts:[]}],elapsedSeconds:0};const calls=[];let progress;
 const api={listLibrary:async()=>({tracks,count:3}),getPrepCatalog:async()=>({strategies:[]}),onProgress:cb=>{progress=cb;return()=>{};},generatePrep:async()=>review,
 openLive:async input=>{calls.push(['open',input]);return state;},getLiveStatus:async input=>{calls.push(['refresh',input]);return state;},advanceLive:async input=>{calls.push(['advance',input]);state={...state,revision:1,current:tracks[1],history:[{track:tracks[0],startedAt:'2026-10-01T10:00:00Z'}],candidates:[]};return state;},clearLive:async input=>{calls.push(['clear',input]);return {cleared:true};},chooseLibrary:async()=>null,...overrides};
 globalThis.document={getElementById:get,createElement:tag=>new Element(tag),title:'',querySelectorAll:selector=>selector==='[data-route]'||selector==='.nav-item'?routes:selector==='[data-mutation]'?[...elements.values()].flatMap(all).filter(n=>'mutation'in n.dataset):[]};globalThis.window=Object.assign(new EventTarget(),{xfin:api});get('prep-count').value='3';get('metadata-filter').value='all';
 await import(`../.out/renderer/app.js?liveApp=${++sequence}`);await tick();
 return {get,calls,nodes:()=>[...elements.values()].flatMap(all),generate:async()=>{get('prep-form').dispatchEvent(new Event('submit',{cancelable:true}));await tick();},navigate:route=>click(routes.find(n=>n.dataset.route===route)),progress:e=>progress(e),restore:()=>{globalThis.window.dispatchEvent(new Event('beforeunload'));[globalThis.document,globalThis.window]=previous;}};
}
test('review explicitly starts manual Live; next updates once and navigation preserves session',async()=>{
 const f=await fixture();try{await f.generate();assert.equal(f.get('start-live').disabled,false);assert.equal(f.get('start-live-hint').hidden,true);click(f.get('start-live'));await tick();assert.equal(document.title,'XfinAudio · Asistente Live');assert.deepEqual(f.calls[0],['open',{reviewId:'review'}]);assert.match(f.get('live-current-heading').textContent,/a/);
 const next=f.nodes().find(n=>n.dataset.liveNext);click(next);click(next);await tick();assert.equal(f.calls.filter(c=>c[0]==='advance').length,1);assert.equal(f.get('live-history').children.length,1);f.navigate('library');f.navigate('live');assert.equal(f.get('live-history').children.length,1);assert.equal(f.calls.filter(c=>c[0]==='open').length,1);
 click(f.get('live-clear'));await tick();assert.equal(f.get('live-content').hidden,true);
 }finally{f.restore();}
});
test('needs-review selection cannot start Live and scan invalidates an active snapshot',async()=>{
 const f=await fixture({generatePrep:async()=>({reviewId:'warning',tracks:[],name:'Warning',variant:'balanced',warnings:['Review'],blockers:[],readiness:'needs_review'})});try{await f.generate();assert.equal(f.get('start-live').disabled,true);assert.equal(f.get('start-live-hint').hidden,false);assert.match(f.get('start-live-hint').textContent,/avisos de revisión/);click(f.get('start-live'));await tick();assert.equal(f.calls.length,0);}finally{f.restore();}
 const g=await fixture();try{await g.generate();click(g.get('start-live'));await tick();click(g.get('choose-library'));await tick();assert.equal(g.get('live-content').hidden,true);}finally{g.restore();}
});
test('disconnect during Live advance retains an unavailable snapshot and ignores late success',async()=>{
 let finish;const f=await fixture({advanceLive:()=>new Promise(resolve=>{finish=resolve;})});try{await f.generate();click(f.get('start-live'));await tick();const current=f.get('live-current-heading').textContent;click(f.nodes().find(n=>n.dataset.liveNext));f.progress({operation:'core',phase:'error',message:'Raw private /path'});assert.equal(f.get('live-content').hidden,false);assert.equal(f.get('live-current-preview').disabled,true);assert.match(f.get('live-unavailable').textContent,/desconectado/);finish({sessionId:'session',revision:1,sourceReviewId:'review',state:'complete',current:{id:'new',title:'Late'},history:[],candidates:[],elapsedSeconds:0});await tick();assert.equal(f.get('live-current-heading').textContent,current);assert.doesNotMatch(f.get('operation-detail').textContent,/private|\/path/);}finally{f.restore();}
});
