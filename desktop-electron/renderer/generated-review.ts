import type { Readiness, ReviewResult, Track } from './model.js';
import { errorCode, userErrorMessage } from './errors.js';
export interface ReviewCheck { label: string; status: Readiness; detail: string; }
export interface ReviewTransition { index: number; leftTrackId: string; rightTrackId: string; totalScore: number; compatibilityScore: number | null; mixabilityScore: number | null; components: Record<string, number>; explanations: string[]; warnings: string[]; }
export interface ReviewEvidence { transitions: ReviewTransition[]; readinessChecks: ReviewCheck[]; readinessSummary: string; engineFacts: string; protectedTrackIds?: string[]; }
export interface DetailedReview extends ReviewResult, ReviewEvidence {}
export interface ReviewComparison { reviewId: string; available: boolean; replacement: Track | null; original: ReviewEvidence & { qualityScore: number }; proposed: ReviewEvidence & { qualityScore: number }; message: string; }
export interface GeneratedReviewApi {
  reviewDetails(input: { reviewId: string }): Promise<DetailedReview>;
  reviewCompare(input: { reviewId: string; trackId: string }): Promise<ReviewComparison>;
  reviewRemove(input: { reviewId: string; trackId: string }): Promise<DetailedReview>;
  reviewReorder(input: { reviewId: string; trackIds: string[] }): Promise<DetailedReview>;
}
interface Host { current(): ReviewResult | null; canAct(): boolean; changed(): void; applied(value: DetailedReview): void; perform<T>(label: string, task: () => Promise<T>, apply: (value: T) => void, failure: (error: unknown) => void): Promise<void>; }
export class GeneratedReviewController {
  pending = false;
  error = '';
  private preview: ReviewComparison | null = null;
  constructor(private api: GeneratedReviewApi, private host: Host) {}
  get snapshot(): ReviewResult | null { return this.host.current(); }
  get comparison(): ReviewComparison | null { return this.preview?.reviewId === this.snapshot?.reviewId ? this.preview : null; }
  get details(): ReviewEvidence | null { const value = this.snapshot as Partial<DetailedReview> | null; return value && Array.isArray(value.transitions) && Array.isArray(value.readinessChecks) && typeof value.engineFacts === 'string' ? value as DetailedReview : null; }
  get editable(): boolean { return Boolean(this.snapshot && this.snapshot.variant !== 'saved' && this.snapshot.reviewId); }
  private async run<T>(label: string, task: (review: ReviewResult) => Promise<T>, apply: (value: T) => void): Promise<void> {
    const current = this.snapshot;
    if (!current || !this.editable || this.pending || !this.host.canAct()) return;
    this.pending = true; this.error = ''; this.host.changed();
    const fail = (error: unknown): void => { if (this.snapshot?.reviewId === current.reviewId) this.error = errorCode(error) === 'protected_track' ? 'Esta pista está protegida por los controles de la sesión. Conserva la apertura, el cierre y el orden obligatorio.' : userErrorMessage(error); };
    try { await this.host.perform(label, () => task(current), (value) => { if (this.snapshot?.reviewId === current.reviewId) apply(value); }, fail); }
    catch (error) { fail(error); }
    finally { this.pending = false; this.host.changed(); }
  }
  async load(): Promise<void> { await this.run('Leyendo evidencia local…', review => this.api.reviewDetails({ reviewId: review.reviewId }), value => this.host.applied(value)); }
  async compare(trackId: string): Promise<void> { await this.run('Comparando reemplazo local…', review => this.api.reviewCompare({ reviewId: review.reviewId, trackId }), value => { this.preview = value; }); }
  async remove(trackId: string): Promise<void> { await this.run('Retirando pista y buscando reemplazo…', review => this.api.reviewRemove({ reviewId: review.reviewId, trackId }), value => { this.preview = null; this.host.applied(value); }); }
  async move(trackId: string, direction: -1 | 1): Promise<void> {
    const tracks = this.snapshot?.tracks ?? []; const index = tracks.findIndex(track => track.id === trackId);
    if (index < 0 || index + direction < 0 || index + direction >= tracks.length) return;
    const ids = tracks.map(track => track.id); [ids[index], ids[index + direction]] = [ids[index + direction], ids[index]];
    await this.run('Reordenando y recalculando transiciones…', review => this.api.reviewReorder({ reviewId: review.reviewId, trackIds: ids }), value => { this.preview = null; this.host.applied(value); });
  }
}
