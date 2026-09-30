/**
 * Connecting an assistant over MCP (doc 64).
 *
 * The better of the two connection paths, and the one to lead with: the assistant gets
 * typed tools with the preconditions in their schemas, instead of a document it has to
 * read and turn into `curl` calls correctly.
 *
 * **The tool list is fetched, not written here.** A hand-kept list is wrong the first time
 * a tool is added, and a reader has no way to tell which half is stale — the same rule the
 * endpoint reference in the guide follows.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { fetchMcpInfo, type McpInfo } from '../api/mcpInfo';
import { useT } from '../i18n';

export function McpPanel(): JSX.Element {
  const [info, setInfo] = useState<McpInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const { t, tp } = useT();

  useEffect(() => {
    const controller = new AbortController();
    void fetchMcpInfo(controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setInfo(found);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        setError(cause instanceof Error ? cause.message : t('admin.mcp.readFailed'));
      });
    return () => controller.abort();
  }, [t]);

  const copy = useCallback(async (): Promise<void> => {
    if (!info) return;
    try {
      await navigator.clipboard.writeText(info.command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      // A webview can refuse the clipboard. The command is on screen either way.
      setError(t('admin.mcp.clipboardFailed'));
    }
  }, [info, t]);

  return (
    <div className="conn__mode">
      <p className="intro__note">
        {t('admin.mcp.introBefore')} <strong>{t('admin.mcp.introStrong')}</strong>{' '}
        {t('admin.mcp.introAfter')}
      </p>

      <h4 className="conn__heading">{t('admin.mcp.step1')}</h4>
      <p className="conn__body">{t('admin.mcp.step1Body')}</p>

      {error && <p className="run__warn">{error}</p>}

      {info && (
        <>
          <pre className="conn__command">{info.command}</pre>
          <button type="button" className="btn btn--primary" onClick={() => void copy()}>
            {copied ? t('admin.mcp.copied') : t('admin.mcp.copy')}
          </button>

          <h4 className="conn__heading">{t('admin.mcp.step2')}</h4>
          <p className="conn__body">{t('admin.mcp.step2Body')}</p>
          <blockquote className="conn__quote">{t('admin.mcp.quote')}</blockquote>

          <h4 className="conn__heading">
            {tp('admin.mcp.toolsTitle', info.tools.length)}
          </h4>
          <p className="conn__body">{t('admin.mcp.toolsBody')}</p>
          <ul className="conn__tools">
            {info.tools.map((tool) => (
              <li key={tool.name} className="conn__tool">
                <code className="conn__toolname">{tool.name}</code>
                <span className="conn__toolsummary">{tool.summary}</span>
              </li>
            ))}
          </ul>

          <p className="conn__note">
            <strong>{t('admin.mcp.noteStrong')}</strong> {t('admin.mcp.noteBody')}
          </p>
        </>
      )}

      {!info && !error && <p role="status">{t('admin.mcp.reading')}</p>}
    </div>
  );
}
