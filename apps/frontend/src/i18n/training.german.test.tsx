/** The Training tab reads German inside a German provider (doc 112). */

import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as foundation from '../api/foundation';
import * as heads from '../api/headInstances';
import type { JobInfo } from '../api/training';
import { TrainingProgress } from '../components/TrainingProgress';
import * as trainerOptions from '../hooks/useTrainerOptions';
import { HeadTrainerTab } from '../tabs/HeadTrainerTab';
import { renderInGerman } from './testing';

vi.mock('../api/foundation');
vi.mock('../api/headInstances');

beforeEach(() => {
  localStorage.clear();
  vi.mocked(heads.listHeadInstances).mockResolvedValue([]);
  vi.mocked(foundation.listFoundations).mockResolvedValue([]);
  vi.spyOn(trainerOptions, 'useTrainerOptions').mockReturnValue({
    datasets: [],
    backbones: [],
    headTypes: [],
    loading: false,
    error: null,
  } as unknown as ReturnType<typeof trainerOptions.useTrainerOptions>);
});

describe('the Training tab in German', () => {
  it('names both modes and the head form in German', async () => {
    renderInGerman(<HeadTrainerTab />);
    await waitFor(() => expect(heads.listHeadInstances).toHaveBeenCalled());

    expect(screen.getByRole('group', { name: 'Was trainieren?' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Ein Modell fine-tunen/ })).toBeInTheDocument();
    expect(screen.getByText('Trainierte Heads')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Training starten' })).toBeDisabled();
  });

  it('shows a run’s progress in German, with plurals', () => {
    const job = {
      job_id: 'j', state: 'running', epoch: 2, total_epochs: 10, head_type_id: 'h', backbone_id: 'b',
      dataset_ids: [], class_names: [], skipped_mixed_class_images: 3, best_metric: null,
      best_epoch: null, primary_metric: null, message: '', head_instance_id: null, history: [],
    } as JobInfo;
    renderInGerman(<TrainingProgress job={job} history={[]} onCancel={() => undefined} />);

    expect(screen.getByText('· Durchgang 2/10')).toBeInTheDocument();
    expect(screen.getByText(/^3 Bilder übersprungen/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Abbrechen' })).toBeInTheDocument();
  });
});
