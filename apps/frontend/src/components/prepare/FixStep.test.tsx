import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { DatasetAudit, PrepState } from '../../api/prep';
import { FixStep } from './FixStep';

const AUDIT = {
  summary: { images: 3, annotations: 3, classes: { 'white-bishop': 20, bishop: 1, blur: 2 }, problems: 1, warnings: 0 },
  copy_groups: [['/a.jpg', '/b.jpg']],
  unreadable: [],
  findings: [],
} as unknown as DatasetAudit;

const SAVED: PrepState = { excluded: ['/x.jpg'], class_map: { old: 'white-bishop' } };

describe('FixStep', () => {
  it('builds the class map from the rows the user changed, on top of the saved one', async () => {
    const user = userEvent.setup();
    const onFix = vi.fn(async () => 0);
    // The prep state loads after the first render, as it does in the app.
    const { rerender } = render(<FixStep audit={AUDIT} state={null} busy={false} onFix={onFix} />);
    rerender(<FixStep audit={AUDIT} state={SAVED} busy={false} onFix={onFix} />);

    expect(screen.getByRole('textbox', { name: 'Train old as' })).toHaveValue('white-bishop');
    const bishop = screen.getByRole('textbox', { name: 'Train bishop as' });
    await user.clear(bishop);
    await user.type(bishop, 'white-bishop');
    await user.click(screen.getByRole('checkbox', { name: 'Leave out blur' }));
    await user.click(screen.getByRole('button', { name: 'Save the class changes' }));

    expect(onFix).toHaveBeenCalledWith('set-class-map', {
      class_map: { bishop: 'white-bishop', blur: null, old: 'white-bishop' },
    });
  });

  it('offers the safe fixes with their counts, and putting everything back', async () => {
    const user = userEvent.setup();
    const onFix = vi.fn(async () => 1);
    render(<FixStep audit={AUDIT} state={SAVED} busy={false} onFix={onFix} />);
    expect(screen.getByRole('button', { name: /Leave out unreadable pictures \(0\)/ })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: /Keep one of each copy \(1 group\)/ }));
    expect(onFix).toHaveBeenCalledWith('exclude-copies', {});
    await user.click(screen.getByRole('button', { name: /Put all 1 left-out/ }));
    expect(onFix).toHaveBeenLastCalledWith('include', { paths: ['/x.jpg'] });
    expect(await screen.findByText(/Run the audit again/)).toBeInTheDocument();
  });
});
