/**
 * `studio` texts (doc 112). English is the source; the current UI text, exactly.
 * The second half lives in `studio2.ts` (300-line gate) and is merged in here.
 */

import { studio2En } from './studio2';

export const studioEn = {
  ...studio2En,
  // The tab
  'studio.tab.lead':
    'Point at a folder of images and choose what proposes the boxes — describe what you are looking for, or run a head you already trained. Either way you accept, reject or correct what comes back.',
  'studio.tab.changeFolder': 'Change folder',
  'studio.tab.runPrompt': 'Run prompt',
  'studio.tab.runModel': 'Run model',
  'studio.tab.loadingImages': 'Loading images…',
  'studio.tab.loadingImage': 'Loading image…',

  // Session setup
  'studio.setup.errorLoadDatasets': 'Could not load datasets.',
  'studio.setup.errorNoHead': 'No head can propose boxes yet — train a detection head first.',
  'studio.setup.errorNoDetector': 'No general detector is installed — get one in Admin / Models.',
  'studio.setup.errorNoConcept': 'Name what you are looking for — that model finds only what you ask for.',
  'studio.setup.errorNoFolder': 'Choose a folder of images, or a dataset you already have.',
  'studio.setup.errorNoDataset': 'Choose an existing dataset or name a new one.',
  'studio.setup.errorCreate': 'Could not create the dataset.',
  'studio.setup.datasetHint':
    'Its boxes load onto the canvas and your edits replace them — this is how you correct or extend a dataset you already have.',
  'studio.setup.headLegend': 'Annotate with',
  'studio.setup.boxThreshold': 'Box threshold',
  'studio.setup.scoreThreshold': 'Score threshold',
  'studio.setup.start': 'Start annotating',

  // Which dataset
  'studio.choice.dataset': 'Dataset',
  'studio.choice.createNew': 'Create a new one…',
  'studio.choice.option_one': '{name} ({count} image)',
  'studio.choice.option_other': '{name} ({count} images)',
  'studio.choice.newName': 'New dataset name',
  'studio.choice.newNamePlaceholder': 'Cats',

  // Annotation target and its guide (doc 104)
  'studio.target.legend': 'What will this dataset train?',
  'studio.guide.annotatingFor': 'Annotating for:',
  'studio.guide.missing_one': '{count} required still open on this picture',
  'studio.guide.missing_other': '{count} required still open on this picture',
  'studio.guide.needs': 'What this model needs',
  'studio.guide.thisPicture': 'This picture',
  'studio.guide.done': 'done',
  'studio.guide.stillOpen': 'still open',
  'studio.guide.required': 'required',
  'studio.guide.recommended': 'recommended',
  'studio.guide.optional': 'optional',

  // What one picture still lacks (lib/pictureChecklist)
  'studio.check.nothingYet': 'Nothing marked yet',
  'studio.check.oneClass': 'One class: {name}',
  'studio.check.severalClasses': 'Several classes ({names}): a classifier skips this picture',
  'studio.check.objects_one': '{count} object',
  'studio.check.objects_other': '{count} objects',
  'studio.check.allOutlined': 'All {count} have an outline',
  'studio.check.someOutlined': '{done} of {count} have an outline',
  'studio.check.noPhrase': 'No phrase yet',
  'studio.check.noPhrases': 'No phrases in this dataset yet',
  'studio.check.checkedAll_one': 'Checked for all {count} phrase',
  'studio.check.checkedAll_other': 'Checked for all {count} phrases',
  'studio.check.checkedSome_one': 'Checked for {checked} of {count} phrase',
  'studio.check.checkedSome_other': 'Checked for {checked} of {count} phrases',

  // The canvas
  'studio.canvas.boxAria': 'Box {number}{text}, {verdict}{score}. Press 1, 2 or 3 to relabel, Delete to remove.',
  'studio.canvas.score': ', score {percent}%',
  'studio.canvas.hint':
    'Drag on the image to draw a box. Click a box to cycle its label, or use the list beside it. With a box focused:',
  'studio.canvas.keyPositive': 'positive',
  'studio.canvas.keyNegative': 'negative',
  'studio.canvas.keyUnclear': 'unclear',
  'studio.canvas.keyDelete': 'Delete',
  'studio.canvas.keyRemove': 'to remove.',

  // The box review list
  'studio.review.aria': 'Boxes',
  'studio.review.count_one': '{count} box',
  'studio.review.count_other': '{count} boxes',
  'studio.review.belowCutoff': '{count} below cutoff',
  'studio.review.hidden': '{count} hidden',
  'studio.review.showAbove': 'Show above',
  'studio.review.removeBelow': 'Remove {count} below',
  'studio.review.emptyNone': 'No boxes yet. Run a model, or drag on the image to draw one.',
  'studio.review.emptyHidden': 'Every box is hidden. Show them again to review them.',
  'studio.review.emptyCutoff': 'Every box is below the cutoff. Lower it to see them.',
  'studio.review.classOf': 'Class of box {number}',
  'studio.review.true': 'True',
  'studio.review.false': 'False',
  'studio.review.notSure': 'Not sure',
  'studio.review.remove': 'Remove',
  'studio.review.verdictAria': '{verdict}, box {number}',

  // The class picker
  'studio.class.newPlaceholder': 'New class',
  'studio.class.renameAria': 'Rename {from}, {label}',
  'studio.class.newAria': 'New class for {label}',
  'studio.class.rename': 'Rename',
  'studio.class.add': 'Add',
  'studio.class.unnamed': '— unnamed —',
  'studio.class.newOption': 'New class…',
  'studio.class.renameEverywhere': 'Rename {name} on every box in this image',

  // The counters
  'studio.counter.image': 'Image',
  'studio.counter.saved': 'Saved images',
  'studio.counter.masks': 'Masks',
  'studio.counter.positive': 'Positive',
  'studio.counter.negative': 'Negative',
  'studio.counter.unclear': 'Unclear',
  'studio.counter.unsaved': 'Unsaved changes',

  // View bar and actions
  'studio.view.legend': 'Show',
  'studio.view.hide_one': 'Hide the {count} box already here',
  'studio.view.hide_other': 'Hide the {count} boxes already here',
  'studio.view.show_one': 'Show {count} hidden box',
  'studio.view.show_other': 'Show {count} hidden boxes',
  'studio.actions.detecting': 'Detecting…',
  'studio.actions.saving': 'Saving…',
  'studio.actions.previous': '← Previous',
  'studio.actions.next': 'Next →',

  // Errors the session hooks write
  'studio.session.saveError': 'Could not save annotations.',
  'studio.session.headFailed': 'Could not run that head.',
  'studio.session.detectorFailed': 'Could not run that detector.',
  'studio.session.promptFailed': 'Could not run the detector.',
  'studio.images.emptyFolder': 'That folder has no images.',
  'studio.images.emptyDataset': 'That dataset has no images.',
  'studio.images.readFolder': 'Could not read that folder.',
  'studio.images.readDataset': 'Could not read that dataset.',
  'studio.images.readPath': 'Could not read that path.',
  'studio.classes.loadError': 'Could not load classes.',
  'studio.classes.addError': 'Could not add that class.',
  'studio.classes.removeError': 'Could not remove that class.',

  // Phrases on an outline (lib/phraseEdit)
  'studio.phrase.needsOutline': 'Phrases go on outlines — make one from this box first.',
  'studio.phrase.otherClass': '"{phrase}" is a phrase of class {className}; this outline is {name}.',
  'studio.phrase.unnamed': 'unnamed',
} as const;
