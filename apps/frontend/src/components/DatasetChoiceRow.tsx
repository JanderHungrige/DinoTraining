/**
 * Which dataset a folder's annotations go into, or the name of a new one. Split out of
 * `SessionSetup` (at the 300-line gate) when doc 104 added the annotation target.
 */

import type { JSX } from 'react';

import type { DatasetInfo } from '../api/datasets';

export interface DatasetChoiceRowProps {
  readonly datasets: readonly DatasetInfo[];
  /** '' means "create a new one". */
  readonly datasetId: string;
  readonly newName: string;
  readonly onDataset: (id: string) => void;
  readonly onNewName: (name: string) => void;
}

export function DatasetChoiceRow(props: DatasetChoiceRowProps): JSX.Element {
  const { datasets, datasetId, newName } = props;
  return (
    <div className="setup__row">
      <label className="setup__field" htmlFor="dataset">
        Dataset
        <select id="dataset" value={datasetId} onChange={(event) => props.onDataset(event.target.value)}>
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
            onChange={(event) => props.onNewName(event.target.value)}
          />
        </label>
      )}
    </div>
  );
}
