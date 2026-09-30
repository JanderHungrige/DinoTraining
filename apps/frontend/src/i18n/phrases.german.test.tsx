import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { PhraseInfo } from '../api/phrases';
import { GuidelinePanel } from '../components/GuidelinePanel';
import { PhraseBar } from '../components/phrases/PhraseBar';
import { renderInGerman } from './testing';

vi.mock('../api/phrases', async () => {
  const actual = await vi.importActual<typeof import('../api/phrases')>('../api/phrases');
  return { ...actual, addPhrase: vi.fn(), changePhrase: vi.fn(), markTheRest: vi.fn() };
});
vi.mock('../api/quality', () => ({ getGuideline: vi.fn(async () => ''), saveGuideline: vi.fn() }));

const CAR: PhraseInfo = { id: 1, text: 'car', class_name: 'car', variants: [], confusable: [], instances: 3, complete: 0, absent: 0, classes: ['car'], umbrella: false };

afterEach(() => localStorage.clear());

describe('phrases in German (doc 112)', () => {
  it('the phrase bar reads German, the phrases stay as written', () => {
    const pictures = { phrases: [CAR], statuses: [], error: '', reload: vi.fn(), mark: vi.fn(async () => undefined) };
    renderInGerman(<PhraseBar datasetId="d1" pictures={pictures} open disabled={false} />);
    expect(screen.getByText('Phrasen')).toBeInTheDocument();
    expect(screen.getByText('Nur für importierte oder teilweise annotierte Datensätze')).toBeInTheDocument();
    expect(screen.getByText('So funktionieren Phrasen')).toBeInTheDocument();
    expect(screen.getByText('Oberbegriffe')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /car 3/ })).toBeInTheDocument();
  });

  it('the guideline reads German', async () => {
    renderInGerman(<GuidelinePanel datasetId="d1" />);
    expect(await screen.findByRole('button', { name: 'Richtlinie speichern' })).toBeInTheDocument();
    expect(screen.getByText(/Annotationsrichtlinie/)).toBeInTheDocument();
  });
});
