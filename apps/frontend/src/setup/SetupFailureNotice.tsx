/** Why the install stopped, in plain words, and the way on (doc 127). */

import type { JSX } from 'react';

import { useT, type Language, type Translator } from '../i18n';
import { formatGb } from './MachineSummary';
import type { SetupFailure } from './shell';

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
    default:
      throw new Error(`Unhandled failure: ${failure satisfies never}`);
  }
}

interface Props {
  readonly failure: SetupFailure;
  readonly onRetry: () => void;
}

export function SetupFailureNotice({ failure, onRetry }: Props): JSX.Element {
  const { t, lang } = useT();
  return (
    <div className="firstrun__failure" role="alert">
      <p>{message(t, lang, failure)}</p>
      {failure.kind !== 'unsupported' && (
        <>
          <p className="firstrun__hint">{t('setup.fail.resume')}</p>
          <button type="button" className="btn btn--primary" onClick={onRetry}>
            {t('setup.retry')}
          </button>
        </>
      )}
    </div>
  );
}
