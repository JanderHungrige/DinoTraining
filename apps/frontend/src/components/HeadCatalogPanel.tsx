/**
 * The "Pretrained heads" section of the Admin tab: install defaults, import community.
 *
 * Kept out of AdminTab so the model catalogue and the head catalogue stay separately
 * readable — they poll differently, fail differently, and are only neighbours on
 * screen.
 */

import { useState, type JSX } from 'react';

import type { BackboneInfo } from '../api/backbones';
import type { HeadTypeInfo } from '../api/heads';
import { useHeadCatalog } from '../hooks/useHeadCatalog';
import { useT } from '../i18n';
import { HeadCatalogCard } from './HeadCatalogCard';
import { HeadImportForm } from './HeadImportForm';

export interface HeadCatalogPanelProps {
  readonly backbones: readonly BackboneInfo[];
  readonly headTypes: readonly HeadTypeInfo[];
}

export function HeadCatalogPanel({
  backbones,
  headTypes,
}: HeadCatalogPanelProps): JSX.Element {
  const { t } = useT();
  const installed = backbones.filter((backbone) => backbone.installed);
  // Defaults to "" — every entry, no verdicts. Seeding this from installed[0] looks
  // tempting but cannot work: backbones arrive asynchronously, so the initialiser
  // always runs against an empty list and the state never catches up. Showing the
  // whole catalogue first is also the better default — the user picks a backbone to
  // narrow it, rather than wondering why six entries are missing.
  const [selected, setSelected] = useState<string>('');
  const { entries, loading, error, notice, busy, install, importHead } = useHeadCatalog(
    selected || undefined,
  );

  return (
    <section className="admin__group">
      <h3 className="admin__grouptitle">{t('admin.heads.title')}</h3>
      <p className="admin__groupnote">{t('admin.heads.note')}</p>

      <label className="field field--inline">
        <span className="field__label">{t('admin.heads.compatibleWith')}</span>
        <select
          className="field__input"
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="">{t('admin.heads.anyBackbone')}</option>
          {installed.map((backbone) => (
            <option key={backbone.id} value={backbone.id}>
              {backbone.id}
            </option>
          ))}
        </select>
      </label>

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="admin__notice" role="status">
          {notice}
        </p>
      )}

      {loading ? (
        <p role="status">{t('admin.heads.loading')}</p>
      ) : (
        <div className="admin__grid">
          {entries.map((entry) => (
            <HeadCatalogCard
              key={entry.id}
              entry={entry}
              busy={busy[entry.id] ?? false}
              onInstall={(entryId) => void install(entryId)}
            />
          ))}
        </div>
      )}

      <h3 className="admin__grouptitle">{t('admin.heads.importTitle')}</h3>
      <HeadImportForm
        headTypes={headTypes}
        backbones={installed}
        busy={busy['import'] ?? false}
        onImport={importHead}
      />
    </section>
  );
}
