/** `phrases` texts (doc 112). English is the source; the current UI text, exactly. */

export const phrasesEn = {
  // The phrase bar (doc 116): an overview; nothing here creates a class
  'phrases.bar.title': 'Phrases',
  'phrases.bar.titleOptional': 'Phrases (optional)',
  'phrases.bar.chipsLabel': 'Classes and umbrella terms, with their outlines',
  'phrases.bar.also': 'Also: {variants}',
  'phrases.bar.noVariations': 'No variations yet',
  'phrases.bar.over': 'Umbrella over {members}',

  // + Umbrella term (doc 115)
  'phrases.umbrella.addLabel': '+ Umbrella term',
  'phrases.umbrella.placeholder': 'screw',
  'phrases.umbrella.classesLabel': 'over the classes',
  'phrases.umbrella.add': 'Add',
  'phrases.umbrella.hint': 'A general name over several classes, e.g. “screw” for m8 and m9. Every outline of those classes answers to it. Write it in English — SAM 3 reads English.',
  'phrases.umbrella.needTwo': 'Tick at least two classes.',
  'phrases.umbrella.noClasses': 'An umbrella term needs two classes. Make classes in the annotation list first.',

  // Manage phrases
  'phrases.manage.title': 'Manage phrases',
  'phrases.manage.variations': 'Variations',
  'phrases.manage.variationsPlaceholder': 'm8 bolt, hex screw m8',
  'phrases.manage.confusable': 'Not to be confused with',
  'phrases.manage.confusablePlaceholder': 'nail, rivet',
  'phrases.manage.save': 'Save',
  'phrases.manage.confusableHint':
    'Names only, and only for things that rarely share a picture with it. SAM 3 is asked for them on complete pictures and learns to find nothing. Something that sits in the same picture (a reflection, a shadow): reject its outline instead — see “How phrases work”.',
  'phrases.manage.delete': 'Delete',
  'phrases.manage.deleteConfirm': 'Really delete “{phrase}”?',
  'phrases.manage.deleteHint': 'Removes the phrase, its links to outlines and its picture checks. The outlines themselves stay, with their class.',
  'phrases.manage.implicit': 'A class’s own phrase: it lasts as long as outlines of class {name} exist.',
  'phrases.manage.umbrella': 'umbrella over {members}',
  'phrases.manage.legacy': 'Older sub-phrase of class {name}, linked to single outlines. It still trains; a new sub-kind is made as a class of its own.',

  // Picture checks — folded (doc 116)
  'phrases.checks.section': 'Only for imported or partly annotated datasets',
  'phrases.checks.intro': 'A picture you save counts as complete for the classes it has then. Check by hand only where that is not true — for example a dataset imported with some classes left out.',
  'phrases.checks.caption': 'This picture',
  'phrases.checks.complete': 'all marked',
  'phrases.checks.absent': 'not in this picture',
  'phrases.checks.unchecked': 'not checked',
  'phrases.checks.markComplete': 'All marked',
  'phrases.checks.markAbsent': 'Not in this picture',
  'phrases.checks.clear': 'clear',
  'phrases.checks.clearLabel': 'Clear the check for {phrase}',
  'phrases.checks.keys': 'Keys while this is open: 1–9 pick a phrase · A all marked · N not in this picture.',
  'phrases.checks.markRest': 'Mark the rest',
  'phrases.checks.markRestFor': 'Mark the rest for',
  'phrases.checks.markRestHint':
    "Only if every picture is fully annotated for this phrase: each unchecked picture becomes 'all marked' where it has an outline of it, 'not in this picture' where it has none.",
  'phrases.checks.marked': 'Marked {complete} all marked, {absent} not in this picture.',

  // How phrases work — *emphasis* and `code` are rendered as such.
  'phrases.help.title': 'How phrases work',
  'phrases.help.classesTerm': 'Classes are phrases',
  'phrases.help.classesText':
    'SAM 3 is asked by name: every class name is a phrase, and its outlines are the answer. Make classes in the annotation list below — for sub-kinds too, e.g. *m8* and *m9* rather than one class “screw”. A picture you save counts as complete for the classes it has then.',
  'phrases.help.umbrellaTerm': 'Umbrella terms',
  'phrases.help.umbrellaText':
    'A general name over several classes: *screw* over *m8* and *m9*. SAM 3 learns both levels from the same outlines — “screw” finds every m8 and m9, “m8” only the m8. Boxes and heads keep learning m8 and m9.',
  'phrases.help.variationsTerm': 'Variations',
  'phrases.help.variationsText':
    'Other wordings of one class — technical vocabulary, 2–4 are enough, separated by commas, in English. The model learns them as one concept and generalises from there.',
  'phrases.help.lookalikesTerm': 'Look-alikes',
  'phrases.help.lookalikesText':
    '*Not to be confused with* names things that look similar but rarely share a picture with the class: a *nail* for a screw. SAM 3 is asked for them and learns to find nothing, which sharpens the boundary. Something wrong *in the same picture* (a reflection proposed as a flame) is rejected (✗) instead: the saved outlines are then the whole answer. If the look-alike should be found too, make it a class.',
  'phrases.help.negativesTerm': 'Hard negatives',
  'phrases.help.negativesText':
    'Training also asks for unrelated everyday phrases (generic negatives, `num_negatives`) and for your other classes on pictures without them (cross negatives, `num_cross_negatives`) — see SAM 3’s training settings.',

  // The annotation guideline
  'phrases.guideline.loading': 'Loading the guideline…',
  'phrases.guideline.saved': 'Saved.',
  'phrases.guideline.title': 'Annotation guideline',
  'phrases.guideline.noneYet': ' (none yet)',
  'phrases.guideline.hint':
    'Write down the conventions, so every picture is annotated the same way: what counts as part of an object, when to mark it unclear, which name is right.',
  'phrases.guideline.placeholder': 'Rings: outline with the hole filled.\nMore than half hidden: unclear.',
  'phrases.guideline.save': 'Save guideline',

  // Second look
  'phrases.secondLook.title': 'Second look',
  'phrases.secondLook.nothingYet': 'Nothing judged yet.',
  'phrases.secondLook.figure': '{changed} of {reviewed} needed a change ({percent} %)',
  'phrases.secondLook.judged': '{reviewed} of {total} judged',
  'phrases.secondLook.right': 'Looks right',
  'phrases.secondLook.changed': 'Needed a change',
  'phrases.secondLook.end': 'End second look',
  'phrases.secondLook.startHint': 'Show a random 5 % of the annotated pictures again, to judge them fresh',
  'phrases.secondLook.lastTime': 'Last time: {figure}',
} as const;
