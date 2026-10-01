/** Why the install stopped, in plain words, and the way on (doc 127). */

import type { JSX } from 'react';

import { useT, type Key, type Language, type Translator } from '../i18n';
import { formatGb } from './MachineSummary';
import { CUDA_VERSION, VC_RUNTIME, type SetupFailure, type Variant, type VcRuntimeReason } from './shell';

/** "CPU" or "GPU (CUDA 13.0)". */
export function variantName(t: Translator['t'], variant: Variant): string {
  const cuda = CUDA_VERSION[variant];
  return cuda ? t('setup.variant.gpu', { cuda }) : t('setup.variant.cpu');
}

const VC_REASONS: Readonly<Record<VcRuntimeReason, Key>> = {
  declined: 'setup.fail.vcRuntime.declined',
  unsigned: 'setup.fail.vcRuntime.unsigned',
  download: 'setup.fail.vcRuntime.download',
  installer: 'setup.fail.vcRuntime.installer',
  still_old: 'setup.fail.vcRuntime.stillOld',
};

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
    case 'vc_runtime':
      return t('setup.fail.vcRuntime', {
        minimum: VC_RUNTIME.minimum,
        found: failure.found ?? t('setup.fail.vcRuntime.none'),
        reason: t(VC_REASONS[failure.reason], { code: String(failure.code ?? '') }),
        url: VC_RUNTIME.url,
      });
    case 'rolled_back':
      return t('setup.fail.rolledBack', { reason: message(t, lang, failure.reason), to: variantName(t, failure.to) });
    default:
      throw new Error(`Unhandled failure: ${failure satisfies never}`);
  }
}

interface Props {
  readonly failure: SetupFailure;
  readonly onRetry: () => void;
  /** Docs 128/129: the way back to a working app — "Back to the app", "Start with the
   *  previous packages". */
  readonly secondary?: { readonly label: string; readonly onClick: () => void };
}

export function SetupFailureNotice({ failure, onRetry, secondary }: Props): JSX.Element {
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
            {secondary && (
              <button type="button" className="btn" onClick={secondary.onClick}>
                {secondary.label}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
