/** The Library and Connection areas in German (doc 112). */

import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as datasets from '../api/datasets';
import * as foundation from '../api/foundation';
import * as heads from '../api/headInstances';
import * as mcpInfo from '../api/mcpInfo';
import { McpPanel } from '../components/McpPanel';
import { LibraryTab } from '../tabs/LibraryTab';
import { renderInGerman } from './testing';

vi.mock('../api/datasets');
vi.mock('../api/foundation');
vi.mock('../api/headInstances');
vi.mock('../api/mcpInfo');

const DATASET = {
  id: 'd1',
  name: 'Chess pieces',
  created_at: '2026-01-01T00:00:00Z',
  counts: { images: 1, positive: 2, negative: 0, unclear: 0 },
} as unknown as datasets.DatasetInfo;

beforeEach(() => {
  vi.mocked(datasets.listDatasets).mockResolvedValue([DATASET]);
  vi.mocked(heads.listHeadInstances).mockResolvedValue([]);
  vi.mocked(foundation.listFoundations).mockResolvedValue([]);
  vi.mocked(mcpInfo.fetchMcpInfo).mockResolvedValue({
    url: 'http://127.0.0.1:8756/mcp',
    command: 'claude mcp add dinotraining',
    tools: [{ name: 'list_datasets', summary: 'List datasets.' }],
  });
});

describe('the admin area in German', () => {
  it('shows the library in German, with German plurals', async () => {
    renderInGerman(<LibraryTab />);
    expect(screen.getByRole('heading', { name: 'Deine Bibliothek' })).toBeInTheDocument();
    expect(await screen.findByText('1 Bild · 2 Boxen')).toBeInTheDocument();
    expect(screen.getByText(/Noch keine Heads/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chess pieces löschen' })).toBeInTheDocument();
  });

  it('explains the MCP connection in German', async () => {
    renderInGerman(<McpPanel />);
    expect(await screen.findByRole('button', { name: 'Befehl kopieren' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Das 1 Tool, das er bekommt' })).toBeInTheDocument();
    expect(screen.getByText('Es funktioniert nur auf diesem Rechner.')).toBeInTheDocument();
  });
});
