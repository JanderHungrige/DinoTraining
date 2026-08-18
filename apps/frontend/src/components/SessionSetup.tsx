/**
 * Session setup: pick a folder, pick or create a dataset, write a prompt.
 *
 * The folder is a text field with an optional native picker. Under Tauri the dialog
 * plugin gives a real picker; in a browser (the `web` dev mode, and Wave 6) there is
 * none, so the field is always editable rather than being disabled without one.
 */

import { useEffect, useState, type FormEvent, type JSX } from 'react';

import { DEFAULT_BOX_THRESHOLD, DEFAULT_TEXT_THRESHOLD } from '../api/annotate';
import { createDataset, listDatasets, type DatasetInfo } from '../api/datasets';
import type { SessionConfig } from '../hooks/useAnnotationSession';
import { hasNativeDialog, pickFolder } from '../lib/dialog';

export interface SessionSetupProps {
  readonly onStart: (config: SessionConfig) => void;
  readonly disabled?: boolean;
}

export function SessionSetup({ onStart, disabled = false }: SessionSetupProps): JSX.Element {
  const [folder, setFolder] = useState('');
  const [prompt, setPrompt] = useState('');
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [datasetId, setDatasetId] = useState('');
  const [newName, setNewName] = useState('');
  const [boxThreshold, setBoxThreshold] = useState(DEFAULT_BOX_THRESHOLD);
  const [error, setError] = useState<string | null>(null);
  const [hasPicker, setHasPicker] = useState(false);

  useEffect(() => {
    setHasPicker(hasNativeDialog());
    void listDatasets()
      .then(setDatasets)
      .catch(() => setError('Could not load datasets.'));
  }, []);

  const handleSubmit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setError(null);

    let targetId = datasetId;
    if (!targetId) {
      if (!newName.trim()) {
        setError('Choose an existing dataset or name a new one.');
        return;
      }
      try {
        const created = await createDataset(newName.trim(), prompt || null);
        targetId = created.id;
        setDatasets((current) => [created, ...current]);
        setDatasetId(created.id);
      } catch {
        setError('Could not create the dataset.');
        return;
      }
    }

    onStart({
      folder: folder.trim(),
      datasetId: targetId,
      prompt: prompt.trim(),
      boxThreshold,
      textThreshold: DEFAULT_TEXT_THRESHOLD,
    });
  };

  return (
    <form className="setup" onSubmit={(event) => void handleSubmit(event)}>
      <div className="setup__row">
        <label className="setup__field setup__field--grow" htmlFor="folder">
          Image folder
          <span className="setup__control">
            <input
              id="folder"
              type="text"
              value={folder}
              placeholder="/Users/you/photos"
              required
              onChange={(event) => setFolder(event.target.value)}
            />
            {hasPicker && (
              <button
                type="button"
                className="btn"
                onClick={() => void pickFolder().then((picked) => picked && setFolder(picked))}
              >
                Browse…
              </button>
            )}
          </span>
        </label>
      </div>

      <div className="setup__row">
        <label className="setup__field" htmlFor="dataset">
          Dataset
          <select
            id="dataset"
            value={datasetId}
            onChange={(event) => setDatasetId(event.target.value)}
          >
            <option value="">Create a new one…</option>
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} ({dataset.counts.images} images)
              </option>
            ))}
          </select>
        </label>

        {!datasetId && (
          <label className="setup__field" htmlFor="newname">
            New dataset name
            <input
              id="newname"
              type="text"
              value={newName}
              placeholder="Cats"
              onChange={(event) => setNewName(event.target.value)}
            />
          </label>
        )}
      </div>

      <div className="setup__row">
        <label className="setup__field setup__field--grow" htmlFor="prompt">
          Prompt
          <input
            id="prompt"
            type="text"
            value={prompt}
            placeholder="a cat. a dog."
            required
            onChange={(event) => setPrompt(event.target.value)}
          />
        </label>

        <label className="setup__field" htmlFor="boxthreshold">
          Box threshold <span className="setup__value">{boxThreshold.toFixed(2)}</span>
          <input
            id="boxthreshold"
            type="range"
            min={0.05}
            max={0.95}
            step={0.05}
            value={boxThreshold}
            onChange={(event) => setBoxThreshold(Number(event.target.value))}
          />
        </label>
      </div>

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
      )}

      <button type="submit" className="btn btn--primary" disabled={disabled}>
        Start annotating
      </button>
    </form>
  );
}
