/**
 * "Import a dataset" (doc 136): pick a folder or a video, see what was recognised, name and
 * describe it, import it in the background with progress.
 */

import { useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import { detectDataset, startImport, type Detection, type DetectionNote, type ImportJob } from '../api/datasetImport';
import { useImportJob } from '../hooks/useImportJob';
import { useT, type Key } from '../i18n';
import { hasNativeDialog, pickVideoFile } from '../lib/dialog';
import { FolderField } from './FolderField';

/** `uncovered` is counted, and worded with its plural apart from these. */
const NOTE_KEYS: Readonly<Record<Exclude<DetectionNote, 'uncovered'>, Key>> = {
  'ambiguous-convention': 'models.import.note.ambiguous',
  'no-annotations': 'models.import.note.noAnnotations',
  'video-frames': 'models.import.note.video',
  'export-pictures-missing': 'models.import.note.exportPictures',
};

/** "boxes, masks" in the reader's language. */
export function annotationTypes(types: readonly string[], t: (key: Key) => string): string {
  return types.map((type) => (type === 'boxes' ? t('models.profile.type.boxes') : type === 'masks' ? t('models.profile.type.masks') : type)).join(', ');
}

const KIND_KEYS: Readonly<Record<Detection['kind'], Key>> = {
  images: 'models.import.kind.images',
  video: 'models.import.kind.video',
  coco: 'models.import.kind.coco',
  yolo: 'models.import.kind.yolo',
  voc: 'models.import.kind.voc',
  openlabel: 'models.import.kind.openlabel',
  dinotraining: 'models.import.kind.dinotraining',
};

export function megabytes(bytes: number): string {
  return String(Math.round(bytes / 1_000_000));
}

export function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

export function DatasetImport({ onImported }: { readonly onImported: () => void }): JSX.Element {
  const { t } = useT();
  const [path, setPath] = useState('');
  const [detection, setDetection] = useState<Detection | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Only the user's override is state; the default comes from the detection (CLAUDE.md).
  const [nameOverride, setNameOverride] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [copy, setCopy] = useState(false);
  const [job, setJob] = useState<ImportJob | null>(null);
  const name = nameOverride ?? detection?.name ?? '';

  const choose = (next: string): void => {
    setPath(next);
    setDetection(null);
    setNameOverride(null);
    setJob(null);
    setError(null);
  };

  const detect = async (): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      setDetection(await detectDataset(path));
    } catch (failure) {
      setError(message(failure));
    } finally {
      setBusy(false);
    }
  };

  const start = async (): Promise<void> => {
    setError(null);
    try {
      setJob(await startImport({ path, name, description: description.trim() || null, copy_images: copy }));
    } catch (failure) {
      setError(message(failure));
    }
  };

  useImportJob(job, setJob, onImported, (failure) => setError(message(failure)));

  const running = job?.state === 'running';
  // Doc 142: an export whose pictures are nowhere would only be refused by the backend.
  const picturesMissing = detection?.notes.includes('export-pictures-missing') ?? false;
  return (
    <section className="dsimport" aria-labelledby="dsimport-title">
      <h3 id="dsimport-title" className="dsimport__title">{t('models.import.title')}</h3>
      <p className="dsimport__lead">{t('models.import.lead')}</p>
      <div className="dsimport__pick">
        <FolderField id="dsimport-path" value={path} onChange={choose} placeholder="/Users/you/datasets/osdar23" />
        {hasNativeDialog() && (
          <button type="button" className="btn btn--small" disabled={running}
            onClick={() => void pickVideoFile().then((picked) => picked && choose(picked))}>
            {t('models.import.video')}
          </button>
        )}
        <button type="button" className="btn btn--primary btn--small" disabled={!path.trim() || busy || running}
          onClick={() => void detect()}>
          {busy ? t('models.import.detecting') : t('models.import.detect')}
        </button>
      </div>

      {error && <p className="dsimport__error" role="alert">{error}</p>}
      {detection && <DetectionSummary detection={detection} />}

      {detection && !job && (
        <div className="dsimport__form">
          <label className="dsimport__field">
            {t('models.import.name')}
            <input type="text" value={name} onChange={(event) => setNameOverride(event.target.value)} />
          </label>
          <label className="dsimport__field">
            {t('models.import.description')}
            <textarea rows={2} value={description} placeholder={t('models.import.descriptionHint')}
              onChange={(event) => setDescription(event.target.value)} />
          </label>
          {detection.kind !== 'dinotraining' && (
            <label className="dsimport__check">
              <input type="checkbox" checked={copy} onChange={(event) => setCopy(event.target.checked)} />
              {t('models.import.copy')}
            </label>
          )}
          <button type="button" className="btn btn--primary" disabled={!name.trim() || picturesMissing} onClick={() => void start()}>
            {t('models.import.start')}
          </button>
        </div>
      )}

      {job && <ImportProgress job={job} />}
    </section>
  );
}

