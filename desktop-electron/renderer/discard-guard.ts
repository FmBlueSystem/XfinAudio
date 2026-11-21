/**
 * Confirmation before an action throws away the edits of the generated review (S4).
 *
 * The question is asked only when the review in hand is no longer the one that was
 * generated, chosen as a variant or opened from a saved playlist: every edit mints a new
 * `reviewId`, so a different id means unsaved work would be lost.
 */
export const DISCARD_MESSAGE = 'Vas a descartar los cambios de esta lista. ¿Continuar?';
export const DISCARD_CONFIRM = 'Descartar cambios';
export const DISCARD_CANCEL = 'Seguir editando';

export interface DiscardGuard {
  /** Records the review just generated, chosen as a variant or opened from a playlist. */
  reset(reviewId: string | null): void;
  /** True when the review in hand is not the one that was generated, chosen or opened. */
  edited(review: { reviewId: string } | null): boolean;
}

export function createDiscardGuard(): DiscardGuard {
  let baseline: string | null = null;
  return {
    reset: (reviewId) => { baseline = reviewId; },
    edited: (review) => review !== null && baseline !== null && review.reviewId !== baseline,
  };
}

export interface DiscardPromptHost { canAct(): boolean; }
export interface DiscardPrompt {
  /** Opens the question; resolves true only when the user accepts the discard. */
  ask(): Promise<boolean>;
}

const shown = (dialog: HTMLDialogElement): void => {
  if (typeof dialog.showModal === 'function') dialog.showModal();
  else dialog.open = true;
};
const hiddenFrom = (dialog: HTMLDialogElement): void => {
  if (typeof dialog.close === 'function' && dialog.open) dialog.close();
  else dialog.open = false;
};

export function createDiscardPrompt(container: HTMLElement, host: DiscardPromptHost): DiscardPrompt {
  const dialog = document.createElement('dialog');
  dialog.id = 'discard-guard'; dialog.className = 'discard-guard';
  dialog.open = false;
  dialog.setAttribute('aria-modal', 'true');
  dialog.setAttribute('role', 'dialog');
  const message = document.createElement('p');
  message.id = 'discard-guard-message'; message.className = 'discard-guard-message'; message.textContent = DISCARD_MESSAGE;
  const actions = document.createElement('div'); actions.className = 'editor-actions';
  const confirm = document.createElement('button');
  confirm.id = 'discard-guard-confirm'; confirm.type = 'button'; confirm.className = 'button primary'; confirm.textContent = DISCARD_CONFIRM;
  const cancel = document.createElement('button');
  cancel.id = 'discard-guard-cancel'; cancel.type = 'button'; cancel.className = 'button subtle'; cancel.textContent = DISCARD_CANCEL;
  actions.append(confirm, cancel);
  dialog.append(message, actions);
  container.append(dialog);
  let answer: ((confirmed: boolean) => void) | null = null;
  const settle = (confirmed: boolean): void => {
    const resolve = answer; answer = null; hiddenFrom(dialog);
    confirm.disabled = false; cancel.disabled = false;
    resolve?.(confirmed);
  };
  confirm.addEventListener('click', () => { if (host.canAct()) settle(true); });
  // Refusing is always safe, so «Seguir editando» and Escape stay available while the app is busy
  // or the core stopped: the question must never trap the review behind it.
  cancel.addEventListener('click', () => settle(false));
  dialog.addEventListener('cancel', (event) => { event.preventDefault(); settle(false); });
  return {
    ask: () => {
      // One question at a time: a second request while it is open still fails closed.
      if (answer) return Promise.resolve(false);
      shown(dialog);
      confirm.disabled = !host.canAct(); cancel.disabled = false;
      return new Promise<boolean>((resolve) => { answer = resolve; });
    },
  };
}
