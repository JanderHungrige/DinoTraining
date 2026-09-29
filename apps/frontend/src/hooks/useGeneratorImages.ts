/**
 * Which images the Dataset Generator works through: the source's listing, narrowed by an
 * optional prescan filter (doc 53).
 *
 * Split out of `useGeneratorSession` when doc 71 needed room in it. The seam is real: this
 * answers "which images", the session answers "what happens on one of them".
 */

import { useEffect, useState } from 'react';

import { ApiError } from '../api/client';
import { resolveImageSource, sourceNoun } from '../lib/imageSource';
import type { GeneratorConfig } from '../types/generatorConfig';

export interface GeneratorImages {
  /** The images to work through: all of them, or the prescan's hits. */
  readonly images: readonly string[];
  /** Every image the source holds, ignoring any prescan filter. */
  readonly allImages: readonly string[];
  readonly filtered: boolean;
  readonly setFilter: (paths: readonly string[] | null) => void;
  readonly loading: boolean;
  readonly listError: string | null;
}

export function useGeneratorImages(config: GeneratorConfig | null): GeneratorImages {
  const [allImages, setAllImages] = useState<readonly string[]>([]);
  // A prescan's hits. Null means no filter. The full list stays loaded, so turning the
  // filter off costs nothing and re-reads nothing.
  const [filter, setFilter] = useState<readonly string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  useEffect(() => {
    // Cleared before the new listing is asked for, not after it arrives (doc 50, bug 1).
    // A source that fails to load must not leave the previous one's images on screen: they
    // render fully interactive, so the user would review the old folder's pictures while
    // the boxes save into the newly chosen dataset.
    setAllImages([]);
    setFilter(null);
    setListError(null);
    if (!config) return;

    const controller = new AbortController();
    setLoading(true);
    resolveImageSource(config.images, controller.signal)
      .then(setAllImages)
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setListError(
          caught instanceof ApiError
            ? caught.message
            : `Could not list that ${sourceNoun(config.images)}.`,
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [config]);

  const kept = filter === null ? null : new Set(filter);
  const images = kept === null ? allImages : allImages.filter((path) => kept.has(path));

  return {
    images,
    allImages,
    filtered: filter !== null,
    setFilter,
    loading,
    listError,
  };
}
