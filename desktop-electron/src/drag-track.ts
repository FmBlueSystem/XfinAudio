/**
 * S9 drag-out: the one place a suggested track becomes an Electron drag.
 *
 * The renderer knows only the public track id. This module turns it into the file
 * `webContents.startDrag` needs, with every dependency injected (`request`,
 * `startDrag`, `fileExists`, `icon`) so the rules are exercised without Electron.
 * The path never leaves here: `drag` answers `null` on every path, and resolving
 * the ids of a `liveFollow` answer ahead only fills this module's own cache.
 */
export interface DragDependencies<Icon> {
  /** The host request that owns `track.resolve`; the only way to a file path. */
  request: (method: string, params: Record<string, unknown>) => Promise<unknown>;
  /** Electron's `webContents.startDrag`, handed the file and the small icon. */
  startDrag: (drag: {file: string; icon: Icon}) => void;
  /** Whether the resolved file is still there when the drag starts. */
  fileExists: (file: string) => Promise<boolean>;
  /** The icon shown under the cursor; created by the host, never by this module. */
  icon: Icon;
}
export interface DragTracks {
  /**
   * Replaces the cache with the ids the latest `liveFollow` answer suggests, each
   * resolved ahead so a drag starts without a core round trip. An answer without
   * suggestions empties it, and a slower earlier answer never wins.
   */
  remember: (answer: unknown) => Promise<void>;
  /** Starts at most one drag for a validated `{trackId}` request; never rejects. */
  drag: (params: unknown) => Promise<null>;
}
const TRACK_ID = /^[a-f0-9]{64}$/;
const isTrackId = (value: unknown): value is string => typeof value === 'string' && TRACK_ID.test(value);
/** Exactly one own `trackId` key: no path, no icon, no alias may ride along. */
function requestTrackId(params: unknown): string | null {
  if (!params || typeof params !== 'object' || Array.isArray(params)) return null;
  const keys = Object.keys(params);
  if (keys.length !== 1 || keys[0] !== 'trackId') return null;
  const value = (params as Record<string, unknown>).trackId;
  return isTrackId(value) ? value : null;
}
/** The public ids a `liveFollow` answer suggests; anything else in it is ignored. */
function suggestedIds(answer: unknown): string[] {
  const raw = (answer as {suggestions?: unknown} | null)?.suggestions;
  if (!Array.isArray(raw)) return [];
  const ids = raw.map(item => (item as {id?: unknown} | null)?.id).filter(isTrackId);
  return [...new Set(ids)];
}
export function createDragTracks<Icon>({request, startDrag, fileExists, icon}: DragDependencies<Icon>): DragTracks {
  let files = new Map<string, string>();
  let generation = 0;
  /** The core's path for one id, or null when it does not resolve: a refusal is never thrown. */
  const resolveFile = async (trackId: string): Promise<string | null> => {
    try {
      const track = await request('track.resolve', {trackId}) as {path?: unknown} | null;
      const file = track?.path;
      return typeof file === 'string' && file.length > 0 ? file : null;
    } catch {
      return null;
    }
  };
  return {
    async remember(answer) {
      const current = ++generation;
      const resolved = await Promise.all(suggestedIds(answer).map(async id => ({id, file: await resolveFile(id)})));
      // A newer answer already owns the cache; an older one may not restore an id it dropped.
      if (current !== generation) return;
      files = new Map();
      for (const {id, file} of resolved) if (file) files.set(id, file);
    },
    async drag(params) {
      // A drag is one-way and best effort: nothing here may reject into the window.
      try {
        const trackId = requestTrackId(params);
        if (!trackId) return null;
        const file = files.get(trackId) ?? await resolveFile(trackId);
        if (!file || !await fileExists(file)) return null;
        startDrag({file, icon});
      } catch {
        // A refused drag changes nothing, and the renderer is told nothing about it.
      }
      return null;
    },
  };
}
