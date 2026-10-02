/**
 * The background loop behind the whole app (docs 76, 77; chosen in Settings, doc 165).
 *
 * Decorative and nothing more: hidden from assistive tech, never focusable, never in the
 * way of a click. Reduced motion and the Settings switch both show the still poster instead,
 * and a hidden window pauses the video so a minimised app decodes nothing.
 */

import { useEffect, useRef, type JSX } from 'react';

import { useReducedMotion } from '../hooks/useReducedMotion';
import { backgroundPoster, backgroundVideo, DEFAULT_BACKGROUND } from '../lib/backgrounds';
import { useLook } from '../lib/look';

/** The default background's files, served from `public/` (the same path under Vite and in
 *  the packaged app). The chosen one comes from Settings (doc 165). */
export const LOOP_SRC = backgroundVideo(DEFAULT_BACKGROUND);
export const POSTER_SRC = backgroundPoster(DEFAULT_BACKGROUND);

export function BackgroundVideo(): JSX.Element {
  const reduced = useReducedMotion();
  const { animatedBackground, background } = useLook();
  const src = backgroundVideo(background);
  const poster = backgroundPoster(background);
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
  }, [moving, src]);

  return (
    <div className="bgvideo" aria-hidden="true">
      {moving ? (
        <video
          key={src}
          ref={video}
          className="bgvideo__media"
          src={src}
          poster={poster}
          autoPlay
          muted
          loop
          playsInline
          disablePictureInPicture
          preload="auto"
          tabIndex={-1}
        />
      ) : (
        <img className="bgvideo__media" src={poster} alt="" />
      )}
      <div className="bgvideo__scrim" />
    </div>
  );
}
