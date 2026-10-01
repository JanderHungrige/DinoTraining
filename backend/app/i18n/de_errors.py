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
    # Phrases (docs 103, 115)
    "A phrase cannot be empty.": "Eine Phrase darf nicht leer sein.",
    "'{a}' is a phrase of class '{b}', not '{c}'.": (
        "„{a}“ ist eine Phrase der Klasse „{b}“, nicht „{c}“."
    ),
    "'{a}' is a variation of '{b}'; use '{b2}' instead.": (
        "„{a}“ ist eine Variante von „{b}“; nimm stattdessen „{b2}“."
    ),
    (
        "'{a}' is already a phrase of its own; it cannot also be a variation of '{b}'. "
        "Delete one, or merge them."
    ): (
        "„{a}“ ist schon eine eigene Phrase und kann nicht zugleich Variante von „{b}“ sein. "
        "Lösch eine davon oder führ sie zusammen."
    ),
    (
        "An umbrella term needs at least {#n} classes; for one class, add '{a}' as a "
        "variation of it instead."
    ): (
        "Ein Oberbegriff braucht mindestens {#n} Klassen; für eine Klasse füg „{a}“ "
        "stattdessen als Variante hinzu."
    ),
    "Not a class of this dataset: {names}.": "Keine Klasse dieses Datensatzes: {names}.",
    "'{a}' is already a class; an umbrella term needs a name of its own.": (
        "„{a}“ ist schon eine Klasse; ein Oberbegriff braucht einen eigenen Namen."
    ),
    "'{a}' is already a phrase of this dataset.": "„{a}“ ist schon eine Phrase dieses Datensatzes.",
    "'{a}' is a variation of '{b}'; use another name.": (
        "„{a}“ ist eine Variante von „{b}“; nimm einen anderen Namen."
    ),
    "'{a}' belongs to class '{b}'; only an umbrella term has several classes.": (
        "„{a}“ gehört zur Klasse „{b}“; nur ein Oberbegriff hat mehrere Klassen."
    ),
    (
        "'{a}' is an umbrella term: it already applies to every outline of its classes, "
        "and is not linked to single outlines."
    ): (
        "„{a}“ ist ein Oberbegriff: Er gilt schon für jeden Umriss seiner Klassen und wird "
        "nicht mit einzelnen Umrissen verknüpft."
    ),
    # MLflow (doc 123)
    "The tracking URI must start with http:// or https://.": (
        "Die Tracking-URI muss mit http:// oder https:// beginnen."
    ),
    "MLflow is not set up: no tracking URI.": "MLflow ist nicht eingerichtet: keine Tracking-URI.",
    "MLflow at {uri} is not reachable: {*reason}": (
        "MLflow unter {uri} ist nicht erreichbar: {reason}"
    ),
    "MLflow answered {#code}: {*reason}": "MLflow antwortete {code}: {reason}",
    "Connected. Experiment '{name}' has id {id}.": (
        "Verbunden. Das Experiment „{name}“ hat die ID {id}."
    ),
    "No such backfill: {job}": "Diesen Versand gibt es nicht: {job}",
    "{#n} heads were not trained here (defaults, imports).": (
        "{n} Heads wurden nicht hier trainiert (Voreinstellungen, Importe)."
    ),
}

__all__ = ["ENTRIES"]
