import type { appEn } from '../en/app';
import type { Catalogue } from '../types';

export const appDe: Catalogue<typeof appEn> = {
  'app.tabs.sections': 'DinoTraining-Bereiche',
  'app.tabs.introLabel': 'Hier starten',
  'app.tabs.introHint':
    'Was diese App macht, was ein Backbone und ein Head sind und was sie noch nicht kann.',
  'app.tabs.studioLabel': 'Annotation Studio',
  'app.tabs.studioHint':
    'Annotiere einen Ordner voller Bilder – per Text-Prompt oder mit einem Head, den du trainiert hast.',
  'app.tabs.prepareLabel': 'Daten vorbereiten',
  'app.tabs.prepareHint':
    'Prüfe einen Datensatz, korrigiere ihn, teile ihn auf und sieh ihn so, wie das Modell ihn sieht – dann speichere ein Rezept.',
  'app.tabs.trainerLabel': 'Training',
  'app.tabs.trainerHint':
    'Trainiere einen Head auf einem eingefrorenen DINO-Backbone oder fine-tune einen ganzen Detektor.',
  'app.tabs.inferenceLabel': 'Inference Viewer',
  'app.tabs.inferenceHint':
    'Lass trainierte Heads und Foundation Models auf ein Bild los, direkt nebeneinander.',
  'app.tabs.generatorLabel': 'Datensatz-Generator',
  'app.tabs.generatorHint':
    'Annotiere neue Bilder automatisch mit einem trainierten Head oder einem Begriff als Prompt und prüfe sie dann.',
  'app.tabs.inspectLabel': 'Datensätze ansehen',
  'app.tabs.inspectHint':
    'Spiel einen Datensatz ab – seine Videos und Bilder – mit den Annotationen, die er enthält.',
  'app.tabs.modelsLabel': 'Modelle & Datensätze',
  'app.tabs.modelsHint': 'Der Einstieg: Modelle laden, Datensätze importieren oder öffnen und finden, was du trainiert hast.',
  'app.tabs.apiLabel': 'Verbindung',
  'app.tabs.apiHint':
    'Lass deinen eigenen KI-Assistenten die App steuern – über MCP oder mit einem Dokument.',
  'app.stub.arrives': 'Kommt mit Welle {wave}.',

  'app.update.available': 'DinoTraining {latest} ist da. Du hast {current}.',
  'app.update.get': 'Holen',
  'app.update.notes': 'Was ist neu',
  'app.update.later': 'Später',
  'app.addApps.question': 'DinoTraining zu deinem Programme-Ordner hinzufügen?',
  'app.addApps.add': 'Hinzufügen',
  'app.addApps.notNow': 'Jetzt nicht',
  'app.addApps.added': 'Hinzugefügt: {path}',
  'app.addApps.failed': 'Konnte nicht hinzugefügt werden: {message}',
  // Doc 140: beside an error
  'app.report.openLog': 'Log öffnen',
  'app.report.issue': 'Problem melden',
  'app.report.issueHint': 'Öffnet ein neues GitHub-Issue mit Fehler, Version und den letzten Zeilen des Logs. Du liest es und schickst es mit deinem GitHub-Konto ab; dein Benutzername wird durch ~ ersetzt.',
  'app.report.failed': 'Die Issue-Seite ließ sich nicht öffnen: {reason}',
  'app.backend.connecting': 'Verbindung zum Backend wird hergestellt …',
  'app.backend.unexpected': 'Unerwarteter Fehler bei der Verbindung zum Backend.',
  'app.client.unreachable':
    'Das DinoTraining-Backend unter {url} ist nicht erreichbar. Läuft der Sidecar-Prozess?',
  'app.client.malformed':
    'Unerwartete Antwort von {path}. Backend und Frontend passen nicht mehr zusammen.',

  'app.verdict.positive': 'Richtig',
  'app.verdict.negative': 'Falsch',
  'app.verdict.unclear': 'Unklar',
  'app.view.masks': 'Umrisse',
  'app.view.boxes': 'Boxen',
  'app.view.both': 'Beides',
  'app.output.masks':
    'Speichert Segmentation Masks. Der COCO-Export enthält außerdem zu jeder Mask eine daraus abgeleitete Box – du bekommst also beides.',
  'app.output.boxes': 'Speichert Boxen.',

  'app.appearance.title': 'Darstellung',
  'app.appearance.animated': 'Animierter Hintergrund',
  'app.appearance.reduced':
    'Dein System wünscht weniger Bewegung, deshalb bleibt der Hintergrund still – egal, was hier eingestellt ist.',
};
