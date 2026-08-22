/**
 * "What must a training dataset look like?" — the disclosure (doc 48).
 *
 * A button rather than a link to a wiki, and a panel rather than a modal: the question is
 * asked *while* filling in the trainer form, and the answer has to be readable next to it
 * rather than instead of it. Nothing here is state the app owns — it is documentation, so
 * closing it loses nothing.
 *
 * The content is in `datasetFormat.ts`. This file is the shell.
 */

import { useId, useState, type JSX } from 'react';

import { DATASET_FORMAT } from '../tabs/datasetFormat';

export function DatasetFormatPanel(): JSX.Element {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="formatinfo">
      <button
        type="button"
        className="btn btn--small"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">ⓘ</span> What must a dataset look like?
      </button>

      {open && (
        <div id={panelId} className="formatinfo__panel">
          <p className="formatinfo__lead">
            Anything in this shape can be imported from <strong>Datasets → Import</strong>.
            Most Roboflow and HuggingFace detection exports already are.
          </p>

          {DATASET_FORMAT.map((section) => (
            <section key={section.heading} className="formatinfo__section">
              <h4 className="formatinfo__heading">{section.heading}</h4>
              {section.body.map((paragraph) => (
                <p key={paragraph} className="formatinfo__body">
                  {paragraph}
                </p>
              ))}
              {section.tree && (
                <pre className="formatinfo__tree">{section.tree.join('\n')}</pre>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
