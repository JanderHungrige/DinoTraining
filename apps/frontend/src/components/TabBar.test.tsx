import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TABS, type TabId } from '../tabs/tabs';
import { TabBar } from './TabBar';

function renderTabBar(activeTab: TabId = 'studio') {
  const onTabChange = vi.fn<(tab: TabId) => void>();
  render(<TabBar activeTab={activeTab} onTabChange={onTabChange} />);
  return { onTabChange };
}

describe('TabBar', () => {
  it('renders every tab as a real button inside a tablist', () => {
    renderTabBar();

    expect(screen.getByRole('tablist', { name: /sections/i })).toBeInTheDocument();
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(TABS.length);
    for (const tab of tabs) {
      expect(tab.tagName).toBe('BUTTON');
    }
  });

  it('marks only the active tab as selected', () => {
    renderTabBar('admin');

    expect(screen.getByRole('tab', { name: 'Admin / Models' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getByRole('tab', { name: 'Annotation Studio' })).toHaveAttribute(
      'aria-selected',
      'false',
    );
  });

  it('keeps only the active tab in the tab order (roving tabindex)', () => {
    renderTabBar('studio');

    expect(screen.getByRole('tab', { name: 'Annotation Studio' })).toHaveAttribute(
      'tabindex',
      '0',
    );
    expect(screen.getByRole('tab', { name: 'Head Trainer' })).toHaveAttribute('tabindex', '-1');
  });

  it('points each tab at the panel it controls', () => {
    renderTabBar('studio');

    expect(screen.getByRole('tab', { name: 'Annotation Studio' })).toHaveAttribute(
      'aria-controls',
      'panel-studio',
    );
  });

  it('reports the clicked tab', async () => {
    const user = userEvent.setup();
    const { onTabChange } = renderTabBar('studio');

    await user.click(screen.getByRole('tab', { name: 'Head Trainer' }));

    expect(onTabChange).toHaveBeenCalledExactlyOnceWith('trainer');
  });

  it('moves to the next tab on ArrowRight', async () => {
    const user = userEvent.setup();
    const { onTabChange } = renderTabBar('studio');

    screen.getByRole('tab', { name: 'Annotation Studio' }).focus();
    await user.keyboard('{ArrowRight}');

    expect(onTabChange).toHaveBeenCalledExactlyOnceWith('trainer');
  });

  it('wraps from the first tab to the last on ArrowLeft', async () => {
    const user = userEvent.setup();
    const { onTabChange } = renderTabBar('studio');

    screen.getByRole('tab', { name: 'Annotation Studio' }).focus();
    await user.keyboard('{ArrowLeft}');

    expect(onTabChange).toHaveBeenCalledExactlyOnceWith('admin');
  });

  it('jumps to the first and last tab with Home and End', async () => {
    const user = userEvent.setup();
    const { onTabChange } = renderTabBar('inference');

    screen.getByRole('tab', { name: 'Inference Viewer' }).focus();
    await user.keyboard('{End}');
    expect(onTabChange).toHaveBeenLastCalledWith('admin');

    await user.keyboard('{Home}');
    expect(onTabChange).toHaveBeenLastCalledWith('studio');
  });

  it('ignores unrelated keys', async () => {
    const user = userEvent.setup();
    const { onTabChange } = renderTabBar('studio');

    screen.getByRole('tab', { name: 'Annotation Studio' }).focus();
    await user.keyboard('{ArrowDown}x');

    expect(onTabChange).not.toHaveBeenCalled();
  });
});
