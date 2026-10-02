import type {LegacyImportController} from './legacy-import.js';
import { createDraftNotice } from './draft-notice.js';
import type { DraftNoticeHost } from './draft-notice.js';
export function createLegacyImportView(root:HTMLElement,controller:LegacyImportController,host:DraftNoticeHost&{canResolveDrafts?():boolean}):()=>void{
  const make=<K extends keyof HTMLElementTagNameMap>(tag:K,id:string,text=''):HTMLElementTagNameMap[K]=>{const node=document.createElement(tag);node.id=`legacy-import-${id}`;node.textContent=text;return node;};
  const section=make('section','section');section.className='surface prep-form';section.setAttribute('aria-labelledby','legacy-import-heading');
  const hint=make('p','hint','Importa sets y caché de la aplicación original únicamente en un perfil nuevo: sin biblioteca, ajustes ni carpetas autorizadas. Cierra la aplicación original y completa su checkpoint de SQLite primero. Se admite el esquema actual; no se combinan perfiles existentes.');hint.className='field-hint';
  const policy=make('p','policy','El origen y el audio no se modifican. Se conservan copias de seguridad. Solo se importan volumen de escucha y cohesión; IA, vigilancia y sonoridad quedan desactivadas. Después tendrás que cerrar y abrir la aplicación, elegir las carpetas musicales y escanearlas para autorizar las pistas.');policy.className='field-hint';
  const summary=make('p','summary');summary.setAttribute('role','status');const names=make('ul','names');
  const error=make('p','error');error.setAttribute('role','alert');
  const button=(id:string,text:string,action:()=>void)=>{const node=make('button',id,text);node.type='button';node.className='button subtle';node.addEventListener('click',()=>{if(!node.disabled&&host.canAct())action();});return node;};
  const choose=button('choose','Elegir carpeta original y revisar',()=>{void controller.choose();});
  const apply=button('apply','Confirmar importación…',()=>{void controller.apply();});
  const discard=button('discard','Descartar vista previa',()=>{void controller.discard();});
  const draftNotice=make('section','draft-notice');const renderDraftNotice=createDraftNotice(draftNotice,'legacy-import','importar datos',{draftBlockers:host.draftBlockers,canAct:()=>host.canResolveDrafts?.()??host.canAct()});
  for(const action of [choose,apply,discard])action.setAttribute('aria-describedby','legacy-import-draft-message');
  section.append(make('h3','heading','Importar datos de la aplicación original'),hint,policy,summary,names,error,draftNotice,choose,apply,discard);root.replaceChildren(section);
  return()=>{renderDraftNotice();const blocked=!host.canAct()||controller.pending||Boolean(controller.result),preview=controller.preview,result=controller.result;choose.disabled=blocked;apply.disabled=blocked||!preview;discard.disabled=blocked||!preview;error.textContent=controller.error;error.hidden=!controller.error;
    summary.textContent=result?`Importación completada: ${result.trackCount} pistas y ${result.playlistCount} sets. Copias conservadas. Cierra y vuelve a abrir la aplicación; después autoriza las carpetas musicales y escanéalas.`:preview?`${preview.trackCount} pistas · ${preview.cachedTrackCount} con caché · ${preview.playlistCount} sets · ${preview.referenceCount} referencias. Volumen ${Math.round(preview.safePreferences.previewVolume*100)} % · cohesión ${Math.round(preview.safePreferences.spectralCohesion*100)} %. El origen permanece intacto.`:controller.pending?'Comprobando datos locales…':'No hay una vista previa seleccionada. No se buscarán datos automáticamente.';
    names.replaceChildren(...(preview?.playlistNames??[]).map(name=>{const item=document.createElement('li');item.textContent=name;return item;}));};
}
