import { useCallback, useRef, useState, type JSX } from 'react';

import { AddToApplications } from './components/AddToApplications';
import { UpdateNotice } from './components/UpdateNotice';
import { BackendStatus } from './components/BackendStatus';
import { LanguageSwitch } from './components/LanguageSwitch';
import { LanguageProvider } from './i18n';
import { BackgroundVideo } from './components/BackgroundVideo';
import { LookProvider } from './lib/look';
import { TabBar } from './components/TabBar';
import { ApiTab } from './tabs/ApiTab';
import { AnnotationStudioTab } from './tabs/AnnotationStudioTab';
import { DatasetGeneratorTab } from './tabs/DatasetGeneratorTab';
import { HeadTrainerTab } from './tabs/HeadTrainerTab';
import { InferenceViewerTab } from './tabs/InferenceViewerTab';
import { InspectTab } from './tabs/InspectTab';
import { IntroTab } from './tabs/IntroTab';
import { ModelsTab } from './tabs/ModelsTab';
import { PrepareTab } from './tabs/PrepareTab';
import { SettingsTab } from './tabs/SettingsTab';
import { SetupGate } from './setup/SetupGate';
import { useAutoExport } from './hooks/useAutoExport';
import { DEFAULT_TAB, type TabId } from './tabs/tabs';
import type { InspectRequest, TrainRequest } from './types/navigation';

interface Navigation {
  readonly onNavigate: (next: TabId) => void;
  /** Doc 74: open Inspect at a dataset (and, when known, one of its sequences). */
  readonly onInspect: (datasetId: string, sequence: string | null) => void;
  readonly inspectRequest: InspectRequest | null;
  /** Doc 90: open Training at a dataset with a recipe chosen. */
  readonly onTrain: (datasetId: string, recipeId: string) => void;
  readonly trainRequest: TrainRequest | null;
}

function renderTab(tab: TabId, nav: Navigation): JSX.Element {
  switch (tab) {
    case 'intro':
      return <IntroTab onNavigate={nav.onNavigate} />;
    case 'studio':
      // Rendered by App itself, kept mounted: see `studioVisited`.
      return <></>;
    case 'trainer':
      return <HeadTrainerTab request={nav.trainRequest} onOpenPrepare={() => nav.onNavigate('prepare')} />;
    case 'prepare':
      return <PrepareTab onTrain={nav.onTrain} />;
    case 'inference':
      return <InferenceViewerTab />;
    case 'generator':
      return <DatasetGeneratorTab onInspect={nav.onInspect} />;
    case 'inspect':
      return <InspectTab request={nav.inspectRequest} />;
    case 'api':
      return <ApiTab />;
    case 'models':
      return <ModelsTab />;
    case 'settings':
      return <SettingsTab />;
    default:
      throw new Error(`Unhandled tab: ${tab satisfies never}`);
  }
}

export function App(): JSX.Element {
  // Doc 144: exports every n minutes while the app is open, when that is switched on.
  useAutoExport();
  const [activeTab, setActiveTab] = useState<TabId>(DEFAULT_TAB);
  const [inspectRequest, setInspectRequest] = useState<InspectRequest | null>(null);
  const [trainRequest, setTrainRequest] = useState<TrainRequest | null>(null);
  // The Studio stays mounted once opened, so a session (picture, unsaved edits, prescan)
  // survives a visit to another tab; its Back button is what ends it.
  const [studioVisited, setStudioVisited] = useState(false);
  if (activeTab === 'studio' && !studioVisited) setStudioVisited(true);
  const nonce = useRef(0);
  const onInspect = useCallback((datasetId: string, sequence: string | null) => {
    nonce.current += 1;
    setInspectRequest({ datasetId, sequence, nonce: nonce.current });
    setActiveTab('inspect');
  }, []);
  const onTrain = useCallback((datasetId: string, recipeId: string) => {
    nonce.current += 1;
    setTrainRequest({ datasetId, recipeId, nonce: nonce.current });
    setActiveTab('trainer');
  }, []);

  return (
    <LanguageProvider>
    <LookProvider>
      <BackgroundVideo />
      <SetupGate>
      <div className="app">
        <header className="app__header">
          <h1 className="app__title">
            {/* Doc 134: the emblem; decorative, the name beside it is the heading. */}
            <img className="app__emblem" src="/emblem.png" alt="" width={28} height={28} />
            V-Rex
          </h1>
          <LanguageSwitch />
          <BackendStatus />
        </header>
        <AddToApplications />
        <UpdateNotice />

        <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

        <main
          className="app__panel"
          id={`panel-${activeTab}`}
          role="tabpanel"
          aria-labelledby={`tab-${activeTab}`}
          tabIndex={0}
        >
          {studioVisited && (
            <div hidden={activeTab !== 'studio'}>
              <AnnotationStudioTab active={activeTab === 'studio'} />
            </div>
          )}
          {renderTab(activeTab, { onNavigate: setActiveTab, onInspect, inspectRequest, onTrain, trainRequest })}
        </main>
      </div>
      </SetupGate>
    </LookProvider>
    </LanguageProvider>
  );
}
