import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { AnnotationTarget } from '../api/annotationTargets';
import { TargetGuide } from './TargetGuide';

const SAM3: AnnotationTarget = {
  id: 'sam3', label: 'Concept outlines (SAM 3)', summary: 's', profile: 'sam3',
  layers: [
    { layer: 'boxes', label: 'Boxes', level: 'optional', why: 'Derived from each outline.' },
    { layer: 'masks', label: 'Outlines (masks)', level: 'required', why: 'Every instance outlined.' },
    { layer: 'picture-status', label: 'Checked per picture', level: 'required', why: 'Unchecked teaches nothing.' },
  ],
};

describe('TargetGuide (doc 104)', () => {
  it('names the target, every layer with its level and why, and what this picture lacks', () => {
    render(<TargetGuide target={SAM3} boxes={[]} phraseCount={2} statuses={[]} />);
    expect(screen.getByText('Concept outlines (SAM 3)')).toBeInTheDocument();
    expect(screen.getByText(/1 required still open on this picture/)).toBeInTheDocument();
    const layers = screen.getByRole('list', { name: 'What this model needs' });
    expect(within(layers).getByText('Boxes').parentElement).toHaveTextContent('optional Boxes — Derived from each outline.');
    const checks = screen.getByRole('list', { name: 'This picture' });
    // Only required and recommended layers are checked; optional ones are just explained.
    expect(within(checks).getAllByRole('listitem')).toHaveLength(2);
    expect(checks).toHaveTextContent('Checked per picture: Complete for its 2 classes once saved');
  });
});
