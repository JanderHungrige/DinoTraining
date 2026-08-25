/**
 * Which model to reach for, and what each is actually good at.
 *
 * Its own component rather than more markup in `IntroTab`, for the same reason the prose
 * lives in `introContent.ts`: this is the part most likely to be edited by someone reading
 * it and thinking "that is not quite right any more", and a table of content beats a table
 * of JSX for that.
 *
 * **Collapsed by default.** The intro's job is to get a first-time user through the loop;
 * this is the question they ask on day three, when they have a head that works and want to
 * know why the other one does not. Open by default it would push the loop off the screen.
 */

import { useState, type JSX } from 'react';

import { MODEL_GUIDE, MODEL_GUIDE_LEAD } from '../tabs/introContent';

export function ModelGuidePanel(): JSX.Element {
  const [open, setOpen] = useState(false);

  return (
    <div className="guide">
      <button
        type="button"
        className="btn guide__toggle"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {open ? '▾' : '▸'} Which model should I use?
      </button>

      {open && (
        <div className="guide__body">
          <p className="intro__note">{MODEL_GUIDE_LEAD}</p>

          <ul className="guide__list">
            {MODEL_GUIDE.map((entry) => (
              <li key={entry.name} className="guide__entry">
                <h4 className="guide__name">{entry.name}</h4>
                <p className="guide__best">{entry.bestFor}</p>

                <div className="guide__cols">
                  <div>
                    <h5 className="guide__colhead">Good at</h5>
                    <ul className="guide__points">
                      {entry.strengths.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h5 className="guide__colhead">Watch out for</h5>
                    <ul className="guide__points">
                      {entry.weaknesses.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Cited, not described. "Better for small objects" is an opinion; the
                    numbers are what settle it, and they were all measured in this app. */}
                {entry.measured && (
                  <p className="guide__measured">
                    <strong>Measured here:</strong> {entry.measured}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
