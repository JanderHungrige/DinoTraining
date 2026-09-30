import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { PhraseInfo } from '../../api/phrases';
import { PictureChecks } from './PictureChecks';

const P = (text: string): PhraseInfo => ({ id: 1, text, class_name: text, variants: [], confusable: [], instances: 0, complete: 0, absent: 0 });

describe('PictureChecks (doc 105)', () => {
  it('shows each phrase\'s state and marks, or clears, one', async () => {
    const user = userEvent.setup();
    const onMark = vi.fn();
    render(
      <PictureChecks
        phrases={[P('ring'), P('blob')]}
        statuses={[{ phrase_id: 1, text: 'ring', status: 'complete' }]}
        active="blob"
        disabled={false}
        onMark={onMark}
      />,
    );
    const ring = screen.getByRole('row', { name: /ring/ });
    expect(ring).toHaveTextContent('all marked');
    expect(within(ring).getByRole('button', { name: 'All marked' })).toBeDisabled();
    await user.click(within(ring).getByRole('button', { name: 'Clear the check for ring' }));
    expect(onMark).toHaveBeenCalledWith('ring', null);
    const blob = screen.getByRole('row', { name: /blob/ });
    expect(blob).toHaveTextContent('not checked');
    await user.click(within(blob).getByRole('button', { name: 'Not in this picture' }));
    expect(onMark).toHaveBeenCalledWith('blob', 'absent');
  });
});
