/**
 * Everything the user types or picks in the Annotation Studio's setup, remembered across
 * tab switches and restarts (doc 69). Ids are *overrides*; see `useGeneratorEntries`.
 */

import type { Dispatch, SetStateAction } from 'react';

import { DEFAULT_BOX_THRESHOLD } from '../api/annotate';
import type { ImageSource } from '../components/ImageSourceField';
import type { ProposalMode } from '../components/ProposalModePicker';
import { isImageSource, isNumber, isOneOf, isString } from '../lib/persisted';
import { usePersistentState } from './usePersistentState';

type Setter<T> = Dispatch<SetStateAction<T>>;

export interface StudioEntries {
  readonly images: ImageSource;
  readonly setImages: Setter<ImageSource>;
  readonly mode: ProposalMode;
  readonly setMode: Setter<ProposalMode>;
  readonly prompt: string;
  readonly setPrompt: Setter<string>;
  readonly concept: string;
  readonly setConcept: Setter<string>;
  readonly newName: string;
  readonly setNewName: Setter<string>;
  readonly boxThreshold: number;
  readonly setBoxThreshold: Setter<number>;
  readonly datasetOverride: string;
  readonly setDatasetOverride: Setter<string>;
  readonly foundationOverride: string;
  readonly setFoundationOverride: Setter<string>;
  readonly headOverride: string;
  readonly setHeadOverride: Setter<string>;
}

const isMode = isOneOf<ProposalMode>(['prompt', 'head', 'foundation']);

export function useStudioEntries(): StudioEntries {
  const [images, setImages] = usePersistentState<ImageSource>(
    'studio.source',
    { kind: 'folder', folder: '' },
    isImageSource,
  );
  const [mode, setMode] = usePersistentState<ProposalMode>('studio.mode', 'prompt', isMode);
  const [prompt, setPrompt] = usePersistentState('studio.prompt', '', isString);
  // Separate from `prompt` — that one is Grounding DINO's. One shared string would
  // carry a stale prompt into a detector run the moment the user switched modes.
  const [concept, setConcept] = usePersistentState('studio.concept', '', isString);
  const [newName, setNewName] = usePersistentState('studio.newName', '', isString);
  const [boxThreshold, setBoxThreshold] = usePersistentState(
    'studio.boxThreshold',
    DEFAULT_BOX_THRESHOLD,
    isNumber,
  );
  const [datasetOverride, setDatasetOverride] = usePersistentState(
    'studio.dataset',
    '',
    isString,
  );
  const [foundationOverride, setFoundationOverride] = usePersistentState(
    'studio.detector',
    '',
    isString,
  );
  const [headOverride, setHeadOverride] = usePersistentState('studio.head', '', isString);

  return {
    images,
    setImages,
    mode,
    setMode,
    prompt,
    setPrompt,
    concept,
    setConcept,
    newName,
    setNewName,
    boxThreshold,
    setBoxThreshold,
    datasetOverride,
    setDatasetOverride,
    foundationOverride,
    setFoundationOverride,
    headOverride,
    setHeadOverride,
  };
}
