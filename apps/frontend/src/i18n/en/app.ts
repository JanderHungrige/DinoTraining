/** `app` texts (doc 112). English is the source; the current UI text, exactly. */

export const appEn = {
  // The top-level tabs (tabs/tabs.ts).
  'app.tabs.sections': 'DinoTraining sections',
  'app.tabs.introLabel': 'Start here',
  'app.tabs.introHint': 'What this app does, what a backbone and a head are, and what it cannot do yet.',
  'app.tabs.studioLabel': 'Annotation Studio',
  'app.tabs.studioHint': 'Label a folder of images — from a text prompt, or from a head you trained.',
  'app.tabs.prepareLabel': 'Prepare data',
  'app.tabs.prepareHint':
    'Check a dataset, fix it, split it and see it as the model will, then save a recipe.',
  'app.tabs.trainerLabel': 'Training',
  'app.tabs.trainerHint': 'Train a head on a frozen DINO backbone, or fine-tune a whole detector.',
  'app.tabs.inferenceLabel': 'Inference Viewer',
  'app.tabs.inferenceHint': 'Run trained heads and foundation models on one image, side by side.',
  'app.tabs.generatorLabel': 'Dataset Generator',
  'app.tabs.generatorHint':
    'Auto-annotate new images with a trained head or a concept prompt, then review.',
  'app.tabs.inspectLabel': 'Inspect datasets',
  'app.tabs.inspectHint':
    'Play back a dataset — its videos and images — with the annotations it holds.',
  'app.tabs.modelsLabel': 'Models & Datasets',
  'app.tabs.modelsHint': 'Start here: download models, import or open datasets, and find what you have trained.',
  'app.tabs.apiLabel': 'Connection',
  'app.tabs.apiHint': 'Let your own AI assistant drive the app — over MCP, or with a document.',
  'app.stub.arrives': 'Arrives in Wave {wave}.',

  // The backend badge and the API client's own messages.
  'app.addApps.question': 'Add DinoTraining to your Applications folder?',
  'app.addApps.add': 'Add',
  'app.addApps.notNow': 'Not now',
  'app.addApps.added': 'Added: {path}',
  'app.addApps.failed': 'Could not add it: {message}',
  'app.backend.connecting': 'Connecting to backend…',
  'app.backend.unexpected': 'Unexpected error contacting the backend.',
  'app.client.unreachable': 'Cannot reach the DinoTraining backend at {url}. Is the sidecar running?',
  'app.client.malformed':
    'Unexpected response shape from {path}. Backend and frontend contracts have drifted.',

  // Verdicts and annotation views (types/annotation.ts, types/annotationView.ts).
  'app.verdict.positive': 'Positive',
  'app.verdict.negative': 'Negative',
  'app.verdict.unclear': 'Unclear',
  'app.view.masks': 'Segmentation',
  'app.view.boxes': 'Bounding boxes',
  'app.view.both': 'Both',
  'app.output.masks':
    'Saves segmentation masks. The COCO export also carries a bounding box derived from each mask, so you get both.',
  'app.output.boxes': 'Saves bounding boxes.',

  // Admin › Appearance.
  'app.appearance.title': 'Appearance',
  'app.appearance.animated': 'Animated background',
  'app.appearance.reduced':
    'Your system asks for reduced motion, so the background stays still whatever this is set to.',
} as const;
