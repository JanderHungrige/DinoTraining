import type { studio2En } from '../en/studio2';
import type { Catalogue } from '../types';

export const studio2De: Catalogue<typeof studio2En> = {
  // Prescan (doc 53)
  'studio.prescan.open': 'Leere Bilder überspringen …',
  'studio.prescan.aria': 'Prescan',
  'studio.prescan.lead_one':
    'Lass das Modell zuerst über {count} Bild laufen und zeig dann nur die, in denen es etwas gefunden hat. Nichts wird gespeichert — das entscheidet nur, was du siehst.',
  'studio.prescan.lead_other':
    'Lass das Modell zuerst über alle {count} Bilder laufen und zeig dann nur die, in denen es etwas gefunden hat. Nichts wird gespeichert — das entscheidet nur, was du siehst.',
  'studio.prescan.lookingFor': 'Suchen nach',
  'studio.prescan.hint': 'Durch Kommas getrennt. Lass es leer, um jedes Bild zu behalten, in dem das Modell irgendetwas findet.',
  'studio.prescan.confidence': 'Confidence',
  'studio.prescan.progress_one': '{scanned} von {total} · bisher {count} Treffer',
  'studio.prescan.progress_other': '{scanned} von {total} · bisher {count} Treffer',
  'studio.prescan.stop': 'Stoppen, Gefundenes behalten',
  'studio.prescan.starting': 'Startet …',
  'studio.prescan.scan_one': '{count} Bild durchsuchen',
  'studio.prescan.scan_other': '{count} Bilder durchsuchen',
  'studio.prescan.ofTotal': '{hits} von {total}',
  'studio.prescan.matched_one': 'Bildern passt',
  'studio.prescan.matched_other': 'Bildern passen',
  'studio.prescan.cancelled': 'bevor du die Suche gestoppt hast',
  'studio.prescan.unreadable_one': 'ließ sich nicht lesen',
  'studio.prescan.unreadable_other': 'ließen sich nicht lesen',
  'studio.prescan.failed': 'die Suche ist fehlgeschlagen: {message}',
  'studio.prescan.showOnly_one': 'Nur den {count} Treffer zeigen',
  'studio.prescan.showOnly_other': 'Nur die {count} Treffer zeigen',
  'studio.prescan.nothingToShow': 'nichts zu zeigen',
  'studio.prescan.startError': 'Die Suche ließ sich nicht starten.',
  'studio.prescan.stopError': 'Die Suche ließ sich nicht stoppen.',

  // The outline tools (doc 106)
  'studio.mask.toolbar': 'Umriss-Werkzeuge',
  'studio.mask.tool': 'Werkzeug',
  'studio.mask.select': 'Auswählen',
  'studio.mask.selectHint': 'Boxen wie gewohnt zeichnen und auswählen',
  'studio.mask.add': '⊕ Hinzufügen',
  'studio.mask.addHint': 'Klick auf das, was zum Umriss gehört; SAM zeichnet ihn neu',
  'studio.mask.remove': '⊖ Entfernen',
  'studio.mask.removeHint': 'Klick auf das, was nicht dazugehört; SAM zeichnet ihn neu',
  'studio.mask.brush': 'Pinsel',
  'studio.mask.brushHint': 'Ziehen, um Pixel hinzuzumalen',
  'studio.mask.erase': 'Radierer',
  'studio.mask.eraseHint': 'Ziehen, um Pixel wegzunehmen',
  'studio.mask.size': 'Größe',
  'studio.mask.undo': 'Rückgängig',
  'studio.mask.fromBoxes': 'Umrisse aus meinen Boxen',
  'studio.mask.working': 'Arbeitet …',
  'studio.mask.selectFirst': 'Wähle eine Box oder einen Umriss aus, um ihn zu bearbeiten.',
  'studio.mask.clicks_one': '{count} Klick auf diesem Umriss — jeder zeichnet ihn neu.',
  'studio.mask.clicks_other': '{count} Klicks auf diesem Umriss — jeder zeichnet ihn neu.',
  'studio.mask.noOutline': 'Diese Box hat noch keinen Umriss: ⊕ Hinzufügen erstellt einen.',
  'studio.mask.outlineFirst': 'Erstelle zuerst einen Umriss: Klick mit ⊕ auf das Objekt.',

  // What proposes the boxes
  'studio.mode.legend': 'Was die Boxen vorschlägt',
  'studio.mode.foundation': 'Ein allgemeiner Detektor — findet Alltagsgegenstände, nichts einzurichten',
  'studio.mode.prompt': 'Grounding DINO — beschreib, was du suchst',
  'studio.mode.head': 'Ein Head, den du trainiert hast — schlägt Boxen für seine eigenen Klassen vor',
  'studio.foundation.legend': 'Detektor',
  'studio.foundation.loading': 'Detektoren werden geladen …',
  'studio.foundation.none': 'Kein Foundation Model im Katalog schlägt Boxen vor.',
  'studio.foundation.notDownloaded_one':
    '{count} allgemeiner Detektor ist verfügbar, aber nicht heruntergeladen. Hol dir einen unter',
  'studio.foundation.notDownloaded_other':
    '{count} allgemeine Detektoren sind verfügbar, aber nicht heruntergeladen. Hol dir einen unter',
  'studio.foundation.adminModels': 'Modelle & Datensätze',
  'studio.foundation.noTraining': '— RF-DETR braucht kein Training und keinen Prompt.',
  'studio.foundation.nonCommercial': 'nicht kommerziell',
  'studio.foundation.whatToFind': 'Was gefunden werden soll',
  'studio.foundation.conceptHint': '{model} findet nur, was du hier nennst. Trenne mehrere mit Kommas oder Punkten.',
  'studio.expert.legend': 'Experten-Head',
  'studio.expert.loading': 'Heads werden geladen …',
  'studio.expert.none':
    'Kein installierter Head kann Boxen vorschlagen. Classification-, Segmentation- und Depth-Heads laufen im Inference Viewer; nur ein Detection-Head schlägt Boxen vor — trainiere einen unter Training.',
  'studio.expert.incompatible_one': '{count} Detection-Head installiert, aber keiner wurde auf',
  'studio.expert.incompatible_other': '{count} Detection-Heads installiert, aber keiner wurde auf',
  'studio.expert.switch': ' trainiert. Wechsle das Backbone oder trainiere einen Head darauf.',

  // Prompt guidance (doc 39)
  'studio.guidance.groundingDino':
    'Grounding DINO liest jede Phrase zwischen Kommas oder Punkten als eigenes Ding, nach dem es suchen soll. Schreib die Phrasen auf Englisch. Eine Art von Label: „a bolt“. Mehrere: „a bolt, a nut, a washer“. Kleinbuchstaben und ein „a“ vorne — in dieser Form wurde es trainiert. Es findet auch Dinge, nach denen du nicht gefragt hast; dafür ist die Ablehnen-Taste da.',
  'studio.guidance.headNone':
    'Hier gibt es keinen Prompt: Ein trainierter Head weiß schon, wonach er sucht. Er schlägt seine eigenen Klassen vor, und du nimmst sie an, lehnst sie ab oder korrigierst sie.',
  'studio.guidance.andMore': '{list} und {count} weitere',
  'studio.guidance.head':
    'Hier gibt es keinen Prompt: Dieser Head wurde darauf trainiert, {classes} zu finden. Er schlägt genau diese vor und sonst nichts — Prompts sind für Modelle, die Wörter verstehen, und dieser nimmt ein Bild.',

  // Where the images come from
  'studio.source.legend': 'Bilder aus',
  'studio.source.folder': 'Einem Ordner',
  'studio.source.dataset': 'Einem Datensatz, den du schon hast',
  'studio.source.folderHint': 'Schon einen Datensatz importiert oder geladen? Wähle stattdessen „Einem Datensatz, den du schon hast“: kein Ordner zu suchen.',
  'studio.source.noneWithImages': 'noch keiner mit Bildern',
  'studio.source.video': 'Einer Videodatei',
  'studio.picker.drop': 'Loslassen, um es zu laden',
  'studio.picker.label': 'Bild oder Ordner',
  'studio.picker.image': 'Bild …',
  'studio.picker.folder': 'Ordner …',
  'studio.picker.load': 'Laden',
  'studio.picker.orDataset': '… oder ein Datensatz, den du schon hast',
  'studio.picker.none': 'Keiner',
  'studio.picker.dragHint': 'Oder zieh ein Bild oder einen Ordner auf dieses Fenster.',
  'studio.folder.drop': 'Loslassen, um diesen Ordner zu nehmen',
  'studio.folder.label': 'Bildordner',
  'studio.folder.hint':
    'Wähl ein Bild, dann wird sein Ordner verwendet. Du kannst auch einen Ordner — oder ein beliebiges Bild darin — auf dieses Fenster ziehen.',

  // A video source (doc 73)
  'studio.video.probeError': 'Dieses Video ließ sich nicht öffnen.',
  'studio.video.file': 'Videodatei',
  'studio.video.pick': 'Video …',
  'studio.video.notVideo': 'Kein Video, das diese App lesen kann — nimm .mp4, .mov, .avi, .mkv, .webm oder .m4v.',
  'studio.video.frames': '{frames} Frames',
  'studio.video.fps': 'mit {fps} fps',
  'studio.video.pastEnd': 'Dieser Bereich liegt hinter dem Ende des Videos.',
  'studio.video.decodes': 'Entpackt {frames} Frames in den Datensatz — etwa {mb} MB (geschätzt).',
  'studio.video.from': 'Ab Frame',
  'studio.video.count': 'Frames',
  'studio.video.every': 'Jeden',
  'studio.video.everyAria': 'Jeden n-ten Frame behalten',
  'studio.video.th': '. Frame',

  // Concept segmenters (doc 65)
  'studio.readiness.title': 'Concept Segmentation — schreib, was du willst, und bekomm Masks',
  'studio.readiness.before': 'Das sind',
  'studio.readiness.pipelines': 'Pipelines',
  'studio.readiness.after':
    ', keine einzelnen Modelle — deshalb stehen sie nicht unter eigenem Namen in der Liste oben. Jede braucht alle ihre Teile.',
  'studio.readiness.ready': 'Bereit',
  'studio.readiness.notInstalled': 'Nicht installiert',
  'studio.readiness.gated': 'braucht deinen Token',
  'studio.readiness.and': 'und',
  'studio.readiness.install': 'Installiere oben {models}.',
  'studio.readiness.installAccess':
    'Installiere oben {models}, nachdem du auf HuggingFace Zugang beantragt hast — der wird von Hand freigegeben, also nicht sofort.',

  // Open the dataset's folder (doc 59)
  'studio.reveal.gone': 'Dieser Ordner ist nicht mehr da: {folder}',
  'studio.reveal.error': 'Dieser Ordner ließ sich nicht öffnen.',
  'studio.reveal.title': 'Die Bilder dieses Datensatzes im Dateimanager zeigen',
  'studio.reveal.opening': 'Öffnet …',
  'studio.reveal.open': 'Ordner öffnen',

  'studio.actions.unsavedBlocked': 'Dieses Bild hat ungespeicherte Änderungen. Speichere zuerst oder schalte „Automatisch speichern“ ein.',

  // Eine Klasse, angelegt nachdem Bilder gespeichert wurden (Doc 118)
  'studio.newClass.label': 'Neue Klassen und die Bilder, die vor ihnen gespeichert wurden',
  'studio.newClass.question_one': '{name} ist neu. {count} Bild wurde davor gespeichert.',
  'studio.newClass.question_other': '{name} ist neu. {count} Bilder wurden davor gespeichert.',
  'studio.newClass.why': 'Kommt {name} darin vor? Bis du es sagst, lässt SAM 3 sie für {name} weg.',
  'studio.newClass.notThere': 'Kommt dort nicht vor',
  'studio.newClass.later': 'Später durchsehen',
  'studio.newClass.marked_one': '{count} Bild markiert: kein {name}.',
  'studio.newClass.marked_other': '{count} Bilder markiert: kein {name}.',
  'studio.newClass.pending_one': '{name}: {count} Bild noch nicht durchgesehen.',
  'studio.newClass.pending_other': '{name}: {count} Bilder noch nicht durchgesehen.',
  'studio.newClass.review': 'Durchsehen für {name}',

  // Durchsehen für eine Klasse (Doc 119)
  'studio.review.label': 'Durchsehen für {name}',
  'studio.review.title': 'Durchsehen für {name} — Bild {position} von {total}.',
  'studio.review.hint': 'Vorgeschlagen wird nur {name}; deine gespeicherten Annotationen bleiben. Speichere, wenn du fertig bist, oder sag, dass keins da ist.',
  'studio.review.notHere': 'Kein {name} hier →',
  'studio.review.end': 'Durchsehen beenden',

  // Back to the overview (the session survives switching tabs until then)
  'studio.back.button': '← Zurück zur Übersicht',
  'studio.back.hint': 'Deine Stelle hier bleibt erhalten, während du andere Tabs besuchst. „Zurück“ beendet diese Sitzung.',
  'studio.back.unsaved': 'Dieses Bild hat ungespeicherte Änderungen. Sie gehen verloren, wenn du ohne Speichern zurückgehst.',
  'studio.back.saveAndGo': 'Speichern und zurück',
  'studio.back.discard': 'Ohne Speichern zurück',
  'studio.back.stay': 'Bleiben',
};
