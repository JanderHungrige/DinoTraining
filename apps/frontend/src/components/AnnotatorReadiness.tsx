/**
 * Which concept segmenters are ready, and what each still needs (doc 65).
 *
 * **The gap this closes was reported as "Grounded SAM does not appear anything to
 * install".** It never did. Grounded SAM is not a model — it is `grounding-dino-tiny`
 * *plus* `sam2.1-hiera-small` working as a pipeline — and Admin listed those two under
 * their own names, in two different family sections, saying nothing about what they add
 * up to. Every other tab calls the thing "Grounded SAM", so the one screen where you
 * install it was the only one that did not.
 *
 * The backend already answered this: `/annotators` reports `ready` and `missing_model_ids`
 * per annotator, and until now it was used in the Dataset Generator and nowhere else.
 * This is that endpoint, shown where installing happens.
 */

import { useEffect, useState, type JSX } from 'react';

import { listAnnotators, type AnnotatorInfo } from '../api/annotators';

export interface AnnotatorReadinessProps {
  /** Bumped by the parent after a download, so readiness re-reads rather than going stale. */
  readonly refreshKey?: number;
}

export function AnnotatorReadiness({ refreshKey = 0 }: AnnotatorReadinessProps): JSX.Element | null {
  const [annotators, setAnnotators] = useState<readonly AnnotatorInfo[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    void listAnnotators(controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setAnnotators(found);
      })
      // Non-fatal: the model list is the point of this tab and must not go down with it.
      .catch(() => undefined);
    return () => controller.abort();
  }, [refreshKey]);

  if (annotators.length === 0) return null;

  return (
    <section className="admin__group">
      <h3 className="admin__grouptitle">Concept segmentation — type what you want, get masks</h3>
      <p className="starter__body">
        These are <strong>pipelines</strong>, not single models, which is why they are not
        in the list above under their own names. Each needs every one of its parts.
      </p>

      <ul className="annot__list">
        {annotators.map((entry) => (
          <li key={entry.id} className="annot">
            <div className="annot__head">
              <span className="annot__name">{entry.name}</span>
              <span className={`annot__state annot__state--${entry.ready ? 'on' : 'off'}`}>
                {entry.ready ? 'Ready' : 'Not installed'}
              </span>
            </div>

            <p className="annot__desc">{entry.description}</p>

            <ul className="annot__parts">
              {entry.models.map((model) => (
                <li key={model.id} className="annot__part">
                  <span aria-hidden="true">{model.installed ? '✓' : '○'}</span>
                  <code>{model.id}</code>
                  <span className="starter__size">{model.approx_size_mb} MB</span>
                  {model.gated && <span className="annot__gated">needs your token</span>}
                </li>
              ))}
            </ul>

            {/* Names the parts rather than offering a button: they are in the list above,
                each with its own licence to read first — which is doc 35's whole point. */}
            {!entry.ready && (
              <p className="annot__todo">
                Install {entry.missing_model_ids.join(' and ')} above
                {entry.requires_access_request
                  ? ', after requesting access on HuggingFace — approved by hand, so it is not instant.'
                  : '.'}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
