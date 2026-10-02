import assert from 'node:assert/strict';
import test from 'node:test';
import {prepSummaries,prepErrorField,revealControl,workflowStep,ToolOrigins} from '../renderer/workflow.ts';
const fields={name:'',count:'20',minutes:'',role:'',start:'',end:'',genre:'',strategy:'',required:[],excluded:[]};
test('hidden active settings summarize actual duration cap, selection and saved-draft scope without changing them',()=>{
 const value={...fields,count:'7',minutes:'30',name:'Viernes',strategy:'harmonic',genre:'House',end:'b',required:['a'],excluded:['c','d']};const before=JSON.stringify(value);
 const summary=prepSummaries(value,true);assert.match(summary.size,/30 minutos.*7 pistas/);assert.match(summary.music,/harmonic.*House.*cierre.*Viernes/);assert.match(summary.tracks,/1 obligatoria.*2 excluidas/);assert.match(summary.saved,/sin guardar.*género.*obligatorias.*excluidas/);assert.equal(JSON.stringify(value),before);
 assert.match(prepSummaries(fields,false).size,/20 pistas/);assert.match(prepSummaries({...value,count:'11'},true).size,/11 pistas/);
});
test('semantic validation points at actionable fields without replacing the existing validator',()=>{
 for(const [message,id] of [['Introduce un número entero entre 2 y 100 pistas','count'],['El nombre admite hasta 200 caracteres','name'],['Elige una estrategia disponible','strategy'],['La duración debe ser mayor que 0 y no superar 600 minutos','minutes'],['El género admite hasta 100 caracteres','genre'],['La apertura y el cierre deben ser pistas distintas','end'],['Una pista excluida no puede ser obligatoria, de apertura o de cierre','excluded'],['Hay más pistas obligatorias, de apertura y de cierre que el número solicitado','count']])assert.equal(prepErrorField(message),'prep-'+id);
});
test('draft and invalid-field reveal opens every disclosure ancestor before focusing the actual control',()=>{
 const outer={tagName:'DETAILS',open:false,parentElement:null};const section={tagName:'SECTION',parentElement:outer};const inner={tagName:'DETAILS',open:false,parentElement:section};let focused=0;const input={tagName:'INPUT',parentElement:inner,focus(){assert.equal(outer.open,true);assert.equal(inner.open,true);focused++;}};
 revealControl(input);assert.equal(focused,1);revealControl(input);assert.equal(focused,2);
});
test('step grouping leaves secondary tools distinct and remembers the actual source through repeat/back',()=>{
 assert.equal(workflowStep('serato'),'review');assert.equal(workflowStep('metadata'),'library');assert.equal(workflowStep('loudness'),'library');assert.equal(workflowStep('ai'),'preferences');
 const origins=new ToolOrigins();origins.enter('review','serato');assert.equal(origins.back('serato'),'review');origins.enter('serato','serato');assert.equal(origins.back('serato'),'review');origins.enter('metadata','serato');assert.equal(origins.back('serato'),'metadata');origins.enter('playlists','serato');assert.equal(origins.back('serato'),'playlists');origins.enter('library','metadata');assert.equal(origins.back('metadata'),'library');origins.enter('review','ai');assert.equal(origins.back('ai'),'review');
});
test('entering an existing tool ancestor keeps its original return instead of creating a cycle',()=>{
 const origins=new ToolOrigins();origins.enter('library','preferences');origins.enter('preferences','ai');origins.enter('ai','preferences');assert.equal(origins.back('preferences'),'library');assert.equal(origins.back('ai'),'preferences');
 origins.enter('ai','live');origins.enter('live','preferences');assert.equal(origins.back('preferences'),'library');
});
test('quantity copy distinguishes a requested count from the duration cap without changing fields',()=>{
 assert.equal(prepSummaries(fields,false).size,'20 pistas solicitadas · sin duración objetivo');assert.match(prepSummaries({...fields,count:'7',minutes:'30'},false).size,/30 minutos · hasta 7 pistas/);
});
