import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { DatasetAudit, PrepTarget } from '../api/prep';
import { FixStep } from '../components/prepare/FixStep';
import { PrepareSteps } from '../components/prepare/PrepareSteps';
import type { PrepareData } from '../hooks/usePrepareData';
import { renderInGerman } from './testing';

vi.mock('../api/prepPlan', async () => {
  const actual = await vi.importActual<typeof import('../api/prepPlan')>('../api/prepPlan');
  return { ...actual, saveRecipe: vi.fn(), previewInput: vi.fn(), previewAugmentation: vi.fn() };
});

const SAM3: PrepTarget = {
  id: 'sam3',
  label: 'Fine-tune SAM 3',
  task: 'segmentation',
  annotation_kind: 'masks',
  input_size: 1008,
  min_visible_px: 28,
} as PrepTarget;

const AUDIT = {
  summary: { images: 3, annotations: 3, classes: { bishop: 2 }, problems: 1, warnings: 0 },
  copy_groups: [['/a.jpg', '/b.jpg'], ['/c.jpg', '/d.jpg']],
  unreadable: [],
  findings: [],
} as unknown as DatasetAudit;

function data(): PrepareData {
  return {
    audit: null,
    auditing: null,
    state: { excluded: [], class_map: {} },
    split: null,
    recipes: [],
    busy: false,
    error: '',
    runAudit: vi.fn(),
    fix: vi.fn(async () => 0),
    split_: vi.fn(async () => undefined),
    reloadRecipes: vi.fn(),
  };
}

describe('Prepare data in German', () => {
  it('names the steps and opens the audit in German', () => {
    renderInGerman(
      <PrepareSteps
        datasetId="d"
        datasetName="Ringe"
        target={SAM3}
        data={data()}
        plans={{ balance: null, augmentation: null }}
        choices={{ key: 'd:sam3' }}
        onChoose={vi.fn()}
      />,
    );
    expect(screen.getByRole('list', { name: 'Vorbereitungsschritte' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Ungleiche Klassen \(nicht genutzt\)/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Prüfung starten' })).toBeEnabled();
  });

  it('offers the safe fixes in German, with German plurals', () => {
    renderInGerman(<FixStep audit={AUDIT} state={{ excluded: ['/x.jpg'], class_map: {} }} busy={false} onFix={vi.fn(async () => 0)} />);
    expect(screen.getByRole('button', { name: 'Von jeder Kopie eine behalten (2 Gruppen)' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Das ausgelassene Bild zurückholen (1)' })).toBeEnabled();
    expect(screen.getByRole('textbox', { name: 'bishop trainieren als' })).toHaveValue('bishop');
  });
});
