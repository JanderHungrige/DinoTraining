import type { studioEn } from '../en/studio';
import type { Catalogue } from '../types';
import { studio2De } from './studio2';

export const studioDe: Catalogue<typeof studioEn> = {
  ...studio2De,
  // The tab
  'studio.tab.lead':
    'Wähle einen Ordner mit Bildern und entscheide, was die Boxen vorschlägt — beschreib, was du suchst, oder lass einen Head laufen, den du schon trainiert hast. So oder so nimmst du an, lehnst ab oder korrigierst, was zurückkommt.',
  'studio.tab.changeFolder': 'Ordner wechseln',
  'studio.tab.runPrompt': 'Prompt ausführen',
  'studio.tab.runModel': 'Modell ausführen',
  'studio.tab.loadingImages': 'Bilder werden geladen …',
  'studio.tab.loadingImage': 'Bild wird geladen …',

  // Session setup
  'studio.setup.errorLoadDatasets': 'Die Datensätze ließen sich nicht laden.',
  'studio.setup.errorNoHead': 'Noch kann kein Head Boxen vorschlagen — trainiere zuerst einen Detektions-Head.',
  'studio.setup.errorNoDetector': 'Es ist kein allgemeiner Detektor installiert — hol dir einen unter Verwaltung / Modelle.',
  'studio.setup.errorNoConcept': 'Nenne, was du suchst — dieses Modell findet nur, wonach du fragst.',
  'studio.setup.errorNoFolder': 'Wähle einen Ordner mit Bildern oder einen Datensatz, den du schon hast.',
  'studio.setup.errorNoDataset': 'Wähle einen vorhandenen Datensatz oder gib einem neuen einen Namen.',
  'studio.setup.errorCreate': 'Der Datensatz ließ sich nicht anlegen.',
  'studio.setup.datasetHint':
    'Seine Boxen werden auf die Arbeitsfläche geladen, und deine Änderungen ersetzen sie — so korrigierst oder erweiterst du einen Datensatz, den du schon hast.',
  'studio.setup.headLegend': 'Annotieren mit',
  'studio.setup.boxThreshold': 'Box-Schwelle',
  'studio.setup.scoreThreshold': 'Konfidenz-Schwelle',
  'studio.setup.start': 'Annotieren starten',

  // Which dataset
  'studio.choice.dataset': 'Datensatz',
  'studio.choice.createNew': 'Neuen anlegen …',
  'studio.choice.option_one': '{name} ({count} Bild)',
  'studio.choice.option_other': '{name} ({count} Bilder)',
  'studio.choice.newName': 'Name des neuen Datensatzes',
  'studio.choice.newNamePlaceholder': 'Katzen',

  // Annotation target and its guide (doc 104)
  'studio.target.legend': 'Was soll dieser Datensatz trainieren?',
  'studio.guide.annotatingFor': 'Annotieren für:',
  'studio.guide.missing_one': '{count} Pflichtpunkt ist auf diesem Bild noch offen',
  'studio.guide.missing_other': '{count} Pflichtpunkte sind auf diesem Bild noch offen',
  'studio.guide.needs': 'Was dieses Modell braucht',
  'studio.guide.thisPicture': 'Dieses Bild',
  'studio.guide.done': 'erledigt',
  'studio.guide.stillOpen': 'noch offen',
  'studio.guide.required': 'Pflicht',
  'studio.guide.recommended': 'empfohlen',
  'studio.guide.optional': 'freiwillig',

  // What one picture still lacks (lib/pictureChecklist)
  'studio.check.nothingYet': 'Noch nichts markiert',
  'studio.check.oneClass': 'Eine Klasse: {name}',
  'studio.check.severalClasses': 'Mehrere Klassen ({names}): ein Klassifikator überspringt dieses Bild',
  'studio.check.objects_one': '{count} Objekt',
  'studio.check.objects_other': '{count} Objekte',
  'studio.check.allOutlined': 'Alle {count} haben einen Umriss',
  'studio.check.someOutlined': '{done} von {count} haben einen Umriss',
  'studio.check.noPhrase': 'Noch keine Phrase',
  'studio.check.noPhrases': 'Noch keine Phrasen in diesem Datensatz',
  'studio.check.checkedAll_one': 'Für {count} Phrase geprüft',
  'studio.check.checkedAll_other': 'Für alle {count} Phrasen geprüft',
  'studio.check.checkedSome_one': 'Für {checked} von {count} Phrase geprüft',
  'studio.check.checkedSome_other': 'Für {checked} von {count} Phrasen geprüft',

  // The canvas
  'studio.canvas.boxAria':
    'Box {number}{text}, {verdict}{score}. Drücke 1, 2 oder 3, um die Bewertung zu ändern, Entf zum Entfernen.',
  'studio.canvas.score': ', Konfidenz {percent} %',
  'studio.canvas.hint':
    'Zieh auf dem Bild, um eine Box zu zeichnen. Klick auf eine Box, um ihre Bewertung weiterzuschalten, oder nutze die Liste daneben. Wenn eine Box ausgewählt ist:',
  'studio.canvas.keyPositive': 'richtig',
  'studio.canvas.keyNegative': 'falsch',
  'studio.canvas.keyUnclear': 'unklar',
  'studio.canvas.keyDelete': 'Entf',
  'studio.canvas.keyRemove': 'zum Entfernen.',

  // The box review list
  'studio.review.aria': 'Boxen',
  'studio.review.count_one': '{count} Box',
  'studio.review.count_other': '{count} Boxen',
  'studio.review.belowCutoff': '{count} unter der Schwelle',
  'studio.review.hidden': '{count} ausgeblendet',
  'studio.review.showAbove': 'Zeigen ab',
  'studio.review.removeBelow': '{count} darunter entfernen',
  'studio.review.emptyNone': 'Noch keine Boxen. Lass ein Modell laufen oder zieh auf dem Bild, um eine zu zeichnen.',
  'studio.review.emptyHidden': 'Alle Boxen sind ausgeblendet. Blende sie wieder ein, um sie zu prüfen.',
  'studio.review.emptyCutoff': 'Alle Boxen liegen unter der Schwelle. Senke sie, um sie zu sehen.',
  'studio.review.classOf': 'Klasse von Box {number}',
  'studio.review.true': 'Richtig',
  'studio.review.false': 'Falsch',
  'studio.review.notSure': 'Unsicher',
  'studio.review.remove': 'Entfernen',
  'studio.review.verdictAria': '{verdict}, Box {number}',

  // The class picker
  'studio.class.newPlaceholder': 'Neue Klasse',
  'studio.class.renameAria': '{from} umbenennen, {label}',
  'studio.class.newAria': 'Neue Klasse für {label}',
  'studio.class.rename': 'Umbenennen',
  'studio.class.add': 'Hinzufügen',
  'studio.class.unnamed': '— ohne Namen —',
  'studio.class.newOption': 'Neue Klasse …',
  'studio.class.renameEverywhere': '{name} auf allen Boxen in diesem Bild umbenennen',

  // The counters
  'studio.counter.image': 'Bild',
  'studio.counter.saved': 'Gespeicherte Bilder',
  'studio.counter.masks': 'Umrisse',
  'studio.counter.positive': 'Richtig',
  'studio.counter.negative': 'Falsch',
  'studio.counter.unclear': 'Unklar',
  'studio.counter.unsaved': 'Ungespeicherte Änderungen',

  // View bar and actions
  'studio.view.legend': 'Anzeigen',
  'studio.view.hide_one': 'Die {count} vorhandene Box ausblenden',
  'studio.view.hide_other': 'Die {count} vorhandenen Boxen ausblenden',
  'studio.view.show_one': '{count} ausgeblendete Box zeigen',
  'studio.view.show_other': '{count} ausgeblendete Boxen zeigen',
  'studio.actions.detecting': 'Erkennung läuft …',
  'studio.actions.saving': 'Speichert …',
  'studio.actions.previous': '← Zurück',
  'studio.actions.next': 'Weiter →',

  // Errors the session hooks write
  'studio.session.saveError': 'Die Annotationen ließen sich nicht speichern.',
  'studio.session.headFailed': 'Dieser Head ließ sich nicht ausführen.',
  'studio.session.detectorFailed': 'Dieser Detektor ließ sich nicht ausführen.',
  'studio.session.promptFailed': 'Der Detektor ließ sich nicht ausführen.',
  'studio.images.emptyFolder': 'Dieser Ordner enthält keine Bilder.',
  'studio.images.emptyDataset': 'Dieser Datensatz enthält keine Bilder.',
  'studio.images.readFolder': 'Dieser Ordner ließ sich nicht lesen.',
  'studio.images.readDataset': 'Dieser Datensatz ließ sich nicht lesen.',
  'studio.images.readPath': 'Dieser Pfad ließ sich nicht lesen.',
  'studio.classes.loadError': 'Die Klassen ließen sich nicht laden.',
  'studio.classes.addError': 'Diese Klasse ließ sich nicht hinzufügen.',
  'studio.classes.removeError': 'Diese Klasse ließ sich nicht entfernen.',

  // Phrases on an outline (lib/phraseEdit)
  'studio.phrase.needsOutline': 'Phrasen gehören an Umrisse — mach zuerst einen aus dieser Box.',
  'studio.phrase.otherClass': '„{phrase}“ ist eine Phrase der Klasse {className}; dieser Umriss ist {name}.',
  'studio.phrase.unnamed': 'ohne Namen',
};
