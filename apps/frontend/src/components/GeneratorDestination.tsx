/**
 * Where generated annotations go: an existing dataset, or a new one.
 *
 * Split out of `GeneratorSetup` when that file passed the project's 300-line limit. It is
 * a genuine seam rather than an arbitrary cut — "which dataset receives the output" is the
 * one question here that has nothing to do with *how* the annotations are produced, and it
 * is the only part that creates something.
 *
 * `''` means "create a new one", which is a valid choice, so readiness depends on the name
 * field rather than on the select having a value.
 */

import { useEffect, useState, type JSX } from 'react';

import { createDataset, listDatasets, type DatasetInfo } from '../api/datasets';
import { RevealDatasetButton } from './RevealDatasetButton';

export interface GeneratorDestinationProps {
  readonly datasetId: string;
  readonly newName: string;
  readonly onSelect: (datasetId: string) => void;
  readonly onNameChange: (name: string) => void;
}

/** An existing dataset id, or a freshly created one. Resolved before the session starts. */
export async function resolveDataset(datasetId: string, newName: string): Promise<string> {
  if (datasetId) return datasetId;
  const created = await createDataset(newName.trim(), null, false);
  return created.id;
}

/** True when the destination is usable: an existing dataset, or a name to create one. */
export function destinationReady(datasetId: string, newName: string): boolean {
  return datasetId !== '' || newName.trim().length > 0;
}

export function GeneratorDestination({
  datasetId,
  newName,
  onSelect,
  onNameChange,
}: GeneratorDestinationProps): JSX.Element {
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    listDatasets(controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setDatasets(found);
      })
      .catch(() => {
        /* creating a new one still works */
      });
    return () => controller.abort();
  }, []);

  return (
    <>
      <label className="genpanel__field">
        <span>Save into</span>
        <select value={datasetId} onChange={(event) => onSelect(event.target.value)}>
          <option value="">Create a new dataset…</option>
          {datasets.map((dataset) => (
            <option key={dataset.id} value={dataset.id}>
              {dataset.name} ({dataset.counts.images} images)
            </option>
          ))}
        </select>
      </label>

      {/* Also a dataset selection: "where does this go" is a thing people want to open
          just as often as "where did this come from". */}
      <RevealDatasetButton datasetId={datasetId} />

      {datasetId === '' && (
        <label className="genpanel__field">
          <span>New dataset name</span>
          <input
            type="text"
            value={newName}
            placeholder="Bolts, round two"
            onChange={(event) => onNameChange(event.target.value)}
          />
        </label>
      )}
    </>
  );
}
