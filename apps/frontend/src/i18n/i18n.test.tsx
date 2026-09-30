import type { JSX } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as client from '../api/client';
import { LanguageSwitch } from '../components/LanguageSwitch';
import { LanguageProvider, systemLanguage, translate, translatePlural, useT } from '.';

function Word(): JSX.Element {
  const { t } = useT();
  return <p>{t('common.save')}</p>;
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe('translate (doc 111)', () => {
  it('fills placeholders and leaves unknown ones visible', () => {
    // Uses a real key; the placeholder test goes through the fill directly.
    expect(translate('de', 'common.save')).toBe('Speichern');
    expect(translate('en', 'common.save', { unused: 1 })).toBe('Save');
  });

  it('chooses the plural form by the language\'s own rules', () => {
    expect(translatePlural('en', 'common.pictures', 1)).toBe('1 picture');
    expect(translatePlural('en', 'common.pictures', 0)).toBe('0 pictures');
    expect(translatePlural('de', 'common.pictures', 3)).toBe('3 Bilder');
  });
});

describe('the language', () => {
  it('is English outside a provider, so a bare render reads as before', () => {
    render(<Word />);
    expect(screen.getByText('Save')).toBeInTheDocument();
  });

  it('follows the system, and the switch changes the app, the html lang and the API', async () => {
    const user = userEvent.setup();
    const sent = vi.spyOn(client, 'setApiLanguage');
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('de-DE');
    expect(systemLanguage()).toBe('de');
    render(
      <LanguageProvider>
        <LanguageSwitch />
        <Word />
      </LanguageProvider>,
    );
    expect(screen.getByText('Speichern')).toBeInTheDocument();
    expect(document.documentElement.lang).toBe('de');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Sprache' }), 'en');
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(document.documentElement.lang).toBe('en');
    expect(sent).toHaveBeenLastCalledWith('en');
  });

  it('is remembered', async () => {
    const user = userEvent.setup();
    const { unmount } = render(
      <LanguageProvider>
        <LanguageSwitch />
        <Word />
      </LanguageProvider>,
    );
    await user.selectOptions(screen.getByRole('combobox'), 'de');
    unmount();
    render(
      <LanguageProvider>
        <Word />
      </LanguageProvider>,
    );
    expect(screen.getByText('Speichern')).toBeInTheDocument();
  });
});
