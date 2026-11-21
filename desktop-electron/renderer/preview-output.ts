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

// ---- S13 (a): the calibration of any controller ----

/** S13 (a): where a calibration lives, per output label and pair. */
export const CALIBRATION_STORAGE_KEY = 'xfin.preview-calibration';
/** S13 (b): the select of a calibrated output. */
export const DESTINATION_LABEL = 'Destino de la preescucha';
/** S13 (b): the calibrated headphones pair, first in the list. */
export const PHONES_DESTINATION = 'Auriculares';
/** S13 (c): the line for a calibrated headphones pair. */
export const PHONES_HINT = 'La preescucha suena directo en los auriculares.';
/** S13 (b): a calibration that offers no pair at all disables the preview. */
export const NO_DESTINATION_MESSAGE = 'La calibración no encontró ninguna salida para la preescucha. Vuelve a calibrar.';
/** S13 (a): the mixer channels a calibration may name. */
export const CALIBRATION_CHANNELS: readonly number[] = [1, 2, 3, 4];

/** S13 (a): a role a pair can hold, as it is written in the stored value. */
export type CalibrationRole = 'phones' | 'room' | 'silent' | `channel:${number}`;
/** S13 (a): one output's calibration: pair → role. */
export type CalibrationRoles = Record<string, CalibrationRole>;
/** S13 (a): every output's calibration: label → pair → role. */
export type Calibration = Record<string, CalibrationRoles>;

/** What an option of the destination select stands for. */
export type DestinationKind = 'phones' | 'channel' | 'pair';

/** S13 (b): one option of the destination select, for the view to render. */
export interface DestinationOption { pair: string; text: string; kind: DestinationKind; }

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
  /**
   * S12 (a): «Canal 3», «Canal 1», «Canal 2», «Canal 4» for the Rane FOUR, none otherwise.
   * S13 (b): the channels of a calibration when the output has one, since it wins.
   */
  readonly channels: readonly MixerChannel[];
  /** S12: the channel the stored pair means on this output, or null when it is not one. */
  readonly channel: number | null;
  /** S13 (a): the chosen output's calibration, or null when it has none. */
  readonly calibration: CalibrationRoles | null;
  /** S13 (c): the role the calibration gives the chosen pair, or null without one. */
  readonly pairRole: CalibrationRole | null;
  /** S13 (b): «Destino de la preescucha» for a calibrated output, empty otherwise. */
  readonly destinationLabel: string;
  readonly available: boolean;
  /** S13 (d): true while the calibration wizard is open: no preview may start. */
  readonly calibrating: boolean;
  /** S13 (d): false when the chosen output is not connected, so «Calibrar canales» is disabled. */
  readonly connected: boolean;
  readonly message: string;
  /** S13 (b): the one list the view renders for the three cases. */
  destinations(playing?: readonly PreviewPlaying[] | null): readonly DestinationOption[];
  refresh(): Promise<void>;
  select(label: string | null): void;
  selectPair(pair: string): void;
  /** S12 (c): choosing a channel chooses its pair; the stored value stays `{label, pair}`. */
  selectChannel(channel: number): void;
  /** S13 (a): stores the roles of the chosen output; S13 (b): chooses the pair it offers first. */
  saveCalibration(roles: Record<string, unknown>): void;
  /** S13 (e): back to the pairs, or to the Rane FOUR table. */
  clearCalibration(): void;
  /** S13 (d): the wizard's own tone, on the pair of its step, without touching the stored choice. */
  toneOn(pair: string): void;
  /** S13 (d): opens the wizard; every preview is refused until `endCalibration`. */
  beginCalibration(): void;
  endCalibration(): void;
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

/** S13 (a): a role read from the stored value, or null when it is not one. */
export function calibrationRole(value: unknown): CalibrationRole | null {
  if (value === 'phones' || value === 'room' || value === 'silent') return value;
  if (typeof value !== 'string') return null;
  const match = /^channel:([1-4])$/.exec(value);
  if (!match) return null;
  const number = Number(match[1]);
  return CALIBRATION_CHANNELS.includes(number) ? (`channel:${number}` as CalibrationRole) : null;
}

