/** `studio` texts, second half (doc 112): prescan, outline tools, pickers, sources. */

export const studio2En = {
  // Prescan (doc 53)
  'studio.prescan.open': 'Skip the empty images…',
  'studio.prescan.aria': 'Prescan',
  'studio.prescan.lead_one':
    'Run the model over all {count} image first, then show only the ones it found something in. Nothing is saved — this only decides what you see.',
  'studio.prescan.lead_other':
    'Run the model over all {count} images first, then show only the ones it found something in. Nothing is saved — this only decides what you see.',
  'studio.prescan.lookingFor': 'Looking for',
  'studio.prescan.hint': 'Comma-separated. Leave empty to keep every image the model finds anything in.',
  'studio.prescan.confidence': 'Confidence',
  'studio.prescan.progress_one': '{scanned} of {total} · {count} match so far',
  'studio.prescan.progress_other': '{scanned} of {total} · {count} matches so far',
  'studio.prescan.stop': 'Stop, keep what it found',
  'studio.prescan.starting': 'Starting…',
  'studio.prescan.scan_one': 'Scan {count} image',
  'studio.prescan.scan_other': 'Scan {count} images',
  'studio.prescan.ofTotal': '{hits} of {total}',
  'studio.prescan.matched_one': 'image matched',
  'studio.prescan.matched_other': 'images matched',
  'studio.prescan.cancelled': 'before you stopped it',
  'studio.prescan.unreadable_one': 'could not be read',
  'studio.prescan.unreadable_other': 'could not be read',
  'studio.prescan.failed': 'the scan failed: {message}',
  'studio.prescan.showOnly_one': 'Show only the {count} match',
  'studio.prescan.showOnly_other': 'Show only the {count} matches',
  'studio.prescan.nothingToShow': 'nothing to show',
  'studio.prescan.startError': 'Could not start the scan.',
  'studio.prescan.stopError': 'Could not stop the scan.',

  // The outline tools (doc 106)
  'studio.mask.toolbar': 'Outline tools',
  'studio.mask.tool': 'Tool',
  'studio.mask.select': 'Select',
  'studio.mask.selectHint': 'Draw and pick boxes as usual',
  'studio.mask.add': '⊕ Add',
  'studio.mask.addHint': 'Click what belongs to the outline; SAM redraws it',
  'studio.mask.remove': '⊖ Remove',
  'studio.mask.removeHint': 'Click what does not belong; SAM redraws it',
  'studio.mask.brush': 'Brush',
  'studio.mask.brushHint': 'Drag to paint pixels in',
  'studio.mask.erase': 'Eraser',
  'studio.mask.eraseHint': 'Drag to take pixels out',
  'studio.mask.size': 'Size',
  'studio.mask.undo': 'Undo',
  'studio.mask.fromBoxes': 'Outlines from my boxes',
  'studio.mask.working': 'Working…',
  'studio.mask.selectFirst': 'Select a box or outline to edit it.',
  'studio.mask.clicks_one': '{count} click on this outline — each one redraws it.',
  'studio.mask.clicks_other': '{count} clicks on this outline — each one redraws it.',
  'studio.mask.noOutline': 'This box has no outline yet: ⊕ Add makes one.',
  'studio.mask.outlineFirst': 'Make an outline first: click ⊕ on the object.',

  // What proposes the boxes
  'studio.mode.legend': 'What proposes the boxes',
  'studio.mode.foundation': 'A general detector — finds everyday objects, nothing to set up',
  'studio.mode.prompt': 'Grounding DINO — describe what you are looking for',
  'studio.mode.head': 'A head you trained — proposes boxes for its own classes',
  'studio.foundation.legend': 'Detector',
  'studio.foundation.loading': 'Loading detectors…',
  'studio.foundation.none': 'No foundation model in the catalogue proposes boxes.',
  'studio.foundation.notDownloaded_one': '{count} general detector is available but not downloaded. Get one in',
  'studio.foundation.notDownloaded_other': '{count} general detectors are available but not downloaded. Get one in',
  'studio.foundation.adminModels': 'Admin / Models',
  'studio.foundation.noTraining': '— RF-DETR needs no training and no prompt.',
  'studio.foundation.nonCommercial': 'non-commercial',
  'studio.foundation.whatToFind': 'What to find',
  'studio.foundation.conceptHint': '{model} finds only what you name here. Separate several with full stops.',
  'studio.expert.legend': 'Expert head',
  'studio.expert.loading': 'Loading heads…',
  'studio.expert.none':
    'No installed head can propose boxes. Classification, segmentation and depth heads run in the Inference Viewer; only a detection head proposes boxes — train one in Training.',
  'studio.expert.incompatible_one': '{count} detection head installed, but none was trained on',
  'studio.expert.incompatible_other': '{count} detection heads installed, but none was trained on',
  'studio.expert.switch': '. Switch backbone, or train a head on this one.',

  // Prompt guidance (doc 39)
  'studio.guidance.groundingDino':
    'Grounding DINO reads each phrase between full stops as a separate thing to look for. One label type: “a bolt”. Several: “a bolt. a nut. a washer.” Lower case, a leading “a”, and a full stop after each — that is the form it was trained on. It will also find things you did not ask for, which is what the reject key is for.',
  'studio.guidance.headNone':
    'No prompt here: a trained head already knows what it is looking for. It proposes its own classes, and you accept, reject or correct them.',
  'studio.guidance.andMore': '{list} and {count} more',
  'studio.guidance.head':
    'No prompt here: this head was trained to find {classes}. It proposes those and nothing else — prompting is for models that take words, and this one takes an image.',

  // Where the images come from
  'studio.source.legend': 'Images from',
  'studio.source.folder': 'A folder',
  'studio.source.dataset': 'A dataset you already have',
  'studio.source.noneWithImages': 'none with images yet',
  'studio.source.video': 'A video file',
  'studio.picker.drop': 'Drop to load it',
  'studio.picker.label': 'Image or folder',
  'studio.picker.image': 'Image…',
  'studio.picker.folder': 'Folder…',
  'studio.picker.load': 'Load',
  'studio.picker.orDataset': '…or a dataset you already have',
  'studio.picker.none': 'None',
  'studio.picker.dragHint': 'Or drag an image or a folder onto this window.',
  'studio.folder.drop': 'Drop to use that folder',
  'studio.folder.label': 'Image folder',
  'studio.folder.hint':
    'Pick an image and its folder is used. You can also drag a folder — or any image inside it — onto this window.',

  // A video source (doc 73)
  'studio.video.probeError': 'That video could not be opened.',
  'studio.video.file': 'Video file',
  'studio.video.pick': 'Video…',
  'studio.video.notVideo': 'Not a video this app can decode — use .mp4, .mov, .avi, .mkv, .webm or .m4v.',
  'studio.video.frames': '{frames} frames',
  'studio.video.fps': 'at {fps} fps',
  'studio.video.pastEnd': 'That range is past the end of the video.',
  'studio.video.decodes': 'Decodes {frames} frames into the dataset — about {mb} MB (estimate).',
  'studio.video.from': 'From frame',
  'studio.video.count': 'Frames',
  'studio.video.every': 'Every',
  'studio.video.everyAria': 'Keep every Nth frame',
  'studio.video.th': 'th',

  // Concept segmenters (doc 65)
  'studio.readiness.title': 'Concept segmentation — type what you want, get masks',
  'studio.readiness.before': 'These are',
  'studio.readiness.pipelines': 'pipelines',
  'studio.readiness.after':
    ', not single models, which is why they are not in the list above under their own names. Each needs every one of its parts.',
  'studio.readiness.ready': 'Ready',
  'studio.readiness.notInstalled': 'Not installed',
  'studio.readiness.gated': 'needs your token',
  'studio.readiness.and': 'and',
  'studio.readiness.install': 'Install {models} above.',
  'studio.readiness.installAccess':
    'Install {models} above, after requesting access on HuggingFace — approved by hand, so it is not instant.',

  // Open the dataset's folder (doc 59)
  'studio.reveal.gone': 'That folder is gone: {folder}',
  'studio.reveal.error': 'Could not open that folder.',
  'studio.reveal.title': "Show this dataset's images in the file manager",
  'studio.reveal.opening': 'Opening…',
  'studio.reveal.open': 'Open folder',
} as const;
