/** `run` texts (doc 112). English is the source; the current UI text, exactly. */

export const runEn = {
  // The tab
  'run.viewer.title': 'Inference Viewer',
  'run.viewer.lead':
    'Point at a single image or a folder, pick one or more heads, and compare the original against what they predicted.',
  'run.viewer.modeLegend': 'What to look at',
  'run.viewer.modeImageName': 'A single image',
  'run.viewer.modeImageHint': 'One picture, every selected model, side by side.',
  'run.viewer.modeVideoName': 'A video or a folder',
  'run.viewer.modeVideoHint':
    'Analyse a range of frames once, then play it back with the annotations.',
  'run.viewer.emptyFolder': 'No images in that folder.',
  'run.viewer.truncated_one': 'Showing the first {count} image in that folder.',
  'run.viewer.truncated_other': 'Showing the first {count} images in that folder.',
  'run.viewer.pickSource_one': 'Pick an image or a folder above to run the selected head.',
  'run.viewer.pickSource_other': 'Pick an image or a folder above to run the selected heads.',
  'run.viewer.position': '{name} — {index} of {total}',
  'run.viewer.running': 'Running…',
  'run.viewer.selectAndRun': 'Select one or more heads and press Run.',
  'run.viewer.previous': '← Previous',
  'run.viewer.next': 'Next →',

  // Side by side
  'run.compare.result': 'Result',
  'run.compare.original': 'Original',
  'run.compare.ariaLabel': 'Image comparison',
  'run.compare.zoomOut': 'Zoom out',
  'run.compare.zoomIn': 'Zoom in',
  'run.compare.reset': 'Reset',
  'run.compare.hint': 'Drag to pan · arrows and +/− work too',

  // The head panel
  'run.heads.loading': 'Loading heads…',
  'run.heads.nothingToRun':
    'Nothing to run yet. Install a foundation model or a ready-made head in Models & Datasets, or train a head in the Training tab.',
  'run.heads.task': 'Task',
  'run.heads.allTasks': 'All tasks',
  'run.heads.trainedOn': 'Trained on',
  'run.heads.anyDataset': 'Any dataset',
  'run.heads.comparing': 'Comparing {count} heads on {task}',
  'run.heads.legend': 'Heads',
  'run.heads.incompatible': 'Registered for {registered}; the selection is running on {current}.',
  'run.heads.foundations': 'Foundation models',
  'run.heads.nonCommercial': 'non-commercial',
  'run.heads.whatToFind': 'What to find',
  'run.heads.conceptHint':
    'Concept models segment only what you name. Separate several with commas or full stops.',
  'run.heads.runNone': 'Run models',
  'run.heads.run_one': 'Run {count} model',
  'run.heads.run_other': 'Run {count} models',
  'run.heads.running': 'Running…',
  'run.heads.clear': 'Clear',
  'run.heads.conceptMissing':
    'Type what to look for — a concept model segments only what you name.',
  'run.viewer.minScore': 'Show boxes from',
  'run.viewer.noneAbove': 'No box at {threshold} or above. Best guess here: {best}. Lower the threshold to see it.',
  'run.viewer.noneAtAll': 'This model found nothing in this picture.',
  'run.heads.passes_one': '{count} backbone pass',
  'run.heads.passes_other': '{count} backbone passes',
  'run.heads.runFailed': 'Could not run that selection.',
  'run.heads.loadFailed': 'Could not load heads.',

  // Tiling
  'run.tiling.toggle': 'Tile the image',
  'run.tiling.columns': 'Columns',
  'run.tiling.rows': 'Rows',
  'run.tiling.count_one': '{count} tile',
  'run.tiling.count_other': '{count} tiles',
  'run.tiling.hintOn':
    'This head trained on {trained} px images and this one is {image} px. Objects arrive about {factor}× smaller than it learned to find.',
  'run.tiling.hintOff':
    'This head trained on {trained} px images and this one is {image} px. Objects arrive about {factor}× smaller than it learned to find — tiling is probably needed.',

  // The sequence player
  'run.sequence.pickSource': 'Pick a folder of frames or a video file above.',
  'run.sequence.openAsImage': 'Open it as a single image',
  'run.sequence.notSequence':
    'That path is not a sequence. Pick a folder of frames or a video file to play one.',
  'run.player.startAt': 'Start at frame',
  'run.player.howMany': 'How many frames',
  'run.player.playAt': 'Play at (fps)',
  'run.player.kindVideo': 'Video',
  'run.player.kindFolder': 'Folder',
  'run.player.frames_one': '{count} frame',
  'run.player.frames_other': '{count} frames',
  'run.player.analysing': 'analysing {count} of them takes {time}',
  'run.player.estimateNote': '(an estimate)',
  'run.player.estimateMoment': 'a moment',
  'run.player.estimateSeconds': 'about {value} sec',
  'run.player.estimateMinutes': 'about {value} min',
  'run.player.estimateHours': 'about {value} hours',
  'run.player.analysingButton': 'Analysing…',
  'run.player.analyse_one': 'Analyse {count} frame',
  'run.player.analyse_other': 'Analyse {count} frames',
  'run.player.stop': 'Stop',
  'run.player.pickModel': 'Pick at least one head or foundation model above.',
  'run.player.progress': 'Analysed {done} of {total} frames…',
  'run.player.stopped': 'Stopped — {done} of {total} frames analysed',
  'run.player.ready': 'Ready — {done} of {total} frames analysed',
  'run.player.unreadable': '{count} could not be read',
  'run.player.frameLabel': 'Frame {index}',
  'run.player.pause': 'Pause',
  'run.player.play': 'Play',
  'run.player.slider': 'Frame',
  'run.player.counter': 'frame {index}',
  'run.player.notAnalysed': 'not analysed',
  'run.player.startFailed': 'The run could not be started.',

  // Overlays
  'run.overlay.className': 'class {index}',
  'run.overlay.legend': 'Classes found by {head}',
  'run.overlay.segmentation': 'Segmentation from {head}',
  'run.overlay.depth': 'Depth from {head}',
  'run.overlay.stored': 'Stored annotations',
  'run.overlay.unnamed': 'unnamed',

  // Mask review and mask source
  'run.maskReview.aria': '{verdict} mask: {concept}{score}. Press 1, 2 or 3 to change the verdict.',
  'run.maskReview.ariaBare': '{verdict} mask{score}. Press 1, 2 or 3 to change the verdict.',
  'run.maskReview.hint':
    'Click a mask to cycle its verdict, or press 1, 2 or 3 with it focused. Rejecting a mask keeps it as a negative rather than deleting it — the trainer can use that.',
  'run.maskSource.annotator': 'Annotator',
  'run.maskSource.concept': 'Concept',
  'run.maskSource.hintPhrases':
    'Grounding DINO finds each phrase and SAM 2.1 turns it into a mask, so several phrases separated by commas or full stops work well. Nothing here is gated — no token, no account.',
  'run.maskSource.hintSingle':
    'SAM 3 looks for one concept per pass — a short noun phrase like “a bolt”. Separate several with commas or full stops: each is searched on its own and labels its own masks.',
} as const;