/** S13 (a): the mixer channel a role names, or null for every other role. */
export function roleChannel(role: CalibrationRole | null | undefined): number | null {
  if (typeof role !== 'string') return null;
  const match = /^channel:([1-4])$/.exec(role);
  return match ? Number(match[1]) : null;
}

const exclusiveRole = (role: CalibrationRole): boolean => role === 'phones' || roleChannel(role) !== null;

/**
 * S13 (a): the roles a calibration keeps. Two pairs cannot hold the same channel number nor both
 * be `phones`: assigning one that is taken clears the earlier pair to `silent`.
 */
export function calibrationRoles(value: unknown): CalibrationRoles {
  const roles: CalibrationRoles = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return roles;
  const taken = new Set<CalibrationRole>();
  for (const [pair, raw] of Object.entries(value as Record<string, unknown>)) {
    if (!pairChannels(pair)) continue;
    const role = calibrationRole(raw);
    if (role === null) continue;
    if (exclusiveRole(role)) {
      if (taken.has(role)) {
        for (const [earlier, earlierRole] of Object.entries(roles)) {
          if (earlierRole === role) roles[earlier] = 'silent';
        }
      }
      taken.add(role);
    }
    roles[pair] = role;
  }
  return roles;
}

/** S13 (a): the stored calibrations; an unreadable or malformed value counts as none. */
export function storedCalibration(storage: PreviewOutputStorage): Calibration {
  const calibration: Calibration = {};
  let parsed: unknown;
  try { parsed = JSON.parse(storage.getItem(CALIBRATION_STORAGE_KEY) ?? 'null'); }
  catch { return calibration; }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return calibration;
  for (const [label, value] of Object.entries(parsed as Record<string, unknown>)) {
    if (!label.trim() || !value || typeof value !== 'object' || Array.isArray(value)) continue;
    const roles = calibrationRoles(value);
    // A label whose roles are all unreadable is malformed too: it is no calibration.
    if (Object.keys(roles).length > 0) calibration[label] = roles;
  }
  return calibration;
}

/** S13 (a): the mixer channels a calibration names, ascending by channel number. */
export function calibrationChannels(roles: CalibrationRoles | null | undefined): MixerChannel[] {
  if (!roles) return [];
  const channels: MixerChannel[] = [];
  for (const [pair, role] of Object.entries(roles)) {
    const number = roleChannel(role);
    if (number !== null) channels.push({ number, pair });
  }
  return channels.sort((left, right) => left.number - right.number);
}

/**
 * S13 (b): the pairs a calibration offers — the `phones` pair first as «Auriculares», then the
 * channels ascending with the marks of S12 (b). A pair marked `room` or `silent` is never offered.
 */
export function calibrationDestinations(
  roles: CalibrationRoles | null | undefined,
  playing?: readonly PreviewPlaying[] | null,
): DestinationOption[] {
  if (!roles) return [];
  const destinations: DestinationOption[] = [];
  const phones = Object.entries(roles).find(([, role]) => role === 'phones')?.[0];
  if (phones !== undefined) destinations.push({ pair: phones, text: PHONES_DESTINATION, kind: 'phones' });
  for (const channel of channelOptions(calibrationChannels(roles), playing)) {
    destinations.push({ pair: channel.pair, text: channel.caption, kind: 'channel' });
  }
  return destinations;
}

export interface DestinationSource {
  /** S13 (a): the chosen output's calibration, or null when it has none. */
  calibration: CalibrationRoles | null;
  /** S12 (a): the Rane FOUR's built-in table; empty for every other output. */
  channels: readonly MixerChannel[];
  /** S11 (c): the stereo pairs of the output, from its channel count. */
  pairs: readonly string[];
  /** S12 (b): the decks of the last `liveFollow` answer, or null when there is none. */
  playing?: readonly PreviewPlaying[] | null;
}

