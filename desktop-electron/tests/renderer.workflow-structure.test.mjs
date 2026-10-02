import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
// Parse the shipped HTML, never synthesize missing IDs. These checks establish
// structure and disclosure ancestry, not native layout or browser focus behavior.
const html=readFileSync(new URL('../renderer/index.html',import.meta.url),'utf8');
const root={tag:'root',attrs:{},children:[]}; const stack=[root]; const nodes=[];
const voids=new Set(['meta','link','input','br','hr','img','source']);
for(const token of html.matchAll(/<!--[\s\S]*?-->|<![^>]*>|<\/?[a-zA-Z][^>]*>/g)){
 const value=token[0]; if(value.startsWith('<!'))continue;
 if(value.startsWith('</')){const tag=value.match(/^<\/(\w+)/)[1];assert.equal(stack.at(-1).tag,tag,'balanced HTML '+tag);stack.pop();continue;}
 const tag=value.match(/^<(\w+)/)[1]; const attrs=Object.fromEntries([...value.matchAll(/([\w-]+)(?:="([^"]*)")?/g)].slice(1).map(([,k,v])=>[k,v??'']));
 const node={tag,attrs,children:[],parent:stack.at(-1),position:token.index};node.parent.children.push(node);nodes.push(node);if(!voids.has(tag))stack.push(node);
}
const byId=id=>{const found=nodes.filter(n=>n.attrs.id===id);assert.equal(found.length,1,'exact actual element '+id);return found[0];};
const ancestor=(node,id)=>{for(let p=node.parent;p;p=p.parent)if(p.attrs.id===id)return true;return false;};
const ids=nodes.filter(n=>n.attrs.id).map(n=>n.attrs.id);
test('actual shell has three primary steps, secondary tools and one persistent player',()=>{
 assert.equal(new Set(ids).size,ids.length,'no duplicate ids');
 assert.deepEqual(byId('workflow-nav').children.filter(n=>n.tag==='button').map(n=>n.attrs['data-route']),['library','prep','review']);
 for(const route of ['library','prep','review','metadata','live','serato','playlists','editor','loudness','ai','preferences'])byId('page-'+route);
 assert.equal(nodes.filter(n=>n.tag==='audio').length,1);
 assert.ok(ancestor(byId('library-status-container'),'library-tools'));
 assert.ok(ancestor(byId('profiles-container'),'library-tools'));
 byId('context-status');byId('tool-back');byId('context-ai');
});
test('Create shows size and starting point before Generate, with saved controls and extra fields after it',()=>{
 const generate=byId('generate-prep');
 for(const id of ['prep-count','prep-role','prep-start'])assert.ok(byId(id).position<generate.position,id);
 for(const id of ['prep-name','prep-strategy','prep-genre','prep-end','prep-required','prep-excluded','prep-settings-container'])assert.ok(byId(id).position>generate.position,id);
 assert.ok(ancestor(byId('prep-strategy'),'prep-advanced'));
 assert.ok(ancestor(byId('prep-required'),'prep-track-options'));
 assert.ok(ancestor(byId('prep-settings-container'),'prep-saved-controls'));
 byId('prep-sizing-summary');byId('prep-options-summary');byId('prep-tracks-summary');byId('prep-saved-summary');
 assert.ok(!nodes.some(n=>n.attrs.class?.includes('workflow-note')),'no permanent instruction column');
 assert.equal(byId('prep-count').attrs.value,'20');assert.equal(byId('prep-count').attrs.max,'100');
 assert.equal(byId('prep-minutes').attrs.max,'600');
});
test('Review leads with active selection and export; variants and saving stay explicit secondary disclosures',()=>{
 assert.equal(byId('variant-comparison').tag,'details');assert.ok(byId('review-table').position<byId('variant-comparison').position);
 assert.match(byId('export-review').attrs.class,/primary/);assert.doesNotMatch(byId('save-playlist').attrs.class,/primary/);
 assert.ok(ancestor(byId('save-form'),'review-save'));
 const serato=byId('page-serato');assert.ok(!serato.children.some(n=>n.attrs['data-route']==='playlists'));
 assert.ok(!html.includes('Volver a playlists'));
});
test('Settings keeps each owning control group mounted behind one named disclosure',()=>{
 for(const [container,group] of [['preferences-container','settings-playback'],['profile-settings-container','settings-cohesion'],['legacy-import-container','settings-import']])assert.ok(ancestor(byId(container),group));
 assert.equal(byId('settings-playback').tag,'details');assert.equal(byId('settings-cohesion').tag,'details');assert.equal(byId('settings-import').tag,'details');
 assert.equal(byId('settings-ai-link').attrs['data-route'],'ai');assert.ok(ancestor(byId('settings-ai-link'),'page-preferences'));
});
test('resume links are discreet conditional mounted-state access, outside the three main steps',()=>{
 for(const id of ['resume-last-export','resume-editor']){const node=byId(id);assert.equal(node.tag,'button');assert.ok('hidden' in node.attrs);assert.ok(ancestor(node,'session-resume'));assert.ok(!ancestor(node,'workflow-nav'));assert.ok(!('data-mutation' in node.attrs));assert.ok(!('data-route' in node.attrs));}
});
test('Settings outer heading stays distinct from the dynamically-created Preferences heading',()=>{
 assert.equal(byId('page-preferences').attrs['aria-labelledby'],'settings-heading');byId('settings-heading');assert.ok(!nodes.some(node=>node.attrs.id==='preferences-heading'));
 const view=readFileSync(new URL('../renderer/preferences-view.ts',import.meta.url),'utf8');assert.match(view,/identify\(make\('h3', 'Preferencias locales'\), 'heading'\)/);
});
test('short-height Create has an explicit compact spacing rule without hiding the primary action',()=>{
 const css=readFileSync(new URL('../renderer/styles.css',import.meta.url),'utf8');assert.match(css,/@media \(max-height: 850px\) and \(min-width: 701px\)/);assert.match(css,/#page-prep \.prep-form \.full-width \{ margin-top: 12px; \}/);byId('prep-count-unit');
});
