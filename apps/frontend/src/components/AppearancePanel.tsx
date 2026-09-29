/**
 * Admin › Appearance (doc 77): the one look setting a user may want to change.
 */

import type { JSX } from 'react';

import { useReducedMotion } from '../hooks/useReducedMotion';
import { useLook } from '../lib/look';

export function AppearancePanel(): JSX.Element {
  const { animatedBackground, setAnimatedBackground } = useLook();
  const reduced = useReducedMotion();

  return (
    <section className="admin__group appearance">
      <h3 className="admin__grouptitle">Appearance</h3>
      <label className="appearance__toggle">
        <input
          type="checkbox"
          checked={animatedBackground}
          onChange={(event) => setAnimatedBackground(event.target.checked)}
        />
        Animated background
      </label>
      {reduced && (
        <p className="appearance__hint">
          Your system asks for reduced motion, so the background stays still whatever this
          is set to.
        </p>
      )}
    </section>
  );
}
