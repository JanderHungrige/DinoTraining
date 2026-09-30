/**
 * Everything the user types or picks in the Generator's setup, remembered across tab
 * switches and restarts (doc 69).
 *
 * Model and dataset choices are stored as *overrides*: the caller derives the effective
 * value with `stillListed(override, ids) || ids[0]`, because what was remembered may have
 * been deleted since, and the lists arrive asynchronously (CLAUDE.md's React-state rule).
 */

import type { Dispatch, SetStateAction } from 'react';

import type { GeneratorMode } from '../components/GeneratorModePicker';
import type { ImageSource } from '../components/ImageSourceField';
import { isImageSource, isNumber, isOneOf, isString } from '../lib/persisted';
import { usePersistentState } from './usePersistentState';

export const DEFAULT_THRESHOLD = 0.3;

type Setter<T> = Dispatch<SetStateAction<T>>;

export interface GeneratorEntries {
  readonly source: ImageSource;
  readonly setSource: Setter<ImageSource>;
  readonly mode: GeneratorMode;
  readonly setMode: Setter<GeneratorMode>;
  readonly concept: string;
  readonly setConcept: Setter<string>;
  readonly newName: string;
  readonly setNewName: Setter<string>;
  readonly threshold: number;
  readonly setThreshold: Setter<number>;
  readonly datasetOverride: string;
  readonly setDatasetOverride: Setter<string>;
  readonly detectorOverride: string;
  readonly setDetectorOverride: Setter<string>;
  readonly annotatorOverride: string;
  readonly setAnnotatorOverride: Setter<string>;
  readonly backboneOverride: string;
  readonly setBackboneOverride: Setter<string>;
  readonly headOverride: string;
  readonly setHeadOverride: Setter<string>;
}

const isMode = isOneOf<GeneratorMode>(['expert', 'masks', 'foundation']);

export function useGeneratorEntries(): GeneratorEntries {
  const [source, setSource] = usePersistentState<ImageSource>(
    'generator.source',
    { kind: 'folder', folder: '' },
    isImageSource,
  );
  // The default is unchanged. A general detector leads the *list*, which is where
  // discoverability lives, but selecting it by default would drop someone who has trained
  // heads and no detector installed onto an empty state telling them to visit Admin.
  const [mode, setMode] = usePersistentState<GeneratorMode>('generator.mode', 'expert', isMode);
  const [concept, setConcept] = usePersistentState('generator.concept', '', isString);
  const [newName, setNewName] = usePersistentState('generator.newName', '', isString);
  const [threshold, setThreshold] = usePersistentState(
    'generator.threshold',
    DEFAULT_THRESHOLD,
    isNumber,
  );
  const [datasetOverride, setDatasetOverride] = usePersistentState(
    'generator.dataset',
    '',
    isString,
  );
  const [detectorOverride, setDetectorOverride] = usePersistentState(
    'generator.detector',
    '',
    isString,
  );
  const [annotatorOverride, setAnnotatorOverride] = usePersistentState(
    'generator.annotator',
    '',
    isString,
  );
  const [backboneOverride, setBackboneOverride] = usePersistentState(
    'generator.backbone',
    '',
    isString,
  );
  const [headOverride, setHeadOverride] = usePersistentState('generator.head', '', isString);

  return {
    source,
    setSource,
    mode,
    setMode,
    concept,
    setConcept,
    newName,
    setNewName,
    threshold,
    setThreshold,
    datasetOverride,
    setDatasetOverride,
    detectorOverride,
    setDetectorOverride,
    annotatorOverride,
    setAnnotatorOverride,
    backboneOverride,
    setBackboneOverride,
    headOverride,
    setHeadOverride,
  };
}