function DetectionSummary({ detection }: { readonly detection: Detection }): JSX.Element {
  const { t, tp } = useT();
  const facts = [
    tp('models.import.pictures', detection.pictures),
    detection.annotation_files ? tp('models.import.annotated', detection.annotated_pictures) : t('models.import.noAnnotations'),
    detection.objects ? tp('models.import.objects', detection.objects) : null,
    detection.classes.length ? tp('models.import.classes', detection.classes.length) : null,
    detection.annotation_types.length ? annotationTypes(detection.annotation_types, t) : null,
    detection.splits.length ? t('models.import.splits', { splits: detection.splits.join(', ') }) : null,
    detection.videos ? tp('models.import.videos', detection.videos) : null,
  ].filter((fact): fact is string => fact !== null);
  return (
    <div className="dsimport__found" role="status">
      <p className="dsimport__kind">
        {t('models.import.found')} <strong>{t(KIND_KEYS[detection.kind])}</strong>
      </p>
      <p>{facts.join(' · ')}</p>
      {detection.classes.length > 0 && (
        <p className="dsimport__classes">{detection.classes.slice(0, 30).join(', ')}{detection.classes.length > 30 ? ' …' : ''}</p>
      )}
      {detection.notes.map((note) => (
        <p key={note} className="dsimport__note">
          {note === 'uncovered' ? tp('models.import.note.uncovered', detection.uncovered) : t(NOTE_KEYS[note])}
        </p>
      ))}
    </div>
  );
}

/** An import's (or an example's download's) progress, failure or result. */
export function ImportProgress({ job }: { readonly job: ImportJob }): JSX.Element {
  const { t, tp } = useT();
  if (job.state === 'failed') {
    return <p className="dsimport__error" role="alert">{t('models.import.failed', { error: job.error ?? '' })}</p>;
  }
  if (job.state === 'complete' && job.result) {
    const result = job.result;
    return (
      <div className="dsimport__done" role="status">
        <p>{t('models.import.done', { name: result.name })}</p>
        <p>
          {tp('models.import.pictures', result.pictures)} · {tp('models.import.annotated', result.annotated_pictures)}
          {result.skipped_pictures || result.skipped_objects
            ? ` · ${t('models.import.skipped', { pictures: String(result.skipped_pictures), objects: String(result.skipped_objects) })}`
            : ''}
        </p>
      </div>
    );
  }
  const value = job.total ? Math.round((job.done / job.total) * 100) : 0;
  return (
    <div className="dsimport__progress" role="status">
      <div className="dsimport__bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}>
        <div className="dsimport__fill" style={{ width: `${value}%` }} />
      </div>
      <p>
        {job.phase === 'download'
          ? t('models.example.downloading', { done: megabytes(job.done), total: megabytes(job.total), current: job.current })
          : t('models.import.running', { done: String(job.done), total: String(job.total), current: job.current })}
      </p>
    </div>
  );
}
