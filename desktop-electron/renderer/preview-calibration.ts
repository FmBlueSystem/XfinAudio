/**
 * S13 (d): the calibration wizard of any controller.
 *
 * The state lives here, without the DOM: the setting renders what this object says and plays the
 * tone it names. Nothing is saved until the last pair is answered, so «Cancelar» at any step
 * leaves the previous calibration exactly as it was.
 */
import { calibrationRoles } from './preview-output.js';
import type { CalibrationRole, CalibrationRoles } from './preview-output.js';

/** S13 (d): the button that opens the wizard, and the one of S13 (e). */
export const CALIBRATION_BUTTON = 'Calibrar canales';
export const CLEAR_CALIBRATION_BUTTON = 'Borrar calibración';
/** S13 (d): the words of the first step, before any tone. */
export const CALIBRATION_WARNING = 'Baja el volumen de la sala antes de empezar: el tono va a sonar por cada salida.';
export const START_BUTTON = 'Empezar';
export const CANCEL_BUTTON = 'Cancelar';
/** S13 (d): the tone again on the pair of the step, without moving on. */
export const REPEAT_TONE_BUTTON = 'Repetir tono';
export const QUESTION = '¿Dónde sonó?';

/** S13 (d): the line once the last pair is answered. */
export const savedLine = (label: string): string => `Calibración guardada para ${label}.`;
/** S13 (d): the heading of one step. */
export const stepHeading = (pair: string, index: number, total: number): string => `Par ${pair} (${index} de ${total})`;

/** S13 (d): one of the seven answers, in the order the setting shows them. */
export interface CalibrationAnswerOption { role: CalibrationRole; text: string; }

export const CALIBRATION_ANSWERS: readonly CalibrationAnswerOption[] = [
  { role: 'phones', text: 'Auriculares' },
  { role: 'room', text: 'Sala' },
  { role: 'channel:1', text: 'Canal 1' },
  { role: 'channel:2', text: 'Canal 2' },
  { role: 'channel:3', text: 'Canal 3' },
  { role: 'channel:4', text: 'Canal 4' },
  { role: 'silent', text: 'No sonó' },
];

type Phase = 'intro' | 'question' | 'closed';

export class CalibrationWizard {
  /** S13 (d): the pairs of the output, in order: one step each. */
  readonly pairs: readonly string[];
  private phase: Phase = 'intro';
  private current = 0;
  private recorded: CalibrationRoles = {};
  private resolved: CalibrationRoles | null = null;

  constructor(pairs: readonly string[]) { this.pairs = [...pairs]; }

  /** Open until it is cancelled or the last pair is answered. */
  get open(): boolean { return this.phase !== 'closed'; }
  /** True from «Empezar» until it closes: the question is on screen. */
  get started(): boolean { return this.phase === 'question'; }
  /** The 1-based step, 0 before «Empezar». */
  get index(): number { return this.phase === 'question' ? this.current : 0; }
  get total(): number { return this.pairs.length; }
  /** The pair the step asks about, and the one its tone plays on. */
  get pair(): string | null { return this.phase === 'question' ? this.pairs[this.current - 1] ?? null : null; }
  get heading(): string {
    const pair = this.pair;
    return pair === null ? '' : stepHeading(pair, this.current, this.total);
  }
  /** The answers given so far, in pair order. */
  get answers(): CalibrationRoles { return { ...this.recorded }; }
  /** The calibration to save, once the last pair is answered; null until then and after cancelling. */
  get result(): CalibrationRoles | null { return this.resolved; }

  /** «Empezar»: the first pair becomes the step. */
  start(): void {
    if (this.phase !== 'intro' || this.pairs.length === 0) return;
    this.phase = 'question';
    this.current = 1;
  }

  /**
   * Records the answer of the step and moves to the next pair, which the caller sounds. It
   * returns that pair, or null when there is none: the last answer closes the wizard.
   */
  answer(role: CalibrationRole): string | null {
    if (this.phase !== 'question') return null;
    const pair = this.pair;
    if (pair === null) return null;
    this.recorded[pair] = role;
    if (this.current >= this.pairs.length) {
      this.phase = 'closed';
      // S13 (a): the roles are resolved when they are saved — never two phones, never a channel twice.
      this.resolved = calibrationRoles(this.recorded);
      return null;
    }
    this.current += 1;
    return this.pair;
  }

  /** «Repetir tono»: the pair of the step, which never advances. */
  repeat(): string | null { return this.phase === 'question' ? this.pair : null; }

  /** «Cancelar»: nothing to save, so the previous calibration stays. */
  cancel(): void {
    this.phase = 'closed';
    this.resolved = null;
    this.recorded = {};
  }
}
