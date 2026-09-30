import { afterEach, describe, expect, it, vi } from 'vitest';

import { getLastAudit, getSplit, listTargets } from './prep';

function respond(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('the Prepare API slice', () => {
  it('reads "not audited / not split yet" as null, not as an error', async () => {
    respond(404, { error: { code: 'not_found', message: 'This dataset has not been split yet.' } });
    await expect(getSplit('d')).resolves.toBeNull();
    await expect(getLastAudit('d')).resolves.toBeNull();
  });

  it('still fails on any other error', async () => {
    respond(500, { error: { code: 'internal', message: 'boom' } });
    await expect(getSplit('d')).rejects.toThrow('boom');
  });

  it('refuses a response of the wrong shape at the boundary', async () => {
    respond(200, [{ id: 'rf-detr-nano' }]);
    await expect(listTargets()).rejects.toThrow(/drifted/);
  });
});
