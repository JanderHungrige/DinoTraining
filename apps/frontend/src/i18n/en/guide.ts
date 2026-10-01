/** `guide` texts: how a dataset must look to be imported, and where to find one (doc 137). */

export const guideEn = {
  'guide.layout.title': 'How must a dataset look?',
  'guide.layout.lead':
    'Point the import at the dataset’s own folder. It recognises these layouts; folder names in the trees are examples, file endings are not.',
  'guide.plain.title': 'Without annotations',
  'guide.plain.text':
    'A folder of pictures (JPEG, PNG, BMP, WebP, TIFF, GIF), up to five folder levels deep, or a single video (MP4, MOV, AVI, MKV, WebM, M4V). The pictures are imported for annotating in the app; a video becomes its frames.',
  'guide.coco.title': 'COCO (Roboflow, Hugging Face, CVAT and most tools)',
  'guide.coco.text':
    'One JSON file per split with "images", "annotations" and "categories"; any file name. "file_name" is relative to the JSON’s folder, "bbox" is [x, y, w, h] in pixels, and "segmentation" (polygons or RLE) becomes masks.',
  'guide.yolo.title': 'YOLO (Ultralytics, Roboflow “YOLOv5/v8”)',
  'guide.yolo.text':
    'Pictures under images/, one .txt per picture under labels/ in the same sub-folders. A line is “class cx cy w h”, normalised to 0–1; a longer line is a polygon and becomes a mask. Class names come from data.yaml (names:) or classes.txt. A picture without a .txt has no objects.',
  'guide.voc.title': 'Pascal VOC',
  'guide.voc.text':
    'One XML per picture in Annotations/, with an <object> per box (<name>, <bndbox>), and the pictures in JPEGImages/ (or beside the XML).',
  'guide.openlabel.title': 'OpenLABEL (OSDaR23)',
  'guide.openlabel.text':
    'A sequence folder with its *_labels.json and one folder per sensor. The pictures of every camera are imported, lidar and radar are ignored, and “track” polylines are left out because a box around a rail to the horizon teaches nothing.',
  'guide.splits':
    'Splits: a folder named train, val (or valid) or test anywhere on the way becomes the split; without one, the app makes a split later in Prepare data.',
  'guide.sites.title': 'Where to find datasets',
  'guide.sites.lead': 'Download in one of the formats above, unpack, and import the folder.',
  'guide.sites.hf': 'Many vision sets; filter by “object detection” or “image segmentation”.',
  'guide.sites.roboflow': 'Community-annotated sets; export as “COCO JSON” or “YOLOv8”.',
  'guide.sites.kaggle': 'Competition and community sets, in the format their authors chose.',
  'guide.sites.openimages': 'Google’s large set with boxes and masks; its CSV needs converting to COCO first.',
  'guide.sites.coco': 'The reference set, 80 everyday classes with boxes and masks.',
  'guide.sites.osdar':
    'Deutsche Bahn’s (Digitale Schiene Deutschland) multi-sensor set from railway lines in Hamburg, with cameras, lidar and radar, in OpenLABEL; imported directly.',
  'guide.sites.osdarData': 'the data portal',
  'guide.sites.licence':
    'Every dataset has its own licence. Check it before training on a dataset, or before sharing a model trained on it.',
} as const;
