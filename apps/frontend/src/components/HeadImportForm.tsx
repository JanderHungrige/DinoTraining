/**
 * Import a community head by HuggingFace repo id.
 *
 * The safetensors-only rule is stated up front rather than discovered through a 415.
 * A user who has to fail once to learn the constraint reads it as a bug in the app,
 * not as a deliberate refusal to run someone else's pickle.
 */

import { useState, type FormEvent, type JSX } from 'react';

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
  const [repoId, setRepoId] = useState('');
  const [numClasses, setNumClasses] = useState('');
  // Only the user's *override* is stored; the effective value falls back to the first
  // option. Seeding state from headTypes[0] instead looks equivalent but is not: both
  // lists arrive asynchronously, so the initialiser runs against an empty array and
  // the state stays "". The <select> then renders its first option while React still
  // believes nothing is selected — which silently disabled the submit button forever.
  const [headTypeOverride, setHeadTypeOverride] = useState('');
  const [backboneOverride, setBackboneOverride] = useState('');
  const headTypeId = headTypeOverride || headTypes[0]?.id || '';
  const backboneId = backboneOverride || backbones[0]?.id || '';

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
        Community heads must be published as <strong>safetensors</strong>. Files in{' '}
        <code>.pt</code> or <code>.pth</code> format are refused — loading one would run
        arbitrary code from the repository.
      </p>

      <div className="headimport__row">
        <label className="field">
          <span className="field__label">HuggingFace repo</span>
          <input
            className="field__input"
            type="text"
            placeholder="owner/name"
            value={repoId}
            onChange={(event) => setRepoId(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Head type</span>
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
          <span className="field__label">Backbone</span>
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
          <span className="field__label">Classes</span>
          <input
            className="field__input"
            type="number"
            min={1}
            placeholder="auto"
            value={numClasses}
            onChange={(event) => setNumClasses(event.target.value)}
          />
        </label>
      </div>

      <button type="submit" className="btn" disabled={!ready || busy}>
        {busy ? 'Importing…' : 'Import head'}
      </button>
    </form>
  );
}
