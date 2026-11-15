/**
 * The single global operation status: one job at a time, always telling the user whether the
 * app is working, where it is inside the work, and how the last operation ended.
 *
 * States are exclusive: `running` (animated indicator, name, numbered step and counts),
 * `done` (green check with the result, settling into a discreet line), `error` and
 * `cancelled` (red, kept until the next operation), and `notice` for a neutral message that
 * is not the outcome of a user-started operation. The region publishes `aria-busy` while it
 * is running, so an assistive technology announces the end instead of every intermediate step.
 */
export type OperationPhase = 'idle' | 'running' | 'done' | 'error' | 'cancelled' | 'notice';
/** One step of a chained job, optionally with the counts of the work inside that step. */
export interface OperationStage {
  index?: number;
  total?: number;
  label?: string;
  current?: number;
  totalCount?: number;
}
export interface OperationStatus {
  readonly cancel: HTMLButtonElement;
  readonly phase: OperationPhase;
  /** Begin a user-started operation; the trigger button shows that it is working. */
  start(name: string, trigger?: HTMLElement | null, stage?: OperationStage | null): void;
  /** Update the visible name and reason while the same operation keeps running. */
  describe(name: string | null, detail?: string): void;
  stage(stage: OperationStage | null): void;
  progress(current: number | null, total?: number): void;
  done(name: string, detail?: string): void;
  fail(name: string, detail?: string): void;
  cancelled(name: string, detail?: string): void;
  notice(name: string, detail?: string): void;
  /** Stop the running indicator without inventing an outcome for the operation. */
  stop(): void;
  hide(): void;
}
type Schedule = (run: () => void, milliseconds: number) => void;
export const SETTLE_MILLISECONDS = 5000;
const spaces = (value: number): string => String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
const step = (value: number | undefined, total: number | undefined): number | null =>
  Number.isSafeInteger(value) && Number.isSafeInteger(total) && Number(total) > 0 && Number(value) > 0 ? Math.min(Number(value), Number(total)) : null;
