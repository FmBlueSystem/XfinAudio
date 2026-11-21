/**
 * S14 (b): the preview setup, kept by the host instead of `localStorage`.
 *
 * The app window's session is in memory (`xfin-offline`), so `localStorage` is empty after
 * every restart. This adapter keeps the controller's storage interface: it is filled once from
 * `getPreviewSetup` and, on every `setItem`, sends the whole current value to `savePreviewSetup`
 * in the S14 (a) shape — `{output, calibration}`. A failed load leaves the system output and no
 * calibration; a failed save keeps the choice for this session and shows nothing.
 */

import { CALIBRATION_STORAGE_KEY, STORAGE_KEY, pairChannels } from './preview-output.js';
import type { PreviewOutputStorage } from './preview-output.js';
import type { PreviewSetup } from './model.js';

/** S14 (a): the two bridge actions, optional until the host ships them. */
export interface PreviewSetupApi {
  getPreviewSetup?(): Promise<PreviewSetup>;
  savePreviewSetup?(input: PreviewSetup): Promise<unknown>;
}

/** S14 (a): an output read from any source, or null when it is not exactly `{label, pair}`. */
export function setupOutput(value: unknown): PreviewSetup['output'] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  if (typeof record.pair !== 'string' || !pairChannels(record.pair)) return null;
  if (record.label === null) return { label: null, pair: record.pair };
  if (typeof record.label !== 'string' || !record.label.trim()) return null;
  return { label: record.label, pair: record.pair };
}

/** S14 (a): the calibration read from any source; a malformed entry is simply not kept. */
export function setupCalibration(value: unknown): PreviewSetup['calibration'] {
  const calibration: PreviewSetup['calibration'] = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return calibration;
  for (const [label, roles] of Object.entries(value as Record<string, unknown>)) {
    if (!label.trim() || !roles || typeof roles !== 'object' || Array.isArray(roles)) continue;
    const kept: Record<string, string> = {};
    for (const [pair, role] of Object.entries(roles as Record<string, unknown>)) {
      if (pairChannels(pair) && typeof role === 'string') kept[pair] = role;
    }
    if (Object.keys(kept).length > 0) calibration[label] = kept;
  }
  return calibration;
}

/** The whole value of the bridge actions, or null when the answer is not one. */
function readSetup(value: unknown): PreviewSetup | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const output = record.output === null || record.output === undefined ? null : setupOutput(record.output);
  // An answer that carries an output nobody could have stored is not one to apply.
  if (record.output !== null && record.output !== undefined && output === null) return null;
  const raw = record.calibration;
  if (raw !== null && raw !== undefined && (typeof raw !== 'object' || Array.isArray(raw))) return null;
  return { output, calibration: setupCalibration(raw) };
}

export class PreviewSetupStorage implements PreviewOutputStorage {
  private readonly api: PreviewSetupApi | undefined;
  private readonly values = new Map<string, string>();
  /** A choice made before the host answered is this session's, so it wins. */
  private written = false;
  private loading: Promise<boolean> | null = null;

  constructor(api: PreviewSetupApi | undefined) { this.api = api; }

  getItem(key: string): string | null { return this.values.get(key) ?? null; }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
    this.written = true;
    this.send();
  }

  /** S14 (b): asks the host once; true when its answer became the stored value. */
  load(): Promise<boolean> {
    if (this.loading === null) this.loading = this.fetch();
    return this.loading;
  }

  /** The whole current value, in the S14 (a) shape the host validates. */
  setup(): PreviewSetup {
    let output: PreviewSetup['output'] = null;
    try { output = setupOutput(JSON.parse(this.values.get(STORAGE_KEY) ?? 'null')); }
    catch { output = null; }
    let calibration: PreviewSetup['calibration'] = {};
    try { calibration = setupCalibration(JSON.parse(this.values.get(CALIBRATION_STORAGE_KEY) ?? 'null')); }
    catch { calibration = {}; }
    return { output, calibration };
  }

  private async fetch(): Promise<boolean> {
    const get = this.api?.getPreviewSetup;
    if (typeof get !== 'function') return false;
    let answer: unknown;
    try { answer = await get.call(this.api); }
    catch { return false; }
    const setup = readSetup(answer);
    if (setup === null || this.written) return false;
    this.values.set(STORAGE_KEY, JSON.stringify(setup.output));
    this.values.set(CALIBRATION_STORAGE_KEY, JSON.stringify(setup.calibration));
    return true;
  }

  private send(): void {
    const save = this.api?.savePreviewSetup;
    if (typeof save !== 'function') return;
    try {
      void Promise.resolve(save.call(this.api, this.setup())).catch(() => {});
    } catch { /* a host that refuses keeps the choice for this session only */ }
  }
}

export function createPreviewSetupStorage(api: PreviewSetupApi | undefined): PreviewSetupStorage {
  return new PreviewSetupStorage(api);
}
