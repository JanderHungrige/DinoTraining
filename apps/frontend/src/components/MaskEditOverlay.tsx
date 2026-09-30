/**
 * The layer that takes the pointer while an outline tool is on (doc 106): a click places a
 * ⊕/⊖ point, a drag paints or erases. It covers exactly the picture, and converts to the
 * picture's own pixels — the coordinates every stored annotation uses.
 */

import { useRef, useState, type JSX, type PointerEvent } from 'react';

import type { ClickPoint } from '../api/segment';
import type { MaskTool } from '../hooks/useMaskEditing';
import type { RenderedImage } from '../lib/geometry';

export interface MaskEditOverlayProps {
  readonly rendered: RenderedImage;
  readonly tool: MaskTool;
  readonly radius: number;
  readonly points: readonly ClickPoint[];
  readonly onClick: (x: number, y: number) => void;
  readonly onStroke: (path: readonly (readonly [number, number])[]) => void;
}

export function MaskEditOverlay({ rendered, tool, radius, points, onClick, onStroke }: MaskEditOverlayProps): JSX.Element | null {
  const layer = useRef<HTMLDivElement>(null);
  const [path, setPath] = useState<[number, number][]>([]);
  const drawing = useRef(false);
  if (tool === 'none' || rendered.width <= 0) return null;
  const scale = rendered.width / rendered.naturalWidth;

  const natural = (event: PointerEvent<HTMLDivElement>): [number, number] => {
    const box = layer.current!.getBoundingClientRect();
    const x = ((event.clientX - box.left) / box.width) * rendered.naturalWidth;
    const y = ((event.clientY - box.top) / box.height) * rendered.naturalHeight;
    return [Math.max(0, Math.min(rendered.naturalWidth - 1, x)), Math.max(0, Math.min(rendered.naturalHeight - 1, y))];
  };
  const brush = tool === 'brush' || tool === 'erase';

  return (
    <div
      ref={layer}
      className={`maskedit maskedit--${tool}`}
      style={{ left: rendered.offsetX, top: rendered.offsetY, width: rendered.width, height: rendered.height }}
      data-testid="mask-edit-layer"
      onPointerDown={(event) => {
        event.stopPropagation();
        if (!brush) {
          const [x, y] = natural(event);
          onClick(x, y);
          return;
        }
        drawing.current = true;
        event.currentTarget.setPointerCapture?.(event.pointerId);
        setPath([natural(event)]);
      }}
      onPointerMove={(event) => {
        event.stopPropagation();
        if (drawing.current) setPath((current) => [...current, natural(event)]);
      }}
      onPointerUp={(event) => {
        event.stopPropagation();
        if (!drawing.current) return;
        drawing.current = false;
        onStroke(path);
        setPath([]);
      }}
    >
      <svg className="maskedit__marks" viewBox={`0 0 ${rendered.naturalWidth} ${rendered.naturalHeight}`} aria-hidden="true">
        {path.length > 0 && (
          <polyline
            points={path.map(([x, y]) => `${x},${y}`).join(' ')}
            className={tool === 'erase' ? 'maskedit__stroke maskedit__stroke--erase' : 'maskedit__stroke'}
            strokeWidth={radius * 2}
          />
        )}
        {points.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r={6 / scale}
            className={point.positive ? 'maskedit__point maskedit__point--add' : 'maskedit__point maskedit__point--remove'}
          />
        ))}
      </svg>
    </div>
  );
}
