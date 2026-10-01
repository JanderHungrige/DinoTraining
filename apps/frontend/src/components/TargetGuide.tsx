/**
 * "Annotating for: …" (doc 104): what each layer means for the chosen model, and what
 * this picture still lacks. It marks; it never blocks saving.
 */

import type { JSX } from 'react';

import type { AnnotationTarget, LayerLevel } from '../api/annotationTargets';
import type { PictureStatus } from '../api/phrases';
import { useT, type Key } from '../i18n';
import { checkLine } from '../lib/pictureChecklist';
import type { CanvasBox } from '../types/annotation';
import '../targets.css';

export interface TargetGuideProps {
  readonly target: AnnotationTarget;
  readonly boxes: readonly CanvasBox[];
  readonly phraseCount: number;
  readonly statuses: readonly PictureStatus[];
}

const BADGE: Record<LayerLevel, Key> = {
  required: 'studio.guide.required',
  recommended: 'studio.guide.recommended',
  optional: 'studio.guide.optional',
};

export function TargetGuide({ target, boxes, phraseCount, statuses }: TargetGuideProps): JSX.Element {
  const tr = useT();
  const { t, tp } = tr;
  const shown = target.layers.filter((rule) => rule.level !== 'optional');
  const lines = shown.map((rule) => ({ rule, line: checkLine(rule.layer, boxes, phraseCount, statuses, tr) }));
  const missing = lines.filter(({ rule, line }) => rule.level === 'required' && !line.met).length;
  return (
    <details className="targetguide">
      <summary>
        {t('studio.guide.annotatingFor')} <strong>{target.label}</strong>
        {missing > 0 && <span className="targetguide__missing"> · {tp('studio.guide.missing', missing)}</span>}
      </summary>
      <div className="targetguide__body">
        <ul className="targetguide__layers" aria-label={t('studio.guide.needs')}>
          {target.layers.map((rule) => (
            <li key={rule.layer}>
              <span className={`targetguide__badge targetguide__badge--${rule.level}`}>{t(BADGE[rule.level])}</span>{' '}
              <strong>{rule.label}</strong> — {rule.why}
            </li>
          ))}
        </ul>
        {lines.length > 0 && (
          <>
            <h4 className="targetguide__title">{t('studio.guide.thisPicture')}</h4>
            <ul className="targetguide__checks" aria-label={t('studio.guide.thisPicture')}>
              {lines.map(({ rule, line }) => (
                <li key={rule.layer} className={line.met ? 'targetguide__met' : rule.level === 'required' ? 'targetguide__open' : ''}>
                  <span aria-hidden="true">{line.met ? '✓' : '○'}</span> {rule.label}: {line.text}
                  <span className="visually-hidden">{` (${t(line.met ? 'studio.guide.done' : 'studio.guide.stillOpen')})`}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </details>
  );
}
