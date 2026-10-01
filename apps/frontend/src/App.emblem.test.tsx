/** Doc 134: the emblem sits before the name, decorative, and the page names it as icon. */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import html from '../index.html?raw';
import svg from '../public/emblem.svg?raw';
import { App } from './App';

describe('the emblem (doc 134)', () => {
  it('stands before the name, and the heading is still just the name', () => {
    render(<App />);
    const heading = screen.getByRole('heading', { level: 1, name: 'DinoTraining' });
    const emblem = heading.querySelector('img');
    expect(emblem).toHaveAttribute('src', '/emblem.svg');
    expect(emblem).toHaveAttribute('alt', '');
  });

  it('is the favicon and ships with the app', () => {
    expect(html).toContain('<link rel="icon" type="image/svg+xml" href="/emblem.svg" />');
    expect(svg).toContain('viewBox="0 0 512 512"');
    expect(svg).not.toMatch(/<text/);
  });
});
