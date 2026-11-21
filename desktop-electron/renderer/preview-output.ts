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

/** S12 (a): the Rane FOUR, by the name its device label carries. */
export const RANE_FOUR_NAME = 'Rane FOUR';
/** S12 (a): the mixer's channels in its physical order, left to right. */
export const RANE_FOUR_CHANNELS: readonly number[] = [3, 1, 2, 4];
/** S12 (c): the channel the Rane FOUR starts on when the user picks it. */
export const PRESELECTED_CHANNEL = 3;

export interface MixerChannel { number: number; pair: string; }

/** S12 (b): a deck of the last `liveFollow` answer, reduced to what a mark needs. */
export interface PreviewPlaying { deck: number | string; title?: string | null; }

export interface MixerChannelOption extends MixerChannel { caption: string; occupied: boolean; }

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
  readonly currentTime?: number;
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
  /** S12 (a): «Canal 3», «Canal 1», «Canal 2», «Canal 4» for the Rane FOUR, none otherwise. */
  readonly channels: readonly MixerChannel[];
  /** S12: the channel the stored pair means on this output, or null when it is not one. */
  readonly channel: number | null;
  readonly available: boolean;
  readonly message: string;
  refresh(): Promise<void>;
  select(label: string | null): void;
  selectPair(pair: string): void;
  /** S12 (c): choosing a channel chooses its pair; the stored value stays `{label, pair}`. */
  selectChannel(channel: number): void;
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

/** S12 (a): channel n takes the pair (2n-1)-(2n). */
export function channelPair(channel: number): string | null {
  if (!Number.isInteger(channel) || channel < 1) return null;
  return `${channel * 2 - 1}-${channel * 2}`;
}

/** S12 (a): four channels for the Rane FOUR — never 9-10 to 13-14 — and none for any other output. */
export function mixerChannels(label: string | null | undefined): readonly MixerChannel[] {
  if (typeof label !== 'string' || !label.includes(RANE_FOUR_NAME)) return [];
  return RANE_FOUR_CHANNELS.map((number) => ({ number, pair: channelPair(number) as string }));
}

/** S12: the channel a pair means, or null when no channel of this mixer uses it. */
export function channelOfPair(channels: readonly MixerChannel[], pair: string): number | null {
  return channels.find((entry) => entry.pair === pair)?.number ?? null;
}

const channelTitle = (entry: PreviewPlaying): string => typeof entry.title === 'string' && entry.title.trim() ? entry.title.trim() : 'Sin título';

/**
 * S12 (b): deck n is channel n. An answer marks every channel free or occupied; without an
 * answer there is no mark, so the screen never claims what Serato did not say.
 */
export function channelOptions(channels: readonly MixerChannel[], playing: readonly PreviewPlaying[] | null | undefined): MixerChannelOption[] {
  const answer = Array.isArray(playing) ? playing : null;
  return channels.map((channel) => {
    const name = `Canal ${channel.number}`;
    if (answer === null) return { ...channel, caption: name, occupied: false };
    const entry = answer.find((item) => String(item?.deck ?? '').trim() === String(channel.number));
    if (!entry) return { ...channel, caption: `${name} · libre`, occupied: false };
    return { ...channel, caption: `${name} · ocupado: ${channelTitle(entry)}`, occupied: true };
  });
}

/** S12 (e): the Rane FOUR's own line, naming the chosen channel. */
export function channelHint(channel: number): string {
  return `Baja el fader del canal ${channel} y activa su CUE para oír la preescucha solo en los auriculares.`;
}

