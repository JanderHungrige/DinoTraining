/** "Carry my corrections to the next picture" and what it carried (doc 170). */

import type { JSX } from 'react';

import { useT } from '../i18n';
import type { CarryCounts } from '../lib/carryCorrections';

export interface CarryCorrectionsProps {
  readonly enabled: boolean;
  readonly onEnabled: (enabled: boolean) => void;
  readonly carried: CarryCounts | null;
}

export function CarryCorrections({ enabled, onEnabled, carried }: CarryCorrectionsProps): JSX.Element {
  const { t } = useT();
  return (
    <div className="studio__carry">
      <label title={t('studio.carry.hint')}>
        <input type="checkbox" checked={enabled} onChange={(event) => onEnabled(event.target.checked)} />{' '}
        {t('studio.carry.label')}
      </label>
      {enabled && carried && (
        <span role="status" className="studio__carrynote">
          {t('studio.carry.done', { renamed: carried.renamed, verdicts: carried.verdicts, removed: carried.removed })}
        </span>
      )}
    </div>
  );
}
