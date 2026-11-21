/**
 * S5: the Live screen follows what Serato is playing.
 *
 * This module only keeps the polling discipline around the core's read-only `liveFollow`
 * answer (S3): never two requests at once, every three seconds, stopped when the screen is
 * left or the switch is off, and a redraw only when the playing tracks change. It never
 * computes a suggestion and never touches Serato.
 */
import type { Track } from './model.js';

export type LiveFollowReason = 'serato_not_found' | 'serato_busy' | 'serato_unreadable' | 'no_session' | 'nothing_playing' | 'not_in_library';

const reasons: LiveFollowReason[] = ['serato_not_found', 'serato_busy', 'serato_unreadable', 'no_session', 'nothing_playing', 'not_in_library'];

/** One open Serato entry: a library track, or the fields Serato itself knows. */
export interface LiveFollowPlaying {
  deck: number | string;
  startedAt: string;
  inLibrary: boolean;
  id?: string;
  title?: string;
  artist?: string;
  bpm?: number | null;
  key?: string | null;
  energy?: number | null;
}

export interface LiveFollowSuggestion extends Track { score: number; }

/** The exact S3 answer; `reason` is null whenever the answer carries suggestions. */
export interface LiveFollowAnswer {
  available: boolean;
  reason: LiveFollowReason | null;
  sessionStartedAt: string | null;
  playing: LiveFollowPlaying[];
  current: Track | null;
  /** S10: the deck `current` comes from, the requested deck, or null. */
  currentDeck?: number | string | null;
  suggestions: LiveFollowSuggestion[];
  playedCount: number;
}

/** S10: the only parameter the core accepts, and only when a deck is chosen. */
export interface LiveFollowDeckInput { deck: string; }
export type LiveFollowInput = Record<string, never> | LiveFollowDeckInput;

/** Optional until the host ships the bridge route: without it the section stays inert. */
export interface LiveFollowApi { liveFollow?(input: LiveFollowInput): Promise<LiveFollowAnswer>; }
export interface LiveFollowHost { canAct(): boolean; changed(): void; }

/** Injected so tests drive the clock instead of waiting three seconds. */
export interface LiveFollowClock { every(intervalMs: number, callback: () => void): () => void; }

export const LIVE_FOLLOW_INTERVAL_MS = 3000;

const browserClock: LiveFollowClock = {
  every: (intervalMs, callback) => { const handle = globalThis.setInterval(callback, intervalMs); return () => globalThis.clearInterval(handle); },
};

export const FOLLOW_MESSAGES: Record<LiveFollowReason, string> = {
  serato_not_found: 'No se encontró el historial de Serato DJ en este equipo.',
  serato_busy: 'No se pudo leer el historial de Serato. Se reintenta solo.',
  serato_unreadable: 'No se pudo leer el historial de Serato. Se reintenta solo.',
  no_session: 'Carga una pista en Serato para ver sugerencias.',
  nothing_playing: 'Carga una pista en Serato para ver sugerencias.',
  not_in_library: '',
};

const unknownTitle = 'Sin título';
const unknownArtist = 'Artista desconocido';

/**
 * S10: a deck is 1 to 8 letters or digits. Anything else is no deck at all, so a stray value
 * never becomes a parameter the core would have to reject.
 */
export function deckOf(value: number | string | null | undefined): string | null {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  const text = String(value).trim();
  return /^[A-Za-z0-9]{1,8}$/.test(text) ? text : null;
}

/** The newest open entry: the one S3 calls the playing track when nothing is in the library. */
function newestPlaying(playing: LiveFollowPlaying[]): LiveFollowPlaying | null {
  let newest: LiveFollowPlaying | null = null;
  for (const entry of playing) if (!newest || String(entry.startedAt ?? '') >= String(newest.startedAt ?? '')) newest = entry;
  return newest;
}

/** The line a reason shows; `not_in_library` names the track that is not in the library. */
export function liveFollowMessage(answer: LiveFollowAnswer | null, reason: LiveFollowReason | null): string {
  if (!reason) return '';
  if (reason === 'not_in_library') {
    const entry = newestPlaying(answer?.playing ?? []);
    return `La pista que suena no está en tu biblioteca: ${entry?.title || unknownTitle} — ${entry?.artist || unknownArtist}.`;
  }
  return FOLLOW_MESSAGES[reason];
}

/** Identity of what the section draws: the current track, the playing tracks, the reason and the chosen deck. */
export function followKey(answer: LiveFollowAnswer | null, reason: LiveFollowReason | null, deck: string | null = null): string {
  if (!answer) return JSON.stringify([reason ? `reason:${reason}` : '', deck]);
  // S10: the table heading names `current`, so a new current track is a new drawing even when
  // the same decks keep playing.
  const current = answer.current ? [answer.current.id, answer.current.title ?? '', answer.current.artist ?? ''] : null;
  const playing = answer.playing.map((entry) => [
    deckOf(entry.deck), entry.startedAt, entry.inLibrary,
    entry.id ?? '', entry.title ?? '', entry.artist ?? '', entry.bpm ?? null, entry.key ?? null,
  ]);
  return JSON.stringify([reason, deck, current, playing]);
}

