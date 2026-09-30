import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { AnnotationTarget } from '../api/annotationTargets';
import { AnnotationTargetPicker } from './AnnotationTargetPicker';

const T = (id: string, label: string, summary: string): AnnotationTarget => ({ id, label, summary, profile: null, layers: [] });

describe('AnnotationTargetPicker (doc 104)', () => {
  it('asks what the dataset will train, with a line per choice', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <AnnotationTargetPicker
        targets={[T('open', 'Keep all options open', 'Any model later.'), T('sam3', 'Concept outlines (SAM 3)', 'Every instance.')]}
        value="open"
        onChange={onChange}
      />,
    );
    expect(screen.getByRole('group', { name: 'What will this dataset train?' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Keep all options open/ })).toBeChecked();
    await user.click(screen.getByRole('radio', { name: /Concept outlines/ }));
    expect(onChange).toHaveBeenCalledWith('sam3');
  });

  it('shows nothing until the list has loaded', () => {
    const { container } = render(<AnnotationTargetPicker targets={[]} value="open" onChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
