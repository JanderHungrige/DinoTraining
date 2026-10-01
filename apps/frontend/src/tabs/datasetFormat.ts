/**
 * What a training dataset must look like to be importable (doc 48).
 *
 * Content lives here rather than inside the component for the reason `introContent.ts`
 * gives: it is prose that will be corrected far more often than the markup around it, and
 * a diff that touches only this file is one a non-React reader can check.
 *
 * **Everything here is a claim about `coco_import.py`.** If that file's rules change, this
 * is wrong until it is edited — which is why the tests assert the two constants below
 * against the importer's own values rather than against a copy of them.
 *
 * The prose is catalogue keys (doc 112); `datasetFormat(t)` builds it in a language.
 */

import { ENGLISH, type Key, type Translator } from '../i18n';

/** The filename `find_coco_files` looks for. Mirrors `COCO_FILENAME` in the backend. */
export const COCO_FILENAME = '_annotations.coco.json';

/** How deep the search goes. Mirrors `find_coco_files`, which is deliberately not recursive. */
export const SEARCH_DEPTH = 1;

export interface FormatSection {
  readonly heading: string;
  readonly body: readonly string[];
  /** Rendered as a monospace block under the body, when present. */
  readonly tree?: readonly string[];
}

/** Each section's key stem and how many body paragraphs it has, in reading order. */
const SECTIONS = [
  { id: 'disk', paragraphs: 2 },
  { id: 'file', paragraphs: 3 },
  { id: 'boxes', paragraphs: 3 },
  { id: 'classes', paragraphs: 2 },
  { id: 'carry', paragraphs: 2 },
  { id: 'trouble', paragraphs: 3 },
] as const;

/** Paths, not prose: the same in every language. */
const TREE: readonly string[] = [
  'my-dataset/',
  '  train/',
  `    ${COCO_FILENAME}`,
  '    img-0001.jpg',
  '    img-0002.jpg',
  '  valid/',
  `    ${COCO_FILENAME}`,
  '    img-0100.jpg',
];

export function datasetFormat({ t }: Translator): readonly FormatSection[] {
  return SECTIONS.map(({ id, paragraphs }) => ({
    heading: t(`intro.format.${id}.heading`),
    body: Array.from({ length: paragraphs }, (_, index) =>
      // Checked against the catalogue by the tests, which read every paragraph.
      t(`intro.format.${id}.body${index + 1}` as Key, { file: COCO_FILENAME }),
    ),
    ...(id === 'disk' ? { tree: TREE } : {}),
  }));
}

/** English, for tests and for callers outside the React tree. */
export const DATASET_FORMAT: readonly FormatSection[] = datasetFormat(ENGLISH);
