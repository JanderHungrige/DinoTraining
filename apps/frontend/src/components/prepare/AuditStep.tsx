/**
 * Step 2: the audit (doc 81). Read-only; it changes nothing, so running it is always safe.
 */

import type { JSX } from 'react';

import type { DatasetAudit } from '../../api/prep';
import type { AuditProgress } from '../../hooks/usePrepareData';
import { FindingCard } from './FindingCard';

const ORDER: Readonly<Record<string, number>> = { problem: 0, warn: 1, info: 2, ok: 3 };

export interface AuditStepProps {
  readonly audit: DatasetAudit | null;
  readonly auditing: AuditProgress | null;
  readonly target: string;
  readonly targetLabel: string;
  readonly onRun: () => void;
}

function Progress({ progress }: { readonly progress: AuditProgress }): JSX.Element {
  const share = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;
  return (
    <p role="status" className="prep-step__status">
      Checking every picture… {progress.done} of {progress.total || '?'} ({share}%)
    </p>
  );
}

export function AuditStep({ audit, auditing, target, targetLabel, onRun }: AuditStepProps): JSX.Element {
  const otherTarget = audit !== null && audit.target !== target;
  const findings = audit ? [...audit.findings].sort((a, b) => (ORDER[a.severity] ?? 9) - (ORDER[b.severity] ?? 9)) : [];
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        The audit opens every picture and reads every annotation, and tells you what would make
        training go wrong — judged for <strong>{targetLabel}</strong>, because what counts as
        &quot;too small&quot; depends on the model. It changes nothing.
      </p>
      <button type="button" className="btn btn--primary" onClick={onRun} disabled={auditing !== null || !target}>
        {audit ? 'Run the audit again' : 'Run the audit'}
      </button>
      {auditing && <Progress progress={auditing} />}
      {otherTarget && (
        <p className="prep-step__note" role="status">
          This audit was made for another model. Run it again to judge the pictures for {targetLabel}.
        </p>
      )}
      {audit && (
        <>
          <p className="prep-step__summary">
            {audit.summary.images} pictures, {audit.summary.annotations} annotations,{' '}
            {Object.keys(audit.summary.classes).length} classes ·{' '}
            <strong>{audit.summary.problems}</strong> problem(s), <strong>{audit.summary.warnings}</strong> to
            look at{audit.excluded > 0 ? ` · ${audit.excluded} left out by a fix` : ''}.
          </p>
          {findings.length === 0 && <p role="status">Nothing to report. The data looks ready.</p>}
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
