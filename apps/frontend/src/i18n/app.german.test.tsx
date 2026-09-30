/** The app shell reads German inside a German provider (doc 112). */

import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { StubPanel } from '../components/StubPanel';
import { TabBar } from '../components/TabBar';
import { labelTitle } from '../types/annotation';
import { describeOutput } from '../types/annotationView';
import { renderInGerman } from './testing';
import { translator } from './translate';

afterEach(() => localStorage.clear());

describe('the app shell in German', () => {
  it('names the tabs and their list in German', () => {
    renderInGerman(<TabBar activeTab="studio" onTabChange={vi.fn()} />);
    expect(screen.getByRole('tablist', { name: 'DinoTraining-Bereiche' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Daten vorbereiten' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Verwaltung / Modelle' })).toBeInTheDocument();
  });

  it('says in German which wave fills a stub', () => {
    renderInGerman(<StubPanel tabId="library" />);
    expect(screen.getByRole('heading', { name: 'Bibliothek' })).toBeInTheDocument();
    expect(screen.getByText('Kommt mit Welle 7.')).toBeInTheDocument();
  });

  it('words verdicts and model output in German through the translator', () => {
    const { t } = translator('de');
    expect(labelTitle(t, 'positive')).toBe('Richtig');
    expect(describeOutput('boxes', t)).toBe('Speichert Boxen.');
  });
});
