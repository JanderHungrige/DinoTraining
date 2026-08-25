/**
 * A markdown parser for exactly the markdown this app generates (doc 63).
 *
 * **Not a general one, and that is the point.** Both ends are written here: the guide comes
 * from `backend/app/docs/`, so the set of constructs is closed and small. A general parser
 * would be a dependency to vet, ~30 KB of bundle, and a much larger surface than the six
 * things actually used.
 *
 * The escape hatch matters more than the coverage: anything unrecognised falls through as a
 * paragraph of its own text. A parser that dropped what it did not understand would lose
 * part of a document whose whole job is to be complete, and it would do so silently.
 *
 * Supported: headings, fenced code, ordered and unordered lists, blockquotes, paragraphs,
 * and inline `code` / `**bold**`.
 */

export type Block =
  | { readonly kind: 'heading'; readonly level: number; readonly text: string }
  | { readonly kind: 'code'; readonly text: string }
  | { readonly kind: 'list'; readonly ordered: boolean; readonly items: readonly string[] }
  | { readonly kind: 'quote'; readonly text: string }
  | { readonly kind: 'paragraph'; readonly text: string };

/** One run of inline text: plain, `code`, or **bold**. */
export type Span =
  | { readonly kind: 'text'; readonly text: string }
  | { readonly kind: 'code'; readonly text: string }
  | { readonly kind: 'bold'; readonly text: string };

const HEADING = /^(#{1,6})\s+(.*)$/;
const BULLET = /^[-*]\s+(.*)$/;
const NUMBERED = /^\d+\.\s+(.*)$/;
const QUOTE = /^>\s?(.*)$/;

export function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? '';

    if (line.trim() === '') {
      index += 1;
      continue;
    }

    // Fenced code first: everything inside is literal, including things that look like
    // headings. A `#` in a shell comment is not a heading, and this is a document full of
    // shell comments.
    if (line.startsWith('```')) {
      const body: string[] = [];
      index += 1;
      while (index < lines.length && !(lines[index] ?? '').startsWith('```')) {
        body.push(lines[index] ?? '');
        index += 1;
      }
      index += 1; // the closing fence
      blocks.push({ kind: 'code', text: body.join('\n') });
      continue;
    }

    const heading = HEADING.exec(line);
    if (heading) {
      blocks.push({
        kind: 'heading',
        level: (heading[1] ?? '#').length,
        text: heading[2] ?? '',
      });
      index += 1;
      continue;
    }

    if (BULLET.test(line) || NUMBERED.test(line)) {
      const ordered = NUMBERED.test(line);
      const items: string[] = [];
      // A list ends at a blank line or at anything that is not an item of the same kind —
      // so a numbered list directly under a bulleted one is two lists, not one.
      while (index < lines.length) {
        const current = lines[index] ?? '';
        const match = ordered ? NUMBERED.exec(current) : BULLET.exec(current);
        if (!match) break;
        items.push(match[1] ?? '');
        index += 1;
      }
      blocks.push({ kind: 'list', ordered, items });
      continue;
    }

    const quote = QUOTE.exec(line);
    if (quote) {
      const body: string[] = [quote[1] ?? ''];
      index += 1;
      while (index < lines.length && QUOTE.test(lines[index] ?? '')) {
        body.push(QUOTE.exec(lines[index] ?? '')?.[1] ?? '');
        index += 1;
      }
      blocks.push({ kind: 'quote', text: body.join(' ') });
      continue;
    }

    // A paragraph runs until a blank line or the start of any other block. Joined with
    // spaces because the source hard-wraps at 96 characters and a browser should not.
    const body: string[] = [];
    while (index < lines.length) {
      const current = lines[index] ?? '';
      if (
        current.trim() === '' ||
        current.startsWith('```') ||
        HEADING.test(current) ||
        BULLET.test(current) ||
        NUMBERED.test(current) ||
        QUOTE.test(current)
      ) {
        break;
      }
      body.push(current.trim());
      index += 1;
    }
    blocks.push({ kind: 'paragraph', text: body.join(' ') });
  }

  return blocks;
}

const INLINE = /(`[^`]+`|\*\*[^*]+\*\*)/g;

/**
 * Split one line into plain, code and bold runs.
 *
 * **Bold may contain code**, and the guide relies on it — "The API is at `…` and only
 * there." is a bold sentence with a path in it, and rendering the backticks literally is
 * what a first look at this in a browser caught.
 *
 * The renderer handles that by parsing a bold span's text again. It terminates because the
 * bold pattern excludes `*`, so bold inside bold cannot match; one level is all there is.
 */
export function parseInline(text: string): Span[] {
  const spans: Span[] = [];
  let last = 0;

  for (const match of text.matchAll(INLINE)) {
    const start = match.index ?? 0;
    if (start > last) spans.push({ kind: 'text', text: text.slice(last, start) });

    const token = match[0];
    if (token.startsWith('`')) {
      spans.push({ kind: 'code', text: token.slice(1, -1) });
    } else {
      spans.push({ kind: 'bold', text: token.slice(2, -2) });
    }
    last = start + token.length;
  }

  if (last < text.length) spans.push({ kind: 'text', text: text.slice(last) });
  return spans;
}
