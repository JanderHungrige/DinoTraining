/**
 * Import a community head by HuggingFace repo id.
 *
 * The safetensors-only rule is stated up front rather than discovered through a 415.
 * A user who has to fail once to learn the constraint reads it as a bug in the app,
 * not as a deliberate refusal to run someone else's pickle.
 */

import { type FormEvent, type JSX } from 'react';

import { usePersistentState } from '../hooks/usePersistentState';
import { useT } from '../i18n';
import { isString, stillListed } from '../lib/persisted';

import type { ImportRequest } from '../api/headCatalog';
import type { BackboneInfo } from '../api/backbones';
import type { HeadTypeInfo } from '../api/heads';

export interface HeadImportFormProps {
  readonly headTypes: readonly HeadTypeInfo[];
  readonly backbones: readonly BackboneInfo[];
  readonly busy: boolean;
  readonly onImport: (request: ImportRequest) => Promise<boolean>;
}

export function HeadImportForm({
  headTypes,
  backbones,
  busy,
  onImport,
}: HeadImportFormProps): JSX.Element {
  const { t } = useT();
  // Doc 69: remembered across tab switches and restarts.
  const [repoId, setRepoId] = usePersistentState('headImport.repoId', '', isString);
  const [numClasses, setNumClasses] = usePersistentState('headImport.numClasses', '', isString);
  // Only the user's *override* is stored; the effective value falls back to the first
  // option. Seeding state from headTypes[0] instead looks equivalent but is not: both
  // lists arrive asynchronously, so the initialiser runs against an empty array and
  // the state stays "". The <select> then renders its first option while React still
  // believes nothing is selected — which silently disabled the submit button forever.
  const [headTypeOverride, setHeadTypeOverride] = usePersistentState(
    'headImport.headType',
    '',
    isString,
  );
  const [backboneOverride, setBackboneOverride] = usePersistentState(
    'headImport.backbone',
    '',
    isString,
  );
  const headTypeId =
    stillListed(headTypeOverride, headTypes.map((entry) => entry.id)) || headTypes[0]?.id || '';
  const backboneId =
    stillListed(backboneOverride, backbones.map((entry) => entry.id)) || backbones[0]?.id || '';

  const ready = repoId.trim() !== '' && headTypeId !== '' && backboneId !== '';

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!ready || busy) return;

    const parsed = Number.parseInt(numClasses, 10);
    const ok = await onImport({
      repo_id: repoId.trim(),
      head_type_id: headTypeId,
      backbone_id: backboneId,
      num_classes: Number.isFinite(parsed) ? parsed : null,
    });
    // Cleared only on success: a failed import is usually a one-character fix, and
    // wiping the field would make the user retype what they nearly had right.
    if (ok) setRepoId('');
  }

  return (
    <form className="headimport" onSubmit={(event) => void submit(event)}>
      <p className="headimport__note">
        {t('admin.import.noteBefore')}
        <strong>safetensors</strong>
        {t('admin.import.noteFiles')}
        <code>.pt</code>
        {t('admin.import.noteOr')}
        <code>.pth</code>
        {t('admin.import.noteAfter')}
      </p>

      <div className="headimport__row">
        <label className="field">
          <span className="field__label">{t('admin.import.repo')}</span>
          <input
            className="field__input"
            type="text"
            placeholder={t('admin.import.repoPlaceholder')}
            value={repoId}
            onChange={(event) => setRepoId(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">{t('admin.import.headType')}</span>
          <select
            className="field__input"
            value={headTypeId}
            onChange={(event) => setHeadTypeOverride(event.target.value)}
          >
            {headTypes.map((headType) => (
              <option key={headType.id} value={headType.id}>
                {headType.title}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">{t('admin.import.backbone')}</span>
          <select
            className="field__input"
            value={backboneId}
            onChange={(event) => setBackboneOverride(event.target.value)}
          >
            {backbones.map((backbone) => (
              <option key={backbone.id} value={backbone.id}>
                {backbone.id}
              </option>
            ))}
          </select>
        </label>

        <label className="field field--narrow">
          <span className="field__label">{t('admin.import.classes')}</span>
          <input
            className="field__input"
            type="number"
            min={1}
            placeholder={t('admin.import.classesPlaceholder')}
            value={numClasses}
            onChange={(event) => setNumClasses(event.target.value)}
          />
        </label>
      </div>

      <button type="submit" className="btn" disabled={!ready || busy}>
        {busy ? t('admin.import.importing') : t('admin.import.submit')}
      </button>
    </form>
  );
}
