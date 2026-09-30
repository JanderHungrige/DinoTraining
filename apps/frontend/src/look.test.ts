/**
 * Lato is bundled with the app, never fetched from Google (doc 78).
 *
 * Read from source rather than rendered: jsdom applies no stylesheets and loads no fonts.
 * (Vitest also hands CSS imports back empty, so the stylesheet's own rules are checked in
 * the running app instead — see doc 78's verification.)
 */

import { describe, expect, it } from 'vitest';

import html from '../index.html?raw';
import main from './main.tsx?raw';

describe('Lato (doc 78)', () => {
  it('is bundled with the app: regular, italic and bold', () => {
    expect(main).toContain('@fontsource/lato/latin-400.css');
    expect(main).toContain('@fontsource/lato/latin-400-italic.css');
    expect(main).toContain('@fontsource/lato/latin-700.css');
  });

  it('is never fetched from Google at runtime', () => {
    for (const source of [main, html]) {
      expect(source).not.toMatch(/fonts\.(googleapis|gstatic)\.com/);
    }
  });
});
