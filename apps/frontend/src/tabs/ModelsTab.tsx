/**
 * Models & Datasets (doc 135): the entry point, right after Start here.
 *
 * Official Models is the former Admin page, unchanged. Datasets and My Models are the
 * former Library's two halves; docs 136-138 add the dataset import, the layout guide and
 * the OSDaR23 example to Datasets.
 */

import { useCallback, useState, type JSX } from 'react';

import { AutoExportSettings } from '../components/AutoExportSettings';
import { DatasetGuide } from '../components/DatasetGuide';
import { DatasetImport } from '../components/DatasetImport';
import { ExampleDataset } from '../components/ExampleDataset';
import { ModelAutoExport } from '../components/ModelAutoExport';
import { SubTabBar, type SubTab } from '../components/SubTabBar';
import { UninstallNotice } from '../components/UninstallNotice';
import { useT } from '../i18n';
import { readPersisted, writePersisted } from '../lib/persisted';
import { AdminTab } from './AdminTab';
import { LibraryTab } from './LibraryTab';

export type ModelsSubTab = 'official' | 'datasets' | 'mine';

const SUB_TABS: readonly ModelsSubTab[] = ['official', 'datasets', 'mine'];
const REMEMBERED = 'models.subtab';

function isSubTab(value: unknown): value is ModelsSubTab {
  return typeof value === 'string' && (SUB_TABS as readonly string[]).includes(value);
}

export function ModelsTab(): JSX.Element {
  const { t } = useT();
  // Remembered: App unmounts a tab on leaving it, and returning should land where you were.
  const [active, setActive] = useState<ModelsSubTab>(() => readPersisted(REMEMBERED, 'official', isSubTab));
  const choose = (next: ModelsSubTab): void => {
    setActive(next);
    writePersisted(REMEMBERED, next);
  };
  // Doc 136: an import re-reads the list underneath it.
  const [listVersion, setListVersion] = useState(0);
  const imported = useCallback(() => setListVersion((n) => n + 1), []);
  const tabs: readonly SubTab<ModelsSubTab>[] = [
    { id: 'official', label: t('models.sub.official') },
    { id: 'datasets', label: t('models.sub.datasets') },
    { id: 'mine', label: t('models.sub.mine') },
  ];

  return (
    <section className="models">
      <SubTabBar tabs={tabs} active={active} onChange={choose} label={t('models.sub.label')} idPrefix="models" />
      <div role="tabpanel" id={`models-panel-${active}`} aria-labelledby={`models-tab-${active}`} className="models__panel">
        {active === 'official' && <AdminTab />}
        {active === 'datasets' && (
          <>
            <h2 className="library__title">{t('models.datasets.title')}</h2>
            <p className="library__lead">{t('models.datasets.lead')}</p>
            <UninstallNotice key={`notice-${listVersion}`} onExported={imported} />
            <DatasetImport onImported={imported} />
            <ExampleDataset onImported={imported} />
            <DatasetGuide />
            <AutoExportSettings onExported={imported} />
            <LibraryTab key={listVersion} kinds={['dataset']} headed={false} />
          </>
        )}
        {active === 'mine' && (
          <>
            <h2 className="library__title">{t('models.mine.title')}</h2>
            <p className="library__lead">{t('models.mine.lead')}</p>
            <UninstallNotice />
            <ModelAutoExport />
            <LibraryTab kinds={['head', 'finetune']} headed={false} />
          </>
        )}
      </div>
    </section>
  );
}
