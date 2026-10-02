export const OFFLINE_FIELDS:Record<string,string[]>={
  queryLibrary:['query','request','status','sortBy','descending','hideDuplicates'],searchPlaylists:['request'],
  comparePlaylists:['playlistIds'],deletePlaylist:['playlistId'],listDeletedPlaylists:[],restorePlaylist:['deletionId'],
};
const playlist=(v:unknown)=>typeof v==='string'&&/^[1-9]\d{0,14}$/.test(v);
const token=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v);
const text=(v:unknown,max:number,empty=false)=>typeof v==='string'&&v.length<=max&&!/[\x00-\x1f]/.test(v)&&(empty||Boolean(v.trim()));
const invalid=()=>{throw new Error('Invalid offline browsing request');};
export function validateOfflineRequest(method:string,params:Record<string,unknown>):void{
  if(!Object.hasOwn(OFFLINE_FIELDS,method))return;
  if(Object.keys(params).some(key=>!OFFLINE_FIELDS[method].includes(key)))invalid();
  if(method==='deletePlaylist'&&!playlist(params.playlistId))invalid();
  if(method==='restorePlaylist'&&!token(params.deletionId))invalid();
  if(method==='searchPlaylists'&&!text(params.request,2000,true))invalid();
  if(method==='comparePlaylists'){
    const ids=params.playlistIds;if(!Array.isArray(ids)||ids.length<2||ids.length>200||new Set(ids).size!==ids.length||!ids.every(playlist))invalid();
  }
  if(method!=='queryLibrary')return;
  if('query'in params&&'request'in params)invalid();
  if('request'in params&&!text(params.request,2000))invalid();
  if('status'in params&&!['all','complete','incomplete'].includes(String(params.status)))invalid();
  if('sortBy'in params&&!['title','artist','genre','bpm','key','energy','duration','format','bitrate'].includes(String(params.sortBy)))invalid();
  for(const key of ['descending','hideDuplicates'])if(key in params&&typeof params[key]!=='boolean')invalid();
  if(!('query'in params))return;
  const query=params.query;if(!query||typeof query!=='object'||Array.isArray(query))invalid();
  const item=query as Record<string,unknown>;
  if(Object.keys(item).some(key=>!['text','genre','bpm_min','bpm_max','key','energy_min','energy_max'].includes(key)))invalid();
  for(const key of ['text','genre'])if(key in item&&item[key]!==null&&!text(item[key],200,true))invalid();
  if('key'in item&&item.key!==null&&(typeof item.key!=='string'||!/^(?:[1-9]|1[0-2])[AB]$/.test(item.key)))invalid();
  for(const [low,high,minimum,maximum,integer] of [['bpm_min','bpm_max',Number.MIN_VALUE,400,false],['energy_min','energy_max',1,10,true]] as const){
    for(const key of [low,high])if(key in item&&item[key]!==null){const value=item[key];if(typeof value!=='number'||!Number.isFinite(value)||value<minimum||value>maximum||(integer&&!Number.isInteger(value)))invalid();}
    if(typeof item[low]==='number'&&typeof item[high]==='number'&&(item[low] as number)>(item[high] as number))invalid();
  }
}
