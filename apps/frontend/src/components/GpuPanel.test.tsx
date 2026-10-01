/**
 * The GPU panel (doc 57).
 *
 * The point of the panel is that it appears in **one** state. Everything else it could say
 * is either noise on a machine that has no NVIDIA GPU, or a report of something already
 * working — and a panel that is always there is one nobody reads.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { AcceleratorInfo } from '../api/models';
import type { RuntimeStatus } from '../setup/shell';
import { GpuPanel } from './GpuPanel';

function info(over: Partial<AcceleratorInfo> = {}): AcceleratorInfo {
  return {
    device: 'cpu',
    torch_variant: 'cpu',
    nvidia: [],
    upgrade_available: false,
    driver_error: null,
    summary: 'Running on cpu. No NVIDIA GPU found.',
    ...over,
  };
}

const WITH_GPU = info({
  nvidia: [{ name: 'NVIDIA GeForce RTX 4090', memory_mb: 24564, driver_version: '550.54.14' }],
  upgrade_available: true,
  summary: 'NVIDIA GeForce RTX 4090 found, but this build runs on cpu.',
});

describe('when it says nothing', () => {
  it('is absent before the report arrives', () => {
    const { container } = render(<GpuPanel accelerator={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('is absent on a machine with no NVIDIA GPU', () => {
    // Most machines. A standing "no GPU found" notice is noise.
    const { container } = render(<GpuPanel accelerator={info()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('is absent when the build already uses CUDA', () => {
    const { container } = render(
      <GpuPanel
        accelerator={info({ ...WITH_GPU, torch_variant: 'cuda', upgrade_available: false })}
       
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('is absent on Apple silicon', () => {
    // The macOS wheel is MPS-capable; telling that user they lack acceleration is wrong.
    const { container } = render(
      <GpuPanel accelerator={info({ device: 'mps', torch_variant: 'mps' })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe('when a GPU is present and unusable', () => {
  it('names the hardware', () => {
    render(<GpuPanel accelerator={WITH_GPU} />);
    expect(screen.getByText('NVIDIA GeForce RTX 4090')).toBeInTheDocument();
    expect(screen.getByText(/24 GB/)).toBeInTheDocument();
    expect(screen.getByText(/550\.54\.14/)).toBeInTheDocument();
  });

  it('in a checkout, says how to install the GPU build, with no button', () => {
    // The checkout's environment is the developer's; the app does not exchange it.
    render(<GpuPanel accelerator={WITH_GPU} />);
    expect(screen.getByText(/uv sync --extra cu130/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('lists several GPUs', () => {
    render(
      <GpuPanel
        accelerator={{
          ...WITH_GPU,
          nvidia: [
            { name: 'RTX 4090', memory_mb: 24564, driver_version: '550.1' },
            { name: 'RTX A6000', memory_mb: 49140, driver_version: '550.1' },
          ],
        }}
       
      />,
    );
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });
});

describe('when the driver is broken', () => {
  it('says so rather than reporting no GPU', () => {
    // "Your driver is broken" and "you have no GPU" need different fixes.
    render(
      <GpuPanel
        accelerator={info({
          driver_error: 'could not communicate with the NVIDIA driver',
          summary: 'An NVIDIA driver is installed but did not respond: could not communicate',
        })}
       
      />,
    );
    expect(screen.getByText(/driver not responding/i)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('in the packaged app (doc 128)', () => {
  const PC_MACHINE: RuntimeStatus['machine'] = {
    os: 'windows',
    arch: 'x86_64',
    apple_silicon: false,
    gpu: { name: 'NVIDIA GeForce RTX 4090', driver: '581.15' },
    choices: [
      { variant: 'cu130', download_gb: 3.5, disk_gb: 10 },
      { variant: 'cpu', download_gb: 1, disk_gb: 3 },
    ],
    note: null,
  };

  it('on the CPU, offers the GPU with its size and switches to it', async () => {
    const onSwitch = vi.fn();
    render(<GpuPanel accelerator={WITH_GPU} runtime={{ variant: 'cpu', machine: PC_MACHINE }} onSwitch={onSwitch} />);
    expect(screen.getByText(/a running training or prescan ends/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Use the GPU (CUDA 13.0, about 3.5 GB download)' }));
    expect(onSwitch).toHaveBeenCalledWith('cu130');
  });

  it('on the GPU and using it: one line, and the way back to the CPU', async () => {
    const onSwitch = vi.fn();
    const onCuda = info({ ...WITH_GPU, device: 'cuda', torch_variant: 'cuda', upgrade_available: false });
    render(<GpuPanel accelerator={onCuda} runtime={{ variant: 'cu130', machine: PC_MACHINE }} onSwitch={onSwitch} />);
    expect(screen.getByRole('heading', { name: 'GPU in use: NVIDIA GeForce RTX 4090, CUDA 13.0' })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Back to CPU' }));
    expect(onSwitch).toHaveBeenCalledWith('cpu');
  });

  it('the GPU build installed but the backend on the CPU: warns, with the reason (doc 57 check)', () => {
    render(<GpuPanel accelerator={WITH_GPU} runtime={{ variant: 'cu130', machine: PC_MACHINE }} onSwitch={vi.fn()} />);
    expect(screen.getByRole('heading', { name: /installed but not used/ })).toBeInTheDocument();
    expect(screen.getByText(WITH_GPU.summary)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back to CPU' })).toBeInTheDocument();
  });

  it('a driver too old for CUDA: the reason, no button', () => {
    const machine = { ...PC_MACHINE, choices: [PC_MACHINE.choices[1]!], note: { kind: 'driver_too_old' as const, driver: '535.98', needed: 560 } };
    render(<GpuPanel accelerator={WITH_GPU} runtime={{ variant: 'cpu', machine }} onSwitch={vi.fn()} />);
    expect(screen.getByText(/535\.98\) is too old/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('a Mac: nothing (MPS is always included)', () => {
    const mac = { ...PC_MACHINE, os: 'macos', arch: 'aarch64', apple_silicon: true, gpu: null, choices: [PC_MACHINE.choices[1]!] };
    const { container } = render(<GpuPanel accelerator={info({ device: 'mps', torch_variant: 'mps' })} runtime={{ variant: 'cpu', machine: mac }} onSwitch={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
