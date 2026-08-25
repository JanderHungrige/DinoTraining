import { useState, type JSX } from 'react';

import { BackendStatus } from './components/BackendStatus';
import { TabBar } from './components/TabBar';
import { AdminTab } from './tabs/AdminTab';
import { ApiTab } from './tabs/ApiTab';
import { AnnotationStudioTab } from './tabs/AnnotationStudioTab';
import { DatasetGeneratorTab } from './tabs/DatasetGeneratorTab';
import { HeadTrainerTab } from './tabs/HeadTrainerTab';
import { InferenceViewerTab } from './tabs/InferenceViewerTab';
import { IntroTab } from './tabs/IntroTab';
import { LibraryTab } from './tabs/LibraryTab';
import { DEFAULT_TAB, type TabId } from './tabs/tabs';

function renderTab(tab: TabId, onNavigate: (next: TabId) => void): JSX.Element {
  switch (tab) {
    case 'intro':
      return <IntroTab onNavigate={onNavigate} />;
    case 'studio':
      return <AnnotationStudioTab />;
    case 'trainer':
      return <HeadTrainerTab />;
    case 'inference':
      return <InferenceViewerTab />;
    case 'generator':
      return <DatasetGeneratorTab />;
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
        {renderTab(activeTab, setActiveTab)}
      </main>
    </div>
  );
}
