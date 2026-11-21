/**
 * S11 (b)-(e): the preview output and channel pair.
 *
 * The browser stays outside: `enumerateDevices`, the `AudioContext` factory, the storage and
 * the device-change listener arrive as arguments, so the routing is tested with fakes. The
 * host answers the `speaker-selection` check and lets the app page read `xfin-audio:` with
 * `Access-Control-Allow-Origin`, which is why the audio element needs `crossOrigin`.
 */

export const SYSTEM_OUTPUT = 'Salida del sistema';
export const STORAGE_KEY = 'xfin.preview-output';
export const TONE_HZ = 440;
export const TONE_SECONDS = 1;
export const TONE_GAIN = 0.05;
const DEFAULT_PAIR = '1-2';

export interface PreviewOutputOption { label: string; deviceId: string; }

export interface MediaDeviceLike { deviceId: string; kind: string; label: string; }

export interface PreviewAudioNode {
  connect(target: PreviewAudioNode, output?: number, input?: number): unknown;
  disconnect(): void;
}

export interface PreviewDestination extends PreviewAudioNode {
  channelCount: number;
  maxChannelCount: number;
  channelCountMode: string;
  channelInterpretation: string;
}

export interface PreviewOscillator extends PreviewAudioNode {
  frequency: { value: number };
  start(when?: number): void;
  stop(when?: number): void;
}

export interface PreviewGainNode extends PreviewAudioNode { gain: { value: number }; }

export interface PreviewAudioContext {
  destination: PreviewDestination;
  createMediaElementSource(element: unknown): PreviewAudioNode;
  createChannelSplitter(count: number): PreviewAudioNode;
  createChannelMerger(count: number): PreviewAudioNode;
  createGain(): PreviewGainNode;
  createOscillator(): PreviewOscillator;
  close?(): Promise<void>;
  setSinkId?(deviceId: string): Promise<void>;
}

export interface PreviewOutputStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface PreviewOutputDeps {
  enumerateDevices(): Promise<readonly MediaDeviceLike[]>;
  createAudioContext(options: { sinkId?: string }): PreviewAudioContext;
  storage: PreviewOutputStorage;
  /** S11 (b): the list is rebuilt on `devicechange`; absent means no live re-listing. */
  listenDeviceChange?(listener: () => void): () => void;
  changed?(): void;
}

export interface PreviewOutputController {
  readonly outputs: readonly PreviewOutputOption[];
  readonly label: string | null;
  readonly pair: string;
  readonly pairs: readonly string[];
  readonly available: boolean;
  readonly message: string;
  refresh(): Promise<void>;
  select(label: string | null): void;
  selectPair(pair: string): void;
  prepare(element: HTMLAudioElement): Promise<boolean>;
  tone(): void;
  dispose(): void;
}

/** S11 (b): audio outputs with a label, never the empty `default` entry. */
export function outputOptions(devices: readonly MediaDeviceLike[]): PreviewOutputOption[] {
  const seen = new Set<string>();
  const options: PreviewOutputOption[] = [];
  for (const entry of devices) {
    if (entry.kind !== 'audiooutput' || entry.deviceId === 'default' || !entry.deviceId) continue;
    const label = typeof entry.label === 'string' ? entry.label.trim() : '';
    if (!label || seen.has(entry.deviceId)) continue;
    seen.add(entry.deviceId);
    options.push({ label, deviceId: entry.deviceId });
  }
  return options;
}

/** S11 (c): one option per stereo pair, «1-2», «3-4», … up to the channel count. */
export function stereoPairs(channelCount: number): string[] {
  if (!Number.isInteger(channelCount) || channelCount < 2) return [];
  const pairs: string[] = [];
  for (let channel = 1; channel + 1 <= channelCount; channel += 2) pairs.push(`${channel}-${channel + 1}`);
  return pairs;
}

