import type { adminEn } from '../en/admin';
import type { Catalogue } from '../types';

export const adminDe: Catalogue<typeof adminEn> = {
  // Bibliothek
  'admin.library.title': 'Deine Bibliothek',
  'admin.library.lead':
    'Alles, was diese App für dich erstellt hat. Löschen ist endgültig und lässt sich auch durch erneutes Ausführen nicht rückgängig machen — ein Head (ein kleines Modell auf dem Backbone), den du löschst, muss neu trainiert werden.',
  'admin.library.images_one': '{count} Bild',
  'admin.library.images_other': '{count} Bilder',
  'admin.library.boxes_one': '{count} Box',
  'admin.library.boxes_other': '{count} Boxen',
  'admin.library.from': 'aus {names}',
  'admin.library.selectedGroup': 'Ausgewählte Einträge',
  'admin.library.selected': 'ausgewählt',
  'admin.library.deleteMany': '{count} endgültig löschen',
  'admin.library.keepThem': 'Behalten',
  'admin.library.deleting': 'Wird gelöscht …',
  'admin.library.deleteSelected': 'Auswahl löschen',
  'admin.library.clearSelection': 'Auswahl aufheben',
  'admin.library.loading': 'Deine Bibliothek wird geladen …',
  'admin.library.datasets': 'Datensätze',
  'admin.library.datasetsEmpty':
    'Noch keine Datensätze. Annotiere einen Ordner, erzeuge einen Datensatz oder importiere einen COCO-Export.',
  'admin.library.heads': 'Trainierte Heads',
  'admin.library.headsEmpty': 'Noch keine Heads. Trainiere einen unter Training.',
  'admin.library.finetunes': 'Fine-getunte Modelle',
  'admin.library.finetunesEmpty': 'Noch keine fine-getunten Modelle. Fine-tune einen Detektor unter Training.',
  'admin.library.selectRow': '{name} auswählen — {detail}',
  // Export (Doc 121)
  'admin.export.export': 'Exportieren',
  'admin.export.exportNamed': '{name} exportieren',
  'admin.export.busy': 'Wird exportiert …',
  'admin.export.hint': 'Ein Zip mit Modellkarte, Weights, Laufzeitcode, Beispiel und README — alles, um es außerhalb dieser App zu nutzen.',
  'admin.export.show': 'Ordner zeigen',
  'admin.export.showNamed': 'Ordner von {name} zeigen',
  'admin.export.written': 'Geschrieben: {path}',
  'admin.export.downloaded': 'Heruntergeladen: {file}',
  'admin.library.deleteNamed': '„{name}“ löschen',
  'admin.library.keep': 'Behalten',
  'admin.library.deleteRow': '{name} löschen',
  'admin.library.delete': 'Löschen',
  'admin.library.listDatasets': 'die Datensätze',
  'admin.library.listHeads': 'die Heads',
  'admin.library.listFinetunes': 'die fine-getunten Modelle',
  'admin.library.listJoin': ' und ',
  'admin.library.loadFailed': 'Konnte {lists} nicht laden.',
  'admin.library.deleteManyFailed':
    'Konnte {failed} von {total} nicht löschen: {names}. Die Listen unten zeigen, was wirklich noch da ist.',
  'admin.library.deleteFailed': 'Konnte das nicht löschen. Die Liste unten zeigt, was wirklich noch da ist.',

  // Verwaltung / Modelle
  'admin.models.title': 'Verwaltung / Modelle',
  'admin.models.loading': 'Modellkatalog wird geladen …',
  'admin.system.device': 'Rechengerät',
  'admin.system.freeDisk': 'Freier Speicherplatz',
  'admin.system.token': 'HuggingFace-Token',
  'admin.system.tokenSet': 'Eingerichtet',
  'admin.system.tokenUnset': 'Nicht gesetzt — zugangsbeschränkte Modelle nicht verfügbar',
  'admin.system.cache': 'Modell-Cache',
  'admin.system.languageNote': 'Die Sprache der App wählst du mit dem Sprachschalter in der Kopfzeile.',
  'admin.family.groundingDino': 'Grounding DINO — Detection mit freien Begriffen',
  'admin.family.rfDetr': 'RF-DETR — allgemeine Object Detection, und das Modell zum Fine-Tunen',
  'admin.family.dinov2': 'DINOv2 — Backbones',
  'admin.family.dinov3': 'DINOv3 — Backbones (zugangsbeschränkt)',
  'admin.family.sam2': 'SAM 2.1 — Segmentation (frei verfügbar)',
  'admin.family.sam3': 'SAM 3 — Segmentation (zugangsbeschränkt, mit deinem eigenen Token)',
  'admin.family.depthAnything': 'Depth Anything V2 — Tiefe aus einem einzelnen Bild',

  // Eine Modellkarte
  'admin.model.downloading': 'Wird heruntergeladen …',
  'admin.model.downloadingPercent': 'Wird heruntergeladen — {percent}%',
  'admin.model.onDisk': '{size} MB auf der Festplatte',
  'admin.model.downloadSize': '~{size} MB Download',
  'admin.model.installed': 'Installiert',
  'admin.model.gated': 'Zugangsbeschränkt',
  'admin.model.licensed': 'Lizenz: {licence}',
  'admin.model.nonCommercial': 'Nicht kommerziell',
  'admin.model.removing': 'Wird entfernt …',
  'admin.model.remove': 'Entfernen',
  'admin.model.starting': 'Startet …',
  'admin.model.download': 'Herunterladen',
  'admin.models.loadFailed': 'Konnte den Modellkatalog nicht laden.',
  'admin.models.lostTrack': 'Der Download ist nicht mehr auffindbar.',
  'admin.models.downloadFailed': 'Download fehlgeschlagen.',
  'admin.models.startFailed': 'Konnte den Download nicht starten.',
  'admin.models.removeFailed': 'Konnte das Modell nicht entfernen.',

  // Welches Modell
  'admin.guide.toggle': 'Welches Modell soll ich nehmen?',
  'admin.guide.goodAt': 'Gut bei',
  'admin.guide.watchOut': 'Achte auf',
  'admin.guide.measured': 'Hier gemessen:',

  // Startpaket
  'admin.starter.done': 'fertig',
  'admin.starter.failed': 'fehlgeschlagen',
  'admin.starter.readyTitle': 'Startklar.',
  'admin.starter.readyBody':
    'Jedes Modell, das ein erster Durchlauf braucht, ist installiert — annotiere per Prompt, trainiere einen Head, fine-tune einen Detektor oder schätze Tiefe.',
  'admin.starter.title': 'Einrichten',
  'admin.starter.body':
    'In der App ist nichts vorinstalliert — die Weights werden bei Bedarf heruntergeladen und zwischengespeichert, das passiert also nur einmal pro Rechner. Diese {count} geben dir alle Funktionen: ein Backbone für trainierte Heads, einen allgemeinen Detektor, beide Hälften von Grounded SAM und Tiefe.',
  'admin.starter.downloading': 'Wird heruntergeladen …',
  'admin.starter.downloadAll': 'Alle {count} herunterladen ({size} GB)',
  'admin.starter.note':
    'Eins nach dem anderen, damit die Fortschrittsanzeigen stimmen. Du kannst die App währenddessen weiter benutzen.',

  // HuggingFace-Token
  'admin.token.manualTitle': 'Eine Person bei Meta gibt das von Hand frei',
  'admin.token.manual': 'manuelle Freigabe',
  'admin.token.openPage': 'Modellseite öffnen',
  'admin.token.haveRead': 'Ich habe die {licence} gelesen',
  'admin.token.saveFailed': 'Konnte den Token nicht speichern.',
  'admin.token.title': 'Zugang zu HuggingFace',
  'admin.token.introBefore':
    'Manche Modelle sind von ihrem Herausgeber zugangsbeschränkt. DinoTraining lädt sie nie für dich herunter und liefert keinen Token mit — du nutzt deinen eigenen und startest jeden Download selbst. Alles, was die frei verfügbaren Modelle brauchen, einschließlich',
  'admin.token.introAfter': 'für Segmentation Masks, funktioniert ganz ohne das.',
  'admin.token.field': 'Dein HuggingFace-Zugangstoken',
  'admin.token.configured': 'Eingerichtet',
  'admin.token.hintBefore': 'Ein Token mit ',
  'admin.token.hintEm': 'Leserecht',
  'admin.token.hintMiddle': ' reicht aus. Erstelle einen unter ',
  'admin.token.hintStored': '. Er wird in ',
  'admin.token.hintAfter': ' gespeichert, ist nur für dich lesbar und verlässt diesen Rechner nie.',
  'admin.token.saving': 'Wird gespeichert …',
  'admin.token.save': 'Token speichern',
  'admin.token.remove': 'Entfernen',
  'admin.token.stateConfigured': 'Eingerichtet ({hint})',
  'admin.token.stored': 'gespeichert',
  'admin.token.stateUnset': 'Nicht gesetzt — zugangsbeschränkte Modelle bleiben nicht verfügbar',
  'admin.token.saved': 'Token gespeichert. Zugangsbeschränkte Modelle werden jetzt angeboten.',
  'admin.token.needs': 'Modelle, die etwas von dir brauchen',

  // GPU
  'admin.gpu.driverTitle': 'NVIDIA-Treiber antwortet nicht',
  'admin.gpu.driverFoot':
    'Den Treiber neu zu installieren oder zu aktualisieren behebt das meistens. Solange er nicht antwortet, kann diese App nicht erkennen, ob eine GPU vorhanden ist.',
  'admin.gpu.title': 'Deine GPU wird nicht genutzt',
  'admin.gpu.driver': 'Treiber {version}',
  'admin.gpu.footBefore':
    'Das Installationsprogramm enthält eine CPU-Version, damit es klein bleibt. GPU-Unterstützung ist ein separater Download von etwa',
  'admin.gpu.footAfter':
    '— so groß, weil er NVIDIAs CUDA-Laufzeit enthält, nicht wegen der App. Training und Inference laufen damit meist um ein Vielfaches schneller.',
  'admin.gpu.downloading': 'Wird heruntergeladen …',
  'admin.gpu.download': 'GPU-Unterstützung herunterladen ({size} GB)',

  // Weitergabe
  'admin.dist.title': 'Bevor du diese App weitergibst',
  'admin.dist.lead_one':
    '{count} installiertes Modell bringt eine Lizenzpflicht mit. Alles andere, was du installiert hast, ist frei lizenziert und kann so mitgeliefert werden.',
  'admin.dist.lead_other':
    '{count} installierte Modelle bringen eine Lizenzpflicht mit. Alles andere, was du installiert hast, ist frei lizenziert und kann so mitgeliefert werden.',
  'admin.dist.foot':
    'Ein Modell hier zu entfernen löscht seine Weights aus dem Cache — damit ist es aus einem Build heraus, sonst muss sich nichts ändern. Du kannst es danach wieder herunterladen.',

  // Vortrainierte Heads
  'admin.heads.backboneFirst': 'Lade zuerst das Backbone {backbone} herunter.',
  'admin.heads.incompatible': 'Passt nicht zum ausgewählten Backbone.',
  'admin.heads.classes_one': '{count} Klasse',
  'admin.heads.classes_other': '{count} Klassen',
  'admin.heads.installed': 'Installiert',
  'admin.heads.ready': 'Bereit zur Nutzung im Inference Viewer',
  'admin.heads.installing': 'Wird installiert …',
  'admin.heads.install': 'Installieren',
  'admin.heads.title': 'Vortrainierte Heads',
  'admin.heads.note':
    'Fertige Heads, die du ohne Training nutzen kannst. Wähle ein Backbone, um zu sehen, welche dazu passen.',
  'admin.heads.compatibleWith': 'Passend zu',
  'admin.heads.anyBackbone': 'Jedes Backbone',
  'admin.heads.loading': 'Head-Katalog wird geladen …',
  'admin.heads.importTitle': 'Einen Head aus der Community importieren',
  'admin.heads.loadFailed': 'Konnte den Head-Katalog nicht laden.',
  'admin.heads.installedNotice': 'Installiert: {summary}',
  'admin.heads.importedNotice': 'Importiert: {summary}',
  'admin.heads.installFailed': 'Konnte den Head nicht installieren.',
  'admin.heads.importFailed': 'Konnte diesen Head nicht importieren.',

  // Community-Head importieren
  'admin.import.noteBefore': 'Community-Heads müssen als ',
  'admin.import.noteFiles': ' veröffentlicht sein. Dateien im Format ',
  'admin.import.noteOr': ' oder ',
  'admin.import.noteAfter': ' werden abgelehnt — sie zu laden würde beliebigen Code aus dem Repository ausführen.',
  'admin.import.repo': 'HuggingFace-Repository',
  'admin.import.repoPlaceholder': 'besitzer/name',
  'admin.import.headType': 'Head-Typ',
  'admin.import.backbone': 'Backbone',
  'admin.import.classes': 'Klassen',
  'admin.import.classesPlaceholder': 'automatisch',
  'admin.import.importing': 'Wird importiert …',
  'admin.import.submit': 'Head importieren',

  // Verbindung
  'admin.connection.title': 'Verbindung',
  'admin.connection.lead':
    'Alles, was diese App tut, tut sie über eine lokale API — also kann dein eigener KI-Assistent das auch. Es gibt zwei Wege, ihm Zugriff zu geben, und beide laufen komplett auf diesem Rechner.',
  'admin.connection.legend': 'Wie verbinden',
  'admin.connection.mcpHint': 'Typisierte Tools, die dein Assistent direkt aufruft. Am besten, wenn er MCP unterstützt.',
  'admin.connection.manualName': 'Jeder Assistent',
  'admin.connection.manualHint': 'Ein Dokument zum Einfügen. Funktioniert überall, auch ohne MCP.',
  'admin.connection.guideFailed': 'Konnte die API-Anleitung nicht laden.',
  'admin.connection.guideStatus': 'Konnte die API-Anleitung nicht laden ({status}).',
  'admin.connection.manualNote':
    'Kopiere dieses Dokument in deinen Assistenten und beschreib, was du willst. Es erklärt jeden Ablauf der Reihe nach und benennt die Stolperfallen — genau das, was ein Schema nicht ausdrücken kann. Nutze das, wenn dein Assistent kein MCP spricht. Das Dokument ist auf Englisch, weil KI-Assistenten es so am besten lesen; schreiben kannst du ihm trotzdem auf Deutsch.',
  'admin.connection.copied': '✓ Kopiert',
  'admin.connection.copyFailed': 'Kopieren fehlgeschlagen — nutze Herunterladen',
  'admin.connection.copy': 'Für deine KI kopieren',
  'admin.connection.downloadMd': '.md herunterladen',
  'admin.connection.savePdf': 'Als PDF speichern',
  'admin.connection.mdNote': 'Markdown lesen diese Modelle am besten — das PDF ist für Menschen.',
  'admin.connection.loadingGuide': 'Anleitung wird geladen …',

  // MCP
  'admin.mcp.readFailed': 'Konnte die MCP-Angaben nicht lesen.',
  'admin.mcp.clipboardFailed':
    'Kein Zugriff auf die Zwischenablage — kopiere den Befehl oben bitte von Hand.',
  'admin.mcp.introBefore': 'MCP gibt deinem Assistenten',
  'admin.mcp.introStrong': 'typisierte Tools',
  'admin.mcp.introAfter':
    'statt eines Dokuments, das er deuten muss. Was jedes Tool braucht, liest er aus dessen Schema — so kann er keinen Parameter erfinden und nicht vergessen, dass ein Modell installiert sein muss, bevor es fine-getunt werden kann. Das ist die bessere Wahl, wenn dein Assistent es unterstützt.',
  'admin.mcp.step1': '1. Verbinden',
  'admin.mcp.step1Body':
    'Der Server läuft in dieser App — es gibt nichts zu installieren oder zu starten. Führe das einmal in einem Terminal aus, während die App läuft:',
  'admin.mcp.copied': 'Kopiert',
  'admin.mcp.copy': 'Befehl kopieren',
  'admin.mcp.step2': '2. Sag, was du willst',
  'admin.mcp.step2Body': 'Dann sprich ganz normal mit deinem Assistenten. Er wählt die Tools selbst:',
  'admin.mcp.quote':
    '„Hier ist ein Link zu einem Bahn-Datensatz. Lade ihn herunter, importiere ihn, fine-tune RF-DETR damit und annotiere mit dem Ergebnis die Bilder in ~/photos.“',
  'admin.mcp.toolsTitle_one': 'Das {count} Tool, das er bekommt',
  'admin.mcp.toolsTitle_other': 'Die {count} Tools, die er bekommt',
  'admin.mcp.toolsBody':
    'Nach Aufgaben geschnitten statt eins pro Endpunkt — die API hat 61 Operationen, und sie alle weiterzugeben hieße, dass dein Assistent die ganze Abstimmung selbst übernehmen müsste.',
  'admin.mcp.noteStrong': 'Es funktioniert nur auf diesem Rechner.',
  'admin.mcp.noteBody':
    'Der Server hört nur auf Loopback, also kann ein Assistent auf diesem Rechner ihn erreichen und einer anderswo nicht. Das ist Absicht: Es gibt keine Anmeldung, und die Tools können jeden Dateipfad lesen, den sie bekommen.',
  'admin.mcp.reading': 'Verbindungsdetails werden gelesen …',
};
