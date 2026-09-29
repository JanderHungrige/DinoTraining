import { useCallback, useRef, useState, type JSX } from 'react';

import { BackendStatus } from './components/BackendStatus';
import { TabBar } from './components/TabBar';
import { AdminTab } from './tabs/AdminTab';
import { ApiTab } from './tabs/ApiTab';
import { AnnotationStudioTab } from './tabs/AnnotationStudioTab';
import { DatasetGeneratorTab } from './tabs/DatasetGeneratorTab';
import { HeadTrainerTab } from './tabs/HeadTrainerTab';
import { InferenceViewerTab } from './tabs/InferenceViewerTab';
import { InspectTab } from './tabs/InspectTab';
import { IntroTab } from './tabs/IntroTab';
import { LibraryTab } from './tabs/LibraryTab';
import { DEFAULT_TAB, type TabId } from './tabs/tabs';
import type { InspectRequest } from './types/navigation';

interface Navigation {
  readonly onNavigate: (next: TabId) => void;
  /** Doc 74: open Inspect at a dataset (and, when known, one of its sequences). */
  readonly onInspect: (datasetId: string, sequence: string | null) => void;
  readonly inspectRequest: InspectRequest | null;
}

function renderTab(tab: TabId, nav: Navigation): JSX.Element {
  switch (tab) {
    case 'intro':
      return <IntroTab onNavigate={nav.onNavigate} />;
    case 'studio':
      return <AnnotationStudioTab />;
    case 'trainer':
      return <HeadTrainerTab />;
    case 'inference':
      return <InferenceViewerTab />;
    case 'generator':
      return <DatasetGeneratorTab onInspect={nav.onInspect} />;
    case 'inspect':
      return <InspectTab request={nav.inspectRequest} />;
    case 'library':
      return <LibraryTab />;
    case 'api':
      return <ApiTab />;
    case 'admin':
      return <AdminTab />;
    default:
      throw new Error(`Unhandled tab: ${tab satisfies never}`);
  }
}

export function App(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>(DEFAULT_TAB);
  const [inspectRequest, setInspectRequest] = useState<InspectRequest | null>(null);
  const nonce = useRef(0);
  const onInspect = useCallback((datasetId: string, sequence: string | null) => {
    nonce.current += 1;
    setInspectRequest({ datasetId, sequence, nonce: nonce.current });
    setActiveTab('inspect');
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">DinoTraining</h1>
        <BackendStatus />
      </header>

      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

      <main
        className="app__panel"
        id={`panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        tabIndex={0}
      >
        {renderTab(activeTab, { onNavigate: setActiveTab, onInspect, inspectRequest })}
      </main>
    </div>
  );
}