/** The 1-based channels of a pair as 0-based merger inputs; `null` when it is not a pair. */
export function pairChannels(pair: string): [number, number] | null {
  const match = /^(\d+)-(\d+)$/.exec(pair);
  if (!match) return null;
  const left = Number(match[1]); const right = Number(match[2]);
  if (!Number.isInteger(left) || left < 1 || right !== left + 1) return null;
  return [left - 1, right - 1];
}

function readStored(storage: PreviewOutputStorage): { label: string | null; pair: string } {
  const fallback = { label: null, pair: DEFAULT_PAIR };
  let parsed: unknown;
  try { parsed = JSON.parse(storage.getItem(STORAGE_KEY) ?? 'null'); }
  catch { return fallback; }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return fallback;
  const record = parsed as Record<string, unknown>;
  const label = record.label === null ? null : typeof record.label === 'string' && record.label.trim() ? record.label : undefined;
  const pair = typeof record.pair === 'string' && pairChannels(record.pair) ? record.pair : undefined;
  if (label === undefined || pair === undefined) return fallback;
  return { label, pair };
}

interface Route {
  context: PreviewAudioContext;
  source: PreviewAudioNode;
  splitter: PreviewAudioNode;
  merger: PreviewAudioNode;
}

export class PreviewOutput implements PreviewOutputController {
  private readonly deps: PreviewOutputDeps;
  private options: PreviewOutputOption[] = [];
  private chosen: string | null = null;
  private chosenPair = DEFAULT_PAIR;
  private channels = 0;
  private selectable = true;
  private listed = false;
  private readonly contexts = new Map<string, PreviewAudioContext>();
  private system: PreviewAudioContext | null = null;
  private route: Route | null = null;
  private stopListening: (() => void) | null = null;

  constructor(deps: PreviewOutputDeps) {
    this.deps = deps;
    const stored = readStored(deps.storage);
    this.chosen = stored.label;
    this.chosenPair = stored.pair;
    this.selectable = stored.label === null;
    const listen = deps.listenDeviceChange;
    if (listen) this.stopListening = listen(() => { void this.refresh(); });
  }

  get outputs(): readonly PreviewOutputOption[] { return this.options; }
  get label(): string | null { return this.chosen; }
  get pair(): string { return this.chosenPair; }
  get pairs(): readonly string[] { return stereoPairs(this.channels); }
  get available(): boolean { return this.selectable; }
  /** S11 (e): only a chosen output that left the list has something to say. */
  get message(): string {
    return this.listed && this.chosen !== null && !this.selectable
      ? `${this.chosen} no está conectado. La preescucha está deshabilitada.` : '';
  }

  async refresh(): Promise<void> {
    let devices: readonly MediaDeviceLike[] = [];
    try { devices = await this.deps.enumerateDevices(); }
    catch { devices = []; }
    this.options = outputOptions(devices);
    this.listed = true;
    this.selectable = this.chosen === null || this.options.some((option) => option.label === this.chosen);
    if (this.selectable && this.chosen !== null) this.channels = this.channelCountOf(this.chosen);
    else if (!this.selectable) this.channels = 0;
    this.normalizePair();
    this.notify();
  }

  select(label: string | null): void {
    const next = !label || label === SYSTEM_OUTPUT ? null : label;
    this.chosen = next;
    this.selectable = next === null || this.options.some((option) => option.label === next);
    this.channels = next === null || !this.selectable ? 0 : this.channelCountOf(next);
    this.normalizePair();
    this.persist();
    this.notify();
  }

  selectPair(pair: string): void {
    if (!pairChannels(pair)) return;
    this.chosenPair = pair;
    this.persist();
    this.notify();
  }

  /** S11 (d): true only when a playback may start; a chosen output never falls back. */
  async prepare(element: HTMLAudioElement): Promise<boolean> {
    if (this.chosen === null) return true;
    if (!this.selectable) return false;
    try { this.build(element); return true; }
    catch { return false; }
  }

