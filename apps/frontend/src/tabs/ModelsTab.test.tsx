import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderInGerman } from '../i18n/testing';

vi.mock('./AdminTab', () => ({ AdminTab: () => <p>the admin page</p> }));
vi.mock('./LibraryTab', () => ({
  LibraryTab: ({ kinds, headed }: { kinds?: readonly string[]; headed?: boolean }) => (
    <p>
      library: {(kinds ?? []).join('+')} {headed === false ? 'unheaded' : 'headed'}
    </p>
  ),
}));

import { ModelsTab } from './ModelsTab';

describe('Models & Datasets (doc 135)', () => {
  it('opens on Official Models, the former Admin page', () => {
    render(<ModelsTab />);
    expect(screen.getByRole('tab', { name: 'Official Models' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('the admin page')).toBeInTheDocument();
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'models-tab-official');
  });

  it('Datasets shows only the datasets, My Models only heads and fine-tunes', async () => {
    const user = userEvent.setup();
    render(<ModelsTab />);
    await user.click(screen.getByRole('tab', { name: 'Datasets' }));
    expect(screen.getByText('library: dataset unheaded')).toBeInTheDocument();
    expect(screen.queryByText('the admin page')).not.toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'My Models' }));
    expect(screen.getByText('library: head+finetune unheaded')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'My Models' })).toBeInTheDocument();
  });

  it('remembers the sub-tab when the tab is left and opened again', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<ModelsTab />);
    await user.click(screen.getByRole('tab', { name: 'Datasets' }));
    unmount();
    render(<ModelsTab />);
    expect(screen.getByRole('tab', { name: 'Datasets' })).toHaveAttribute('aria-selected', 'true');
  });

  it('speaks German', () => {
    renderInGerman(<ModelsTab />);
    expect(screen.getByRole('tab', { name: 'Offizielle Modelle' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Datensätze' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Meine Modelle' })).toBeInTheDocument();
  });
});
