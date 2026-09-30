/** The intro and the dataset-format guide read German inside a German provider (doc 112). */

import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DatasetFormatPanel } from '../components/DatasetFormatPanel';
import { IntroTab } from '../tabs/IntroTab';
import { datasetFormat } from '../tabs/datasetFormat';
import { modelGuide } from '../tabs/introContent';
import { renderInGerman } from './testing';
import { ENGLISH, translator } from './translate';

afterEach(() => localStorage.clear());

describe('the intro in German', () => {
  it('explains the loop in German and names each tab as the German tab bar does', () => {
    renderInGerman(<IntroTab onNavigate={vi.fn()} />);
    expect(screen.getByRole('heading', { level: 2, name: 'Worum es hier geht' })).toBeInTheDocument();
    expect(screen.getByText('Ein eingefrorenes Backbone')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Modell-Ansicht öffnen' })).toBeInTheDocument();
    expect(screen.getAllByText('Warum an dieser Stelle:')).toHaveLength(9);
  });

  it('opens the dataset-format guide in German, with the file name filled in', async () => {
    renderInGerman(<DatasetFormatPanel />);
    await userEvent.setup().click(screen.getByRole('button', { name: /Wie muss ein Datensatz aussehen\?/ }));
    expect(screen.getByText('Die Form auf der Festplatte')).toBeInTheDocument();
    expect(screen.getByText(/nach einer Datei namens _annotations\.coco\.json/)).toBeInTheDocument();
  });
});

describe('keys built from a pattern', () => {
  // The model guide and the format sections build their keys from stems, which the
  // compiler cannot check; an unknown key would come back as undefined.
  it('resolves every model-guide and format text in both languages', () => {
    for (const t of [ENGLISH, translator('de')]) {
      const texts = [
        ...modelGuide(t).flatMap((e) => [e.name, e.bestFor, ...e.strengths, ...e.weaknesses, e.measured ?? 'x']),
        ...datasetFormat(t).flatMap((s) => [s.heading, ...s.body]),
      ];
      expect(texts.every((text) => typeof text === 'string' && text.length > 0)).toBe(true);
    }
    expect(modelGuide(translator('de')).filter((entry) => entry.measured)).toHaveLength(2);
  });
});
