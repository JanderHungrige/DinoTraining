/** Why the install stopped, in plain words, and the way on (doc 127). */

import type { JSX } from 'react';

import { useT, type Language, type Translator } from '../i18n';
import { formatGb } from './MachineSummary';
import { CUDA_VERSION, type SetupFailure, type Variant } from './shell';

/** "CPU" or "GPU (CUDA 13.0)". */
export function variantName(t: Translator['t'], variant: Variant): string {
  const cuda = CUDA_VERSION[variant];
  return cuda ? t('setup.variant.gpu', { cuda }) : t('setup.variant.cpu');
}

function message(t: Translator['t'], lang: Language, failure: SetupFailure): string {
  switch (failure.kind) {
    case 'offline':
      return t('setup.fail.offline');
    case 'disk':
      return t('setup.fail.disk', {
        needed: formatGb(failure.needed_gb, lang),
        free: formatGb(failure.free_gb, lang),
        path: failure.path,
      });
    case 'unsupported':
      return t('setup.fail.unsupported');
    case 'failed':
      return t('setup.fail.failed', { message: failure.message });
    case 'rolled_back':
      return t('setup.fail.rolledBack', { reason: message(t, lang, failure.reason), to: variantName(t, failure.to) });
    default:
      throw new Error(`Unhandled failure: ${failure satisfies never}`);
  }
}

interface Props {
  readonly failure: SetupFailure;
  readonly onRetry: () => void;
  /** Doc 128: a failed switch leaves a working app to go back to. */
  readonly onBack?: () => void;
}

export function SetupFailureNotice({ failure, onRetry, onBack }: Props): JSX.Element {
  const { t, lang } = useT();
  return (
    <div className="firstrun__failure" role="alert">
      <p>{message(t, lang, failure)}</p>
      {failure.kind !== 'unsupported' && (
        <>
          <p className="firstrun__hint">{t('setup.fail.resume')}</p>
          <div className="firstrun__choices">
            <button type="button" className="btn btn--primary" onClick={onRetry}>
              {t('setup.retry')}
            </button>
            {onBack && (
              <button type="button" className="btn" onClick={onBack}>
                {t('setup.back')}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
