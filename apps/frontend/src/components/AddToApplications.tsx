/**
 * "Add DinoTraining to your Applications folder?" (doc 130).
 *
 * Only for a Homebrew install: a formula cannot write outside its prefix, so the app
 * offers the link itself. The shell decides whether there is anything to offer; "Not
 * now" is remembered, so the bar asks once.
 */

import { useEffect, useState, type JSX } from 'react';

import { useT } from '../i18n';
import { isBoolean, readPersisted, writePersisted } from '../lib/persisted';
import { inShell } from '../setup/shell';

const DISMISSED = 'addToApplications.dismissed';

type State =
  | { readonly kind: 'hidden' }
  | { readonly kind: 'offer'; readonly folder: string }
  | { readonly kind: 'added'; readonly path: string }
  | { readonly kind: 'failed'; readonly message: string };

export function AddToApplications(): JSX.Element | null {
  const { t } = useT();
  const [state, setState] = useState<State>({ kind: 'hidden' });

  useEffect(() => {
    if (!inShell() || readPersisted(DISMISSED, false, isBoolean)) return;
    let cancelled = false;
    void import('@tauri-apps/api/core')
      .then(({ invoke }) => invoke<string | null>('applications_offer'))
      .then((folder) => {
        if (!cancelled && folder) setState({ kind: 'offer', folder });
      })
      .catch((error: unknown) => console.warn('applications_offer failed', error));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === 'hidden') return null;

  const add = async (): Promise<void> => {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      setState({ kind: 'added', path: await invoke<string>('add_to_applications') });
    } catch (error) {
      setState({ kind: 'failed', message: String(error) });
    }
  };
  const dismiss = (): void => {
    writePersisted(DISMISSED, true);
    setState({ kind: 'hidden' });
  };

  return (
    <div className="addapps" role="status">
      {state.kind === 'offer' && (
        <>
          <span>{t('app.addApps.question')}</span>
          <button type="button" className="btn btn--primary btn--small" onClick={() => void add()}>
            {t('app.addApps.add')}
          </button>
          <button type="button" className="btn btn--small" onClick={dismiss}>
            {t('app.addApps.notNow')}
          </button>
        </>
      )}
      {state.kind === 'added' && <span>{t('app.addApps.added', { path: state.path })}</span>}
      {state.kind === 'failed' && <span className="addapps__error">{t('app.addApps.failed', { message: state.message })}</span>}
    </div>
  );
}