/** «Paso 2 de 2 · Completando perfiles · 340 de 1 200», or only the parts that apply. */
export function stageLine(stage: OperationStage | null | undefined): string {
  if (!stage) return '';
  const parts: string[] = [];
  const number = step(stage.index, stage.total);
  if (number !== null) parts.push(`Paso ${number} de ${spaces(Number(stage.total))}`);
  if (stage.label) parts.push(stage.label);
  if (Number.isSafeInteger(stage.current) && Number.isSafeInteger(stage.totalCount) && Number(stage.totalCount) > 0) parts.push(`${spaces(Number(stage.current))} de ${spaces(Number(stage.totalCount))}`);
  return parts.join(' · ');
}
const create = <K extends keyof HTMLElementTagNameMap>(tag: K, text = ''): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
};
const defaultSchedule: Schedule = (run, milliseconds) => {
  const timer = setTimeout(run, milliseconds);
  // A pending settle must never keep a headless test process alive.
  const unref = (timer as unknown as { unref?: () => void }).unref;
  if (typeof unref === 'function') unref.call(timer);
};
export function createOperationStatus(root: HTMLElement, options: { schedule?: Schedule; settleMilliseconds?: number } = {}): OperationStatus {
  const schedule = options.schedule ?? defaultSchedule;
  const settleMilliseconds = options.settleMilliseconds ?? SETTLE_MILLISECONDS;
  // The label, detail, bar and cancel button are the shipped controls: the view adopts the
  // elements the page already provides instead of rebuilding them, and only adds the working
  // indicator and the stage line the status region did not have.
  const owned = <T extends HTMLElement>(id: string, fallback: () => T): T => {
    const found = typeof document.getElementById === 'function' ? document.getElementById(id) : null;
    return (found as T | null) ?? fallback();
  };
  const indicator = create('span');
  indicator.id = 'operation-indicator';
  indicator.className = 'operation-indicator';
  indicator.setAttribute('aria-hidden', 'true');
  const name = owned('operation-label', () => { const node = create('strong'); node.id = 'operation-label'; return node; });
  const stepNode = create('span');
  stepNode.id = 'operation-stage';
  stepNode.className = 'operation-stage';
  const detail = owned('operation-detail', () => { const node = create('span'); node.id = 'operation-detail'; return node; });
  const progress = owned<HTMLProgressElement>('operation-progress', () => { const node = create('progress'); node.id = 'operation-progress'; return node; });
  progress.setAttribute('aria-label', 'Progreso de la operación');
  progress.hidden = true;
  const cancel = owned<HTMLButtonElement>('cancel-operation', () => { const node = create('button', 'Cancelar'); node.id = 'cancel-operation'; node.className = 'button subtle'; node.type = 'button'; return node; });
  cancel.hidden = true;
  const mount = (parent: Element | null, node: HTMLElement, before: Element | null = null): void => {
    if (!parent) return;
    if (typeof parent.insertBefore === 'function') parent.insertBefore(node, before);
    else if (typeof parent.append === 'function') parent.append(node);
  };
  mount(root, indicator, (root.firstChild ?? null) as Element | null);
  mount(name.parentElement ?? root, stepNode, name.nextSibling as Element | null);
  let phase: OperationPhase = 'idle';
  let trigger: HTMLElement | null = null;
  let generation = 0;
  const release = (): void => {
    if (!trigger) return;
    trigger.setAttribute('aria-busy', 'false');
    trigger.classList.toggle('is-working', false);
    trigger = null;
  };
  const paint = (next: OperationPhase): void => {
    phase = next;
    root.hidden = next === 'idle';
    root.classList.toggle('is-running', next === 'running');
    root.classList.toggle('is-done', next === 'done');
    root.classList.toggle('is-error', next === 'error');
    root.classList.toggle('is-cancelled', next === 'cancelled');
    root.classList.toggle('is-notice', next === 'notice');
    root.classList.toggle('is-settled', false);
    root.setAttribute('aria-busy', next === 'running' ? 'true' : 'false');
    indicator.textContent = next === 'done' ? '✓' : next === 'error' ? '!' : next === 'cancelled' ? '×' : '';
  };
  const bar = (current: number | null, total?: number): void => {
    if (current === null || !Number.isSafeInteger(total) || Number(total) <= 0) {
      progress.removeAttribute('value');
      progress.hidden = phase !== 'running';
      return;
    }
    progress.max = Number(total);
    progress.value = Math.min(Number(total), Math.max(0, Number(current)));
    progress.hidden = phase !== 'running';
  };
  const finish = (next: OperationPhase, label: string, reason: string): void => {
    generation += 1;
    release();
    paint(next);
    name.textContent = label;
    stepNode.textContent = '';
    detail.textContent = reason;
    progress.hidden = true;
  };
  return {
    cancel,
    get phase() { return phase; },
    start(label, nextTrigger = null, stage = null) {
      generation += 1;
      release();
      trigger = nextTrigger;
      if (trigger) {
        trigger.setAttribute('aria-busy', 'true');
        trigger.classList.toggle('is-working', true);
      }
      paint('running');
      name.textContent = label;
      stepNode.textContent = stageLine(stage);
      detail.textContent = '';
      bar(null);
    },
    describe(label, reason) {
      if (label !== null) name.textContent = label;
      if (reason !== undefined) detail.textContent = reason;
    },
    stage(value) { if (phase === 'running') stepNode.textContent = stageLine(value); },
    progress(current, total) { bar(current, total); },
    done(label, reason = '') {
      finish('done', label, reason);
      const token = generation;
      schedule(() => { if (token !== generation || phase !== 'done') return; root.classList.toggle('is-settled', true); }, settleMilliseconds);
    },
    fail(label, reason = '') { finish('error', label, reason); },
    cancelled(label, reason = '') { finish('cancelled', label, reason); },
    notice(label, reason = '') { finish('notice', label, reason); },
    stop() {
      if (phase !== 'running') return;
      generation += 1;
      release();
      paint('notice');
      progress.hidden = true;
    },
    hide() {
      generation += 1;
      release();
      paint('idle');
      root.hidden = true;
      name.textContent = '';
      stepNode.textContent = '';
      detail.textContent = '';
      progress.hidden = true;
    },
  };
}
