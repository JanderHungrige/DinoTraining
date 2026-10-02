# Microsoft-Store-Eintrag — Deutsch (de-de)

Doc 154. Jeden Abschnitt in Partner Center → Store-Einträge → Deutsch (Deutschland) kopieren.

## Produktname

V-Rex

## Kurzbeschreibung

V-Rex, Vision Representation & Experimentation: eine kostenlose Trainings-Pipeline für Vision-Foundation-Models. Bring einem Bildmodell mit ein paar hundert Bildern etwas bei: mit Grounding DINO und SAM annotieren, kleine Heads auf eingefrorenen DINOv2/DINOv3-Backbones in Minuten trainieren, anwenden und neue Daten annotieren lassen. Der erste Start lädt Python und PyTorch (etwa 1–6 GB).

## Beschreibung

Der erste Start lädt, worauf die App läuft: Python und PyTorch von GitHub, PyPI und pytorch.org, etwa 1 GB für die CPU-Version und bis zu 6 GB für NVIDIA-Grafikkarten (CUDA). Fehlt Windows eine aktuelle Microsoft-Visual-C++-Laufzeit, bietet die App an, sie von Microsoft zu installieren. Modelle (DINOv2, DINOv3, Grounding DINO, SAM) kommen von Hugging Face, wenn du sie auswählst.

V-Rex (Vision Representation & Experimentation) ist eine Trainings-Pipeline für Vision-Foundation-Models. Es deckt den ganzen Kreislauf auf deinem eigenen Rechner ab:

- Annotieren: Schreib, wonach du suchst, und Grounding DINO und SAM zeichnen Boxen und Masken; du nimmst sie an, korrigierst oder verwirfst sie.
- Trainieren: kleine Heads (Klassifikation, Detektion, Segmentierung, Tiefe) auf einem eingefrorenen DINOv2- oder DINOv3-Backbone, in Minuten, auf der CPU oder einer NVIDIA-Grafikkarte.
- Anwenden: ein trainiertes Modell auf neue Bilder loslassen und prüfen, was es findet.
- Daten erzeugen: ein trainiertes Modell neue Bilder annotieren lassen, die Vorschläge prüfen, neu trainieren.

Deine Arbeit bleibt deine: Bilder, Annotationen und Modelle bleiben auf deinem Rechner oder in dem Cloud-Speicher, den du selbst verbindest (Amazon S3, Azure Blob Storage, Google Cloud Storage). Annotationen werden in den Ordner des Datensatzes oder einen Ordner deiner Wahl exportiert, per Knopf, beim Schließen der App oder alle paar Minuten. Kein Konto, keine Telemetrie.

Importiert COCO-, YOLO-, Pascal-VOC- und OpenLABEL-Datensätze; exportiert COCO. Open Source unter der MIT-Lizenz.

## Neuerungen in dieser Version

Versionshinweise: https://github.com/JanderHungrige/DinoTraining/releases

## Produktfeatures

- Annotieren mit Text-Prompts: Boxen von Grounding DINO, Masken von SAM
- Klassifikations-, Detektions- und Segmentierungs-Heads auf eingefrorenem DINOv2/DINOv3 trainieren
- Läuft auf CPU oder NVIDIA-Grafikkarte (CUDA), in der App umschaltbar
- Modellgestütztes Annotieren neuer Daten
- Datensätze in der Cloud: Amazon S3, Azure Blob Storage, Google Cloud Storage
- Automatischer Export von Annotationen und Modellen
- Importiert COCO, YOLO, Pascal VOC und OpenLABEL; exportiert COCO
- MLflow-Tracking (optional)
- Deutsch und Englisch
- Kein Konto, keine Telemetrie, Open Source (MIT)

## Suchbegriffe (max. 7)

Bildverarbeitung; Annotation; DINOv2; Objekterkennung; Segmentierung; maschinelles Lernen; PyTorch

## Zusätzliche Systemanforderungen

- Mindestens: Windows 10 Version 1809 (64 Bit), 8 GB Arbeitsspeicher, 10 GB freier Speicherplatz, Internetverbindung für den ersten Start
- Empfohlen: 16 GB Arbeitsspeicher, eine NVIDIA-Grafikkarte mit 6 GB oder mehr

## Links

- Datenschutzerklärung: https://dino.w3rth.de/privacy.html#de
- Website: https://dino.w3rth.de
- Support: https://github.com/JanderHungrige/DinoTraining/issues
- Copyright- und Markeninformationen: © 2026 JanderHungrige
