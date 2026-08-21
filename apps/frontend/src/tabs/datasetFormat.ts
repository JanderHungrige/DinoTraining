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
 */

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

export const DATASET_FORMAT: readonly FormatSection[] = [
  {
    heading: 'The shape on disk',
    body: [
      `Point the importer at a folder. It looks for a file called ${COCO_FILENAME} in that folder and in each folder directly inside it — one level, not a full walk, so pointing it at your home directory does not enumerate your whole disk.`,
      'Each annotation file sits beside the images it describes. A split per folder is the layout Roboflow and most HuggingFace exports already unpack to, so in practice this needs no rearranging.',
    ],
    tree: [
      'my-dataset/',
      '  train/',
      `    ${COCO_FILENAME}`,
      '    img-0001.jpg',
      '    img-0002.jpg',
      '  valid/',
      `    ${COCO_FILENAME}`,
      '    img-0100.jpg',
    ],
  },
  {
    heading: 'The annotation file',
    body: [
      'Standard COCO detection JSON: an `images` list, an `annotations` list, and a `categories` list. Nothing else is read.',
      'Each image needs `id` and `file_name`. The file name is resolved relative to the folder the annotation file is in, so it must not be an absolute path from whoever exported it.',
      'Each annotation needs `image_id`, `category_id` and `bbox`.',
    ],
  },
  {
    heading: 'Boxes',
    body: [
      '`bbox` is `[x, y, width, height]` in **absolute pixels from the top-left** — plain COCO, not normalised, and not `[x1, y1, x2, y2]`.',
      'That is the same convention this app stores, so boxes are copied rather than converted and there is no transform to get wrong. A YOLO export (normalised centre-x, centre-y, width, height, in one `.txt` per image) is a different format and is not read — convert it first.',
      'A box with zero or negative width or height is skipped, and the import tells you how many it skipped.',
    ],
  },
  {
    heading: 'Classes',
    body: [
      'Class names come from the `categories` list, resolved through each annotation’s `category_id`. **Names, never ids** — so gaps, an unused placeholder, or ids that do not start at zero are all fine.',
      'Do not assume category 0 is a placeholder and delete it. Of the three reference datasets here, two have a placeholder at id 0 and the third’s id 0 is the real class `platelets`. The importer never filters by id for exactly this reason.',
    ],
  },
  {
    heading: 'What the import does not carry',
    body: [
      'Everything imported is marked **positive**, with provenance `imported`. A published dataset asserts that something is present; it has no equivalent of this app’s negative and unclear verdicts, and inventing one would put a judgement in the store that nobody made.',
      'Segmentation masks, keypoints, crowd flags and captions are ignored. This importer reads detection boxes.',
    ],
  },
  {
    heading: 'If it will not import',
    body: [
      `No annotation file found — check the name is exactly ${COCO_FILENAME}, and that it is at most one folder deep from where you pointed.`,
      'Images imported but no boxes — usually `category_id` values that no `categories` entry matches, or `bbox` in the wrong convention.',
      'Fewer images than expected — a `file_name` that does not resolve beside its annotation file. The import reports the count it skipped rather than failing, so check that number.',
    ],
  },
];
