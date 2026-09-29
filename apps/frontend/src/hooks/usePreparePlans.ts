/**
 * The Balance and Augment steps' recommendations (docs 86, 87), loaded for one dataset
 * and model, and loaded again when the data they judge changes (`version`).
 */

import { useEffect, useState } from 'react';

import { getAugmentation, getBalance, type AugmentationPlan, type BalancePlan } from '../api/prepPlan';

export function usePreparePlans(
  datasetId: string,
  target: string,
  version: string,
): { balance: BalancePlan | null; augmentation: AugmentationPlan | null; error: string } {
  const [balance, setBalance] = useState<BalancePlan | null>(null);
  const [augmentation, setAugmentation] = useState<AugmentationPlan | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    setBalance(null);
    setAugmentation(null);
    setError('');
    if (!datasetId || !target) return;
    let live = true;
    const fail = (cause: unknown): void => {
      if (live) setError(cause instanceof Error ? cause.message : String(cause));
    };
    getBalance(datasetId, target)
      .then((plan) => live && setBalance(plan))
      .catch(fail);
    getAugmentation(datasetId, target)
      .then((plan) => live && setAugmentation(plan))
      .catch(fail);
    return () => {
      live = false;
    };
  }, [datasetId, target, version]);
  return { balance, augmentation, error };
}
