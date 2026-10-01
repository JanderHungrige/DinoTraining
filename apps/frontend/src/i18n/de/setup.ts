import type { setupEn } from '../en/setup';
import type { Catalogue } from '../types';

export const setupDe: Catalogue<typeof setupEn> = {
  'setup.title': 'Willkommen bei DinoTraining',
  'setup.intro':
    'Ein Schritt vor dem ersten Start: DinoTraining rechnet seine Modelle mit PyTorch, und das wird jetzt einmal von den offiziellen Servern geladen. Danach funktioniert die App offline.',

  'setup.found.appleSilicon': 'Gefunden: ein Mac mit Apple Silicon. Seine GPU wird über MPS genutzt.',
  'setup.found.nvidia': 'Gefunden: {name}, Treiber {driver}.',
  'setup.found.cpu':
    'Keine NVIDIA-Grafikkarte gefunden, deshalb rechnet DinoTraining auf der CPU. Alles funktioniert; Training und Prescans dauern länger.',
  'setup.note.driverTooOld':
    'Dein NVIDIA-Treiber ({driver}) ist zu alt für die GPU-Version von PyTorch; sie braucht {needed} oder neuer. Aktualisiere den Treiber und starte DinoTraining neu, um die GPU zu nutzen. Bis dahin läuft es auf der CPU.',
  'setup.note.intelMac':
    'Dieser Mac hat einen Intel-Prozessor. PyTorch, das DinoTraining braucht, gibt es für Intel-Macs nicht mehr, deshalb kann DinoTraining hier nicht laufen.',
  'setup.note.unsupported':
    'DinoTraining läuft auf Macs mit Apple Silicon und auf 64-Bit-PCs mit Intel oder AMD unter Windows oder Linux. Dieser Rechner ist {os} auf {arch}.',

  'setup.choice.install': 'Installieren (etwa {gb} GB Download)',
  'setup.choice.gpu': 'Mit GPU-Unterstützung installieren (CUDA {cuda}, etwa {gb} GB Download)',
  'setup.choice.cpuOnly': 'Nur CPU (kleiner, etwa {gb} GB)',

  'setup.progress.python': 'Python wird geladen…',
  'setup.progress.packages': 'PyTorch und die übrigen Pakete werden geladen… {done} von {total} MB',
  'setup.progress.installing': 'Wird installiert…',
  'setup.progress.done': 'Installiert.',
  'setup.progress.starting': 'Die KI-Engine startet…',
  'setup.progress.ready': 'Fertig.',
  'setup.progress.current': '{name} geladen',
  'setup.open': 'DinoTraining öffnen',

  'setup.fail.offline':
    'Keine Internetverbindung. Beim ersten Start werden Python und PyTorch einmal geladen; danach funktioniert DinoTraining offline.',
  'setup.fail.disk':
    'Dafür braucht es etwa {needed} GB freien Platz auf {path}, frei sind {free} GB. Schaffe etwas Platz und versuche es dann noch einmal.',
  'setup.fail.unsupported': 'Auf diesem Rechner kann DinoTraining nicht laufen (siehe oben).',
  'setup.fail.failed': 'Die Installation wurde abgebrochen: {message}',
  'setup.fail.resume': 'Was schon geladen war, bleibt erhalten; ein neuer Versuch macht dort weiter.',
  'setup.variant.cpu': 'der CPU',
  'setup.variant.gpu': 'der GPU (CUDA {cuda})',
  'setup.switch.titleGpu': 'Wechsel auf die GPU',
  'setup.switch.titleCpu': 'Wechsel auf die CPU',
  'setup.switch.intro':
    'PyTorch wird ausgetauscht. Das Backend ist so lange gestoppt; deine Datensätze und Modelle bleiben, wie sie sind.',
  'setup.fail.rolledBack': 'Der Wechsel hat nicht geklappt: {reason} Du bist wieder auf {to}, wie vorher.',
  'setup.back': 'Zurück zur App',
  'setup.update.title': 'DinoTrainings Pakete werden aktualisiert',
  'setup.update.intro':
    'Diese Version von DinoTraining wurde mit neueren Paketen getestet. Geladen wird nur, was sich geändert hat; deine Datensätze und Modelle bleiben, wie sie sind.',
  'setup.update.previous': 'Mit den bisherigen Paketen starten (das Update wird beim nächsten Mal wieder versucht)',
  'setup.retry': 'Noch einmal versuchen',

  'setup.game.label': 'Dino Run: ein kleines Spiel, während DinoTraining installiert. Leertaste oder Klick zum Springen.',
  'setup.game.hint': 'Leertaste oder Klick: über die Steine springen, während du wartest',
  'setup.game.playing': 'Leertaste oder Klick: springen',
  'setup.game.over': 'Autsch. Springen für eine neue Runde',
  'setup.game.score': 'Punkte {score}',
  'setup.game.best': 'Rekord {best}',

  'setup.tip.label': 'Schon gewusst?',
  'setup.tip.backbone':
    'Das Backbone (DINOv2 oder DINOv3) wird nie verändert. Es macht aus jedem Bild Features, und nur der kleine Head darauf lernt: deshalb dauert ein Training Minuten.',
  'setup.tip.head':
    'Ein Head ist ein kleines Modell auf dem Backbone. Ein Backbone kann viele Heads tragen: einen für Boxen, einen für Masks, einen für Tiefe.',
  'setup.tip.phrases':
    'Phrasen sagen Grounding DINO, wonach es suchen soll. Mehrere Phrasen können eine Klasse finden, und eine Verwechslungs-Phrase hält die Fehler draußen.',
  'setup.tip.saved':
    'Ein gespeichertes Bild gilt als vollständig: Was von seinen Klassen nicht markiert ist, wird als Hintergrund gelernt.',
  'setup.tip.generator':
    'Der Dataset Generator annotiert neue Bilder mit einem Head, den du trainiert hast. Du prüfst nur noch seine Vorschläge.',
  'setup.tip.export':
    'Ein trainiertes Modell lässt sich als Zip mit kleiner Runtime und als ONNX exportieren, um es außerhalb von DinoTraining zu nutzen.',
  'setup.tip.offline': 'Modelle werden einmal unter Modelle & Datensätze geladen. Danach braucht DinoTraining kein Internet mehr.',
};
