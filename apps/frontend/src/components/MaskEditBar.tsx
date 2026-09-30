/** The outline tools (doc 106): ⊕/⊖ clicks, brush, eraser, size, undo, outlines from boxes. */

import type { JSX } from 'react';

import type { MaskEditing, MaskTool } from '../hooks/useMaskEditing';
import '../maskedit.css';

const TOOLS: readonly { id: MaskTool; label: string; hint: string }[] = [
  { id: 'none', label: 'Select', hint: 'Draw and pick boxes as usual' },
  { id: 'add', label: '⊕ Add', hint: 'Click what belongs to the outline; SAM redraws it' },
  { id: 'remove', label: '⊖ Remove', hint: 'Click what does not belong; SAM redraws it' },
  { id: 'brush', label: 'Brush', hint: 'Drag to paint pixels in' },
  { id: 'erase', label: 'Eraser', hint: 'Drag to take pixels out' },
];

export interface MaskEditBarProps {
  readonly editing: MaskEditing;
  /** What is selected: an outline, a box without one, or nothing. */
  readonly selection: 'outline' | 'box' | 'none';
  readonly disabled: boolean;
}

export function MaskEditBar({ editing, selection, disabled }: MaskEditBarProps): JSX.Element {
  const { tool } = editing;
  const off = disabled || editing.busy;
  return (
    <div className="maskbar" role="toolbar" aria-label="Outline tools">
      <div className="maskbar__tools" role="radiogroup" aria-label="Tool">
        {TOOLS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            role="radio"
            aria-checked={tool === entry.id}
            className={`btn btn--small${tool === entry.id ? ' maskbar__on' : ''}`}
            title={entry.hint}
            disabled={off || (entry.id !== 'none' && selection === 'none') || ((entry.id === 'brush' || entry.id === 'erase') && selection !== 'outline')}
            onClick={() => editing.setTool(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </div>
      {(tool === 'brush' || tool === 'erase') && (
        <label className="maskbar__size">
          Size <span className="setup__value">{editing.radius} px</span>
          <input type="range" min={1} max={60} value={editing.radius} onChange={(e) => editing.setRadius(Number(e.target.value))} />
        </label>
      )}
      <button type="button" className="btn btn--small" disabled={off || !editing.canUndo} onClick={editing.undo}>
        Undo
      </button>
      <button type="button" className="btn btn--small" disabled={off || editing.unoutlined === 0} onClick={editing.outlineAll}>
        Outlines from my boxes{editing.unoutlined > 0 ? ` (${editing.unoutlined})` : ''}
      </button>
      <span className="maskbar__hint" role="status">
        {editing.busy
          ? 'Working…'
          : selection === 'none'
            ? 'Select a box or outline to edit it.'
            : tool === 'add' || tool === 'remove'
              ? `${editing.points.length} click${editing.points.length === 1 ? '' : 's'} on this outline — each one redraws it.`
              : selection === 'box'
                ? 'This box has no outline yet: ⊕ Add makes one.'
                : ''}
      </span>
      {editing.error && <span className="run__warn" role="alert">{editing.error}</span>}
    </div>
  );
}
