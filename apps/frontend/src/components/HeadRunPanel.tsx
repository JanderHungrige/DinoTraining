/**
 * Pick heads to run over the current image.
 *
 * Heads are presented by **`summary`** — task, provenance, training data, metrics —
 * never by a filename. That is doc 12's cross-tab contract, and Wave 2 shipped a bug
 * from breaking it; `summary` is rendered as the backend composed it rather than
 * rebuilt here, so the same head reads identically in every tab.
 */

import type { JSX } from 'react';

import { KIND_LABELS, type HeadInstanceInfo } from '../api/headInstances';
import type { HeadRunState } from '../hooks/useHeadRun';

export interface HeadRunPanelProps {
  readonly state: HeadRunState;
  readonly onRun: () => void;
  readonly disabled?: boolean;
}

export function HeadRunPanel({ state, onRun, disabled = false }: HeadRunPanelProps): JSX.Element {
  const { heads, selected, running, loadingHeads, backboneId } = state;

  if (loadingHeads) return <p role="status">Loading heads…</p>;

  if (heads.length === 0) {
    return (
      <p role="status">
        No heads installed yet. Install a default from the Admin tab, or train one in the
        Head Trainer.
      </p>
    );
  }

  const describeHead = (head: HeadInstanceInfo): string =>
    `${KIND_LABELS[head.kind]} · ${head.summary}`;

  return (
    <div className="runpanel">
      <fieldset className="runpanel__heads">
        <legend>Heads</legend>
        {heads.map((head) => {
          const incompatible = state.isIncompatible(head);
          return (
            <label
              key={head.id}
              className={`runpanel__head${incompatible ? ' runpanel__head--off' : ''}`}
              title={
                incompatible
                  ? `Registered for ${head.backbone_id}; the selection is running on ${backboneId}.`
                  : head.summary
              }
            >
              <input
                type="checkbox"
                checked={selected.includes(head.id)}
                disabled={incompatible || disabled}
                onChange={() => state.toggle(head.id)}
              />
              <span className="runpanel__headname">{head.name}</span>
              <span className="runpanel__headmeta">{describeHead(head)}</span>
            </label>
          );
        })}
      </fieldset>

      <div className="runpanel__actions">
        <button
          type="button"
          className="btn btn--primary"
          onClick={onRun}
          disabled={disabled || running || selected.length === 0}
        >
          {running ? 'Running…' : `Run ${selected.length || ''} head${selected.length === 1 ? '' : 's'}`}
        </button>
        <button
          type="button"
          className="btn"
          onClick={state.clear}
          disabled={selected.length === 0 || running}
        >
          Clear
        </button>
        {state.result && (
          <span className="runpanel__cost">
            {state.result.passes} backbone pass{state.result.passes === 1 ? '' : 'es'} ·{' '}
            {Math.round(state.result.elapsed_ms)} ms
          </span>
        )}
      </div>

      {state.error && (
        <p className="admin__error" role="alert">
          {state.error}
        </p>
      )}
    </div>
  );
}
