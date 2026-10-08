/**
 * Import barrier for the `electron` module, shared by main and preload.
 *
 * `require('electron')` only returns the real API object while the process is
 * running inside the Electron runtime. When the binary is launched with
 * ELECTRON_RUN_AS_NODE=1 (e.g. leaked from Electron-based editors, task
 * runners or agent harnesses), it runs as plain Node.js, the built-in
 * `electron` module is never registered, and the npm package's index.js
 * answers with the binary path string instead. Failing fast here replaces the
 * confusing "Cannot read properties of undefined (reading 'setName')" with an
 * actionable message.
 */
import {app,BrowserWindow,dialog,ipcMain,ipcRenderer,protocol,session,shell,contextBridge,screen,systemPreferences,desktopCapturer,webFrameMain,net,nativeTheme} from 'electron';

// Main and preload see different API surfaces (app/BrowserWindow are
// main-process only), so the only cross-process failure signature is the npm
// package fallback: the raw module export being the binary path string.
const electronExport:unknown=require('electron');
if(typeof electronExport==='string'){
  const leaked=typeof process!=='undefined'&&!!process.env?.ELECTRON_RUN_AS_NODE;
  throw new Error(
    leaked
      ? 'ELECTRON_RUN_AS_NODE=1 is set, so the Electron binary is running as plain Node.js and require("electron") returns the binary path. Launch with it unset: env -u ELECTRON_RUN_AS_NODE electron .'
      : 'require("electron") returned a string instead of the Electron API object; the electron binary is probably missing. Run "npm install" inside desktop-electron to restore it.'
  );
}

export {
  app, BrowserWindow, dialog, ipcMain, ipcRenderer,
  protocol, session, shell, contextBridge,
  screen, systemPreferences, desktopCapturer,
  webFrameMain, net, nativeTheme,
};
