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

import { ModelGuidePanel } from '../components/ModelGuidePanel';
import { useT } from '../i18n';
import { introConcepts, introLead, introLimits, introStages } from './introContent';
import { tabLabel, type TabId } from './tabs';

export interface IntroTabProps {
  /** Jump to the tab a stage describes. Reading should turn into doing. */
  readonly onNavigate: (tab: TabId) => void;
}

export function IntroTab({ onNavigate }: IntroTabProps): JSX.Element {
  const translator = useT();
  const { t } = translator;
  return (
    <section className="intro">
      <h2 className="studio__title">{t('intro.title')}</h2>
      <p className="intro__lead">{introLead(translator)}</p>

      <h3 className="intro__heading">{t('intro.loop.heading')}</h3>
      <p className="intro__note">{t('intro.loop.note')}</p>

      <ol className="intro__stages">
        {introStages(translator).map((stage, index) => (
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
                {t('intro.loop.open', { tab: tabLabel(t, stage.tab) })}
              </button>
            </div>
            <p className="intro__what">{stage.what}</p>
            <p className="intro__why">
              <strong>{t('intro.loop.whyHere')}</strong> {stage.why}
            </p>
          </li>
        ))}
      </ol>

      <h3 className="intro__heading">{t('intro.concepts.heading')}</h3>
      <dl className="intro__concepts">
        {introConcepts(translator).map((concept) => (
          <div key={concept.term} className="intro__concept">
            <dt className="intro__term">{concept.term}</dt>
            <dd className="intro__body">{concept.body}</dd>
          </div>
        ))}
      </dl>

      {/* After the concepts and before the limits: it only makes sense once "backbone"
          and "head" mean something, and it answers the question the limits list provokes. */}
      <h3 className="intro__heading">{t('intro.model.heading')}</h3>
      <p className="intro__note">{t('intro.model.note')}</p>
      <ModelGuidePanel />

      <h3 className="intro__heading">{t('intro.limits.heading')}</h3>
      <p className="intro__note">{t('intro.limits.note')}</p>
      <ul className="intro__limits">
        {introLimits(translator).map((limit) => (
          <li key={limit}>{limit}</li>
        ))}
      </ul>
    </section>
  );
}
