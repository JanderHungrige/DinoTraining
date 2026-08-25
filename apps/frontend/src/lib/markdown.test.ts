/**
 * The markdown parser (doc 63).
 *
 * Purpose-built for the guide this app generates, so the tests are about the constructs
 * that document actually contains — and about the one property that matters more than
 * coverage: **nothing is dropped**. A parser that silently discarded what it did not
 * recognise would lose part of a document whose entire job is to be complete, and the loss
 * would be invisible.
 */

import { describe, expect, it } from 'vitest';

import { parseInline, parseMarkdown } from './markdown';

describe('blocks', () => {
  it('reads headings and their level', () => {
    const [first, second] = parseMarkdown('# Title\n\n### Deep');

    expect(first).toEqual({ kind: 'heading', level: 1, text: 'Title' });
    expect(second).toEqual({ kind: 'heading', level: 3, text: 'Deep' });
  });

  it('keeps a fenced block literal', () => {
    // The guide is full of shell comments. A `#` inside a fence is a comment, not a
    // heading, and treating it as one would shred every code sample in the document.
    const blocks = parseMarkdown('```\nGET /models   # what exists\n```');

    expect(blocks).toEqual([{ kind: 'code', text: 'GET /models   # what exists' }]);
  });

  it('keeps blank lines inside a fence', () => {
    const blocks = parseMarkdown('```\na\n\nb\n```');

    expect(blocks[0]).toEqual({ kind: 'code', text: 'a\n\nb' });
  });

  it('groups consecutive bullets into one list', () => {
    const blocks = parseMarkdown('- one\n- two\n- three');

    expect(blocks).toEqual([
      { kind: 'list', ordered: false, items: ['one', 'two', 'three'] },
    ]);
  });

  it('tells an ordered list from a bulleted one', () => {
    const [ordered, bulleted] = parseMarkdown('1. first\n2. second\n\n- loose');

    expect(ordered).toMatchObject({ ordered: true, items: ['first', 'second'] });
    expect(bulleted).toMatchObject({ ordered: false, items: ['loose'] });
  });

  it('does not run two kinds of list together', () => {
    // A numbered list directly under a bulleted one is two lists. Merging them would
    // renumber the steps of a recipe, which is the one thing a recipe cannot survive.
    const blocks = parseMarkdown('- a\n1. b');

    expect(blocks).toHaveLength(2);
  });

  it('joins a hard-wrapped paragraph back into one line', () => {
    // The source wraps at 96 characters for the file; a browser should not inherit that.
    const blocks = parseMarkdown('one two\nthree four');

    expect(blocks).toEqual([{ kind: 'paragraph', text: 'one two three four' }]);
  });

  it('ends a paragraph at the next block rather than swallowing it', () => {
    const blocks = parseMarkdown('text\n## Heading');

    expect(blocks.map((b) => b.kind)).toEqual(['paragraph', 'heading']);
  });

  it('reads a blockquote, including a multi-line one', () => {
    const blocks = parseMarkdown('> asked for\n> in one sentence');

    expect(blocks).toEqual([{ kind: 'quote', text: 'asked for in one sentence' }]);
  });

  it('drops nothing it does not understand', () => {
    // The load-bearing property. Unknown syntax degrades to a paragraph carrying its own
    // text, so the worst case is ugly rather than absent.
    const blocks = parseMarkdown('| a | b |\n| - | - |');

    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toMatchObject({ kind: 'paragraph' });
    expect(JSON.stringify(blocks)).toContain('a');
  });

  it('is empty for an empty document rather than throwing', () => {
    expect(parseMarkdown('')).toEqual([]);
    expect(parseMarkdown('\n\n\n')).toEqual([]);
  });

  it('survives an unclosed fence', () => {
    // Truncation is a real failure mode for a fetched document.
    expect(() => parseMarkdown('```\nno closing fence')).not.toThrow();
  });
});

describe('inline', () => {
  it('splits code out of surrounding text', () => {
    expect(parseInline('call `GET /models` first')).toEqual([
      { kind: 'text', text: 'call ' },
      { kind: 'code', text: 'GET /models' },
      { kind: 'text', text: ' first' },
    ]);
  });

  it('reads bold', () => {
    expect(parseInline('**Paths** are absolute')).toEqual([
      { kind: 'bold', text: 'Paths' },
      { kind: 'text', text: ' are absolute' },
    ]);
  });

  it('handles several runs in one line', () => {
    const spans = parseInline('the class is `prompt`, **not** `text`');

    expect(spans.filter((s) => s.kind === 'code')).toHaveLength(2);
    expect(spans.filter((s) => s.kind === 'bold')).toHaveLength(1);
  });

  it('keeps the backticks inside bold, for the renderer to parse again', () => {
    // "**The API is at `http://...` and only there.**" is a real line in the guide, and
    // the first look at it in a browser showed the backticks rendered literally. The
    // parser reports the bold run whole; `MarkdownView` re-parses it.
    const spans = parseInline('**at `127.0.0.1` only**');

    expect(spans).toEqual([{ kind: 'bold', text: 'at `127.0.0.1` only' }]);
  });

  it('leaves plain text alone', () => {
    expect(parseInline('nothing special')).toEqual([
      { kind: 'text', text: 'nothing special' },
    ]);
  });

  it('does not lose an unmatched backtick', () => {
    expect(parseInline('a ` b').map((s) => s.text).join('')).toBe('a ` b');
  });
});
