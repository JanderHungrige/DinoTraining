/**
 * The dataset guide (doc 137): how a downloaded dataset must be laid out for the import to
 * read it, per format, and where to find datasets. Two folded sections below the import.
 * The folder trees are not translated (they are file names); the explanations are.
 */

import type { JSX } from 'react';

import { useT, type Key } from '../i18n';

interface Format {
  readonly title: Key;
  readonly text: Key;
  readonly tree: string;
}

const FORMATS: readonly Format[] = [
  {
    title: 'guide.plain.title',
    text: 'guide.plain.text',
    tree: 'my-pictures/\n  day1/0001.jpg\n  day1/0002.jpg\n  day2/0001.png\n\ndrive.mp4',
  },
  {
    title: 'guide.coco.title',
    text: 'guide.coco.text',
    tree: 'my-dataset/\n  train/\n    _annotations.coco.json\n    0001.jpg\n  valid/\n    _annotations.coco.json\n    0101.jpg',
  },
  {
    title: 'guide.yolo.title',
    text: 'guide.yolo.text',
    tree: 'my-dataset/\n  data.yaml\n  images/train/0001.jpg\n  images/val/0101.jpg\n  labels/train/0001.txt\n  labels/val/0101.txt',
  },
  {
    title: 'guide.voc.title',
    text: 'guide.voc.text',
    tree: 'VOC2012/\n  Annotations/0001.xml\n  JPEGImages/0001.jpg',
  },
  {
    title: 'guide.openlabel.title',
    text: 'guide.openlabel.text',
    tree: '1_calibration_1.2/\n  1_calibration_1.2_labels.json\n  rgb_center/012_1631441453.299996000.png\n  rgb_left/…\n  lidar/…',
  },
];

interface Site {
  readonly href: string;
  readonly name: string;
  readonly text: Key;
}

const SITES: readonly Site[] = [
  { href: 'https://huggingface.co/datasets', name: 'Hugging Face', text: 'guide.sites.hf' },
  { href: 'https://universe.roboflow.com', name: 'Roboflow Universe', text: 'guide.sites.roboflow' },
  { href: 'https://www.kaggle.com/datasets', name: 'Kaggle', text: 'guide.sites.kaggle' },
  { href: 'https://storage.googleapis.com/openimages/web/index.html', name: 'Open Images V7', text: 'guide.sites.openimages' },
  { href: 'https://cocodataset.org', name: 'COCO', text: 'guide.sites.coco' },
];

const OSDAR_NEWS = 'https://digitale-schiene-deutschland.de/en/news/2023/OSDaR23-multi-sensor-data-set-for-machine-learning';
const OSDAR_DATA = 'https://data.fid-move.de/dataset/osdar23';

function External({ href, children }: { readonly href: string; readonly children: string }): JSX.Element {
  return <a href={href} target="_blank" rel="noreferrer noopener">{children}</a>;
}

export function DatasetGuide(): JSX.Element {
  const { t } = useT();
  return (
    <div className="dsguide">
      <details className="dsguide__section">
        <summary>{t('guide.layout.title')}</summary>
        <p className="dsguide__lead">{t('guide.layout.lead')}</p>
        {FORMATS.map((format) => (
          <div key={format.title} className="dsguide__format">
            <h4>{t(format.title)}</h4>
            <div className="dsguide__body">
              <p>{t(format.text)}</p>
              <pre className="dsguide__tree" translate="no">{format.tree}</pre>
            </div>
          </div>
        ))}
        <p className="dsguide__lead">{t('guide.splits')}</p>
      </details>
      <details className="dsguide__section">
        <summary>{t('guide.sites.title')}</summary>
        <p className="dsguide__lead">{t('guide.sites.lead')}</p>
        <ul className="dsguide__sites">
          {SITES.map((site) => (
            <li key={site.href}>
              <External href={site.href}>{site.name}</External> — {t(site.text)}
            </li>
          ))}
          <li>
            <External href={OSDAR_NEWS}>OSDaR23</External> — {t('guide.sites.osdar')}{' '}
            (<External href={OSDAR_DATA}>{t('guide.sites.osdarData')}</External>)
          </li>
        </ul>
        <p className="dsguide__lead">{t('guide.sites.licence')}</p>
      </details>
    </div>
  );
}
