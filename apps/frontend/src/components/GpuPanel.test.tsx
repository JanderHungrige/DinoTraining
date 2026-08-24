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
    const { container } = render(<GpuPanel accelerator={null} downloadMb={2400} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('is absent on a machine with no NVIDIA GPU', () => {
    // Most machines. A standing "no GPU found" notice is noise.
    const { container } = render(<GpuPanel accelerator={info()} downloadMb={2400} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('is absent when the build already uses CUDA', () => {
    const { container } = render(
      <GpuPanel
        accelerator={info({ ...WITH_GPU, torch_variant: 'cuda', upgrade_available: false })}
        downloadMb={2400}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('is absent on Apple silicon', () => {
    // The macOS wheel is MPS-capable; telling that user they lack acceleration is wrong.
    const { container } = render(
      <GpuPanel accelerator={info({ device: 'mps', torch_variant: 'mps' })} downloadMb={2400} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe('when a GPU is present and unusable', () => {
  it('names the hardware', () => {
    render(<GpuPanel accelerator={WITH_GPU} downloadMb={2400} />);
    expect(screen.getByText('NVIDIA GeForce RTX 4090')).toBeInTheDocument();
    expect(screen.getByText(/24 GB/)).toBeInTheDocument();
    expect(screen.getByText(/550\.54\.14/)).toBeInTheDocument();
  });

  it('says why the installer did not include it', () => {
    // Without this the 2.4 GB reads as the app being bloated rather than as CUDA being big.
    render(<GpuPanel accelerator={WITH_GPU} downloadMb={2400} />);
    expect(screen.getByText(/CUDA runtime, not because the app is/)).toBeInTheDocument();
  });

  it('states the download size before offering it', () => {
    render(<GpuPanel accelerator={WITH_GPU} downloadMb={2400} onDownload={vi.fn()} />);
    expect(screen.getByRole('button', { name: /2\.3 GB/ })).toBeInTheDocument();
  });

  it('offers the download', async () => {
    const onDownload = vi.fn();
    render(<GpuPanel accelerator={WITH_GPU} downloadMb={2400} onDownload={onDownload} />);
    await userEvent.setup().click(screen.getByRole('button'));
    expect(onDownload).toHaveBeenCalled();
  });

  it('shows no button when there is nothing to call', () => {
    // The panel is still worth showing: knowing the GPU is idle matters even before the
    // download exists.
    render(<GpuPanel accelerator={WITH_GPU} downloadMb={2400} />);
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
        downloadMb={2400}
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
        downloadMb={2400}
      />,
    );
    expect(screen.getByText(/driver not responding/i)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