/**
 * S13 (b): one list for the three cases — a calibration, the built-in Rane FOUR table, and the
 * plain pairs of any other output. A stored calibration wins over the built-in table.
 */
export function destinationOptions(source: DestinationSource): DestinationOption[] {
  const answer = source.playing ?? null;
  if (source.calibration !== null) return calibrationDestinations(source.calibration, answer);
  if (source.channels.length > 0) {
    return channelOptions(source.channels, answer).map((channel) => ({ pair: channel.pair, text: channel.caption, kind: 'channel' as const }));
  }
  return source.pairs.map((pair) => ({ pair, text: pair, kind: 'pair' as const }));
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
  /** S13 (d): the calibration wizard is open, so no preview may start. */
  private wizard = false;
  private listed = false;
  private readonly contexts = new Map<string, PreviewAudioContext>();
  private system: PreviewAudioContext | null = null;
  private route: Route | null = null;
  private stopListening: (() => void) | null = null;
  private calibrations: Calibration;

  constructor(deps: PreviewOutputDeps) {
    this.deps = deps;
    const stored = readStored(deps.storage);
    this.chosen = stored.label;
    this.chosenPair = stored.pair;
    this.selectable = stored.label === null;
    this.calibrations = storedCalibration(deps.storage);
    const listen = deps.listenDeviceChange;
    if (listen) this.stopListening = listen(() => { void this.refresh(); });
  }

  get outputs(): readonly PreviewOutputOption[] { return this.options; }
  get label(): string | null { return this.chosen; }
  get pair(): string { return this.chosenPair; }
  get pairs(): readonly string[] { return stereoPairs(this.channelCount); }
  /** S13 (b): a calibration's channels replace the built-in table of the Rane FOUR. */
  get channels(): readonly MixerChannel[] {
    const roles = this.calibration;
    return roles === null ? mixerChannels(this.chosen) : calibrationChannels(roles);
  }
  get channel(): number | null { return channelOfPair(this.channels, this.chosenPair); }
  get calibration(): CalibrationRoles | null {
    const label = this.chosen;
    return label !== null && Object.hasOwn(this.calibrations, label) ? this.calibrations[label] : null;
  }
  get pairRole(): CalibrationRole | null { return this.calibration?.[this.chosenPair] ?? null; }
  get destinationLabel(): string { return this.calibration === null ? '' : DESTINATION_LABEL; }
  get calibrating(): boolean { return this.wizard; }
  get connected(): boolean { return this.selectable; }
  get available(): boolean {
    if (!this.selectable) return false;
    // S13 (d): while the wizard is open no preview can start.
    if (this.wizard) return false;
    // S13 (b): a calibration that offers no pair at all disables the preview.
    return this.calibration === null || calibrationDestinations(this.calibration, null).length > 0;
  }
  /**
   * S11 (e): only a chosen output that left the list has something to say.
   * S13 (b): a calibration with no usable pair says so instead.
   * S13 (d): an open wizard has its own words, so nothing is said here.
   */
  get message(): string {
    if (!this.listed || this.chosen === null) return '';
    if (!this.selectable) return `${this.chosen} no está conectado. La preescucha está deshabilitada.`;
    if (this.wizard) return '';
    return this.available ? '' : NO_DESTINATION_MESSAGE;
  }

  /** S13 (b): one list for the three cases, in the order the view renders it. */
  destinations(playing?: readonly PreviewPlaying[] | null): readonly DestinationOption[] {
    return destinationOptions({ calibration: this.calibration, channels: this.channels, pairs: this.pairs, playing: playing ?? null });
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
    // S13 (b): a calibration wins over that table, so picking the output chooses its first pair.
    if (picked) this.chooseCalibratedPair();
    this.normalizePair();
    this.persist();
    this.notify();
  }

  /** S13 (a): stores the chosen output's calibration, validated and with taken roles resolved. */
  saveCalibration(roles: Record<string, unknown>): void {
    const label = this.chosen;
    if (label === null) return;
    this.calibrations[label] = calibrationRoles(roles);
    this.writeCalibrations();
    // S13 (b): the phones pair if there is one, else the lowest-numbered channel pair.
    this.chooseCalibratedPair();
    this.persist();
    this.notify();
  }

  /** S13 (e): the output goes back to its pairs, or to the S12 table for the Rane FOUR. */
  clearCalibration(): void {
    const label = this.chosen;
    if (label === null || !Object.hasOwn(this.calibrations, label)) return;
    delete this.calibrations[label];
    this.writeCalibrations();
    const offered = this.destinations(null);
    if (offered.length > 0 && !offered.some((option) => option.pair === this.chosenPair)) {
      this.chosenPair = offered[0].pair;
    }
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
    const match = this.channels.find((entry) => entry.number === channel);
    if (match) this.selectPair(match.pair);
  }

  /** S11 (d): true only when a playback may start; a chosen output never falls back. */
  async prepare(element: HTMLAudioElement): Promise<boolean> {
    if (!this.available) return false;
    try {
      // Before the element was ever routed, the system output needs no graph at all.
      if (this.chosen === null) { if (this.route !== null) await this.routeSystem(this.route); return true; }
      await this.build(element);
      return true;
    } catch { this.silence(); return false; }
  }

  /** S11 (c): a one-second quiet tone on exactly the chosen output and pair. */
  tone(): void {
    // S13 (d): the wizard sounds its own pair; the «Probar» button waits for it to close.
    if (this.wizard) return;
    if (this.chosen === null) { this.playTone(null); return; }
    if (!this.available) return;
    this.playTone(this.chosenPair);
  }

  /**
   * S13 (d): the tone of a wizard step, on the pair it asks about. It never touches the stored
   * choice, so cancelling leaves the previous pair exactly where it was.
   */
  toneOn(pair: string): void {
    if (this.chosen === null || !this.selectable || !pairChannels(pair)) return;
    this.playTone(pair);
  }

  /** S13 (d): open, so `available` refuses every preview until `endCalibration`. */
  beginCalibration(): void {
    if (this.wizard) return;
    this.wizard = true;
    this.notify();
  }

  endCalibration(): void {
    if (!this.wizard) return;
    this.wizard = false;
    this.notify();
  }

  private playTone(pair: string | null): void {
    try {
      const context = pair === null ? this.systemContext() : this.contextFor(this.chosen as string);
      if (context === null) return;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.frequency.value = TONE_HZ;
      gain.gain.value = TONE_GAIN;
      oscillator.connect(gain);
      if (pair === null) gain.connect(context.destination);
      else {
        // The destination must carry every channel of the device, discrete: with its default
        // of two channels it folds the merger down and every pair sounds on 1-2.
        const destination = context.destination;
        destination.channelCount = destination.maxChannelCount;
        destination.channelCountMode = 'explicit';
        destination.channelInterpretation = 'discrete';
        const merger = context.createChannelMerger(destination.maxChannelCount);
        const [left, right] = pairChannels(pair) ?? [0, 1];
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

  private writeCalibrations(): void {
    try { this.deps.storage.setItem(CALIBRATION_STORAGE_KEY, JSON.stringify(this.calibrations)); }
    catch { /* a storage that refuses keeps the calibration for this session only */ }
  }

  private normalizePair(): void {
    // S13 (b): the pairs the output offers are the ones the select shows, calibration included.
    const offered = this.destinations(null).map((option) => option.pair);
    if (offered.length > 0) { if (!offered.includes(this.chosenPair)) this.chosenPair = offered[0]; return; }
    const pairs = stereoPairs(this.channelCount);
    if (pairs.length > 0 && !pairs.includes(this.chosenPair)) this.chosenPair = pairs[0];
  }

  /** S13 (b): the pair a calibration offers first — `phones`, else the lowest channel. */
  private chooseCalibratedPair(): void {
    const roles = this.calibration;
    if (roles === null) return;
    const offered = calibrationDestinations(roles, null);
    if (offered.length > 0) this.chosenPair = offered[0].pair;
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
