/**
 * Step 2: the audit (doc 81). Read-only; it changes nothing, so running it is always safe.
 */

import type { JSX } from 'react';

import type { DatasetAudit } from '../../api/prep';
import type { AuditProgress } from '../../hooks/usePrepareData';
import { useT } from '../../i18n';
import { FindingCard } from './FindingCard';
import { richText } from './richText';

const ORDER: Readonly<Record<string, number>> = { problem: 0, warn: 1, info: 2, ok: 3 };

export interface AuditStepProps {
  readonly audit: DatasetAudit | null;
  readonly auditing: AuditProgress | null;
  readonly target: string;
  readonly targetLabel: string;
  readonly onRun: () => void;
}

function Progress({ progress }: { readonly progress: AuditProgress }): JSX.Element {
  const { t } = useT();
  const share = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;
  return (
    <p role="status" className="prep-step__status">
      {t('prepare.audit.progress', { done: progress.done, total: progress.total || '?', share })}
    </p>
  );
}

function Summary({ audit }: { readonly audit: DatasetAudit }): JSX.Element {
  const { t } = useT();
  const { summary } = audit;
  const text = t('prepare.audit.summary', {
    images: summary.images,
    annotations: summary.annotations,
    classes: Object.keys(summary.classes).length,
    excluded: audit.excluded > 0 ? t('prepare.audit.excluded', { count: audit.excluded }) : '',
  });
  return (
    <p className="prep-step__summary">
      {richText(text, { problems: <strong>{summary.problems}</strong>, warnings: <strong>{summary.warnings}</strong> })}
    </p>
  );
}

export function AuditStep({ audit, auditing, target, targetLabel, onRun }: AuditStepProps): JSX.Element {
  const { t } = useT();
  const otherTarget = audit !== null && audit.target !== target;
  const findings = audit ? [...audit.findings].sort((a, b) => (ORDER[a.severity] ?? 9) - (ORDER[b.severity] ?? 9)) : [];
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        {richText(t('prepare.audit.why'), { model: <strong>{targetLabel}</strong> })}
      </p>
      <button type="button" className="btn btn--primary" onClick={onRun} disabled={auditing !== null || !target}>
        {audit ? t('prepare.audit.runAgain') : t('prepare.audit.run')}
      </button>
      {auditing && <Progress progress={auditing} />}
      {otherTarget && (
        <p className="prep-step__note" role="status">
          {t('prepare.audit.otherModel', { model: targetLabel })}
        </p>
      )}
      {audit && (
        <>
          <Summary audit={audit} />
          {findings.length === 0 && <p role="status">{t('prepare.audit.nothing')}</p>}
          <div className="prep-findings">
            {findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
