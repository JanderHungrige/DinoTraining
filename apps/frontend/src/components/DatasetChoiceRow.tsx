/**
 * Which dataset a folder's annotations go into, or the name of a new one. Split out of
 * `SessionSetup` (at the 300-line gate) when doc 104 added the annotation target.
 */

import type { JSX } from 'react';

import type { DatasetInfo } from '../api/datasets';
import { useT } from '../i18n';

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
  const { t, tp } = useT();
  return (
    <div className="setup__row">
      <label className="setup__field" htmlFor="dataset">
        {t('studio.choice.dataset')}
        <select id="dataset" value={datasetId} onChange={(event) => props.onDataset(event.target.value)}>
          <option value="">{t('studio.choice.createNew')}</option>
          {datasets.map((dataset) => (
            <option key={dataset.id} value={dataset.id}>
              {tp('studio.choice.option', dataset.counts.images, { name: dataset.name })}
            </option>
          ))}
        </select>
      </label>

      {!datasetId && (
        <label className="setup__field" htmlFor="newname">
          {t('studio.choice.newName')}
          <input
            id="newname"
            type="text"
            value={newName}
            placeholder={t('studio.choice.newNamePlaceholder')}
            onChange={(event) => props.onNewName(event.target.value)}
          />
        </label>
      )}
    </div>
  );
}
