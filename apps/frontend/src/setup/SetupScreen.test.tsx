import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderInGerman } from '../i18n/testing';
import type { Machine, Progress, SetupFailure } from './shell';

const shell = vi.hoisted(() => ({
  install: vi.fn<(variant: string) => Promise<void>>(),
  progress: null as ((p: Progress) => void) | null,
}));

vi.mock('./shell', async (original) => ({
  ...(await original<typeof import('./shell')>()),
  setupInstall: shell.install,
  onProgress: (handler: (p: Progress) => void) => {
    shell.progress = handler;
    return Promise.resolve(() => undefined);
  },
}));

// jsdom has no canvas; the game is tested through its rules (runRules.test.ts).
vi.mock('./DinoRun', () => ({
  DinoRun: ({ onPlay }: { onPlay?: () => void }) => (
    <button type="button" onClick={onPlay}>
      play
    </button>
  ),
}));

import { SetupScreen } from './SetupScreen';

const MAC: Machine = {
  os: 'macos',
  arch: 'aarch64',
  apple_silicon: true,
  gpu: null,
  choices: [{ variant: 'cpu', download_gb: 1, disk_gb: 3 }],
  note: null,
};

const PC: Machine = {
  os: 'windows',
  arch: 'x86_64',
  apple_silicon: false,
  gpu: { name: 'NVIDIA GeForce RTX 4070', driver: '581.15' },
  choices: [
    { variant: 'cu130', download_gb: 3.5, disk_gb: 10 },
    { variant: 'cpu', download_gb: 1, disk_gb: 3 },
  ],
  note: null,
};

beforeEach(() => {
  shell.install.mockReset();
  shell.progress = null;
});

describe('SetupScreen', () => {
  it('a Mac is offered one install, with MPS named', () => {
    render(<SetupScreen machine={MAC} onDone={() => undefined} />);
    expect(screen.getByText(/Apple silicon\. Its GPU is used through MPS/)).toBeInTheDocument();
    expect(screen.getAllByRole('button')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Install (about 1 GB download)' })).toBeInTheDocument();
  });

  it('an NVIDIA PC chooses between the GPU build and the CPU, GPU first', () => {
    render(<SetupScreen machine={PC} onDone={() => undefined} />);
    expect(screen.getByText('Found: NVIDIA GeForce RTX 4070, driver 581.15.')).toBeInTheDocument();
    const [gpu, cpu] = screen.getAllByRole('button');
    expect(gpu).toHaveTextContent('CUDA 13.0, about 3.5 GB');
    expect(cpu).toHaveTextContent('CPU only');
  });

  it('an Intel Mac gets the reason and no button', () => {
    render(<SetupScreen machine={{ ...MAC, apple_silicon: false, arch: 'x86_64', choices: [], note: { kind: 'intel_mac' } }} onDone={() => undefined} />);
    expect(screen.getByText(/Intel processor/)).toBeInTheDocument();
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });

  it('installs the chosen variant, shows the progress, and opens the app when nobody played', async () => {
    let finish: () => void = () => undefined;
    shell.install.mockImplementation(() => new Promise<void>((resolve) => (finish = resolve)));
    const onDone = vi.fn();
    render(<SetupScreen machine={PC} onDone={onDone} />);

    fireEvent.click(screen.getByRole('button', { name: /CPU only/ }));
    expect(shell.install).toHaveBeenCalledWith('cpu');
    act(() => shell.progress?.({ phase: 'packages', done_mb: 50, total_mb: 100, current: 'torch' }));
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '48');
    expect(screen.getByText('torch downloaded')).toBeInTheDocument();
    expect(screen.getByText(/Did you know\?/)).toBeInTheDocument();
    // uv is done: the shell now starts the backend, and the screen says so.
    act(() => shell.progress?.({ phase: 'done', done_mb: 100, total_mb: 100, current: null }));
    expect(screen.getByText('Starting the AI engine…')).toBeInTheDocument();

    await act(async () => finish());
    await waitFor(() => expect(onDone).toHaveBeenCalled());
  });

  it('someone playing is not interrupted: the app waits for their click', async () => {
    let finish: () => void = () => undefined;
    shell.install.mockImplementation(() => new Promise<void>((resolve) => (finish = resolve)));
    const onDone = vi.fn();
    render(<SetupScreen machine={MAC} onDone={onDone} />);
    fireEvent.click(screen.getByRole('button', { name: /Install/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'play' }));
    await act(async () => finish());

    fireEvent.click(await screen.findByRole('button', { name: 'Open DinoTraining' }));
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('offline: says so, and Try again installs the same variant again', async () => {
    const offline: SetupFailure = { kind: 'offline' };
    shell.install.mockRejectedValueOnce(offline).mockImplementation(() => new Promise(() => undefined));
    render(<SetupScreen machine={PC} onDone={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: /GPU support/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('No internet connection');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(shell.install).toHaveBeenLastCalledWith('cu130');
    expect(shell.install).toHaveBeenCalledTimes(2);
  });

  it('too little disk space names the numbers', async () => {
    shell.install.mockRejectedValue({ kind: 'disk', needed_gb: 10, free_gb: 4.2, path: 'C:\\Users\\jan' });
    render(<SetupScreen machine={PC} onDone={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: /GPU support/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('about 10 GB free on C:\\Users\\jan, and 4.2 GB are free');
  });

  it('an unattended install starts without a click', () => {
    shell.install.mockImplementation(() => new Promise(() => undefined));
    render(<SetupScreen machine={MAC} auto="cpu" onDone={() => undefined} />);
    expect(shell.install).toHaveBeenCalledWith('cpu');
    expect(shell.install).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('speaks German', () => {
    renderInGerman(<SetupScreen machine={PC} onDone={() => undefined} />);
    expect(screen.getByRole('heading', { name: 'Willkommen bei DinoTraining' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nur CPU/ })).toBeInTheDocument();
    // Numbers in German, too.
    expect(screen.getByRole('button', { name: /etwa 3,5 GB Download/ })).toBeInTheDocument();
  });
});
