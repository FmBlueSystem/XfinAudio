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
/**
 * Core review texts are free-form English without codes and other code reads them, so the
 * presentation translates them by pattern: every pattern below is one exact text the core
 * builds in `playlist_service.py`, `prep_copilot.py` or `scoring.py`, with its numbers and
 * names kept. A text that matches no pattern is shown unchanged.
 */
/** The two colour gates publish a fixed prerequisite and exclusion reason; each keeps its own
 * meaning in Spanish while an unrecognized one stays as the core wrote it. */
const gatePrerequisites:Record<string,string>={'a colour or spectral profile':'color o perfil espectral','an energy, color, or spectral profile':'energía, color o perfil espectral'};
const gateExclusions:Record<string,string>={'strict colour eligibility':'la elegibilidad estricta de color','strict color-and-exact-energy eligibility':'la elegibilidad estricta de color y energía exacta'};
const reviewNotices:[RegExp,(...parts:string[])=>string][]=[
  [/^Track count shortfall: selected (\d+) of (\d+) requested tracks$/,(_,selected,requested)=>`Se seleccionaron ${selected} de las ${requested} pistas solicitadas`],
  [/^Excluded (\d+) incomplete track\(s\)$/,(_,count)=>`Se excluyeron ${count} pista(s) con metadatos incompletos`],
  [/^Mandatory manual prefix exceeds the BPM ceiling; revise the manual order$/,()=>'El orden manual obligatorio supera el límite de salto de BPM; revisa el orden manual'],
  [/^start_path ignored because manual order prefix is applied$/,()=>'Se ignoró la pista de apertura porque se aplica el orden manual'],
  [/^same_vibe metadata unavailable; falling back to harmonic sequencing$/,()=>'No hay metadatos de ambiente para mismo ambiente; se vuelve a la secuencia armónica'],
  [/^Arc target of (\d+) track\(s\) is shorter than the (\d+) manually ordered track\(s\); no generated tracks were added$/,(_,target,manual)=>`El objetivo de arco de ${target} pista(s) es menor que las ${manual} pistas en orden manual; no se añadieron pistas generadas`],
  [/^Duration is unknown for one or more tracks; slot coverage cannot be verified$/,()=>'La duración de una o más pistas es desconocida; no se puede verificar la cobertura del hueco'],
  [/^Duration shortfall: the selected playable tracks do not cover the requested slot$/,()=>'Faltan minutos: las pistas reproducibles seleccionadas no cubren el hueco solicitado'],
  [/^Genre '(.+)' left the set short: (\d+) track\(s\) for a slot that wants about (\d+)$/,(_,genre,count,expected)=>`El género «${genre}» dejó la lista corta: ${count} pista(s) para un hueco de unas ${expected}`],
  [/^Filtered (\d+) track\(s\) outside (.+) energy range$/,(_,count,strategy)=>`Se filtraron ${count} pista(s) fuera del rango de energía de ${strategy}`],
  [/^Filtered (\d+) track\(s\) outside (.+) BPM range$/,(_,count,strategy)=>`Se filtraron ${count} pista(s) fuera del rango de BPM de ${strategy}`],
  [/^Filtered (\d+) track\(s\) outside loudness target band$/,(_,count)=>`Se filtraron ${count} pista(s) fuera de la banda de sonoridad objetivo`],
  [/^Loudness coverage (\d+) of (\d+) applied; (\d+) left in$/,(_,measured,total,left)=>`Sonoridad medida en ${measured} de ${total} pistas; ${left} quedan dentro`],
  [/^Mandatory control tracks are missing after playlist gates; no complete controlled set returned$/,()=>'Faltan pistas de control obligatorias después de los filtros de la lista; no se devolvió un conjunto controlado completo'],
  [/^Mandatory controls exceed the requested track count; no tracks were silently discarded$/,()=>'Las pistas de control obligatorias superan el número de pistas solicitado; no se descartó ninguna pista en silencio'],
  [/^same_genre filter applied: (.+)$/,(_,genre)=>`Filtro de mismo género aplicado: ${genre}`],
  [/^same_genre: no candidates match anchor genre '(.+)'; falling back to unfiltered scoring$/,(_,genre)=>`Mismo género: ninguna pista coincide con el género ancla «${genre}»; se vuelve a la puntuación sin filtro`],
  [/^No candidates in genre '(.+)'; showing every genre instead$/,(_,genre)=>`No hay pistas del género «${genre}»; se muestran todos los géneros`],
  [/^Genre locked to '(.+)'$/,(_,genre)=>`Género fijado en «${genre}»`],
  [/^(\w+): anchor is missing (.+) prerequisite; no generated candidates were produced$/,(_,strategy,missing)=>`${strategy}: a la pista ancla le falta el requisito de ${gatePrerequisites[missing] ?? missing}; no se generaron candidatos`],
  [/^(\w+): (.+) excluded every generated candidate; returning only preserved controls without widening to unfiltered scoring$/,(_,strategy,reason)=>`${strategy}: ${gateExclusions[reason] ?? reason} excluyó todos los candidatos generados; solo se devuelven los controles conservados, sin ampliar a la puntuación sin filtro`],
  [/^(\w+) filter applied: (.+)$/,(_,strategy,value)=>`Filtro de ${strategy} aplicado: ${value}`],
  [/^(\w+): strict eligibility left (\d+) generated candidate\(s\) for (\d+) requested slot\(s\)$/,(_,strategy,left,requested)=>`${strategy}: la elegibilidad estricta dejó ${left} candidato(s) generado(s) para ${requested} hueco(s) solicitado(s)`],
  [/^Filtered (\d+) track\(s\) outside (.+) energy tolerance$/,(_,count,strategy)=>`Se filtraron ${count} pista(s) fuera de la tolerancia de energía de ${strategy}`],
  [/^Harmonic compatibility score is (.+)$/,(_,value)=>`Compatibilidad armónica: ${value}`],
  [/^BPM difference is (.+)%$/,(_,value)=>`Diferencia de BPM: ${value}%`],
  [/^Energy handoff \(out→in\) difference is (.+)$/,(_,value)=>`Salto de energía (salida→entrada): ${value}`],
  [/^Energy level difference is (.+)$/,(_,value)=>`Diferencia de nivel de energía: ${value}`],
  [/^Energy boost (.+) → (.+): (a semitone|a whole step) up lifts the floor, but cut rather than blend — overlapping these keys clashes$/,(_,from,to,interval)=>`Subida de energía ${from} → ${to}: subir ${interval==='a semitone'?'medio tono':'un tono completo'} levanta la pista, pero corta en vez de mezclar; superponer estas tonalidades choca`],
  [/^Tag overlap is (.+)$/,(_,value)=>`Etiquetas en común: ${value}`],
  [/^Edge spectral similarity \(out→in\) is (.+)$/,(_,value)=>`Similitud espectral de los extremos (salida→entrada): ${value}`],
  [/^Spectral similarity is (.+)$/,(_,value)=>`Similitud espectral: ${value}`],
  [/^Tonal compatibility is (.+)$/,(_,value)=>`Compatibilidad tonal: ${value}`],
  [/^Danceability similarity is (.+)$/,(_,value)=>`Similitud de bailabilidad: ${value}`],
  [/^Pitch\/key normalization shifted (left|right) key from (.+) to (.+)$/,(_,side,from,to)=>`La normalización de tono/tonalidad movió la tonalidad ${side==='left'?'izquierda':'derecha'} de ${from} a ${to}`],
  [/^invalid Camelot key$/,()=>'Tonalidad Camelot inválida'],
  [/^Duration shortfall: the hard track count cap prevents this variant from covering the booked slot$/,()=>'Faltan minutos: el límite estricto de pistas impide que esta variante cubra el hueco reservado'],
  [/^Incoming pool: (\d+) track\(s\)$/,(_,count)=>`Pistas de partida: ${count}`],
  [/^Genre focus '(.+)': no match; full candidate pool retained$/,(_,genre)=>`Enfoque de género «${genre}»: sin coincidencias; se conserva todo el conjunto de candidatas`],
  [/^adventurous variant may bridge outside genre focus: (.+)$/,(_,genre)=>`La variante exploratoria puede conectar fuera del enfoque de género: ${genre}`],
  [/^No tracks match genre focus '(.+)'; keeping the full candidate pool$/,(_,genre)=>`Ninguna pista coincide con el enfoque de género «${genre}»; se conserva todo el conjunto de candidatas`],
  [/^Genre focus: none set$/,()=>'Enfoque de género: sin definir'],
  [/^Genre focus '(.+)': not applied \(bridging allowed\)$/,(_,genre)=>`Enfoque de género «${genre}»: no aplicado (se permiten conexiones)`],
  [/^Genre focus '(.+)': (\d+) -> (\d+) track\(s\), (\d+) outside focus$/,(_,genre,before,after,outside)=>`Enfoque de género «${genre}»: de ${before} a ${after} pista(s), ${outside} fuera del enfoque`],
  [/^Genre focus '(.+)': matched all (\d+) track\(s\)$/,(_,genre,count)=>`Enfoque de género «${genre}»: coinciden las ${count} pista(s)`],
  [/^Genre focus matched only the anchor: kept (\d+) of (\d+) pool track\(s\) after all gates$/,(_,kept,incoming)=>`El enfoque de género solo coincidió con la pista ancla: se conservaron ${kept} de ${incoming} pista(s) tras todos los filtros`],
  [/^Only the anchor survived the gates: kept (\d+) of (\d+) pool track\(s\)$/,(_,kept,incoming)=>`Solo la pista ancla sobrevivió a los filtros: se conservaron ${kept} de ${incoming} pista(s)`],
  [/^(\d+) required track\(s\) could not pass playlist gates$/,(_,count)=>`${count} pista(s) obligatoria(s) no pudieron pasar los filtros de la lista`],
  [/^All required tracks are present in the playlist variant$/,()=>'Todas las pistas obligatorias están en la variante de la lista'],
  [/^A required transition cannot satisfy the adjacent BPM gate$/,()=>'Una transición obligatoria no puede cumplir el filtro de BPM entre pistas vecinas'],
  [/^Blocked — (\d+) blocker\(s\), (\d+) review item\(s\); required tracks missing$/,(_,blockers,items)=>`Bloqueada — ${blockers} bloqueo(s), ${items} aviso(s); faltan pistas obligatorias`],
  [/^Strictest option: stays close to the requested genre focus and hard gates\.$/,()=>'Opción más estricta: se mantiene cerca del enfoque de género solicitado y de los filtros estrictos.'],
  [/^Middle option: allows tagged bridges while preserving the set intent\.$/,()=>'Opción intermedia: permite conexiones entre géneros etiquetados y conserva la intención de la sesión.'],
  [/^Exploratory option: allows broader bridges but keeps readiness checks visible\.$/,()=>'Opción exploratoria: permite conexiones más amplias pero mantiene visibles las comprobaciones de preparación.'],
];
export function localizeReviewNotice(message:string):string {
  for(const [pattern,translate] of reviewNotices){const match=pattern.exec(message);if(match)return translate(...match);}
  return message;
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
