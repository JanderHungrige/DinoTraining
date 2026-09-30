import type { runEn } from '../en/run';
import type { Catalogue } from '../types';

export const runDe: Catalogue<typeof runEn> = {
  // The tab
  'run.viewer.title': 'Modell-Ansicht',
  'run.viewer.lead':
    'Wähle ein einzelnes Bild oder einen Ordner, such dir einen oder mehrere Heads aus und vergleiche das Original mit dem, was sie vorhergesagt haben.',
  'run.viewer.modeLegend': 'Was du ansehen willst',
  'run.viewer.modeImageName': 'Ein einzelnes Bild',
  'run.viewer.modeImageHint': 'Ein Bild, jedes ausgewählte Modell, nebeneinander.',
  'run.viewer.modeVideoName': 'Ein Video oder ein Ordner',
  'run.viewer.modeVideoHint':
    'Analysiere einen Bereich von Einzelbildern einmal und spiel ihn dann mit den Annotationen ab.',
  'run.viewer.emptyFolder': 'In diesem Ordner sind keine Bilder.',
  'run.viewer.truncated_one': 'Es wird das erste {count} Bild in diesem Ordner gezeigt.',
  'run.viewer.truncated_other': 'Es werden die ersten {count} Bilder in diesem Ordner gezeigt.',
  'run.viewer.pickSource_one':
    'Wähle oben ein Bild oder einen Ordner, um den ausgewählten Head laufen zu lassen.',
  'run.viewer.pickSource_other':
    'Wähle oben ein Bild oder einen Ordner, um die ausgewählten Heads laufen zu lassen.',
  'run.viewer.position': '{name} — {index} von {total}',
  'run.viewer.running': 'Läuft …',
  'run.viewer.selectAndRun': 'Wähle einen oder mehrere Heads aus und klicke auf Ausführen.',
  'run.viewer.previous': '← Zurück',
  'run.viewer.next': 'Weiter →',

  // Side by side
  'run.compare.result': 'Ergebnis',
  'run.compare.original': 'Originalbild',
  'run.compare.ariaLabel': 'Bildvergleich',
  'run.compare.zoomOut': 'Verkleinern',
  'run.compare.zoomIn': 'Vergrößern',
  'run.compare.reset': 'Zurücksetzen',
  'run.compare.hint': 'Ziehen zum Verschieben · Pfeiltasten und +/− gehen auch',

  // The head panel
  'run.heads.loading': 'Heads werden geladen …',
  'run.heads.nothingToRun':
    'Noch nichts zum Ausführen da. Installiere ein Basismodell oder einen fertigen Head im Tab Verwaltung, oder trainiere einen Head im Tab Training.',
  'run.heads.task': 'Aufgabe',
  'run.heads.allTasks': 'Alle Aufgaben',
  'run.heads.trainedOn': 'Trainiert auf',
  'run.heads.anyDataset': 'Beliebiger Datensatz',
  'run.heads.comparing': '{count} Heads im Vergleich bei {task}',
  'run.heads.legend': 'Heads (kleine Modelle auf dem Backbone)',
  'run.heads.incompatible':
    'Registriert für {registered}; die Auswahl läuft gerade auf {current}.',
  'run.heads.foundations': 'Basismodelle',
  'run.heads.nonCommercial': 'nicht kommerziell',
  'run.heads.whatToFind': 'Was gefunden werden soll',
  'run.heads.conceptHint':
    'Begriffsmodelle segmentieren nur, was du benennst – am besten auf Englisch. Trenne mehrere Begriffe mit Punkten.',
  'run.heads.runNone': 'Modelle ausführen',
  'run.heads.run_one': '{count} Modell ausführen',
  'run.heads.run_other': '{count} Modelle ausführen',
  'run.heads.running': 'Läuft …',
  'run.heads.clear': 'Leeren',
  'run.heads.conceptMissing':
    'Gib ein, wonach gesucht werden soll – ein Begriffsmodell segmentiert nur, was du benennst.',
  'run.heads.passes_one': '{count} Backbone-Durchlauf',
  'run.heads.passes_other': '{count} Backbone-Durchläufe',
  'run.heads.runFailed': 'Diese Auswahl konnte nicht ausgeführt werden.',
  'run.heads.loadFailed': 'Die Heads konnten nicht geladen werden.',

  // Tiling
  'run.tiling.toggle': 'Bild in Kacheln teilen',
  'run.tiling.columns': 'Spalten',
  'run.tiling.rows': 'Zeilen',
  'run.tiling.count_one': '{count} Kachel',
  'run.tiling.count_other': '{count} Kacheln',
  'run.tiling.hintOn':
    'Dieser Head wurde auf Bildern mit {trained} px trainiert, dieses Bild hat {image} px. Objekte erscheinen etwa {factor}× kleiner, als er sie zu finden gelernt hat.',
  'run.tiling.hintOff':
    'Dieser Head wurde auf Bildern mit {trained} px trainiert, dieses Bild hat {image} px. Objekte erscheinen etwa {factor}× kleiner, als er sie zu finden gelernt hat – Kacheln sind wahrscheinlich nötig.',

  // The sequence player
  'run.sequence.pickSource': 'Wähle oben einen Ordner mit Einzelbildern oder eine Videodatei.',
  'run.sequence.notSequence':
    'Dieser Pfad ist keine Bildfolge. Wähle einen Ordner mit Einzelbildern oder eine Videodatei, um sie abzuspielen.',
  'run.player.startAt': 'Ab Einzelbild',
  'run.player.howMany': 'Wie viele Einzelbilder',
  'run.player.playAt': 'Abspielen mit (fps)',
  'run.player.kindVideo': 'Videodatei',
  'run.player.kindFolder': 'Ordner',
  'run.player.frames_one': '{count} Einzelbild',
  'run.player.frames_other': '{count} Einzelbilder',
  'run.player.analysing': '{count} davon zu analysieren dauert {time}',
  'run.player.estimateNote': '(geschätzt)',
  'run.player.estimateMoment': 'einen Moment',
  'run.player.estimateSeconds': 'etwa {value} Sek.',
  'run.player.estimateMinutes': 'etwa {value} Min.',
  'run.player.estimateHours': 'etwa {value} Stunden',
  'run.player.analysingButton': 'Wird analysiert …',
  'run.player.analyse_one': '{count} Einzelbild analysieren',
  'run.player.analyse_other': '{count} Einzelbilder analysieren',
  'run.player.stop': 'Anhalten',
  'run.player.pickModel': 'Wähle oben mindestens einen Head oder ein Basismodell.',
  'run.player.progress': '{done} von {total} Einzelbildern analysiert …',
  'run.player.stopped': 'Angehalten — {done} von {total} Einzelbildern analysiert',
  'run.player.ready': 'Fertig — {done} von {total} Einzelbildern analysiert',
  'run.player.unreadable': '{count} konnten nicht gelesen werden',
  'run.player.frameLabel': 'Einzelbild {index}',
  'run.player.pause': 'Pausieren',
  'run.player.play': 'Abspielen',
  'run.player.slider': 'Einzelbild',
  'run.player.counter': 'Einzelbild {index}',
  'run.player.notAnalysed': 'nicht analysiert',
  'run.player.startFailed': 'Der Durchlauf konnte nicht gestartet werden.',

  // Overlays
  'run.overlay.className': 'Klasse {index}',
  'run.overlay.legend': 'Von {head} gefundene Klassen',
  'run.overlay.segmentation': 'Segmentierung von {head}',
  'run.overlay.depth': 'Tiefe von {head}',
  'run.overlay.stored': 'Gespeicherte Annotationen',
  'run.overlay.unnamed': 'ohne Namen',

  // Mask review and mask source
  'run.maskReview.aria':
    'Umriss ({verdict}): {concept}{score}. Drücke 1, 2 oder 3, um die Bewertung zu ändern.',
  'run.maskReview.ariaBare':
    'Umriss ({verdict}){score}. Drücke 1, 2 oder 3, um die Bewertung zu ändern.',
  'run.maskReview.hint':
    'Klicke auf einen Umriss, um seine Bewertung weiterzuschalten, oder drücke 1, 2 oder 3, während er ausgewählt ist. Ein abgelehnter Umriss wird nicht gelöscht, sondern als Negativbeispiel behalten – das Training kann ihn nutzen.',
  'run.maskSource.annotator': 'Annotationsmodell',
  'run.maskSource.concept': 'Begriff',
  'run.maskSource.hintPhrases':
    'Grounding DINO findet jede Phrase und SAM 2.1 macht daraus einen Umriss (Maske). Mehrere Phrasen, getrennt durch Punkte, funktionieren also gut – am besten auf Englisch. Hier ist nichts zugangsbeschränkt: kein Token, kein Konto.',
  'run.maskSource.hintSingle':
    'SAM 3 nimmt einen Begriff nach dem anderen – eine einzelne englische Nominalphrase wie „a bolt“. Mehrere Phrasen in einem Feld werden als ein langer Begriff gelesen und passen schlecht; lass sie einzeln laufen.',
};
