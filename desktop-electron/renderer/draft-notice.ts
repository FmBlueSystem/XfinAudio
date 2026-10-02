export interface DraftBlocker { id: string; label: string; resolve(): void; }
export interface DraftNoticeHost { canAct(): boolean; draftBlockers?(): DraftBlocker[]; }
export const draftMessage = (drafts: DraftBlocker[], action: string): string =>
  `Guarda o descarta los cambios de ${drafts.map(draft => draft.label).join(', ')} antes de ${action}. Tus borradores se conservan.`;

/** Shows the exact pending scopes without making their Save/Discard controls unavailable. */
export function createDraftNotice(root: HTMLElement, prefix: string, action: string, host: DraftNoticeHost): () => boolean {
  root.id = `${prefix}-draft-notice`; root.className = 'review-notice';
  const message = document.createElement('p'); message.id = `${prefix}-draft-message`; message.setAttribute('role', 'status');
  const actions = document.createElement('div'); actions.className = 'editor-actions'; root.append(message, actions);
  let rendered = ''; let buttons: HTMLButtonElement[] = [];
  return () => {
    const drafts = host.draftBlockers?.() ?? []; root.hidden = drafts.length === 0;
    message.textContent = drafts.length ? draftMessage(drafts, action) : '';
    const key = drafts.map(draft => draft.id).join(',');
    if (key !== rendered) {
      rendered = key; actions.replaceChildren(); buttons = [];
      for (const draft of drafts) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'button subtle';
        button.id = `${prefix}-draft-resolve-${draft.id}`; button.textContent = `Revisar ${draft.label}`;
        button.addEventListener('click', () => { if (!button.disabled && host.canAct()) draft.resolve(); });
        actions.append(button); buttons.push(button);
      }
    }
    for (const button of buttons) button.disabled = !host.canAct();
    return drafts.length > 0;
  };
}
