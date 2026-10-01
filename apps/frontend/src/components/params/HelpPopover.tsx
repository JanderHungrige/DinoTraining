/**
 * The ? behind a parameter (doc 100): what it does, its default, and why.
 *
 * A real button, so it is reachable by keyboard and named for a screen reader ("About
 * Rounds"). Esc or a click outside closes it; Esc gives focus back to the button, so a
 * keyboard user is not left somewhere else on the page.
 */

import { useEffect, useId, useRef, useState, type JSX } from 'react';

import { useT } from '../../i18n';

export interface HelpPopoverProps {
  readonly label: string;
  readonly help: string;
  readonly defaultText: string;
  readonly why: string;
}

export function HelpPopover({ label, help, defaultText, why }: HelpPopoverProps): JSX.Element {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const box = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent): void => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      button.current?.focus();
    };
    const onPointer = (event: PointerEvent): void => {
      const target = event.target as Node;
      if (!box.current?.contains(target) && !button.current?.contains(target)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  return (
    <span className="param-help">
      <button
        ref={button}
        type="button"
        className="param-help__button"
        aria-label={t('training.params.about', { label })}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((current) => !current)}
      >
        ?
      </button>
      {open && (
        <span ref={box} id={id} role="note" className="param-help__box">
          <span className="param-help__text">{help}</span>
          <span className="param-help__default">
            <strong>{t('training.params.default', { value: defaultText })}</strong> — {why}
          </span>
        </span>
      )}
    </span>
  );
}
