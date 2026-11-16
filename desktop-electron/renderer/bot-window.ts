/**
 * S1: the list assistant is a bot button with a floating window, not a section of the AI
 * panel. This controller owns only what the window shows — whether the review screen offers
 * it, whether it is open, and how many proposed changes are still waiting — while the chat
 * keeps its own conversation and its own bridge (`ListChatApi`). The list is never changed
 * by opening, minimising or closing the window.
 */
export const BOT_WINDOW_TITLE = 'Asistente de lista';
export const BOT_BUTTON_LABEL = 'Abrir asistente de lista';
export const BOT_MINIMIZE = 'Minimizar';

export interface BotWindowHost {
  /** The same authority every other panel uses: the core is connected and no job owns it. */
  canAct(): boolean;
  /** One render request for every change; the view redraws itself from this controller. */
  changed(): void;
  /** The changes the last reply still proposes, which the badge counts. */
  pending(): number;
}

export class BotWindowController {
  /** True only where the chat exists: the review screen, with the chat bridge available. */
  available = false;
  /** True while the floating window is on screen; minimising keeps the conversation. */
  open = false;
  private host: BotWindowHost;
  constructor(host: BotWindowHost) { this.host = host; }
  /** The badge number; zero hides it. It counts pending changes even while the window is closed. */
  get badge(): number {
    if (!this.available) return 0;
    const count = this.host.pending();
    return Number.isInteger(count) && count > 0 ? count : 0;
  }
  get canOpen(): boolean { return this.available && this.host.canAct(); }
  /**
   * Published by the app on every screen change: leaving the review screen hides the button
   * and the window without discarding the conversation the chat controller keeps.
   */
  setAvailable(value: boolean): void {
    if (typeof value !== 'boolean' || value === this.available) return;
    this.available = value;
    if (!value) this.open = false;
    this.host.changed();
  }
  show(): void {
    if (!this.available || this.open) return;
    this.open = true;
    this.host.changed();
  }
  minimize(): void {
    if (!this.open) return;
    this.open = false;
    this.host.changed();
  }
  toggle(): void { if (this.open) this.minimize(); else this.show(); }
}
