import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { GeneratorActionBar } from '../components/GeneratorActionBar';
import { UnclearQuestion } from '../components/UnclearQuestion';
import { InspectTab } from '../tabs/InspectTab';
import { renderInGerman } from './testing';

vi.mock('../api/datasets', async () => {
  const actual = await vi.importActual<typeof import('../api/datasets')>('../api/datasets');
  return {
    ...actual,
    listDatasets: vi.fn(async () => [{ id: 'd1', name: 'Bolzen', counts: { images: 1, masks: 0 } }]),
    listDatasetImages: vi.fn(async () => []),
  };
});
vi.mock('../api/datasetSequences', async () => {
  const actual =
    await vi.importActual<typeof import('../api/datasetSequences')>('../api/datasetSequences');
  return {
    ...actual,
    listDatasetSequences: vi.fn(async () => ({
      dataset_id: 'd1',
      class_names: [],
      sequences: [],
      loose: [{ index: 0, path: '/d1/a.jpg', annotated: false, classes: [] }],
    })),
  };
});

describe('the Generator and Inspect in German', () => {
  it('names the toolbar and its automation boxes in German', () => {
    renderInGerman(
      <GeneratorActionBar
        proposeLabel="Boxen vorschlagen"
        proposing={false}
        saving={false}
        dirty
        canGoPrevious
        canGoNext
        autoPropose
        autoSave
        onAutoProposeChange={vi.fn()}
        onAutoSaveChange={vi.fn()}
        onPropose={vi.fn()}
        onSave={vi.fn()}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: 'Im Datensatz speichern' })).toBeInTheDocument();
    expect(screen.getByText('Automatisch vorschlagen')).toBeInTheDocument();
    expect(screen.getByText('Automatisch speichern')).toBeInTheDocument();
  });

  it('asks about unclear proposals in German, with the word in italics', () => {
    renderInGerman(
      <UnclearQuestion
        imageNumber={2}
        imageTotal={9}
        count={3}
        band={{ low: 0.3, high: 0.5 }}
        onContinue={vi.fn()}
        onStop={vi.fn()}
      />,
    );
    const alert = screen.getByRole('alert', { name: 'Die Analyse wartet auf dich' });
    expect(alert).toHaveTextContent('Angehalten bei Bild 2 von 9.');
    expect(alert).toHaveTextContent('3 Vorschläge haben einen Score zwischen 0.30 und 0.50');
    expect(alert.querySelector('em')).toHaveTextContent('unklar');
  });

  it('shows the Inspect tab in German, singular for one picture', async () => {
    renderInGerman(<InspectTab request={null} />);
    expect(screen.getByRole('heading', { name: 'Datensätze ansehen' })).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: 'Bolzen (1 Bild)' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '▶ Abspielen' })).toBeInTheDocument();
  });
});
