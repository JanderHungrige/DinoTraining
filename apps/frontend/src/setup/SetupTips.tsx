/** One sentence at a time about the app, while it installs (doc 127). */

import { useEffect, useState, type JSX } from 'react';

import { useT, type Key } from '../i18n';

export const TIP_KEYS: readonly Key[] = [
  'setup.tip.backbone',
  'setup.tip.head',
  'setup.tip.phrases',
  'setup.tip.saved',
  'setup.tip.generator',
  'setup.tip.export',
  'setup.tip.offline',
];

export const TIP_EVERY_MS = 9_000;

export function SetupTips(): JSX.Element {
  const { t } = useT();
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % TIP_KEYS.length), TIP_EVERY_MS);
    return () => window.clearInterval(timer);
  }, []);
  const key = TIP_KEYS[index] ?? 'setup.tip.backbone';
  return (
    <p className="firstrun__tip">
      <span className="firstrun__tipLabel">{t('setup.tip.label')}</span> {t(key)}
    </p>
  );
}
