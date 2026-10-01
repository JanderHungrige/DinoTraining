/** The outline tools (doc 106): ⊕/⊖ clicks, brush, eraser, size, undo, outlines from boxes. */

import type { JSX } from 'react';

import type { MaskEditing, MaskTool } from '../hooks/useMaskEditing';
import { useT, type Key } from '../i18n';
import '../maskedit.css';

const TOOLS: readonly { id: MaskTool; label: Key; hint: Key }[] = [
  { id: 'none', label: 'studio.mask.select', hint: 'studio.mask.selectHint' },
  { id: 'add', label: 'studio.mask.add', hint: 'studio.mask.addHint' },
  { id: 'remove', label: 'studio.mask.remove', hint: 'studio.mask.removeHint' },
  { id: 'brush', label: 'studio.mask.brush', hint: 'studio.mask.brushHint' },
  { id: 'erase', label: 'studio.mask.erase', hint: 'studio.mask.eraseHint' },
];

export interface MaskEditBarProps {
  readonly editing: MaskEditing;
  /** What is selected: an outline, a box without one, or nothing. */
  readonly selection: 'outline' | 'box' | 'none';
  readonly disabled: boolean;
}

export function MaskEditBar({ editing, selection, disabled }: MaskEditBarProps): JSX.Element {
  const { t, tp } = useT();
  const { tool } = editing;
  const off = disabled || editing.busy;
  return (
    <div className="maskbar" role="toolbar" aria-label={t('studio.mask.toolbar')}>
      <div className="maskbar__tools" role="radiogroup" aria-label={t('studio.mask.tool')}>
        {TOOLS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            role="radio"
            aria-checked={tool === entry.id}
            className={`btn btn--small${tool === entry.id ? ' maskbar__on' : ''}`}
            title={t(entry.hint)}
            disabled={off || (entry.id !== 'none' && selection === 'none') || ((entry.id === 'brush' || entry.id === 'erase') && selection !== 'outline')}
            onClick={() => editing.setTool(entry.id)}
          >
            {t(entry.label)}
          </button>
        ))}
      </div>
      {(tool === 'brush' || tool === 'erase') && (
        <label className="maskbar__size">
          {t('studio.mask.size')} <span className="setup__value">{editing.radius} px</span>
          <input type="range" min={1} max={60} value={editing.radius} onChange={(e) => editing.setRadius(Number(e.target.value))} />
        </label>
      )}
      <button type="button" className="btn btn--small" disabled={off || !editing.canUndo} onClick={editing.undo}>
        {t('studio.mask.undo')}
      </button>
      <button type="button" className="btn btn--small" disabled={off || editing.unoutlined === 0} onClick={editing.outlineAll}>
        {t('studio.mask.fromBoxes')}{editing.unoutlined > 0 ? ` (${editing.unoutlined})` : ''}
      </button>
      <span className="maskbar__hint" role="status">
        {editing.busy
          ? t('studio.mask.working')
          : selection === 'none'
            ? t('studio.mask.selectFirst')
            : tool === 'add' || tool === 'remove'
              ? tp('studio.mask.clicks', editing.points.length)
              : selection === 'box'
                ? t('studio.mask.noOutline')
                : ''}
      </span>
      {editing.error && <span className="run__warn" role="alert">{editing.error}</span>}
    </div>
  );
}
