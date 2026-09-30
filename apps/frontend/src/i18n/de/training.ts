import type { trainingEn } from '../en/training';
import type { Catalogue } from '../types';

export const trainingDe: Catalogue<typeof trainingEn> = {
  // The tab and its two modes
  'training.tab.title': 'Training',
  'training.mode.legend': 'Was trainieren?',
  'training.mode.head.name': 'DINO-Head',
  'training.mode.head.hint':
    'Eingefrorenes Backbone, trainiert in wenigen Minuten. Am besten für Klassifikation und Segmentierung.',
  'training.mode.finetune.name': 'Ein Modell fine-tunen',
  'training.mode.finetune.hint':
    'Passt ein ganzes Modell an — einen Detektor, SAM oder ein DINO-Backbone. Langsamer, oft deutlich stärker.',
  'training.tab.loadingOptions': 'Optionen werden geladen …',
  'training.tab.finetuneIntro':
    'Passt ein ganzes Basismodell an deine Daten an — einen Detektor, SAM oder ein DINO-Backbone —, statt nur einen kleinen Head auf einem eingefrorenen Backbone zu trainieren. Langsamer und oft deutlich stärker: Bei Blutzellen mit einer Aufteilung ohne Überschneidungen erreichte RF-DETR 0,62 Test-mAP, ein DINO-Head nur 0,41. Jeder Lauf wird mit dem Modell verglichen, von dem er ausging.',
  'training.tab.headIntro':
    'Das Backbone bleibt eingefroren — nur der Head (ein kleines Modell auf dem Backbone) wird trainiert. Die Vorverarbeitung wählen wir passend zu Backbone und Head-Typ für dich.',
  'training.tab.modelMissing': 'Wähle zuerst ein Backbone und einen Head-Typ.',
  'training.tab.trainedHeads': 'Trainierte Heads',

  // The head form
  'training.form.noBackbone': 'Kein Backbone installiert — lade zuerst eins unter Verwaltung / Modelle herunter.',
  'training.form.chooseBackbone': 'Wähle ein Backbone.',
  'training.form.chooseDataset': 'Wähle mindestens einen Datensatz.',
  'training.form.chooseHeadType': 'Wähle einen Head-Typ.',
  'training.form.notTrainable':
    '{title} lässt sich hier nicht trainieren — nutze seine vortrainierte Standardversion für Vorhersagen.',
  'training.form.incompatible': 'Dieser Head-Typ passt nicht zu diesem Backbone.',
  'training.form.datasets': 'Datensätze',
  'training.form.noDatasets': 'Noch keine Datensätze — annotiere zuerst ein paar Bilder im Annotation Studio.',
  'training.form.images_one': '({count} Bild)',
  'training.form.images_other': '({count} Bilder)',
  'training.form.backbone': 'Backbone',
  'training.form.selectBackbone': 'Backbone auswählen …',
  'training.form.headType': 'Head-Typ',
  'training.form.inferenceOnly':
    'Über seine vortrainierte Standardversion für Vorhersagen nutzbar — hier nicht trainierbar.',
  'training.form.starting': 'Startet …',
  'training.form.start': 'Training starten',

  // Live progress
  'training.progress.state.pending': 'In der Warteschlange',
  'training.progress.state.running': 'Trainiert',
  'training.progress.state.complete': 'Fertig',
  'training.progress.state.failed': 'Fehlgeschlagen',
  'training.progress.state.cancelled': 'Abgebrochen',
  'training.progress.epoch': '· Durchgang {epoch}/{total}',
  'training.progress.testLabel': 'Auf den Testbildern:',
  'training.progress.testNote':
    '{scores} — der ehrliche Wert: Diese Bilder wurden weder zum Trainieren noch zur Wahl des besten Durchgangs benutzt.',
  'training.progress.skipped_one':
    '{count} Bild übersprungen — seine Boxen nennen mehr als eine Klasse, damit kann Klassifikation nichts anfangen.',
  'training.progress.skipped_other':
    '{count} Bilder übersprungen — ihre Boxen nennen mehr als eine Klasse, damit kann Klassifikation nichts anfangen.',
  'training.progress.classes': 'Klassen:',
  'training.progress.bestCriterion': '(Kriterium für das beste Modell)',
  'training.progress.caption': 'Verlust und Metriken pro Durchgang',
  'training.progress.epochHeader': 'Durchgang',
  'training.progress.trainLoss': 'Trainingsverlust',
  'training.progress.valLoss': 'Validierungsverlust',
  'training.progress.saved': 'Als Head gespeichert — du kannst ihn jetzt in der Modell-Ansicht verwenden.',

  // Recipes
  'training.recipe.label': 'Vorbereitungs-Rezept',
  'training.recipe.none': 'Keins — mit den Daten trainieren, wie sie sind',
  'training.recipe.outOfDate': '(veraltet)',
  'training.recipe.uses':
    'Nutzt die Aufteilung, Klassenänderungen, Kacheln, den Umgang mit ungleichen Klassen ({imbalance}) und die veränderten Kopien ({augmentation}) des Rezepts.',
  'training.recipe.missing':
    'Kein Rezept: Die Bilder werden zufällig aufgeteilt, sodass fast gleiche Bilder auf beiden Seiten landen können und der Wert besser aussieht, als das Modell ist. Im Tab „Daten vorbereiten“ entsteht ein Rezept.',
  'training.explainer.title': 'Was ist ein Rezept?',
  'training.explainer.required': 'Dieses Modell braucht eins.',
  'training.explainer.whatBefore': 'Ein Rezept ist die gespeicherte Vorbereitung',
  'training.explainer.whatStrong': 'eines Datensatzes für ein Modell',
  'training.explainer.whatAfter':
    ': welche Bilder trainieren, welche den besten Durchgang auswählen und welche den endgültigen Wert liefern — so aufgeteilt, dass fast gleiche Bilder zusammenbleiben — dazu Korrekturen an Klassen, die Eingabegröße und Kacheln, der Umgang mit ungleichen Klassen und veränderte Kopien.',
  'training.explainer.whyBefore':
    'Ohne Rezept werden die Bilder zufällig aufgeteilt, sodass fast gleiche Bilder auf beiden Seiten landen können und der Wert besser aussieht, als das Modell ist. Rezepte entstehen Schritt für Schritt unter',
  'training.explainer.whyStrong': 'Daten vorbereiten',
  'training.explainer.whyAfter':
    '; das Standard-Rezept übernimmt dort alle Empfehlungen für dich und lässt sich später verfeinern.',
  'training.explainer.making': 'Standard-Rezept wird erstellt …',
  'training.explainer.create': 'Standard-Rezept erstellen',
  'training.explainer.openPrepare': 'Daten vorbereiten öffnen',
  'training.explainer.starting': 'Startet …',
  'training.explainer.failed': 'Das Standard-Rezept konnte nicht erstellt werden.',

  // Trained heads
  'training.heads.empty': 'Noch keine trainierten Heads. Starte oben einen Lauf.',
  'training.heads.backbone': 'Backbone {id}',
  'training.heads.bestEpoch': 'bester Durchgang {epoch}',
  'training.heads.ofTotal': 'von {total}',
  'training.heads.delete': 'Löschen',
  'training.heads.kind.default': 'Standard',
  'training.heads.kind.community': 'Community-Beitrag',
  'training.heads.kind.trainedHere': 'Hier trainiert',

  // Parameters
  'training.params.about': 'Über {label}',
  'training.params.default': 'Standard: {value}',
  'training.params.defaultSentence': 'Standard: {value}.',
  'training.params.on': 'an',
  'training.params.off': 'aus',
  'training.params.resetOne': '{label} auf {value} zurücksetzen',
  'training.params.backToDefault': 'Zurück zum Standard, {value}',
  'training.params.changed': 'geändert',
  'training.params.setByRecipe': 'Vom Rezept festgelegt',
  'training.params.loadFailed': 'Die Einstellungen konnten nicht geladen werden: {error}',
  'training.params.loading': 'Einstellungen werden geladen …',
  'training.params.legend': 'Trainingseinstellungen · {title}',
  'training.params.advanced': 'Erweiterte Einstellungen',
  'training.params.advancedChanged': 'Erweiterte Einstellungen ({count} geändert)',
  'training.params.resetAll': 'Alle auf Standard zurücksetzen',
  'training.params.enterNumber': 'Gib eine Zahl ein.',
  'training.params.enterWhole': 'Gib eine ganze Zahl ein.',
  'training.params.between': 'Zwischen {low} und {high}.',
  'training.params.any': 'beliebig',

  // Fine-tuning a foundation model
  'training.finetune.kind.boxes': 'Boxen',
  'training.finetune.kind.instanceMasks': 'Umrisse (eine Maske pro Objekt)',
  'training.finetune.kind.phraseMasks': 'Umrisse, benannt durch eine Phrase',
  'training.finetune.kind.imageLabels': 'Eine Klasse pro Bild',
  'training.finetune.needs': 'Was {model} braucht',
  'training.finetune.annotations': 'Annotationen',
  'training.finetune.atLeast': 'Mindestens',
  'training.finetune.minimums': '{images} Bilder, {perClass} pro Klasse',
  'training.finetune.pictures': 'Bilder',
  'training.finetune.recipe': 'Rezept',
  'training.finetune.recipeRequired': 'Nötig (Daten vorbereiten)',
  'training.finetune.recipeRecommended': 'Empfohlen',
  'training.finetune.whatTrains': 'Was trainiert wird:',
  'training.finetune.ready': 'Sind die Daten bereit?',
  'training.finetune.beforeAfter': 'Vorher und nachher',
  'training.finetune.onPictures': 'Auf den Bildern ({heldOut})',
  'training.finetune.onTest': 'Auf den Testbildern',
  'training.finetune.onValidation': 'Auf den Validierungsbildern',
  'training.finetune.onHeldOut': 'Auf den zurückgehaltenen Bildern',
  'training.finetune.before': 'Vorher (Basis)',
  'training.finetune.after': 'Nach dem Fine-Tuning',
  'training.finetune.afterRound': 'Nach dem Fine-Tuning (Durchgang {round})',
  'training.finetune.saved':
    'Gespeichert. Es wird jetzt überall angeboten, wo seine Art von Modell gefragt ist: Wähle es über seinen Namen.',
  'training.finetune.model': 'Modell',
  'training.finetune.dataset': 'Datensatz',
  'training.finetune.notYet': '(noch nicht)',
  'training.finetune.name': 'Name',
  'training.finetune.starting': 'Startet …',
  'training.finetune.start': 'Fine-Tuning starten',
  'training.finetune.round': 'Durchgang {epoch} von {total}',
  'training.finetune.roundBase': 'Durchgang {epoch} von {total} — zuerst wird das Basismodell gemessen',

  // Errors the frontend writes
  'training.error.streamLost': 'Die Verbindung zum Training ist abgerissen. Der Lauf läuft vielleicht noch.',
  'training.error.start': 'Das Training konnte nicht gestartet werden.',
  'training.error.cancel': 'Der Lauf konnte nicht abgebrochen werden.',
  'training.error.options': 'Die Trainingsoptionen konnten nicht geladen werden.',
  'training.error.headTypes': 'Die Head-Typen konnten nicht geladen werden.',
};
