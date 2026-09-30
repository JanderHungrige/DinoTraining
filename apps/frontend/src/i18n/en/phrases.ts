/** `phrases` texts (doc 112). English is the source; the current UI text, exactly. */

export const phrasesEn = {
  // The phrase bar
  'phrases.bar.title': 'Phrases',
  'phrases.bar.titleOptional': 'Phrases (optional)',
  'phrases.bar.chipsLabel': 'Phrases — keys 1–9 pick one',
  'phrases.bar.also': 'Also: {variants}',
  'phrases.bar.noVariations': 'No variations yet',
  'phrases.bar.addLabel': '+ phrase',
  'phrases.bar.addPlaceholder': 'signal, railway signal, light signal',
  'phrases.bar.addButton': 'Add',
  'phrases.bar.addHint': 'Commas separate variations of one phrase.',
  'phrases.bar.classLabel': 'belongs to',
  'phrases.bar.ownClass': 'a class of its own (new)',
  'phrases.bar.ownClassHint': ' It becomes a new class: outlines you link to it train as “{name}”.',
  'phrases.bar.joinsClass': ' It joins class {name}: a more specific way to ask SAM 3 for some of its outlines. Outlines linked to it still train as {name} for boxes and heads.',
  'phrases.bar.keys': 'Keys: 1–9 pick a phrase · A all marked · N not in this picture.',

  // The selected outline's phrases
  'phrases.selected.needsOutline': '#{number}: phrases go on outlines — make one from this box first.',
  'phrases.selected.groupLabel': 'Phrases of outline {number}',
  'phrases.selected.answersTo': '#{number} answers to',
  'phrases.selected.classAlways': 'Its class name is always one of its phrases',
  'phrases.selected.remove': 'Remove {phrase} from outline {number}',
  'phrases.selected.add': 'Add “{phrase}”',
  'phrases.selected.otherClass': '"{phrase}" is a phrase of class {className}; this outline is {outline}.',
  'phrases.selected.unnamed': 'unnamed',

  // This picture's checks
  'phrases.checks.caption': 'This picture',
  'phrases.checks.complete': 'all marked',
  'phrases.checks.absent': 'not in this picture',
  'phrases.checks.unchecked': 'not checked',
  'phrases.checks.markComplete': 'All marked',
  'phrases.checks.markAbsent': 'Not in this picture',
  'phrases.checks.clear': 'clear',
  'phrases.checks.clearLabel': 'Clear the check for {phrase}',

  // Manage phrases
  'phrases.manage.title': 'Manage phrases',
  'phrases.manage.variations': 'Variations',
  'phrases.manage.variationsPlaceholder': 'railway signal, light signal',
  'phrases.manage.confusable': 'Not to be confused with',
  'phrases.manage.confusablePlaceholder': 'street lamp, traffic sign',
  'phrases.manage.save': 'Save',
  'phrases.manage.confusableHint':
    'Names only, and only for things that rarely share a picture with it. SAM 3 is asked for them on pictures marked “all marked” and learns to find nothing. Something that sits in the same picture (a reflection, a shadow): reject its outline instead — see “How phrases work”.',
  'phrases.manage.delete': 'Delete',
  'phrases.manage.deleteConfirm': 'Really delete “{phrase}”?',
  'phrases.manage.deleteHint': 'Removes the phrase, its links to outlines and its picture checks. The outlines themselves stay, with their class.',
  'phrases.manage.implicit': 'A class’s own phrase: it lasts as long as outlines of class {name} exist.',
  'phrases.manage.markRest': 'Mark the rest',
  'phrases.manage.markRestHint':
    "Only if every picture is fully annotated for this phrase: each unchecked picture becomes 'all marked' where it has an outline of it, 'not in this picture' where it has none.",
  'phrases.manage.marked': 'Marked {complete} all marked, {absent} not in this picture.',

  // How phrases work — *emphasis* and `code` are rendered as such.
  'phrases.help.title': 'How phrases work',
  'phrases.help.variationsTerm': 'Phrase variations',
  'phrases.help.variationsText':
    'Type the phrase the way you would ask for it, plus 2–4 other wordings, separated by commas. The model learns them as one concept. You do not need every synonym: a few teach it that the wording can vary, and it generalises from there.',
  'phrases.help.checksTerm': 'All marked · Not in this picture',
  'phrases.help.checksText':
    'SAM 3 learns from every picture you checked. *All marked* says every instance of this phrase here has an outline. *Not in this picture* says there is none, and teaches the model *not* to find it here. Once a phrase is checked on any picture, a picture you did not check is left out for it, never guessed. A phrase never checked keeps the automatic rule — no outline means none here — which is only right if you annotated every instance. If you did, *Mark the rest* under Manage phrases checks all remaining pictures in one step.',
  'phrases.help.classesTerm': 'Phrases and classes',
  'phrases.help.classesText':
    'A *class* is what boxes and heads learn, and every class name is also a phrase. “+ phrase” asks where the new phrase *belongs to*: *a class of its own* makes a new thing to find (it gets its own outlines); an existing class makes a more specific wording for some of that class’s outlines, e.g. “red car” in class car — select an outline and add the phrase to it. Commas give one phrase several wordings, not several phrases.',
  'phrases.help.lookalikesTerm': 'Look-alikes and wrong proposals',
  'phrases.help.lookalikesText':
    '*Two things you both want found* (signal and street light): give each its own class, outline both. Each is then automatically a negative for the other; nothing goes under “not to be confused with”. *A wrong proposal* (a reflection proposed as a flame): reject it (✗), and mark the picture *All marked* for flame. The flame outlines are then the whole answer on that picture, so the model learns the reflection is not one — no new class needed. Add a class “flame reflection” only if you want reflections found too. *Not to be confused with* is for names of things that rarely share a picture with the phrase; it is never asked on a picture where you rejected an outline of the phrase.',
  'phrases.help.negativesTerm': 'Hard negatives',
  'phrases.help.negativesText':
    'Pictures marked *not in this picture* are the strongest lessons, especially when something similar *is* there. Training also adds generic unrelated phrases (generic negatives, `num_negatives`) and other phrases of your dataset (cross negatives, `num_cross_negatives`) — see SAM 3’s training settings.',

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
