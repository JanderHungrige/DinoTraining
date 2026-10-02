import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Prediction } from '../api/inference';
import { renderInGerman } from '../i18n/testing';
import { ScoreNote } from './ScoreThreshold';

const weak: Prediction = {
  instance_id: 'h', head_name: 'weak', head_type_id: 'dense-detector', task: 'detection', render_hint: 'boxes',
  class_names: ['person'], payload: { boxes: [[0, 0, 1, 1]], scores: [0.208], classes: [0] }, grid: [32, 32], elapsed_ms: 1,
};

describe('ScoreNote (2026-10-02)', () => {
  it('says there is a weaker guess below the threshold', () => {
    render(<ScoreNote prediction={weak} minScore={0.3} />);
    expect(screen.getByRole('status')).toHaveTextContent('No box at 0.30 or above. Best guess here: 0.21. Lower the threshold to see it.');
  });

  it('says nothing when there is something to see, and speaks German', () => {
    const { container } = render(<ScoreNote prediction={weak} minScore={0.2} />);
    expect(container).toBeEmptyDOMElement();
    renderInGerman(<ScoreNote prediction={{ ...weak, payload: { boxes: [], scores: [], classes: [] } }} minScore={0.3} />);
    expect(screen.getByRole('status')).toHaveTextContent('Dieses Modell hat in diesem Bild nichts gefunden.');
  });
});
