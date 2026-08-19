/**
 * Wave 4 — where the user supplies their own HuggingFace token.
 *
 * The app never downloads gated weights on anyone's behalf, so this panel's job is to make
 * the obligations visible and give the token somewhere to live. It never renders a token:
 * the backend returns `configured` and a masked `hint`, and there is no state here that
 * holds a saved value.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import {
  acceptLicence,
  clearToken,
  fetchLicenceNotices,
  fetchTokenStatus,
  saveToken,
  type LicenceNotice,
  type TokenStatus,
} from '../api/settings';

const TOKEN_HELP_URL = 'https://huggingface.co/settings/tokens';

function LicenceRow({
  notice,
  onAccept,
  busy,
}: {
  readonly notice: LicenceNotice;
  readonly onAccept: (modelId: string) => void;
  readonly busy: boolean;
}): JSX.Element {
  return (
    <li className="tokenpanel__licence">
      <div className="tokenpanel__licence-head">
        <strong>{notice.model_id}</strong>
        <span className="tokenpanel__licence-name">{notice.licence}</span>
        {notice.requires_access_request ? (
          <span className="tokenpanel__badge" title="A person at Meta approves this by hand">
            manual approval
          </span>
        ) : null}
      </div>
      <p className="tokenpanel__explain">{notice.explanation}</p>
      <div className="tokenpanel__licence-actions">
        <a href={notice.licence_url} target="_blank" rel="noreferrer noopener">
          Open the model page
        </a>
        <label className="tokenpanel__ack">
          <input
            type="checkbox"
            checked={notice.accepted}
            disabled={notice.accepted || busy}
            onChange={() => onAccept(notice.model_id)}
          />
          I have read the {notice.licence}
        </label>
      </div>
    </li>
  );
}

export function TokenPanel(): JSX.Element {
  const [status, setStatus] = useState<TokenStatus | null>(null);
  const [notices, setNotices] = useState<readonly LicenceNotice[]>([]);
  // Only the user's typing lives here. The saved token is never loaded into state —
  // there is nothing to load, because the backend does not return it.
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const [nextStatus, nextNotices] = await Promise.all([
      fetchTokenStatus(signal),
      fetchLicenceNotices(signal),
    ]);
    setStatus(nextStatus);
    setNotices(nextNotices);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal).catch(() => {
      /* the panel renders its not-configured state; the models panel reports outages */
    });
    return () => controller.abort();
  }, [refresh]);

  const run = async (action: () => Promise<TokenStatus>): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
      setDraft('');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the token.');
    } finally {
      setBusy(false);
    }
  };

  const onSave = async (): Promise<void> => {
    await run(() => saveToken(draft.trim()));
    setSaved(true);
  };

  return (
    <section className="tokenpanel">
      <h3 className="tokenpanel__title">HuggingFace access</h3>

      <p className="tokenpanel__intro">
        Some models are gated by their publisher. DinoTraining never downloads them for you
        and never ships a token — you provide your own, and you start every download
        yourself. Everything needed for the open models, including{' '}
        <strong>Grounded SAM</strong> for segmentation masks, works without any of this.
      </p>

      <label className="tokenpanel__field">
        <span>Your HuggingFace access token</span>
        <input
          type="password"
          autoComplete="off"
          spellCheck={false}
          placeholder={status?.configured ? (status.hint ?? 'Configured') : 'hf_…'}
          value={draft}
          disabled={busy}
          onChange={(event) => {
            setDraft(event.target.value);
            setSaved(false);
          }}
        />
      </label>

      <p className="tokenpanel__hint">
        A <em>read</em> token is enough. Create one at{' '}
        <a href={TOKEN_HELP_URL} target="_blank" rel="noreferrer noopener">
          {TOKEN_HELP_URL}
        </a>
        . It is stored in <code>{status?.env_file ?? '.env'}</code>, readable only by you,
        and never leaves this machine.
      </p>

      <div className="tokenpanel__actions">
        <button type="button" disabled={busy || draft.trim().length === 0} onClick={onSave}>
          {busy ? 'Saving…' : 'Save token'}
        </button>
        {status?.configured ? (
          <button type="button" disabled={busy} onClick={() => void run(clearToken)}>
            Remove
          </button>
        ) : null}
        <span className="tokenpanel__state">
          {status?.configured
            ? `Configured (${status.hint ?? 'stored'})`
            : 'Not set — gated models stay unavailable'}
        </span>
      </div>

      {saved ? <p className="tokenpanel__ok">Token saved. Gated models are now offered.</p> : null}
      {error ? <p className="tokenpanel__error">{error}</p> : null}

      {notices.length > 0 ? (
        <>
          <h4 className="tokenpanel__subtitle">Models that need something from you</h4>
          <ul className="tokenpanel__licences">
            {notices.map((notice) => (
              <LicenceRow
                key={notice.model_id}
                notice={notice}
                busy={busy}
                onAccept={(modelId) => void run(() => acceptLicence(modelId))}
              />
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
