/** "Picture cache" in Cloud storage (doc 149): how much linked pictures use, its bound, empty it. */

import { useEffect, useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import { clearCache, getCache, setCacheBound, type CacheState } from '../api/cloud';
import { useT } from '../i18n';

const GB = 1024 ** 3;

function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

export function CloudCache(): JSX.Element | null {
  const { t, lang } = useT();
  const [state, setState] = useState<CacheState | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [problem, setProblem] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    getCache(controller.signal)
      .then(setState)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setProblem(message(error));
      });
    return () => controller.abort();
  }, []);

  if (!state) return problem ? <p className="dsimport__error" role="alert">{problem}</p> : null;

  const run = (work: Promise<CacheState>): void => {
    setProblem('');
    work.then((next) => { setState(next); setDraft(null); }).catch((error: unknown) => setProblem(message(error)));
  };
  const format = (value: number): string => value.toLocaleString(lang, { maximumFractionDigits: 2 });
  const save = (): void => {
    const value = Number((draft ?? '').replace(',', '.'));
    if (draft !== null && value > 0) run(setCacheBound(value));
  };

  return (
    <div className="cloud__cache" role="group" aria-label={t('cloud.cache.title')}>
      <h4>{t('cloud.cache.title')}</h4>
      <p className="dsguide__lead">{t('cloud.cache.use', { used: format(state.used_bytes / GB), bound: format(state.bound_gb) })}</p>
      <div className="cloud__buttons">
        <label className="dsimport__check">
          {t('cloud.cache.bound')}
          <input type="number" min={0.1} step={0.5} className="autoexport__minutes" value={draft ?? String(state.bound_gb)}
            onChange={(event) => setDraft(event.target.value)} onBlur={save} />
        </label>
        <button type="button" className="btn btn--small" disabled={state.used_bytes === 0} onClick={() => run(clearCache())}>
          {t('cloud.cache.clear')}
        </button>
      </div>
      {problem && <p className="dsimport__error" role="alert">{problem}</p>}
    </div>
  );
}
