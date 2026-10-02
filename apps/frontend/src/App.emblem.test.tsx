/** Docs 134/160: the logo sits before the name, decorative, and the page names it as icon. */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import html from '../index.html?raw';
import logo from '../public/emblem.png?url';
import { App } from './App';

describe('the logo (docs 134, 160)', () => {
  it('stands before the name, and the heading is still just the name', () => {
    render(<App />);
    const heading = screen.getByRole('heading', { level: 1, name: 'V-Rex' });
    const emblem = heading.querySelector('img');
    expect(emblem).toHaveAttribute('src', '/emblem.png');
    expect(emblem).toHaveAttribute('alt', '');
  });

  it('is the favicon and ships with the app', () => {
    expect(html).toContain('<link rel="icon" type="image/png" href="/emblem.png" />');
    expect(logo).toMatch(/emblem\.png$/);
  });
});
