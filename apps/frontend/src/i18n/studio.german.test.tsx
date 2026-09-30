/** The Annotation Studio reads German inside a German provider (doc 112). */

import { screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { BoxReviewList } from '../components/BoxReviewList';
import { SessionSetup } from '../components/SessionSetup';
import { fetchMock, head, routes } from '../components/sessionSetup.testkit';
import { checkLine } from '../lib/pictureChecklist';
import { renderInGerman } from './testing';
import { translator } from './translate';

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
});

describe('the Studio in German', () => {
  it('sets a session up in German', async () => {
    routes([head()]);
    renderInGerman(<SessionSetup onStart={vi.fn()} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.getByRole('group', { name: 'Was die Boxen vorschlägt' })).toBeInTheDocument();
    expect(screen.getByText('Bilder aus')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Annotieren starten' })).toBeInTheDocument();
  });

  it('reviews boxes in German, with the plural chosen by count', () => {
    renderInGerman(
      <BoxReviewList
        boxes={[]}
        hidden={new Set()}
        selectedId={null}
        threshold={0}
        onSelect={vi.fn()}
        onLabel={vi.fn()}
        onRename={vi.fn()}
        onRemove={vi.fn()}
        onThreshold={vi.fn()}
        onRemoveHidden={vi.fn()}
        classes={[]}
        onCreateClass={vi.fn()}
      />,
    );
    expect(screen.getByRole('complementary', { name: 'Boxen' })).toHaveTextContent('0 Boxen');
    expect(screen.getByRole('status')).toHaveTextContent(/^Noch keine Boxen\./);
  });

  it('writes the picture checklist in German', () => {
    expect(checkLine('boxes', [], 0, [], translator('de')).text).toBe('Noch nichts markiert');
  });
});
