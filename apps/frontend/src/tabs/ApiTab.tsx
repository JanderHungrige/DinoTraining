/**
 * The Connection tab (docs 63 and 64) — two ways to let an assistant drive this app.
 *
 * **Two modes, switched at the top**, for the reason the Training tab has them: the second
 * option is the better one and would be invisible below the first. MCP leads because a
 * typed tool an assistant cannot misuse beats a document it has to interpret correctly.
 *
 * The manual half is what remains for assistants without MCP, and is documented below.
 *
 * **Copy is the primary action, not download.** The stated use is pasting this into an
 * assistant's context so it can drive the app: "here is a dataset link, fine-tune RF-DETR
 * on it, then generate a dataset." A file on disk is one step further from that than the
 * clipboard is.
 *
 * PDF was asked for and is here, and it is the *worst* of the three formats for that
 * purpose — a model handed a PDF has to have it extracted first and layout becomes noise.
 * It is produced by the browser's own print of the rendered document rather than by a
 * generator on the backend: adding `weasyprint` to a sidecar that is already 636 MB frozen
 * (doc 56) to reproduce something the OS print dialog does better is the wrong trade.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { fetchAgentGuide, GUIDE_FILENAME } from '../api/agentGuide';
import { MarkdownView } from '../components/MarkdownView';
import { McpPanel } from '../components/McpPanel';

type CopyState = 'idle' | 'copied' | 'failed';

/** Which way of connecting is on screen. */
type ConnectionMode = 'mcp' | 'manual';

const MODES: readonly { id: ConnectionMode; name: string; hint: string }[] = Object.freeze([
  {
    id: 'mcp',
    name: 'MCP',
    hint: 'Typed tools your assistant calls directly. Best, if it supports MCP.',
  },
  {
    id: 'manual',
    name: 'Any assistant',
    hint: 'One document to paste in. Works anywhere, including without MCP.',
  },
]);

export function ApiTab(): JSX.Element {
  // MCP first: it is the better path, and the one that needs finding.
  const [mode, setMode] = useState<ConnectionMode>('mcp');
  const [guide, setGuide] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<CopyState>('idle');

  useEffect(() => {
    const controller = new AbortController();
    void fetchAgentGuide(controller.signal)
      .then((text) => {
        if (!controller.signal.aborted) setGuide(text);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        setError(cause instanceof Error ? cause.message : 'Could not load the API guide.');
      });
    return () => controller.abort();
  }, []);

  const copy = useCallback(async (): Promise<void> => {
    if (!guide) return;
    try {
      await navigator.clipboard.writeText(guide);
      setCopied('copied');
    } catch {
      // A webview can refuse the clipboard. Saying so beats a button that appears to work,
      // and the download beside it is the way through.
      setCopied('failed');
    }
    window.setTimeout(() => setCopied('idle'), 2500);
  }, [guide]);

  const download = useCallback((): void => {
    if (!guide) return;
    const url = URL.createObjectURL(new Blob([guide], { type: 'text/markdown' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = GUIDE_FILENAME;
    link.click();
    URL.revokeObjectURL(url);
  }, [guide]);

  return (
    <section className="apidocs">
      <h2 className="studio__title">Connection</h2>
      <p className="studio__lead">
        Everything this app does, it does through a local API — so your own AI assistant can
        do it too. Two ways to give it access, and both run entirely on this machine.
      </p>

      <fieldset className="modeswitch">
        <legend className="modeswitch__legend">How to connect</legend>
        {MODES.map((entry) => (
          <label
            key={entry.id}
            className={`modeswitch__option${mode === entry.id ? ' modeswitch__option--on' : ''}`}
          >
            <input
              type="radio"
              name="connection-mode"
              value={entry.id}
              checked={mode === entry.id}
              onChange={() => setMode(entry.id)}
            />
            <span className="modeswitch__name">{entry.name}</span>
            <span className="modeswitch__hint">{entry.hint}</span>
          </label>
        ))}
      </fieldset>

      {mode === 'mcp' && <McpPanel />}

      {mode === 'manual' && (
        <div className="conn__mode">
          <p className="intro__note">
            Copy this document into your assistant and describe what you want. It documents
            every workflow in order, with the traps named — which is the part a schema
            cannot express. Use this when your assistant does not speak MCP.
          </p>

      <div className="apidocs__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={!guide}
          onClick={() => void copy()}
        >
          {copied === 'copied'
            ? '✓ Copied'
            : copied === 'failed'
              ? 'Could not copy — use Download'
              : 'Copy for your AI'}
        </button>
        <button type="button" className="btn" disabled={!guide} onClick={download}>
          Download .md
        </button>
        {/* Print, not "export": the browser's dialog is what turns it into a PDF, and
            calling it Export would promise a file this button does not create. */}
        <button type="button" className="btn" disabled={!guide} onClick={() => window.print()}>
          Save as PDF
        </button>
        <span className="apidocs__note">
          Markdown is what these models read best — the PDF is for people.
        </span>
      </div>

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
      )}

      {!guide && !error && <p role="status">Loading the guide…</p>}

      {/* The print target. Everything outside it is hidden when printing — see the
          `@media print` block — so the PDF is the document and not the app around it. */}
      {guide && (
        <article className="apidocs__doc" id="api-guide">
          <MarkdownView source={guide} />
        </article>
      )}
        </div>
      )}
    </section>
  );
}
