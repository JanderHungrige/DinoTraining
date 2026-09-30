import type { generatorEn } from '../en/generator';
import type { Catalogue } from '../types';

export const generatorDe: Catalogue<typeof generatorEn> = {
  // Der Datensatz-Generator
  'generator.tab.title': 'Datensatz-Generator',
  'generator.tab.lead':
    'Richte einen Head, den du schon trainiert hast, auf neue Bilder. Er schlägt Boxen vor, du nimmst sie an oder lehnst sie ab, und das Ergebnis wird der Datensatz für den nächsten Head.',
  'generator.tab.inspect': 'Ansehen, was ich gerade annotiert habe',
  'generator.tab.changeSetup': 'Einstellungen ändern',
  'generator.tab.proposingWith': 'Vorschläge von',
  'generator.tab.decoding': 'Frames werden in den Datensatz entpackt — {done} von {total} …',
  'generator.tab.listing': 'Bilder werden aufgelistet …',
  'generator.tab.noImages': 'In diesem Ordner sind keine Bilder.',
  'generator.tab.loadingImage': 'Bild lädt …',
  'generator.tab.proposeMasks': 'Masks vorschlagen',
  'generator.tab.proposeBoxes': 'Boxen vorschlagen',

  // Die Werkzeugleiste
  'generator.bar.label': 'Dieses Bild prüfen',
  'generator.bar.proposing': 'Schlägt vor …',
  'generator.bar.saving': 'Speichert …',
  'generator.bar.save': 'Im Datensatz speichern',
  'generator.bar.previous': '← Zurück',
  'generator.bar.next': 'Weiter →',
  'generator.bar.automation': 'Automatik',
  'generator.bar.autoProposeTitle': 'Vorschlagen, sobald ein neues Bild erscheint',
  'generator.bar.autoProposeAria':
    'Automatisch vorschlagen: bei jedem neuen Bild von selbst vorschlagen',
  'generator.bar.autoPropose': 'Automatisch vorschlagen',
  'generator.bar.autoSaveTitle': 'Ein geändertes Bild speichern, wenn du weitergehst',
  'generator.bar.autoSaveAria':
    'Automatisch speichern: beim Wechsel zu einem anderen Bild von selbst speichern',
  'generator.bar.autoSave': 'Automatisch speichern',

  // Automatischer Durchlauf
  'generator.autoplay.stop': '■ Stopp',
  'generator.autoplay.startTitle':
    'Vorschlagen, eine halbe Sekunde zeigen, speichern und weiter — von diesem Bild bis zum letzten',
  'generator.autoplay.start': '▶ Analyse starten',
  'generator.autoplay.hiddenTitle': 'Ohne jedes Bild zu zeichnen; nur den Fortschritt zeigen',
  'generator.autoplay.hiddenAria': 'Im Hintergrund laufen, ohne jedes Bild zu zeichnen',
  'generator.autoplay.hidden': 'Im Hintergrund',
  'generator.autoplay.runningHidden': '— läuft im Hintergrund, Bild {done} von {total}',
  'generator.autoplay.progressAria': 'Fortschritt der Analyse, {percent} Prozent',
  'generator.autoplay.saved': '{count} gespeichert',
  'generator.autoplay.empty': '{count} ohne Fund',
  'generator.autoplay.failed': '{count} fehlgeschlagen',
  'generator.autoplay.skipped': '{count} schon gespeichert',
  'generator.autoplay.asked': '{count} nachgefragt',
  'generator.autoplay.finished': 'Die Analyse hat das letzte Bild erreicht.',
  'generator.autoplay.stopped':
    'Die Analyse hat hier angehalten. Korrigiere, was falsch ist; beim Weitergehen wird es gespeichert.',
  'generator.autoplay.saveFailed':
    'Die Analyse hat angehalten, weil ein Bild nicht gespeichert werden konnte.',
  'generator.autoplay.lastFailure': 'Letzter Fehler: {error}',
  'generator.autoplay.nothingProposed': 'Es konnte nichts vorgeschlagen werden.',

  // Nachfragen bei unklaren Vorschlägen
  'generator.unclear.legend': 'Während der Analyse',
  'generator.unclear.toggle': 'Frag mich bei einem Score zwischen',
  'generator.unclear.lowAria': 'Niedrigster Score, bei dem gefragt wird',
  'generator.unclear.and': 'und',
  'generator.unclear.highAria': 'Höchster Score, bei dem gefragt wird',
  'generator.unclear.hint':
    'Scores bedeuten bei jedem Modell etwas anderes — wähle den Bereich, in dem dieses Modell rät.',
  'generator.unclear.waitingAria': 'Die Analyse wartet auf dich',
  'generator.unclear.paused': 'Angehalten bei Bild {number} von {total}.',
  'generator.unclear.scored_one':
    '{count} Vorschlag hat einen Score zwischen {low} und {high} und ist als {unclear} markiert. Klicke eine Box an, um ihre Einstufung zu wechseln (oder wähle sie aus und drücke 1 richtig · 2 falsch · 3 unklar), und mach dann weiter. Lässt du ihn so, wird er als unklar gespeichert.',
  'generator.unclear.scored_other':
    '{count} Vorschläge haben einen Score zwischen {low} und {high} und sind als {unclear} markiert. Klicke eine Box an, um ihre Einstufung zu wechseln (oder wähle sie aus und drücke 1 richtig · 2 falsch · 3 unklar), und mach dann weiter. Lässt du sie so, werden sie als unklar gespeichert.',
  'generator.unclear.word': 'unklar',
  'generator.unclear.continue': 'Weiter',
  'generator.unclear.stopHere': 'Hier anhalten',

  // Einstellungen
  'generator.setup.detector': 'Detector',
  'generator.setup.datasetHint':
    'Seine Bilder werden neu in den Datensatz annotiert, den du unten wählst — die Quelle ist nur, woher die Bilder kommen.',
  'generator.setup.backbone': 'Backbone',
  'generator.setup.threshold': 'Score-Threshold — {value}',
  'generator.setup.starting': 'Startet …',
  'generator.setup.start': 'Generieren starten',
  'generator.mode.legend': 'Was die Annotationen vorschlägt',
  'generator.mode.foundation':
    'Ein allgemeiner Detector — findet alltägliche Objekte, nichts einzurichten',
  'generator.mode.expert': 'Ein Head, den du trainiert hast — schlägt Boxen vor',
  'generator.mode.masks': 'Grounded SAM — gib einen Begriff ein, bekomme Masks',
  'generator.destination.saveInto': 'Speichern in',
  'generator.destination.createNew': 'Neuen Datensatz anlegen …',
  'generator.destination.option_one': '{name} ({count} Bild)',
  'generator.destination.option_other': '{name} ({count} Bilder)',
  'generator.destination.newName': 'Name des neuen Datensatzes',
  'generator.destination.placeholder': 'Schrauben, zweite Runde',

  // Meldungen der Sitzung
  'generator.session.proposeFailed': 'Für dieses Bild konnte nichts vorgeschlagen werden.',
  'generator.session.saveFailed': 'Konnte nicht im Datensatz speichern.',
  'generator.session.listFailedDataset': 'Die Bilder dieses Datensatzes konnten nicht aufgelistet werden.',
  'generator.session.listFailedFolder': 'Die Bilder dieses Ordners konnten nicht aufgelistet werden.',
  'generator.session.masksFirst': 'Schlag erst Masks vor, bevor du speicherst.',
  'generator.session.notLoaded':
    'Das Bild ist noch nicht geladen, deshalb können seine Boxen noch nicht platziert werden.',
  'generator.session.masksFor_one': '{count} Mask für „{concept}“',
  'generator.session.masksFor_other': '{count} Masks für „{concept}“',

  // Datensätze ansehen
  'generator.inspect.title': 'Datensätze ansehen',
  'generator.inspect.lead':
    'Spiel einen Datensatz ab, mit allem eingezeichnet, was er enthält — ein Video, einen Ordner oder seine einzelnen Bilder.',
  'generator.inspect.dataset': 'Datensatz',
  'generator.inspect.noDatasets': 'Noch keine Datensätze',
  'generator.inspect.play': 'Abspielen',
  'generator.inspect.loose': 'Bilder außerhalb einer Sequenz · {count}',
  'generator.inspect.loading': 'Datensatz lädt …',
  'generator.inspect.empty': 'Dieser Datensatz hat noch keine Bilder.',
  'generator.inspect.loadFailed': 'Dieser Datensatz konnte nicht geladen werden.',
  'generator.timeline.empty': 'In dieser Sequenz ist noch nichts annotiert.',
  'generator.timeline.barAria': '{name}: in {count} von {total} Frames',
  'generator.timeline.jumps': 'Zwischen Annotationen springen',
  'generator.timeline.hint': 'Klicke auf einen Balken, um eine Klasse zu wählen.',
  'generator.timeline.first': '⇤ Erste',
  'generator.timeline.previous': '◀ Vorige',
  'generator.timeline.next': 'Nächste ▶',
  'generator.player.frame': 'Frame {index}',
  'generator.player.noFrame': 'Kein Frame',
  'generator.player.transport': 'Wiedergabe',
  'generator.player.back': '◀ Frame zurück',
  'generator.player.pause': '❚❚ Anhalten',
  'generator.player.play': '▶ Abspielen',
  'generator.player.forward': 'Frame vor ▶',
  'generator.player.position': 'Position in der Sequenz',
  'generator.player.atFrame': ' · Frame {index}',
  'generator.player.notAnnotated': ' · nicht annotiert',
};
