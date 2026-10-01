import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CloudConnection, CloudFields, CloudTestResult } from '../api/cloud';
import { renderInGerman } from '../i18n/testing';

const api = vi.hoisted(() => ({
  list: vi.fn<() => Promise<CloudConnection[]>>(),
  save: vi.fn<(fields: CloudFields, secrets: Record<string, string>, id: string | null) => Promise<CloudConnection>>(),
  remove: vi.fn<(id: string) => Promise<void>>(),
  test: vi.fn<(id: string, bucket: string) => Promise<CloudTestResult>>(),
}));
vi.mock('../api/cloud', async (original) => ({
  ...(await original<typeof import('../api/cloud')>()),
  listConnections: api.list,
  saveConnection: api.save,
  deleteConnection: api.remove,
  testConnection: api.test,
}));

import { CloudConnections } from './CloudConnections';

const MINIO: CloudConnection = {
  id: 'c1', name: 'Lab MinIO', kind: 's3', endpoint: 'http://minio.lab:9000', region: 'us-east-1', account: null,
  created_at: '2026-10-01T12:00:00+00:00', secrets_set: ['access_key', 'secret_key'],
};

beforeEach(() => {
  api.list.mockReset().mockResolvedValue([MINIO]);
  api.save.mockReset().mockResolvedValue(MINIO);
  api.remove.mockReset().mockResolvedValue(undefined);
  api.test.mockReset();
});

function open(): void {
  fireEvent.click(screen.getByText(/^Cloud storage/));
}

describe('CloudConnections (doc 147)', () => {
  it('lists a connection with its kind and where it is, saying the secret is set but never showing it', async () => {
    render(<CloudConnections />);
    open();
    expect(await screen.findByText('Lab MinIO')).toBeInTheDocument();
    expect(screen.getByText('S3-compatible · http://minio.lab:9000 · Secret saved')).toBeInTheDocument();
  });

  it('tests against a bucket and says what happened', async () => {
    api.test.mockResolvedValue({ ok: false, message: 'The credentials were refused for photos.' });
    render(<CloudConnections />);
    open();
    fireEvent.click(await screen.findByRole('button', { name: 'Test' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Bucket or container' }), { target: { value: 'photos' } });
    fireEvent.click(screen.getByRole('button', { name: 'Test the connection' }));
    expect(await screen.findByText('The credentials were refused for photos.')).toBeInTheDocument();
    expect(api.test).toHaveBeenCalledWith('c1', 'photos');
  });

  it('adds an Azure connection with only Azure fields, and a GCS key from a file', async () => {
    api.list.mockResolvedValue([]);
    render(<CloudConnections />);
    open();
    fireEvent.click(await screen.findByRole('button', { name: 'Add a connection' }));
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind' }), { target: { value: 'azure' } });
    expect(screen.queryByText('Region')).toBeNull();
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Team blobs' } });
    fireEvent.change(screen.getByRole('textbox', { name: 'Storage account name' }), { target: { value: 'teamstore' } });
    fireEvent.change(screen.getByLabelText('Account key'), { target: { value: 'k3y' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(api.save).toHaveBeenCalledWith(
        { name: 'Team blobs', kind: 'azure', endpoint: null, region: null, account: 'teamstore' },
        { account_key: 'k3y' },
        null,
      ),
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Add a connection' }));
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind' }), { target: { value: 'gcs' } });
    const key = new File(['{"type": "service_account"}'], 'key.json', { type: 'application/json' });
    fireEvent.change(screen.getByLabelText('Choose the key file…'), { target: { files: [key] } });
    await waitFor(() => expect(screen.getByRole('textbox', { name: /Service account key/ })).toHaveValue('{"type": "service_account"}'));
  });

  it('edits without showing the saved secret, and deletes in two clicks, in German', async () => {
    renderInGerman(<CloudConnections />);
    fireEvent.click(screen.getByText(/^Cloud-Speicher/));
    fireEvent.click(await screen.findByRole('button', { name: 'Bearbeiten' }));
    expect(screen.getByLabelText('Secret Access Key')).toHaveValue('');
    expect(screen.getByLabelText('Secret Access Key')).toHaveAttribute('placeholder', 'Gespeichert; leer lassen, um es zu behalten');
    expect(screen.getByRole('combobox', { name: 'Art' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Lab MinIO und seine Secrets löschen' }));
    await waitFor(() => expect(api.remove).toHaveBeenCalledWith('c1'));
  });
});
