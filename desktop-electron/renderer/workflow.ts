import type {PrepFields} from './model.js';

/** Presentation only: all values still pass through buildPrepInput unchanged. */
export function prepSummaries(fields: PrepFields, dirty: boolean): {size:string;music:string;tracks:string;saved:string} {
  return {
    size: fields.minutes.trim() ? `${fields.minutes} minutos · hasta ${fields.count} pistas` : `${fields.count} pistas solicitadas · sin duración objetivo`,
    music: [fields.strategy || 'Estrategia predeterminada', fields.genre.trim(), fields.end ? 'Con pista de cierre' : '', fields.name.trim()].filter(Boolean).join(' · '),
    tracks: `${fields.required.length} obligatorias · ${fields.excluded.length} excluidas`,
    saved: `${dirty ? 'Cambios sin guardar' : 'Guardar o restaurar'} · solo género, obligatorias y excluidas`,
  };
}
export function localizeReviewNotice(message:string):string {
  const shortfall=/^Track count shortfall: selected (\d+) of (\d+) requested tracks$/.exec(message);
  return shortfall ? `Se seleccionaron ${shortfall[1]} de las ${shortfall[2]} pistas solicitadas` : message;
}
export function prepErrorField(message: string, fields?: Pick<PrepFields,'required'|'excluded'>): string {
  if(message === 'Selecciona hasta 100 pistas distintas en cada lista') {
    const invalid=(values: readonly string[])=>values.length>100||new Set(values).size!==values.length;
    return fields&&!invalid(fields.required)&&invalid(fields.excluded)?'prep-excluded':'prep-required';
  }
  const rules: [RegExp,string][] = [[/número entero|número solicitado/,'count'],[/nombre/,'name'],[/estrategia/,'strategy'],[/duración/,'minutes'],[/momento/,'role'],[/género/,'genre'],[/apertura y el cierre.*distintas/,'end'],[/excluida/,'excluded']];
  return 'prep-'+(rules.find(([pattern])=>pattern.test(message))?.[1] ?? 'required');
}
/** Native details can be nested by a tool or settings view. Reveal every ancestor. */
export function revealControl(input: HTMLElement): void {
  for(let node:HTMLElement|null=input;node;node=node.parentElement)if(node.tagName?.toLowerCase()==='details')(node as HTMLDetailsElement).open=true;
  input.focus();
}
export function workflowStep(route:string):string {
  if(['metadata','loudness'].includes(route))return 'library';
  if(route==='serato')return 'review';
  if(route==='ai')return 'preferences';
  if(route==='editor')return 'playlists';
  return route;
}
/** Explicit tool origins, not browser history. Re-entry never overwrites its own origin. */
export class ToolOrigins {
  private origins=new Map<string,string>();
  enter(from:string,to:string):boolean {
    if(from===to||!['metadata','loudness','serato','editor','ai','preferences','live'].includes(to))return false;
    const visited=new Set<string>();
    for(let ancestor:string|undefined=from;ancestor&&!visited.has(ancestor);ancestor=this.origins.get(ancestor)){
      if(ancestor===to)return false;
      visited.add(ancestor);
    }
    this.origins.set(to,from); return true;
  }
  back(route:string):string {return this.origins.get(route)??({serato:'review',editor:'playlists',ai:'preferences',live:'review'}[route]??'library');}
}
