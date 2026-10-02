import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useContext, type JSX } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as api from '../api/annotationTargets';
import { LanguageProvider } from '../i18n';
import { LanguageContext } from '../i18n/LanguageProvider';
import { useAnnotationTargetList } from './useAnnotationTargetList';

vi.mock('../api/annotationTargets', async () => {
  const actual = await vi.importActual<typeof import('../api/annotationTargets')>('../api/annotationTargets');
  return { ...actual, listAnnotationTargets: vi.fn() };
});

function Probe(): JSX.Element {
  const targets = useAnnotationTargetList();
  const { setLang } = useContext(LanguageContext);
  return (
    <>
      <p>{targets.map((target) => target.label).join(', ')}</p>
      <button type="button" onClick={() => setLang('en')}>English</button>
    </>
  );
}

beforeEach(() => {
  localStorage.setItem('dinotraining.v1.language', JSON.stringify('de'));
  vi.mocked(api.listAnnotationTargets)
    .mockReset()
    .mockResolvedValueOnce([{ id: 'everything', label: 'Alle Möglichkeiten offenhalten' }] as never)
    .mockResolvedValueOnce([{ id: 'everything', label: 'Keep every option open' }] as never);
});

describe('the annotation targets follow the language (2026-10-02)', () => {
  it('are read again in the new language when the language changes', async () => {
    render(<LanguageProvider><Probe /></LanguageProvider>);
    expect(await screen.findByText('Alle Möglichkeiten offenhalten')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'English' }));
    expect(await screen.findByText('Keep every option open')).toBeInTheDocument();
    await waitFor(() => expect(api.listAnnotationTargets).toHaveBeenCalledTimes(2));
  });
});
