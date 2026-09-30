/**
 * One audit finding (doc 81), as a non-expert reads it: what was found, why it matters
 * for training, what to do, and the pictures to look at.
 *
 * The thumbnails are the "look at these" sheet (doc 89): blur, bad lighting and wrong
 * labels are judged by a person, and a finding that only *names* files leaves them to
 * be found by hand.
 */

import type { JSX } from 'react';

import { imageUrl } from '../../api/annotate';
import type { Finding } from '../../api/prep';

const SEVERITY_LABEL: Readonly<Record<string, string>> = {
  problem: 'Problem',
  warn: 'Worth fixing',
  info: 'Good to know',
  ok: 'Fine',
};

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function FindingCard({ finding }: { readonly finding: Finding }): JSX.Element {
  return (
    <article className={`prep-finding prep-finding--${finding.severity}`}>
      <header className="prep-finding__head">
        <span className="prep-finding__badge">{SEVERITY_LABEL[finding.severity] ?? finding.severity}</span>
        <h4 className="prep-finding__title">{finding.title}</h4>
      </header>
      <p className="prep-finding__what">{finding.what}</p>
      <p className="prep-finding__why">
        <strong>Why it matters: </strong>
        {finding.why}
      </p>
      <p className="prep-finding__action">
        <strong>What to do: </strong>
        {finding.action}
      </p>
      {finding.examples.length > 0 && (
        <div className="prep-finding__examples" aria-label="Pictures to look at">
          {finding.examples.slice(0, 6).map((path) => (
            <a key={path} href={imageUrl(path)} target="_blank" rel="noreferrer" title={path}>
              <img src={imageUrl(path)} alt={fileName(path)} loading="lazy" />
            </a>
          ))}
        </div>
      )}
    </article>
  );
}
