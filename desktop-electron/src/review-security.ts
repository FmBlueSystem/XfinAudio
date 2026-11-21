/** Independent allowlist and value validation for deterministic review and Prep controls. */
export const REVIEW_CONTROL_FIELDS: Record<string, string[]> = {
  reviewDetails: ['reviewId'], reviewCompare: ['reviewId', 'trackId'], reviewRemove: ['reviewId', 'trackId'], reviewReplace: ['reviewId', 'trackId', 'replacementId'], reviewExtend: ['reviewId', 'targetTrackCount'], reviewReorder: ['reviewId', 'trackIds'],
  reviewUndo: ['reviewId'], reviewRedo: ['reviewId'], reviewResume: [],
  prepSettings: [], savePrepSettings: ['revision', 'requiredTrackIds', 'excludedTrackIds', 'genreFocus', 'clearUnavailable'], savePlaylistReview: ['reviewId'],
};
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const id = (value: unknown): boolean => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
/**
 * A saved list answers a review payload of its own now: the core owns `reviewId`, `variant`,
 * `canSave` and everything else it connects to. Only an answer without a review identity keeps
 * the read-only fallback the host used to fabricate for every saved list.
 */
export function savedPlaylistReview(result: Record<string, unknown>): Record<string, unknown> {
  const reviewId = result.reviewId;
  if (typeof reviewId === 'string' && reviewId !== '') return result;
  return {...result, reviewId: '', variant: 'saved', canSave: false};
}
const ids = (value: unknown): value is string[] => Array.isArray(value) && value.length <= 100 && value.every(id) && new Set(value).size === value.length;
export function validateReviewControlRequest(method: string, params: Record<string, unknown>): void {
  if (!Object.hasOwn(REVIEW_CONTROL_FIELDS, method)) return;
  const fields = REVIEW_CONTROL_FIELDS[method];
  if (Object.keys(params).length !== fields.length || Object.keys(params).some(key => !fields.includes(key))) throw new Error('Missing or unexpected review control fields');
  // A review control and saving a saved list's edits both address a review by uuid alone; the
  // recovery read takes no identity at all and Prep settings carry their own revision.
  if (method === 'savePlaylistReview' || (method.startsWith('review') && method !== 'reviewResume')) {
    if (typeof params.reviewId !== 'string' || !UUID.test(params.reviewId)) throw new Error('Invalid review identity');
    if (['reviewCompare', 'reviewRemove', 'reviewReplace'].includes(method) && !id(params.trackId)) throw new Error('Invalid track identity');
    if (method === 'reviewReplace' && !id(params.replacementId)) throw new Error('Invalid replacement identity');
    if (method === 'reviewExtend' && (!Number.isInteger(params.targetTrackCount) || Number(params.targetTrackCount) < 2 || Number(params.targetTrackCount) > 100)) throw new Error('Choose 2–100 tracks');
    if (method === 'reviewReorder' && !ids(params.trackIds)) throw new Error('Invalid review order');
  }
  if (method === 'savePrepSettings') {
    if (!id(params.revision) || !ids(params.requiredTrackIds) || !ids(params.excludedTrackIds) || typeof params.genreFocus !== 'string' || params.genreFocus.length > 100 || /[\x00-\x1f]/.test(params.genreFocus) || typeof params.clearUnavailable !== 'boolean') throw new Error('Invalid Prep controls');
    const excluded = new Set(params.excludedTrackIds);
    if (params.requiredTrackIds.some(value => excluded.has(value))) throw new Error('Required tracks cannot be excluded');
  }
}
