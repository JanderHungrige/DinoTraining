/** `prepare` texts (doc 112). English is the source; the current UI text, exactly. */

export const prepareEn = {
  // The tab and its pickers
  'prepare.tab.title': 'Prepare data',
  'prepare.tab.lead':
    'Get a dataset ready for training, step by step. Each step recommends a setting and says why; you can change it, or skip ahead if you know what you need.',
  'prepare.tab.dataset': 'Dataset',
  'prepare.tab.noDatasets': 'No datasets with pictures yet',
  'prepare.tab.datasetOption_one': '{name} ({count} picture)',
  'prepare.tab.datasetOption_other': '{name} ({count} pictures)',
  'prepare.tab.model': 'Model to train',

  // The steps
  'prepare.nav.label': 'Preparation steps',
  'prepare.nav.unused': ' (not used)',
  'prepare.step.audit': 'Check the data',
  'prepare.step.fix': 'Fix what is safe',
  'prepare.step.split': 'Split',
  'prepare.step.input': 'What the model sees',
  'prepare.step.balance': 'Unequal classes',
  'prepare.step.augment': 'Changed copies',
  'prepare.step.save': 'Save the recipe',
  'prepare.unused.balance':
    'Fine-tuning this model does not balance classes: every picture counts once. The recipe still records a choice, used if you train a DINO head with it.',
  'prepare.unused.augment':
    'Fine-tuning this model trains on the pictures as they are: it makes no changed copies. The recipe still records a choice, used if you train a DINO head with it.',
  'prepare.option.recommended': 'recommended',

  // Shared table headings
  'prepare.table.class': 'Class',
  'prepare.table.examples': 'Examples',
  'prepare.table.pictures': 'Pictures',

  // Check the data
  'prepare.audit.why':
    'The audit opens every picture and reads every annotation, and tells you what would make training go wrong — judged for {model}, because what counts as "too small" depends on the model. It changes nothing.',
  'prepare.audit.run': 'Run the audit',
  'prepare.audit.runAgain': 'Run the audit again',
  'prepare.audit.progress': 'Checking every picture… {done} of {total} ({share}%)',
  'prepare.audit.otherModel': 'This audit was made for another model. Run it again to judge the pictures for {model}.',
  'prepare.audit.summary':
    '{images} pictures, {annotations} annotations, {classes} classes · {problems} problem(s), {warnings} to look at{excluded}.',
  'prepare.audit.excluded': ' · {count} left out by a fix',
  'prepare.audit.nothing': 'Nothing to report. The data looks ready.',
  'prepare.audit.failed': 'The audit failed.',

  // One finding
  'prepare.finding.problem': 'Problem',
  'prepare.finding.warn': 'Worth fixing',
  'prepare.finding.info': 'Good to know',
  'prepare.finding.ok': 'Fine',
  'prepare.finding.why': 'Why it matters: ',
  'prepare.finding.action': 'What to do: ',
  'prepare.finding.examples': 'Pictures to look at',

  // Fix what is safe
  'prepare.fix.why':
    'These fixes are safe: nothing is deleted, and everything can be undone. Judgement calls — blurry or wrongly labelled pictures — are yours; the audit shows you where to look.',
  'prepare.fix.copies_one': 'Keep one of each copy ({count} group)',
  'prepare.fix.copies_other': 'Keep one of each copy ({count} groups)',
  'prepare.fix.unreadable': 'Leave out unreadable pictures ({count})',
  'prepare.fix.putBack_one': 'Put all {count} left-out picture back',
  'prepare.fix.putBack_other': 'Put all {count} left-out pictures back',
  'prepare.fix.leftOut_one': '{count} picture left out.',
  'prepare.fix.leftOut_other': '{count} pictures left out.',
  'prepare.fix.putBackDone_one': '{count} picture put back.',
  'prepare.fix.putBackDone_other': '{count} pictures put back.',
  'prepare.fix.again': 'Run the audit again to see the effect.',
  'prepare.fix.auditFirst': 'Run the audit first: the fixes act on what it found.',
  'prepare.fix.classesLegend': 'Classes as training will see them',
  'prepare.fix.classesHint':
    "Merge a class into another by giving it the other's name, or leave it out. The stored annotations keep their names, so this can always be changed back.",
  'prepare.fix.trainAs': 'Train as',
  'prepare.fix.leaveOut': 'Leave out',
  'prepare.fix.trainNameAs': 'Train {name} as',
  'prepare.fix.leaveOutName': 'Leave out {name}',
  'prepare.fix.saveClasses': 'Save the class changes',

  // Split
  'prepare.split.why':
    'The model learns from the training pictures and is scored on pictures it has never seen. If a near-copy of a test picture is in training — the next frame of a video, another photo of the same scene — the score measures memory, not learning. So frames and scenes are kept together, and frames right at a boundary are set aside.',
  'prepare.split.auto': 'Split automatically (recommended)',
  'prepare.split.again': 'Split again',
  'prepare.split.keep': 'Keep the split the dataset came with',
  'prepare.split.train': 'Training',
  'prepare.split.val': 'Validation',
  'prepare.split.test': 'Test',
  'prepare.split.buffer':
    '{count} frame(s) beside a boundary are set aside: too close to frames on the other side to be fair either way.',

  // What the model sees
  'prepare.input.why':
    'Every model shrinks a picture to a fixed size before looking at it. Below are your own pictures exactly as this model will get them. If you cannot see an object here, neither can the model.',
  'prepare.input.preparing': 'Preparing the pictures…',
  'prepare.input.sizes':
    '{label}: a typical object is {median} across, the smallest tenth {p10} px. This model needs about {needed} px — {share} are smaller.',
  'prepare.input.whole': 'Whole pictures',
  'prepare.input.onTiles': 'On tiles',
  'prepare.input.tiles': 'Cut into tiles',
  'prepare.input.recommended': 'Recommended',
  'prepare.input.off': 'Off — whole pictures',
  'prepare.input.grid': '{count} tiles along the long side',
  'prepare.input.seenAlt': 'As the model sees {path}',
  'prepare.input.objects_one': '{count} object',
  'prepare.input.objects_other': '{count} objects',
  'prepare.input.tooSmall': ', {count} too small (red)',
  'prepare.input.cutOff': ', {count} cut off',
  'prepare.input.oneTile': ' · one tile',

  // Unequal classes
  'prepare.balance.counting': 'Counting the classes…',
  'prepare.balance.why':
    'A model rewards itself for being right often. When one class is far more common, it can look accurate while mostly ignoring the rare ones — often the ones that matter.',
  'prepare.balance.ratio': 'The largest class has {ratio} the examples of the smallest.',
  'prepare.balance.label': 'How to handle unequal classes',
  'prepare.balance.countsAs': 'Counts as',
  'prepare.balance.perRound': 'Shown per round',
  'prepare.balance.notApplied':
    'Fine-tuning this model does not apply the choice yet; it is saved in the recipe for when it does.',

  // Changed copies
  'prepare.augment.looking': 'Looking at the classes…',
  'prepare.augment.why':
    'Shown the same pictures every round, a model learns those pictures. Changing each one a little — lighting, a crop, a mirror image — teaches it what stays the same: the object. Boxes always move with the picture.',
  'prepare.augment.label': 'How to change the pictures',
  'prepare.augment.noMirroring': 'no mirroring',
  'prepare.augment.originalAlt': 'The original',
  'prepare.augment.changedAlt': 'Changed version {n}',
  'prepare.augment.original': 'Original',
  'prepare.augment.version': 'Version {n}',

  // Save the recipe
  'prepare.save.why':
    'The recipe records everything decided here, so training uses exactly this preparation and a trained model can say how its data was prepared. Saving under the same name makes a new version; nothing is overwritten.',
  'prepare.save.model': 'Model: {model}',
  'prepare.save.tiles': 'Tiles: {tiles}',
  'prepare.save.tilesRecommended': 'as recommended',
  'prepare.save.tilesOff': 'off',
  'prepare.save.tilesGrid': '{count} along the long side',
  'prepare.save.balance': 'Unequal classes: {value}',
  'prepare.save.augment': 'Changed copies: {value}',
  'prepare.save.augmentNone': 'none',
  'prepare.save.strategyNone': 'left as they are',
  'prepare.save.strategyWeighted': 'rare classes count more',
  'prepare.save.strategyBalanced': 'rare classes shown more often',
  'prepare.save.name': 'Recipe name',
  'prepare.save.defaultName': '{dataset} for {model}',
  'prepare.save.button': 'Save the recipe',
  'prepare.save.recipeLine': '— {target}, {train}/{val}/{test} pictures, {imbalance}, {augmentation}',
  'prepare.save.outOfDate': ' Out of date: {reasons}',
  'prepare.save.train': 'Train with {name} · v{version}',
} as const;
