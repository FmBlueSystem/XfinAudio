import type {App} from 'electron';
import {mkdirSync,realpathSync} from 'node:fs';
import path from 'node:path';

/** Bind all Chromium-owned storage before Electron's ready event. */
export function configureStorage(app:Pick<App,'getPath'|'setPath'|'isPackaged'>,requestedRoot?:string):string {
  const selected=!app.isPackaged&&requestedRoot?requestedRoot:app.getPath('userData');
  if(!path.isAbsolute(selected))throw new Error('XFIN_DATA_DIR must be an absolute isolated directory');
  mkdirSync(selected,{recursive:true});
  const root=realpathSync(selected);
  const paths={userData:'chromium-profile',sessionData:'chromium-session',logs:'logs',crashDumps:'crashes'} as const;
  for(const [name,leaf] of Object.entries(paths)) {
    const directory=path.join(root,leaf);
    mkdirSync(directory,{recursive:true});
    const canonical=realpathSync(directory);
    if(!canonical.startsWith(root+path.sep))throw new Error('Application storage escaped its data directory');
    app.setPath(name as keyof typeof paths,canonical);
  }
  return root;
}
