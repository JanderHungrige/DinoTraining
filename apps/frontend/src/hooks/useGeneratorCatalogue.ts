/**
 * What the Dataset Generator's setup can choose from: datasets, annotators, detectors and
 * trained heads. Four independent loads with four deliberately different failure policies,
 * kept together so the setup form reads as choices rather than as fetching.
 */

import { useEffect, useState } from 'react';

import { listAnnotators, type AnnotatorInfo } from '../api/annotators';
import { listDatasets, type DatasetInfo } from '../api/datasets';
import { listFoundations, type FoundationInfo } from '../api/foundation';
import { listHeadInstances, type HeadInstanceInfo } from '../api/headInstances';

export interface GeneratorCatalogue {
  readonly datasets: readonly DatasetInfo[];
  readonly annotators: readonly AnnotatorInfo[];
  readonly foundations: readonly FoundationInfo[];
  readonly heads: readonly HeadInstanceInfo[];
  readonly loadingHeads: boolean;
}

export function useGeneratorCatalogue(): GeneratorCatalogue {
  // Loaded here as well as in `GeneratorDestination`: the source picker offers datasets
  // to *read* and the destination offers them to *write*, and the two lists answer
  // different questions — one filters to datasets that have images.
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [annotators, setAnnotators] = useState<readonly AnnotatorInfo[]>([]);
  const [foundations, setFoundations] = useState<readonly FoundationInfo[]>([]);
  const [heads, setHeads] = useState<readonly HeadInstanceInfo[]>([]);
  const [loadingHeads, setLoadingHeads] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    void listDatasets(signal)
      .then(setDatasets)
      .catch(() => setDatasets([]));
    listAnnotators(signal)
      .then((found) => {
        if (!signal.aborted) setAnnotators(found);
      })
      .catch(() => {
        /* the mask mode falls back to the ungated default */
      });
    // Non-fatal: the other two modes still work if the catalogue is unhappy.
    listFoundations(signal)
      .then((found) => {
        if (!signal.aborted) setFoundations(found);
      })
      .catch(() => undefined);
    listHeadInstances({}, signal)
      .then((found) => {
        if (!signal.aborted) setHeads(found);
      })
      .catch(() => {
        /* the picker renders its own empty state */
      })
      .finally(() => {
        if (!signal.aborted) setLoadingHeads(false);
      });
    return () => controller.abort();
  }, []);

  return { datasets, annotators, foundations, heads, loadingHeads };
}
