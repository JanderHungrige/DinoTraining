/**
 * "Ask me when a prediction is unclear", with the user's own score range (doc 72).
 */

import type { JSX } from 'react';

import { useT } from '../i18n';
import type { UnclearBand } from '../lib/unclearBand';

export interface UnclearBandFieldProps {
  readonly enabled: boolean;
  readonly band: UnclearBand;
  readonly disabled: boolean;
  readonly onEnabledChange: (enabled: boolean) => void;
  readonly onBandChange: (band: UnclearBand) => void;
}

function bound(value: string, fallback: number): number {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function UnclearBandField({
  enabled,
  band,
  disabled,
  onEnabledChange,
  onBandChange,
}: UnclearBandFieldProps): JSX.Element {
  const { t } = useT();
  return (
    <fieldset className="unclearband" disabled={disabled}>
      <legend className="unclearband__legend">{t('generator.unclear.legend')}</legend>
      <label className="unclearband__toggle">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => onEnabledChange(event.target.checked)}
        />
        {t('generator.unclear.toggle')}
      </label>
      <input
        type="number"
        className="unclearband__bound"
        min={0}
        max={1}
        step={0.05}
        value={band.low}
        disabled={disabled || !enabled}
        aria-label={t('generator.unclear.lowAria')}
        onChange={(event) => onBandChange({ ...band, low: bound(event.target.value, band.low) })}
      />
      <span aria-hidden="true">{t('generator.unclear.and')}</span>
      <input
        type="number"
        className="unclearband__bound"
        min={0}
        max={1}
        step={0.05}
        value={band.high}
        disabled={disabled || !enabled}
        aria-label={t('generator.unclear.highAria')}
        onChange={(event) => onBandChange({ ...band, high: bound(event.target.value, band.high) })}
      />
      <span className="unclearband__hint">{t('generator.unclear.hint')}</span>
    </fieldset>
  );
}
