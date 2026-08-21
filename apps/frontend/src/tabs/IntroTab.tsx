/**
 * The Intro tab (doc 38) — what this app is, in plain language.
 *
 * A **tab**, not a first-run overlay: an overlay is seen once and then in the way, and the
 * moment someone actually wants this is three days in, when they have forgotten what a
 * frozen backbone was. A tab is re-readable forever and costs nothing to skip.
 *
 * Every stage links to the tab it describes, so reading turns into doing without hunting
 * along the tab bar. The prose lives in `introContent.ts` — see the note there on why.
 */

import type { JSX } from 'react';

import { INTRO_CONCEPTS, INTRO_LEAD, INTRO_LIMITS, INTRO_STAGES } from './introContent';
import { getTab, type TabId } from './tabs';

export interface IntroTabProps {
  /** Jump to the tab a stage describes. Reading should turn into doing. */
  readonly onNavigate: (tab: TabId) => void;
}

export function IntroTab({ onNavigate }: IntroTabProps): JSX.Element {
  return (
    <section className="intro">
      <h2 className="studio__title">What this is</h2>
      <p className="intro__lead">{INTRO_LEAD}</p>

      <h3 className="intro__heading">The loop</h3>
      <p className="intro__note">
        The tabs are in the order you use them. You will go round more than once — that is
        the point, not a sign you did it wrong the first time.
      </p>

      <ol className="intro__stages">
        {INTRO_STAGES.map((stage, index) => (
          <li key={stage.tab} className="intro__stage">
            <div className="intro__stagehead">
              <span className="intro__step" aria-hidden="true">
                {index + 1}
              </span>
              <h4 className="intro__stagetitle">{stage.title}</h4>
              <button
                type="button"
                className="btn intro__go"
                onClick={() => onNavigate(stage.tab)}
              >
                Open {getTab(stage.tab).label}
              </button>
            </div>
            <p className="intro__what">{stage.what}</p>
            <p className="intro__why">
              <strong>Why here:</strong> {stage.why}
            </p>
          </li>
        ))}
      </ol>

      <h3 className="intro__heading">Two words this app uses constantly</h3>
      <dl className="intro__concepts">
        {INTRO_CONCEPTS.map((concept) => (
          <div key={concept.term} className="intro__concept">
            <dt className="intro__term">{concept.term}</dt>
            <dd className="intro__body">{concept.body}</dd>
          </div>
        ))}
      </dl>

      <h3 className="intro__heading">What it cannot do yet</h3>
      <p className="intro__note">
        Listed because being told is better than concluding it is broken.
      </p>
      <ul className="intro__limits">
        {INTRO_LIMITS.map((limit) => (
          <li key={limit}>{limit}</li>
        ))}
      </ul>
    </section>
  );
}
