import type { Track } from './model.js';
import { userErrorMessage } from './errors.js';
export interface LiveSnapshot {
  sessionId: string; revision: number; sourceReviewId: string; state: 'active' | 'complete'; current: Track;
  history: { track: Track; startedAt: string }[];
  candidates: { track: Track; score: number; alerts: string[] }[];
  elapsedSeconds: number;
}
export interface LiveApi {
  openLive(input: { reviewId: string }): Promise<LiveSnapshot>;
  getLiveStatus(input: { sessionId: string }): Promise<LiveSnapshot>;
  advanceLive(input: { sessionId: string; revision: number; trackId: string }): Promise<LiveSnapshot>;
  clearLive(input: { sessionId: string }): Promise<{ cleared: true }>;
}
export interface LiveHost {
  canAct(): boolean;
  changed(): void;
  /** Use the app-wide gate, without cancellation; route changes do not discard session results. */
  perform<T>(label: string, task: () => Promise<T>, apply: (value: T, currentRoute: boolean) => void, failure: (error: unknown) => void): Promise<void>;
}
const stale = (): Error & { code: string } => Object.assign(new Error('Live response no longer matches its source'), { code: 'stale_live' });
const matches = (value: LiveSnapshot, reviewId: string): boolean => value.sourceReviewId === reviewId && Boolean(value.sessionId && value.current?.id)
  && Number.isInteger(value.revision) && value.revision >= 0 && Number.isFinite(value.elapsedSeconds) && value.elapsedSeconds >= 0;

/** Manual guidance only. The renderer never builds rankings, infers readiness or starts audio. */
export class LiveController {
  private current: LiveSnapshot | null = null;
  private generation = 0;
  private available = false;
  private api: LiveApi;
  private host: LiveHost;
  pending = false;
  error = '';
  constructor(api: LiveApi, host: LiveHost) { this.api = api; this.host = host; }
  get snapshot(): LiveSnapshot | null { return this.current; }
  get valid(): boolean { return this.available; }
  invalidate(options: { preserveSnapshot?: boolean } = {}): void {
    this.generation++; this.available = false; this.error = '';
    if (!options.preserveSnapshot) this.current = null;
    this.host.changed();
  }
  private async run<T>(label: string, task: () => Promise<T>, apply: (value: T) => void): Promise<void> {
    if (this.pending || !this.host.canAct()) return;
    const generation = this.generation;
    this.pending = true; this.error = ''; this.host.changed();
    const fail = (error: unknown): void => {
      if (generation !== this.generation) return;
      this.available = false; this.error = userErrorMessage(error); this.host.changed();
    };
    try { await this.host.perform(label, task, (value) => { if (generation === this.generation) apply(value); }, fail); }
    catch (error) { fail(error); }
    finally { this.pending = false; this.host.changed(); }
  }
  private accept(value: LiveSnapshot): void { this.current = value; this.available = true; this.error = ''; this.host.changed(); }
  async start(reviewId: string): Promise<void> {
    if (!reviewId || this.pending || !this.host.canAct()) return;
    const previous = this.current;
    const same = this.available && previous?.sourceReviewId === reviewId;
    if (!same) this.invalidate();
    await this.run('Abriendo asistente Live…', () => this.api.openLive({ reviewId }), (value) => {
      if (!matches(value, reviewId) || (same && previous && (value.sessionId !== previous.sessionId || value.revision < previous.revision))) throw stale();
      this.accept(value);
    });
  }
  async refresh(): Promise<void> {
    const previous = this.current;
    if (!previous) return;
    await this.run('Actualizando estado de Live…', () => this.api.getLiveStatus({ sessionId: previous.sessionId }), (value) => {
      if (!matches(value, previous.sourceReviewId) || value.sessionId !== previous.sessionId || value.revision < previous.revision) throw stale();
      this.accept(value);
    });
  }
  async advance(trackId: string): Promise<void> {
    const previous = this.current;
    if (!previous || !this.available || previous.state !== 'active' || !previous.candidates.some((candidate) => candidate.track.id === trackId)) return;
    await this.run('Marcando la siguiente pista…', () => this.api.advanceLive({ sessionId: previous.sessionId, revision: previous.revision, trackId }), (value) => {
      if (!matches(value, previous.sourceReviewId) || value.sessionId !== previous.sessionId || value.revision <= previous.revision || value.current.id !== trackId) throw stale();
      this.accept(value);
    });
  }
  async clear(): Promise<void> {
    const previous = this.current;
    if (!previous || this.pending || !this.host.canAct()) return;
    this.available = false;
    await this.run('Finalizando la sesión de Live…', () => this.api.clearLive({ sessionId: previous.sessionId }), (result) => {
      if (!result.cleared) throw stale();
      this.invalidate();
    });
  }
}

/** Display-only clock: authoritative current-track seconds plus elapsed monotonic time; no polling. */
export class LiveElapsedClock {
  private snapshot: LiveSnapshot | null = null;
  private seconds = 0;
  private at = 0;
  private running = false;
  read(snapshot: LiveSnapshot | null, connected: boolean, now = performance.now()): number {
    if (snapshot !== this.snapshot) {
      this.snapshot = snapshot;
      this.seconds = snapshot && Number.isFinite(snapshot.elapsedSeconds) ? Math.max(0, snapshot.elapsedSeconds) : 0;
    } else if (this.running) this.seconds += Math.max(0, now - this.at) / 1000;
    this.at = now;
    this.running = Boolean(snapshot) && connected;
    return this.seconds;
  }
}
