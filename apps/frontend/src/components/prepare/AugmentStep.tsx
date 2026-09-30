/**
 * Step 7: augmentation (doc 87). A preset per kind of picture, and one of the user's own
 * pictures shown as the model gets it, then changed as training will change it.
 */

import { useEffect, useState, type JSX } from 'react';

import { previewAugmentation, type AugmentationPlan, type AugmentationPreview } from '../../api/prepPlan';
import { useT } from '../../i18n';
import { OptionList } from './OptionList';

export interface AugmentStepProps {
  readonly datasetId: string;
  readonly target: string;
  readonly plan: AugmentationPlan | null;
  readonly preset: string;
  readonly onPreset: (preset: string) => void;
}

function usePreview(datasetId: string, target: string, preset: string) {
  const [preview, setPreview] = useState<AugmentationPreview | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    setPreview(null);
    setError('');
    if (!datasetId || !target || !preset) return;
    let live = true;
    previewAugmentation(datasetId, target, preset)
      .then((found) => live && setPreview(found))
      .catch((cause: unknown) => live && setError(cause instanceof Error ? cause.message : String(cause)));
    return () => {
      live = false;
    };
  }, [datasetId, target, preset]);
  return { preview, error };
}

function Strip({ preview }: { readonly preview: AugmentationPreview }): JSX.Element {
  const { t } = useT();
  return (
    <div className="prep-seen">
      {preview.images.map((image, index) => (
        <figure key={image.data_url.slice(-40) + index} className="prep-seen__item">
          <img src={image.data_url} alt={index === 0 ? t('prepare.augment.originalAlt') : t('prepare.augment.changedAlt', { n: index })} />
          <figcaption>{index === 0 ? t('prepare.augment.original') : t('prepare.augment.version', { n: index })}</figcaption>
        </figure>
      ))}
    </div>
  );
}

export function AugmentStep({ datasetId, target, plan, preset, onPreset }: AugmentStepProps): JSX.Element {
  const { t } = useT();
  const { preview, error } = usePreview(datasetId, target, preset);
  if (!plan) return <p role="status">{t('prepare.augment.looking')}</p>;
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        {t('prepare.augment.why')}
      </p>
      <p className="prep-step__summary">{plan.reason}</p>
      <OptionList
        name="prep-augment"
        label={t('prepare.augment.label')}
        options={plan.presets.map((option) => ({ ...option, badges: option.guarded ? [t('prepare.augment.noMirroring')] : [] }))}
        recommended={plan.recommended}
        value={preset}
        onChange={onPreset}
      />
      {error && <p className="admin__error" role="alert">{error}</p>}
      {preview && <Strip preview={preview} />}
    </div>
  );
}
