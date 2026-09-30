"""German for the error messages users see most (the error envelope's `message`, doc 113):
the API's 404/409/422 details and the global handlers in core/errors.py."""

from __future__ import annotations

ENTRIES: dict[str, str] = {
    # core/errors.py and Starlette's defaults
    "Request validation failed.": "Die Anfrage ist ungültig.",
    "An internal error occurred. Check the backend log for details.": (
        "Ein interner Fehler ist aufgetreten. Details stehen im Backend-Log."
    ),
    "Not Found": "Nicht gefunden",
    "Method Not Allowed": "Methode nicht erlaubt",
    # Not found
    "Dataset not found: {dataset}": "Datensatz nicht gefunden: {dataset}",
    "Unknown dataset: {dataset}": "Unbekannter Datensatz: {dataset}",
    "Image not found": "Bild nicht gefunden",
    "Unknown job: {job}": "Unbekannter Auftrag: {job}",
    "Unknown training job: {job}": "Unbekannter Trainingsauftrag: {job}",
    "Unknown head: {head}": "Unbekannter Head: {head}",
    "Unknown model: {model}": "Unbekanntes Modell: {model}",
    "Unknown foundation model: {model}": "Unbekanntes Foundation Model: {model}",
    "Unknown catalogue entry: {entry}": "Unbekannter Katalogeintrag: {entry}",
    "Unknown backbone: {backbone}": "Unbekanntes Backbone: {backbone}",
    "Unknown annotator: {annotator}": "Unbekannter Annotierer: {annotator}",
    "No such run: {job}": "Diesen Lauf gibt es nicht: {job}",
    "No such extraction: {job}": "Diese Extraktion gibt es nicht: {job}",
    "No prescan job {job}": "Keinen Prescan {job}",
    "No such recipe: {recipe}": "Dieses Rezept gibt es nicht: {recipe}",
    "No such phrase: {phrase}": "Diese Phrase gibt es nicht: {phrase}",
    "No such fine-tune job: {job}": "Diesen Fine-Tuning-Auftrag gibt es nicht: {job}",
    "No such default-recipe job: {job}": "Diesen Standardrezept-Auftrag gibt es nicht: {job}",
    "No such audit: {job}": "Diese Prüfung gibt es nicht: {job}",
    "No fine-tuned model {model}": "Kein fine-getuntes Modell {model}",
    "No fine-tunable model {model}": "Kein fine-tunebares Modell {model}",
    "This dataset has not been audited yet.": "Dieser Datensatz wurde noch nicht geprüft.",
    "This dataset has not been split yet.": "Dieser Datensatz hat noch keinen Split.",
    "No second look has been started.": "Es wurde noch kein Zweiter Blick gestartet.",
    "Frame {#index} is outside 0..{#last}": "Frame {index} liegt außerhalb von 0..{last}",
    # Refusals
    "Audit this dataset first: the fix uses its findings.": (
        "Prüfe diesen Datensatz zuerst: Die Korrektur nutzt die Befunde der Prüfung."
    ),
    "{name} is not a stored class in this dataset.": (
        "{name} ist keine gespeicherte Klasse in diesem Datensatz."
    ),
    "Not images of this dataset: {paths}": "Keine Bilder dieses Datensatzes: {paths}",
    "The picture cannot be read: {error}": "Das Bild lässt sich nicht lesen: {error}",
    "Invalid model path": "Ungültiger Modellpfad",
    "Refusing to delete the cache root": "Das Cache-Hauptverzeichnis wird nicht gelöscht",
    # Models that are not installed or are gated
    "{model} is not installed — download the backbone first.": (
        "{model} ist nicht installiert – lade zuerst das Backbone herunter."
    ),
    "{model} is not installed — download it in Admin / Models first.": (
        "{model} ist nicht installiert – lade es zuerst unter Verwaltung / Modelle herunter."
    ),
    "{model} is not installed — download it first.": (
        "{model} ist nicht installiert – lade es zuerst herunter."
    ),
    "{model} is not installed. Download it in Admin / Models first.": (
        "{model} ist nicht installiert. Lade es zuerst unter Verwaltung / Modelle herunter."
    ),
    "{model} is not installed. Download it in the Admin tab before annotating.": (
        "{model} ist nicht installiert. Lade es vor dem Annotieren unter Verwaltung herunter."
    ),
    "{model} is not installed. Download it from the Admin tab — {name} needs {models}.": (
        "{model} ist nicht installiert. Lade es unter Verwaltung herunter – {name} braucht "
        "{models}."
    ),
    "{model} is already installed": "{model} ist schon installiert",
    "Download in progress for {model}": "{model} wird gerade heruntergeladen",
    "Download already running for {model}": "Der Download von {model} läuft schon",
    "{model} is gated. Accept the licence at {url}, then set HF_TOKEN in .env and restart.": (
        "{model} ist zugangsbeschränkt. Akzeptiere die Lizenz unter {url}, trag dann HF_TOKEN "
        "in .env ein und starte neu."
    ),
    "That does not look like a HuggingFace access token. Create one at "
    "https://huggingface.co/settings/tokens — a read token is enough.": (
        "Das sieht nicht nach einem HuggingFace-Zugangstoken aus. Erstelle eins unter "
        "https://huggingface.co/settings/tokens – ein Lese-Token reicht."
    ),
}

__all__ = ["ENTRIES"]
