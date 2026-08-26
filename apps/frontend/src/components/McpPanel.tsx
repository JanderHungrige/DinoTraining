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

export function McpPanel(): JSX.Element {
  const [info, setInfo] = useState<McpInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void fetchMcpInfo(controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setInfo(found);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        setError(cause instanceof Error ? cause.message : 'Could not read the MCP details.');
      });
    return () => controller.abort();
  }, []);

  const copy = useCallback(async (): Promise<void> => {
    if (!info) return;
    try {
      await navigator.clipboard.writeText(info.command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      // A webview can refuse the clipboard. The command is on screen either way.
      setError('Could not reach the clipboard — copy the command above by hand.');
    }
  }, [info]);

  return (
    <div className="conn__mode">
      <p className="intro__note">
        MCP gives your assistant <strong>typed tools</strong> rather than a document to
        interpret. It reads what each one needs from the tool schema, so it cannot invent a
        parameter or forget that a model has to be installed before it can be fine-tuned.
        This is the better option if your assistant supports it.
      </p>

      <h4 className="conn__heading">1. Connect it</h4>
      <p className="conn__body">
        The server runs inside this app — there is nothing to install or launch. Run this
        once in a terminal, with the app running:
      </p>

      {error && <p className="run__warn">{error}</p>}

      {info && (
        <>
          <pre className="conn__command">{info.command}</pre>
          <button type="button" className="btn btn--primary" onClick={() => void copy()}>
            {copied ? 'Copied' : 'Copy the command'}
          </button>

          <h4 className="conn__heading">2. Ask for what you want</h4>
          <p className="conn__body">
            Then talk to your assistant normally. It will pick the tools itself:
          </p>
          <blockquote className="conn__quote">
            “Here is a link to a rail dataset. Download it, import it, fine-tune RF-DETR on
            it, then use the result to annotate the images in ~/photos.”
          </blockquote>

          <h4 className="conn__heading">
            The {info.tools.length} tools it gets
          </h4>
          <p className="conn__body">
            Task-shaped rather than one per endpoint — the API has 61 operations, and
            handing over all of them would leave your assistant doing the orchestration.
          </p>
          <ul className="conn__tools">
            {info.tools.map((tool) => (
              <li key={tool.name} className="conn__tool">
                <code className="conn__toolname">{tool.name}</code>
                <span className="conn__toolsummary">{tool.summary}</span>
              </li>
            ))}
          </ul>

          <p className="conn__note">
            <strong>It only works on this machine.</strong> The server is bound to
            loopback, so an assistant running here can reach it and one running anywhere
            else cannot. That is deliberate: there is no authentication, and the tools can
            read any file path they are given.
          </p>
        </>
      )}

      {!info && !error && <p role="status">Reading the connection details…</p>}
    </div>
  );
}
