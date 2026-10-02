import { describe, expect, it } from 'vitest';

import mainSource from './main.tsx?raw';

const css: Record<string, string> = import.meta.glob('./*.css', { query: '?raw', import: 'default', eager: true });
const sheets = Object.keys(css).map((path) => path.slice(2));
const read = (name: string): string => (name === 'main.tsx' ? mainSource : (css[`./${name}`] ?? ''));

describe('the look (doc 157)', () => {
  it('has one scheme: no light-mode overrides wash the background loop out', () => {
    expect(sheets).toContain('sketch.css');
    for (const name of sheets) {
      expect(read(name), name).not.toMatch(/prefers-color-scheme:\s*light/);
    }
  });

  it('loads the sketch layer last, so it wins over the structure it draws', () => {
    const main = read('main.tsx');
    expect(main.indexOf("import './sketch.css'")).toBeGreaterThan(main.indexOf("import './look.css'"));
    expect(main.indexOf("import './look.css'")).toBeGreaterThan(main.indexOf("import './styles.css'"));
  });

  it('draws only classes that still exist elsewhere', () => {
    const others = sheets.filter((name) => name !== 'sketch.css').map(read).join('\n');
    const drawn = new Set(read('sketch.css').match(/\.[a-z][a-z0-9_-]*(?:--[a-z0-9-]+)?/g) ?? []);
    drawn.delete('.app');
    const stale = [...drawn].filter((selector) => !others.includes(`${selector} `) && !others.includes(`${selector}:`) && !others.includes(`${selector},`));
    expect(stale).toEqual([]);
  });
});