  /** S11 (c): a one-second quiet tone on exactly the chosen output and pair. */
  tone(): void {
    try {
      if (this.chosen !== null && !this.selectable) return;
      const context = this.chosen === null ? this.systemContext() : this.contextFor(this.chosen);
      if (context === null) return;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.frequency.value = TONE_HZ;
      gain.gain.value = TONE_GAIN;
      oscillator.connect(gain);
      if (this.chosen === null) gain.connect(context.destination);
      else {
        const splitter = context.createChannelSplitter(2);
        const merger = context.createChannelMerger(context.destination.maxChannelCount);
        const [left, right] = pairChannels(this.chosenPair) ?? [0, 1];
        gain.connect(splitter);
        splitter.connect(merger, 0, left);
        splitter.connect(merger, 1, right);
        merger.connect(context.destination);
      }
      // `onended` is not part of the routing subset, so it is set on the concrete node.
      const ended = oscillator as unknown as { onended: (() => void) | null };
      ended.onended = () => { oscillator.disconnect(); gain.disconnect(); };
      oscillator.start(0);
      oscillator.stop(TONE_SECONDS);
    } catch { /* a device that cannot be opened simply does not beep */ }
  }

  dispose(): void {
    this.stopListening?.();
    this.stopListening = null;
    this.teardown();
    for (const context of this.contexts.values()) void context.close?.();
    this.contexts.clear();
    void this.system?.close?.();
    this.system = null;
  }

  private notify(): void { this.deps.changed?.(); }

  private persist(): void {
    try { this.deps.storage.setItem(STORAGE_KEY, JSON.stringify({ label: this.chosen, pair: this.chosenPair })); }
    catch { /* a storage that refuses keeps the choice for this session only */ }
  }

  private normalizePair(): void {
    const pairs = stereoPairs(this.channels);
    if (pairs.length > 0 && !pairs.includes(this.chosenPair)) this.chosenPair = pairs[0];
  }

  private contextFor(label: string): PreviewAudioContext | null {
    const existing = this.contexts.get(label);
    if (existing) return existing;
    const option = this.options.find((entry) => entry.label === label);
    if (!option) return null;
    const context = this.deps.createAudioContext({ sinkId: option.deviceId });
    this.contexts.set(label, context);
    return context;
  }

  private systemContext(): PreviewAudioContext {
    if (this.system === null) this.system = this.deps.createAudioContext({});
    return this.system;
  }

  /** The channel count of an output comes from the device itself, opened at its sink id. */
  private channelCountOf(label: string): number {
    try {
      const context = this.contextFor(label);
      const count = context?.destination.maxChannelCount ?? 0;
      return Number.isInteger(count) && count > 0 ? count : 0;
    } catch { return 0; }
  }

  /** Left to the first channel of the pair, right to the second, silence on every other one. */
  private build(element: HTMLAudioElement): void {
    const label = this.chosen;
    if (label === null) return;
    const context = this.contextFor(label);
    if (context === null) throw new Error('preview output is not listed');
    if (this.route !== null && this.route.context !== context) this.teardown();
    if (this.route === null) {
      const destination = context.destination;
      destination.channelCount = destination.maxChannelCount;
      destination.channelCountMode = 'explicit';
      destination.channelInterpretation = 'discrete';
      this.route = {
        context,
        source: context.createMediaElementSource(element),
        splitter: context.createChannelSplitter(2),
        merger: context.createChannelMerger(destination.maxChannelCount),
      };
    }
    const route = this.route;
    const [left, right] = pairChannels(this.chosenPair) ?? [0, 1];
    route.splitter.disconnect();
    route.merger.disconnect();
    route.source.disconnect();
    route.source.connect(route.splitter);
    route.splitter.connect(route.merger, 0, left);
    route.splitter.connect(route.merger, 1, right);
    route.merger.connect(context.destination);
  }

  private teardown(): void {
    const route = this.route;
    this.route = null;
    if (!route) return;
    route.source.disconnect();
    route.splitter.disconnect();
    route.merger.disconnect();
    for (const [label, context] of this.contexts) {
      if (context !== route.context) continue;
      this.contexts.delete(label);
      void context.close?.();
    }
  }
}

export function createPreviewOutput(deps: PreviewOutputDeps): PreviewOutput {
  return new PreviewOutput(deps);
}
