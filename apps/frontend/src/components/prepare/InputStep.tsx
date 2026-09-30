/**
 * Step 5: what the model sees (doc 85). The most important picture in the flow: the
 * user's own images at the model's resolution, enlarged without smoothing, with the
 * objects too small to learn marked red.
 */

import { useEffect, useState, type JSX } from 'react';

import { previewInput, type InputPreview, type ObjectSizes } from '../../api/prepPlan';

export interface InputStepProps {
  readonly datasetId: string;
  readonly target: string;
  /** Tiles along the long edge, or null for the plan's own choice. */
  readonly grid: number | null;
  readonly onGrid: (grid: number | null) => void;
}

function Sizes({ label, sizes }: { readonly label: string; readonly sizes: ObjectSizes }): JSX.Element {
  return (
    <p className="prep-step__summary">
      {label}: a typical object is <strong>{sizes.median_px} px</strong> across, the smallest tenth{' '}
      {sizes.p10_px} px. This model needs about {sizes.needed_px} px —{' '}
      <strong>{Math.round(sizes.too_small_share * 100)}%</strong> are smaller.
    </p>
  );
}

function usePreview(datasetId: string, target: string, grid: number | null) {
  const [preview, setPreview] = useState<InputPreview | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    setPreview(null);
    setError('');
    if (!datasetId || !target) return;
    let live = true;
    previewInput(datasetId, target, grid)
      .then((found) => live && setPreview(found))
      .catch((cause: unknown) => live && setError(cause instanceof Error ? cause.message : String(cause)));
    return () => {
      live = false;
    };
  }, [datasetId, target, grid]);
  return { preview, error };
}

function GridPicker({ grid, onGrid }: { readonly grid: number | null; readonly onGrid: (grid: number | null) => void }): JSX.Element {
  return (
    <label className="genpanel__field prep-step__grid">
      <span>Cut into tiles</span>
      <select
        value={grid === null ? 'auto' : String(grid)}
        onChange={(event) => onGrid(event.target.value === 'auto' ? null : Number(event.target.value))}
      >
        <option value="auto">Recommended</option>
        <option value="1">Off — whole pictures</option>
        {[2, 3, 4, 5, 6].map((n) => (
          <option key={n} value={n}>
            {n} tiles along the long side
          </option>
        ))}
      </select>
    </label>
  );
}

function Seen({ preview }: { readonly preview: InputPreview }): JSX.Element {
  return (
    <div className="prep-seen">
      {preview.images.map((image) => (
        <figure key={image.path} className="prep-seen__item">
          <img src={image.data_url} alt={`As the model sees ${image.path}`} width={image.width} height={image.height} />
          <figcaption>
            {image.objects} object(s){image.too_small ? `, ${image.too_small} too small (red)` : ''}
            {image.lost ? `, ${image.lost} cut off` : ''}
            {image.tile ? ' · one tile' : ''}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

export function InputStep({ datasetId, target, grid, onGrid }: InputStepProps): JSX.Element {
  const { preview, error } = usePreview(datasetId, target, grid);
  const plan = preview?.plan;
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        Every model shrinks a picture to a fixed size before looking at it. Below are your own
        pictures exactly as this model will get them. If you cannot see an object here, neither can
        the model.
      </p>
      {error && <p className="admin__error" role="alert">{error}</p>}
      {!preview && !error && <p role="status">Preparing the pictures…</p>}
      {plan && (
        <>
          <p className="prep-step__summary">
            <strong>{plan.input_size} px.</strong> {plan.fit_explained}
          </p>
          {plan.objects && <Sizes label="Whole pictures" sizes={plan.objects} />}
          {plan.tiling.objects_after && <Sizes label="On tiles" sizes={plan.tiling.objects_after} />}
          <p className="prep-step__note">{plan.tiling.reason}</p>
          {plan.tiling.supported && <GridPicker grid={grid} onGrid={onGrid} />}
          {plan.masks && <p className="prep-step__hint">{plan.masks}</p>}
        </>
      )}
      {preview && <Seen preview={preview} />}
    </div>
  );
}
