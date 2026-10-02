/** Independent allowlist and value validation for deterministic review and Prep controls. */
export const REVIEW_CONTROL_FIELDS: Record<string, string[]> = {
  reviewDetails: ['reviewId'], reviewCompare: ['reviewId', 'trackId'], reviewRemove: ['reviewId', 'trackId'], reviewReorder: ['reviewId', 'trackIds'],
  prepSettings: [], savePrepSettings: ['revision', 'requiredTrackIds', 'excludedTrackIds', 'genreFocus', 'clearUnavailable'],
};
const id = (value: unknown): boolean => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const ids = (value: unknown): value is string[] => Array.isArray(value) && value.length <= 100 && value.every(id) && new Set(value).size === value.length;
export function validateReviewControlRequest(method: string, params: Record<string, unknown>): void {
  if (!Object.hasOwn(REVIEW_CONTROL_FIELDS, method)) return;
  const fields = REVIEW_CONTROL_FIELDS[method];
  if (Object.keys(params).length !== fields.length || Object.keys(params).some(key => !fields.includes(key))) throw new Error('Missing or unexpected review control fields');
  if (method.startsWith('review')) {
    if (typeof params.reviewId !== 'string' || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(params.reviewId)) throw new Error('Invalid review identity');
    if (['reviewCompare', 'reviewRemove'].includes(method) && !id(params.trackId)) throw new Error('Invalid track identity');
    if (method === 'reviewReorder' && !ids(params.trackIds)) throw new Error('Invalid review order');
  }
  if (method === 'savePrepSettings') {
    if (!id(params.revision) || !ids(params.requiredTrackIds) || !ids(params.excludedTrackIds) || typeof params.genreFocus !== 'string' || params.genreFocus.length > 100 || /[\x00-\x1f]/.test(params.genreFocus) || typeof params.clearUnavailable !== 'boolean') throw new Error('Invalid Prep controls');
    const excluded = new Set(params.excludedTrackIds);
    if (params.requiredTrackIds.some(value => excluded.has(value))) throw new Error('Required tracks cannot be excluded');
  }
}
