/**
 * Step 5: what the model sees (doc 85). The most important picture in the flow: the
 * user's own images at the model's resolution, enlarged without smoothing, with the
 * objects too small to learn marked red.
 */

import { useEffect, useState, type JSX } from 'react';

import { previewInput, type InputPreview, type ObjectSizes } from '../../api/prepPlan';
import { useT } from '../../i18n';
import { richText } from './richText';

export interface InputStepProps {
  readonly datasetId: string;
  readonly target: string;
  /** Tiles along the long edge, or null for the plan's own choice. */
  readonly grid: number | null;
  readonly onGrid: (grid: number | null) => void;
}

function Sizes({ label, sizes }: { readonly label: string; readonly sizes: ObjectSizes }): JSX.Element {
  const { t } = useT();
  const text = t('prepare.input.sizes', { label, p10: sizes.p10_px, needed: sizes.needed_px });
  return (
    <p className="prep-step__summary">
      {richText(text, {
        median: <strong>{sizes.median_px} px</strong>,
        share: <strong>{Math.round(sizes.too_small_share * 100)}%</strong>,
      })}
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
  const { t } = useT();
  return (
    <label className="genpanel__field prep-step__grid">
      <span>{t('prepare.input.tiles')}</span>
      <select
        value={grid === null ? 'auto' : String(grid)}
        onChange={(event) => onGrid(event.target.value === 'auto' ? null : Number(event.target.value))}
      >
        <option value="auto">{t('prepare.input.recommended')}</option>
        <option value="1">{t('prepare.input.off')}</option>
        {[2, 3, 4, 5, 6].map((n) => (
          <option key={n} value={n}>
            {t('prepare.input.grid', { count: n })}
          </option>
        ))}
      </select>
    </label>
  );
}

function Seen({ preview }: { readonly preview: InputPreview }): JSX.Element {
  const { t, tp } = useT();
  return (
    <div className="prep-seen">
      {preview.images.map((image) => (
        <figure key={image.path} className="prep-seen__item">
          <img src={image.data_url} alt={t('prepare.input.seenAlt', { path: image.path })} width={image.width} height={image.height} />
          <figcaption>
            {tp('prepare.input.objects', image.objects)}
            {image.too_small ? t('prepare.input.tooSmall', { count: image.too_small }) : ''}
            {image.lost ? t('prepare.input.cutOff', { count: image.lost }) : ''}
            {image.tile ? t('prepare.input.oneTile') : ''}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

export function InputStep({ datasetId, target, grid, onGrid }: InputStepProps): JSX.Element {
  const { t } = useT();
  const { preview, error } = usePreview(datasetId, target, grid);
  const plan = preview?.plan;
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        {t('prepare.input.why')}
      </p>
      {error && <p className="admin__error" role="alert">{error}</p>}
      {!preview && !error && <p role="status">{t('prepare.input.preparing')}</p>}
      {plan && (
        <>
          <p className="prep-step__summary">
            <strong>{plan.input_size} px.</strong> {plan.fit_explained}
          </p>
          {plan.objects && <Sizes label={t('prepare.input.whole')} sizes={plan.objects} />}
          {plan.tiling.objects_after && <Sizes label={t('prepare.input.onTiles')} sizes={plan.tiling.objects_after} />}
          <p className="prep-step__note">{plan.tiling.reason}</p>
          {plan.tiling.supported && <GridPicker grid={grid} onGrid={onGrid} />}
          {plan.masks && <p className="prep-step__hint">{plan.masks}</p>}
        </>
      )}
      {preview && <Seen preview={preview} />}
    </div>
  );
}
