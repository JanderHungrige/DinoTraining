/**
 * The particle loop behind the whole app (docs 76, 77).
 *
 * Decorative and nothing more: hidden from assistive tech, never focusable, never in the
 * way of a click. Reduced motion and the Admin switch both show the still poster instead,
 * and a hidden window pauses the video so a minimised app decodes nothing.
 */

import { useEffect, useRef, type JSX } from 'react';

import { useReducedMotion } from '../hooks/useReducedMotion';
import { useLook } from '../lib/look';

/** Served from `public/`, so the same path works under Vite and in the packaged app. */
export const LOOP_SRC = `${import.meta.env.BASE_URL}background/particles-loop.mp4`;
export const POSTER_SRC = `${import.meta.env.BASE_URL}background/particles-poster.jpg`;

export function BackgroundVideo(): JSX.Element {
  const reduced = useReducedMotion();
  const { animatedBackground } = useLook();
  const moving = animatedBackground && !reduced;
  const video = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    if (!moving) return;
    const sync = (): void => {
      const element = video.current;
      if (!element) return;
      if (document.hidden) element.pause();
      // A rejected play() (autoplay policy) is not an error worth a console line: the
      // poster is showing, which is exactly the fallback.
      else void element.play()?.catch(() => undefined);
    };
    // Once now as well: a start blocked while the window was in the background would
    // otherwise wait for a visibility change that never comes.
    sync();
    document.addEventListener('visibilitychange', sync);
    return () => document.removeEventListener('visibilitychange', sync);
  }, [moving]);

  return (
    <div className="bgvideo" aria-hidden="true">
      {moving ? (
        <video
          ref={video}
          className="bgvideo__media"
          src={LOOP_SRC}
          poster={POSTER_SRC}
          autoPlay
          muted
          loop
          playsInline
          disablePictureInPicture
          preload="auto"
          tabIndex={-1}
        />
      ) : (
        <img className="bgvideo__media" src={POSTER_SRC} alt="" />
      )}
      <div className="bgvideo__scrim" />
    </div>
  );
}