/** S12 (d): a notice, never a block, for the chosen channel that Serato has a track on. */
export function channelNotice(channels: readonly MixerChannel[], channel: number | null | undefined, playing: readonly PreviewPlaying[] | null | undefined): string {
  if (channel === null || channel === undefined) return '';
  const option = channelOptions(channels, playing).find((entry) => entry.number === channel);
  return option?.occupied ? `El canal ${channel} tiene una pista cargada en Serato: al activar su CUE vas a oír las dos.` : '';
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

/**
 * S11 (f): an audio element attached to Web Audio only sounds through that context, and it
 * can be attached once. So the element has one context and one source for its whole life;
 * changing the output changes the device of that context (`setSinkId`, `''` = system).
 */
interface Route {
  element: { pause?: () => void };
  context: PreviewAudioContext;
  source: PreviewAudioNode;
  splitter: PreviewAudioNode;
  merger: PreviewAudioNode | null;
  /** The device the context plays on: a device id, or `''` for the system output. */
  sink: string;
}

export class PreviewOutput implements PreviewOutputController {
  private readonly deps: PreviewOutputDeps;
  private options: PreviewOutputOption[] = [];
  private chosen: string | null = null;
  private chosenPair = DEFAULT_PAIR;
  private channelCount = 0;
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
  get pairs(): readonly string[] { return stereoPairs(this.channelCount); }
  get channels(): readonly MixerChannel[] { return mixerChannels(this.chosen); }
  get channel(): number | null { return channelOfPair(this.channels, this.chosenPair); }
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
    const wasSelectable = this.selectable;
    this.selectable = this.chosen === null || this.options.some((option) => option.label === this.chosen);
    if (this.selectable && this.chosen !== null) this.channelCount = this.channelCountOf(this.chosen);
    else if (!this.selectable) this.channelCount = 0;
    // S11 (f): the chosen output left while a preview may be playing: silence it at once.
    if (wasSelectable && !this.selectable) this.silence();
    this.normalizePair();
    this.notify();
  }

  select(label: string | null): void {
    const next = !label || label === SYSTEM_OUTPUT ? null : label;
    const picked = next !== this.chosen;
    this.chosen = next;
    this.selectable = next === null || this.options.some((option) => option.label === next);
    this.channelCount = next === null || !this.selectable ? 0 : this.channelCountOf(next);
    // S12 (c): the one automatic choice. Picking the Rane FOUR preselects «Canal 3»; every
    // other change, and every later Serato answer, leaves the chosen channel alone.
    const preset = picked ? mixerChannels(next).find((entry) => entry.number === PRESELECTED_CHANNEL) : undefined;
    if (preset) this.chosenPair = preset.pair;
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

  /** S12 (c): a channel is only another way to choose its pair. */
  selectChannel(channel: number): void {
    const match = mixerChannels(this.chosen).find((entry) => entry.number === channel);
    if (match) this.selectPair(match.pair);
  }

  /** S11 (d): true only when a playback may start; a chosen output never falls back. */
  async prepare(element: HTMLAudioElement): Promise<boolean> {
    if (!this.selectable) return false;
    try {
      // Before the element was ever routed, the system output needs no graph at all.
      if (this.chosen === null) { if (this.route !== null) await this.routeSystem(this.route); return true; }
      await this.build(element);
      return true;
    } catch { this.silence(); return false; }
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
        // The destination must carry every channel of the device, discrete: with its default
        // of two channels it folds the merger down and every pair sounds on 1-2.
        const destination = context.destination;
        destination.channelCount = destination.maxChannelCount;
        destination.channelCountMode = 'explicit';
        destination.channelInterpretation = 'discrete';
        const merger = context.createChannelMerger(destination.maxChannelCount);
        const [left, right] = pairChannels(this.chosenPair) ?? [0, 1];
        // The tone is mono: the same signal to both channels of the pair.
        gain.connect(merger, 0, left);
        gain.connect(merger, 0, right);
        merger.connect(destination);
      }
      // `onended` is not part of the routing subset, so it is set on the concrete node.
      const ended = oscillator as unknown as { onended: (() => void) | null };
      ended.onended = () => { oscillator.disconnect(); gain.disconnect(); };
      // Times are on the context's own clock, which runs from the moment it was opened.
      const now = context.currentTime ?? 0;
      oscillator.start(now);
      oscillator.stop(now + TONE_SECONDS);
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
    const pairs = stereoPairs(this.channelCount);
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
  private async build(element: HTMLAudioElement): Promise<void> {
    const option = this.options.find((entry) => entry.label === this.chosen);
    if (!option) throw new Error('preview output is not listed');
    if (this.route === null) {
      // The context already opened on this device to count its channels becomes the element's
      // own; it leaves the per-device map because it may later move to another device.
      const context = this.contexts.get(option.label) ?? this.deps.createAudioContext({ sinkId: option.deviceId });
      this.contexts.delete(option.label);
      this.route = {
        element, context, sink: option.deviceId, merger: null,
        source: context.createMediaElementSource(element),
        splitter: context.createChannelSplitter(2),
      };
    }
    const route = this.route;
    this.disconnect(route);
    if (route.sink !== option.deviceId) await this.moveTo(route, option.deviceId);
    const destination = route.context.destination;
    destination.channelCount = destination.maxChannelCount;
    destination.channelCountMode = 'explicit';
    destination.channelInterpretation = 'discrete';
    if (route.merger === null) route.merger = route.context.createChannelMerger(destination.maxChannelCount);
    const [left, right] = pairChannels(this.chosenPair) ?? [0, 1];
    route.source.connect(route.splitter);
    route.splitter.connect(route.merger, 0, left);
    route.splitter.connect(route.merger, 1, right);
    route.merger.connect(destination);
  }

  /** S11 (f): back to the system output: the same context, moved to the default device, in stereo. */
  private async routeSystem(route: Route): Promise<void> {
    this.disconnect(route);
    if (route.sink !== '') await this.moveTo(route, '');
    const destination = route.context.destination;
    destination.channelCount = Math.min(2, destination.maxChannelCount);
    destination.channelCountMode = 'explicit';
    destination.channelInterpretation = 'speakers';
    route.source.connect(destination);
  }

  /** Nothing is connected while the device changes, so no sound reaches either device. */
  private async moveTo(route: Route, sink: string): Promise<void> {
    if (!route.context.setSinkId) throw new Error('the audio context cannot change its output');
    await route.context.setSinkId(sink);
    route.sink = sink;
    route.merger = null;
  }

  private disconnect(route: Route): void {
    route.source.disconnect();
    route.splitter.disconnect();
    route.merger?.disconnect();
  }

  /** Cut the sound of the routed element and pause it. */
  private silence(): void {
    const route = this.route;
    if (!route) return;
    this.disconnect(route);
    try { route.element.pause?.(); } catch { /* an element that cannot pause is already silent */ }
  }

  private teardown(): void {
    const route = this.route;
    this.route = null;
    if (!route) return;
    this.disconnect(route);
    void route.context.close?.();
  }
}

export function createPreviewOutput(deps: PreviewOutputDeps): PreviewOutput {
  return new PreviewOutput(deps);
}
