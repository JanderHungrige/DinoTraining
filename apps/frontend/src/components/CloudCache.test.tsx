import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CacheState } from '../api/cloud';
import { renderInGerman } from '../i18n/testing';

const api = vi.hoisted(() => ({
  get: vi.fn<() => Promise<CacheState>>(),
  bound: vi.fn<(gb: number) => Promise<CacheState>>(),
  clear: vi.fn<() => Promise<CacheState>>(),
}));
vi.mock('../api/cloud', () => ({ getCache: api.get, setCacheBound: api.bound, clearCache: api.clear }));

import { CloudCache } from './CloudCache';

const USED: CacheState = { bound_gb: 5, used_bytes: 1.5 * 1024 ** 3, datasets: [] };

beforeEach(() => {
  api.get.mockReset().mockResolvedValue(USED);
  api.bound.mockReset().mockImplementation(async (gb) => ({ ...USED, bound_gb: gb }));
  api.clear.mockReset().mockResolvedValue({ ...USED, used_bytes: 0 });
});

describe('CloudCache (doc 149)', () => {
  it('says how much of the bound is used, changes the bound and empties it', async () => {
    render(<CloudCache />);
    expect(await screen.findByText(/1\.5 of 5 GB used by pictures from linked datasets/)).toBeInTheDocument();
    const size = screen.getByRole('spinbutton', { name: 'Size in GB' });
    fireEvent.change(size, { target: { value: '20' } });
    fireEvent.blur(size);
    await waitFor(() => expect(api.bound).toHaveBeenCalledWith(20));
    fireEvent.click(screen.getByRole('button', { name: 'Empty the cache' }));
    expect(await screen.findByText(/^0 of 5 GB used/)).toBeInTheDocument(); // the server's answer
    expect(screen.getByRole('button', { name: 'Empty the cache' })).toBeDisabled();
  });

  it('ignores a size that is not positive, and speaks German', async () => {
    renderInGerman(<CloudCache />);
    const size = await screen.findByRole('spinbutton', { name: 'Größe in GB' });
    expect(screen.getByText(/1,5 von 5 GB belegt/)).toBeInTheDocument();
    fireEvent.change(size, { target: { value: '0' } });
    fireEvent.blur(size);
    expect(api.bound).not.toHaveBeenCalled();
  });
});
