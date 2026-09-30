import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { SetupStatus } from './shell';

const status = vi.hoisted(() => vi.fn<() => Promise<SetupStatus>>());
const shellFlag = vi.hoisted(() => ({ inside: false }));

vi.mock('./shell', async (original) => ({
  ...(await original<typeof import('./shell')>()),
  inShell: () => shellFlag.inside,
  setupStatus: status,
  onProgress: () => Promise.resolve(() => undefined),
}));

vi.mock('./DinoRun', () => ({ DinoRun: () => null }));

import { SetupGate } from './SetupGate';

afterEach(() => {
  shellFlag.inside = false;
  status.mockReset();
});

const MACHINE = {
  os: 'macos',
  arch: 'aarch64',
  apple_silicon: true,
  gpu: null,
  choices: [{ variant: 'cpu' as const, download_gb: 1, disk_gb: 3 }],
  note: null,
};

describe('SetupGate', () => {
  it('outside the desktop shell the app renders at once, without asking', () => {
    render(<SetupGate>app</SetupGate>);
    expect(screen.getByText('app')).toBeInTheDocument();
    expect(status).not.toHaveBeenCalled();
  });

  it('a packaged app with its environment installed shows the app', async () => {
    shellFlag.inside = true;
    status.mockResolvedValue({ needed: false, machine: null, auto: null, update: null });
    render(<SetupGate>app</SetupGate>);
    expect(await screen.findByText('app')).toBeInTheDocument();
  });

  it('a packaged app without its environment shows the setup, not the app', async () => {
    shellFlag.inside = true;
    status.mockResolvedValue({ needed: true, machine: MACHINE, auto: null, update: null });
    render(<SetupGate>app</SetupGate>);
    expect(await screen.findByRole('heading', { name: 'Welcome to DinoTraining' })).toBeInTheDocument();
    expect(screen.queryByText('app')).not.toBeInTheDocument();
  });

  it('a shell that cannot answer still shows the app', async () => {
    shellFlag.inside = true;
    status.mockRejectedValue(new Error('unknown command setup_status'));
    const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    render(<SetupGate>app</SetupGate>);
    expect(await screen.findByText('app')).toBeInTheDocument();
    spy.mockRestore();
  });
});