/** A payload from an older or partial core never becomes a fabricated answer. */
function normalize(value: unknown): LiveFollowAnswer | null {
  const raw = value as Partial<LiveFollowAnswer> | null;
  if (!raw || typeof raw !== 'object') return null;
  const playing = Array.isArray(raw.playing)
    ? raw.playing.filter((entry): entry is LiveFollowPlaying => Boolean(entry) && typeof entry === 'object' && entry.deck !== undefined)
      .map((entry) => ({ ...entry, deck: entry.deck as number | string, startedAt: String(entry.startedAt ?? ''), inLibrary: entry.inLibrary === true }))
    : [];
  const suggestions = Array.isArray(raw.suggestions)
    ? raw.suggestions.filter((item): item is LiveFollowSuggestion => Boolean(item) && typeof item === 'object' && typeof item.id === 'string' && Number.isFinite(item.score))
    : [];
  const reason = reasons.includes(raw.reason as LiveFollowReason) ? raw.reason as LiveFollowReason : null;
  return {
    available: raw.available === true,
    reason,
    sessionStartedAt: typeof raw.sessionStartedAt === 'string' ? raw.sessionStartedAt : null,
    playing,
    current: raw.current && typeof raw.current === 'object' && typeof raw.current.id === 'string' ? raw.current as Track : null,
    currentDeck: typeof raw.currentDeck === 'number' || typeof raw.currentDeck === 'string' ? raw.currentDeck : null,
    suggestions,
    playedCount: typeof raw.playedCount === 'number' && Number.isFinite(raw.playedCount) ? raw.playedCount : 0,
  };
}

/**
 * The polling owner: the Live screen starts it on entry, stops it on exit, and the switch
 * turns it off without leaving the screen. A failed read keeps polling, because the core
 * answers `serato_busy` while another job runs and never asks the user to retry by hand.
 */
export class LiveFollowController {
  private value: LiveFollowAnswer | null = null;
  private failure: LiveFollowReason | null = null;
  private chosen: string | null = null;
  private enabled = true;
  private running = false;
  private cancel: (() => void) | null = null;
  private generation = 0;
  private drawn = '';
  pending = false;
  constructor(private readonly api: LiveFollowApi, private readonly host: LiveFollowHost, private readonly clock: LiveFollowClock = browserClock) {}
  get answer(): LiveFollowAnswer | null { return this.value; }
  get reason(): LiveFollowReason | null { return this.failure ?? this.value?.reason ?? null; }
  get message(): string { return liveFollowMessage(this.value, this.reason); }
  get following(): boolean { return this.enabled; }
  get polling(): boolean { return this.running && this.enabled && this.cancel !== null; }
  get key(): string { return followKey(this.value, this.reason, this.chosen); }
  /** S10: the deck the user clicked, or null while the newest deck is followed. */
  get chosenDeck(): string | null { return this.chosen; }
  /** False while the host has not shipped `liveFollow`: the section renders without requests. */
  get available(): boolean { return typeof this.api?.liveFollow === 'function'; }

  start(): void {
    if (this.running) return;
    this.running = true;
    if (!this.available || !this.enabled) return;
    this.ask();
    this.arm();
  }
  stop(): void {
    if (!this.running) return;
    this.running = false;
    // The choice lasts while the Live screen is open: leaving returns to the newest deck.
    this.chosen = null;
    // Anything still in flight belongs to the screen that was left.
    this.generation += 1;
    this.disarm();
  }
  /**
   * S10: follows one deck. The click asks at once instead of waiting for the next poll, and an
   * answer already in flight for the previous deck is dropped so it never reaches the screen.
   * A null deck (the «Automático» button) goes back to the newest open entry.
   */
  chooseDeck(deck: number | string | null | undefined): void {
    const next = deckOf(deck);
    if (next === this.chosen) return;
    this.chosen = next;
    this.generation += 1;
    // The armed timer stays: every later poll builds its parameter from the chosen deck.
    if (this.running && this.enabled && this.available) { this.ask(); this.arm(); }
    this.publish();
  }
  setFollowing(following: boolean): void {
    if (this.enabled === following) return;
    this.enabled = following;
    this.generation += 1;
    this.disarm();
    if (this.running && following && this.available) { this.ask(); this.arm(); }
    this.host.changed();
  }
  private arm(): void { if (this.cancel === null) this.cancel = this.clock.every(LIVE_FOLLOW_INTERVAL_MS, () => this.ask()); }
  private disarm(): void { if (this.cancel !== null) { this.cancel(); this.cancel = null; } }
  private ask(): void {
    if (!this.running || !this.enabled || this.pending || !this.available || !this.host.canAct()) return;
    const liveFollow = this.api.liveFollow as (input: LiveFollowInput) => Promise<LiveFollowAnswer>;
    const input: LiveFollowInput = this.chosen === null ? {} : { deck: this.chosen };
    const generation = this.generation;
    this.pending = true;
    Promise.resolve().then(() => liveFollow(input)).then(
      (value) => { if (generation === this.generation) this.accept(value); },
      () => { if (generation === this.generation) this.fail(); },
    ).finally(() => { this.pending = false; });
  }
  private accept(value: unknown): void {
    const next = normalize(value);
    if (!next) { this.fail(); return; }
    this.value = next;
    this.failure = null;
    this.publish();
  }
  private fail(): void {
    // The fixed line only: a transport error must never reach the screen with a path.
    this.failure = 'serato_unreadable';
    this.publish();
  }
  private publish(): void {
    const key = this.key;
    if (key === this.drawn) return;
    this.drawn = key;
    this.host.changed();
  }
}
