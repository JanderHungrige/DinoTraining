/**
 * Pick heads to run over the current image, optionally narrowed to one task.
 *
 * Same-task comparison is **not a separate mechanism** — it is this list filtered by
 * task, which is why there is no compare mode to switch into. Select three segmenters
 * and you get three result panes; select a segmenter and a classifier and you get two.
 *
 * Heads are presented by **`summary`** — task, provenance, training data, metrics —
 * never by a filename. That is doc 12's cross-tab contract, and Wave 2 shipped a bug
 * from breaking it; `summary` is rendered as the backend composed it rather than
 * rebuilt here, so the same head reads identically in every tab.
 */

import { useMemo, type JSX } from 'react';

import { describeHead, groupByTask } from '../api/headInstances';
import type { HeadTask } from '../api/heads';
import type { HeadRunState } from '../hooks/useHeadRun';

export interface HeadRunPanelProps {
  readonly state: HeadRunState;
  readonly onRun: () => void;
  /** Makes the whole panel inert — nothing can be chosen or run. */
  readonly disabled?: boolean;
  /**
   * Blocks only the Run button, leaving the selection live.
   *
   * Separate from `disabled` because doc 34 renders this panel before an image exists:
   * "there is nothing to run on" must not also mean "you may not choose". Folding the two
   * together made the whole panel inert and quietly defeated moving it out of the guard.
   */
  readonly runDisabled?: boolean;
}

const ALL_TASKS = '' as const;

export function HeadRunPanel({
  state,
  onRun,
  disabled = false,
  runDisabled = false,
}: HeadRunPanelProps): JSX.Element {
  const { heads, selected, running, loadingHeads, backboneId, taskFilter } = state;

  // Grouping is doc 12's `groupByTask`, not a second implementation: the tasks offered
  // are exactly the tasks the installed heads cover, so an empty group cannot be picked.
  const tasks = useMemo(() => [...groupByTask(heads).keys()].sort(), [heads]);

  const visible = useMemo(
    () => (taskFilter ? heads.filter((head) => head.task === taskFilter) : heads),
    [heads, taskFilter],
  );

  if (loadingHeads) return <p role="status">Loading heads…</p>;

  if (heads.length === 0) {
    return (
      <p role="status">
        No heads installed yet. Install a default from the Admin tab, or train one in the
        Head Trainer.
      </p>
    );
  }

  // Counted together: a foundation model is as much "a thing you chose to run" as a head,
  // and a Run button that stays dead after ticking one would read as broken.
  const totalSelected = selected.length + state.selectedFoundations.length;
  const nothingSelected = totalSelected === 0;
  const runLabel = `Run ${totalSelected || ''} model${totalSelected === 1 ? '' : 's'}`;

  const sameTaskCount = state.selectedTask
    ? selected.filter((id) => heads.find((h) => h.id === id)?.task === state.selectedTask).length
    : 0;

  return (
    <div className="runpanel">
      <div className="runpanel__filter">
        <label htmlFor="task-filter">Task</label>
        <select
          id="task-filter"
          value={taskFilter ?? ALL_TASKS}
          onChange={(event) =>
            state.setTaskFilter(event.target.value === ALL_TASKS ? null : (event.target.value as HeadTask))
          }
          disabled={disabled || running}
        >
          <option value={ALL_TASKS}>All tasks</option>
          {tasks.map((task) => (
            <option key={task} value={task}>
              {task}
            </option>
          ))}
        </select>
        {sameTaskCount > 1 && (
          <span className="runpanel__compare">
            Comparing {sameTaskCount} heads on {state.selectedTask}
          </span>
        )}
      </div>

      <fieldset className="runpanel__heads">
        <legend>Heads</legend>
        {visible.map((head) => {
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

      {state.foundations.length > 0 && (
        <fieldset className="runpanel__heads">
          <legend>Foundation models</legend>
          {/* A separate group because these are a different kind of thing, not a filtered
              view of the same list: they have no backbone, so `isIncompatible` has nothing
              to say about them and the backbone tooltip would be meaningless. Their
              results land in the same panes. */}
          {state.foundations.map((entry) => (
            <label key={entry.id} className="runpanel__head" title={entry.description}>
              <input
                type="checkbox"
                checked={state.selectedFoundations.includes(entry.id)}
                disabled={disabled}
                onChange={() => state.toggleFoundation(entry.id)}
              />
              <span className="runpanel__headname">{entry.title}</span>
              <span className="runpanel__headmeta">
                {entry.task} · {entry.licence}
                {entry.non_commercial ? ' · non-commercial' : ''}
              </span>
            </label>
          ))}
        </fieldset>
      )}

      <div className="runpanel__actions">
        <button
          type="button"
          className="btn btn--primary"
          onClick={onRun}
          disabled={disabled || runDisabled || running || nothingSelected}
        >
          {running ? 'Running…' : runLabel}
        </button>
        <button
          type="button"
          className="btn"
          onClick={state.clear}
          disabled={nothingSelected || running}
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
