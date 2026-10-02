import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const invoke = vi.hoisted(() => vi.fn());
vi.mock('@tauri-apps/api/core', () => ({ invoke }));

function inShell(on: boolean): void {
  if (on) Object.defineProperty(window, '__TAURI_INTERNALS__', { value: {}, configurable: true });
  else delete (window as unknown as Record<string, unknown>)['__TAURI_INTERNALS__'];
}

beforeEach(() => {
  vi.resetModules();
  invoke.mockReset();
});
afterEach(() => inShell(false));

describe('the app edition (doc 156)', () => {
  it('asks the shell once and keeps its answer', async () => {
    inShell(true);
    invoke.mockResolvedValue('store');
    const { appEdition } = await import('./edition');
    expect(await appEdition()).toBe('store');
    expect(await appEdition()).toBe('store');
    expect(invoke).toHaveBeenCalledTimes(1);
    expect(invoke).toHaveBeenCalledWith('app_edition');
  });

  it('is web without a shell, and an installer when the shell does not know the command', async () => {
    const { appEdition } = await import('./edition');
    expect(await appEdition()).toBe('web');
    expect(invoke).not.toHaveBeenCalled();

    vi.resetModules();
    inShell(true);
    invoke.mockRejectedValue(new Error('command app_edition not found'));
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const fresh = await import('./edition');
    expect(await fresh.appEdition()).toBe('installer');
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('reveals a folder through the shell, which knows where the Store put it', async () => {
    inShell(true);
    invoke.mockResolvedValue('C:\\Users\\jan\\AppData\\Local\\Packages\\x\\LocalCache\\Local\\DinoTraining');
    const { revealFolder } = await import('./dialog');
    await revealFolder('C:\\Users\\jan\\AppData\\Local\\DinoTraining');
    expect(invoke).toHaveBeenCalledWith('reveal_path', { path: 'C:\\Users\\jan\\AppData\\Local\\DinoTraining' });
  });
});
