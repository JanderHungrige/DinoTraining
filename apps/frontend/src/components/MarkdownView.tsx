/**
 * Renders the blocks `parseMarkdown` produces (doc 63).
 *
 * Split from the parser so the parser can be tested without a DOM — it is the half with
 * the edge cases, and the half most likely to be wrong.
 *
 * Semantic elements throughout, because this document is also the print source: a PDF is
 * produced by the browser's own print of this markup, and `<h2>`/`<ol>`/`<pre>` are what
 * give it an outline and sensible page breaks. Divs styled to look like headings would
 * print as grey rectangles.
 */

import type { JSX } from 'react';

import { parseInline, parseMarkdown, type Block } from '../lib/markdown';

export interface MarkdownViewProps {
  readonly source: string;
}

export function MarkdownView({ source }: MarkdownViewProps): JSX.Element {
  return (
    <div className="md">
      {parseMarkdown(source).map((block, index) => (
        <BlockView key={index} block={block} />
      ))}
    </div>
  );
}

function BlockView({ block }: { readonly block: Block }): JSX.Element {
  switch (block.kind) {
    case 'heading': {
      // Clamped to h6, and offset by one: the page already has an <h2> for the tab, so the
      // guide's own `#` becomes an h3 rather than competing with it.
      const level = Math.min(6, block.level + 2);
      const Tag = `h${level}` as 'h3';
      return (
        <Tag className={`md__h md__h--${block.level}`}>
          <Inline text={block.text} />
        </Tag>
      );
    }
    case 'code':
      return (
        <pre className="md__code">
          <code>{block.text}</code>
        </pre>
      );
    case 'list': {
      const Tag = block.ordered ? 'ol' : 'ul';
      return (
        <Tag className="md__list">
          {block.items.map((item, index) => (
            <li key={index}>
              <Inline text={item} />
            </li>
          ))}
        </Tag>
      );
    }
    case 'quote':
      return (
        <blockquote className="md__quote">
          <Inline text={block.text} />
        </blockquote>
      );
    default:
      return (
        <p className="md__p">
          <Inline text={block.text} />
        </p>
      );
  }
}

function Inline({ text }: { readonly text: string }): JSX.Element {
  return (
    <>
      {parseInline(text).map((span, index) => {
        if (span.kind === 'code') return <code key={index}>{span.text}</code>;
        // Bold is parsed again: the guide writes bold sentences with paths in them, and
        // rendering those backticks literally is what a first look in a browser caught.
        // Terminates because the bold pattern excludes `*`, so this cannot nest further.
        if (span.kind === 'bold') {
          return (
            <strong key={index}>
              <Inline text={span.text} />
            </strong>
          );
        }
        return <span key={index}>{span.text}</span>;
      })}
    </>
  );
}
