"""German for what each fine-tunable model needs (doc 92: requirements.py) and the
readiness checks before a job starts (preflight.py)."""

from __future__ import annotations

_MASKS = (
    "One mask per object, per image: an outline of exactly that object, stored as an "
    "annotation with its class name. Boxes alone are not enough; the model learns outlines "
    "from outlines. Make masks in the Annotation Studio or the Dataset Generator with "
    "Grounded SAM, then correct them. Reject wrong masks rather than deleting them: a "
    "rejected mask teaches 'not this'. Every image must be segmented completely for the "
    "classes you train, because an object left without a mask is taught as background."
)
_MASKS_DE = (
    "Ein Umriss (Mask) pro Objekt und Bild: ein Umriss genau dieses Objekts, gespeichert als "
    "Annotation mit seinem Klassennamen. Boxen allein reichen nicht; das Modell lernt Umrisse "
    "aus Umrissen. Erstelle Umrisse im Annotation Studio oder im Datensatz-Generator mit "
    "Grounded SAM und korrigiere sie dann. Lehne falsche Umrisse ab, statt sie zu löschen: "
    "Ein abgelehnter Umriss bringt „das nicht“ bei. Jedes Bild muss für die Klassen, die du "
    "trainierst, vollständig umrissen sein, denn ein Objekt ohne Umriss wird als Hintergrund "
    "gelernt."
)

FRAGMENTS: dict[str, str] = {
    "every class": "jede Klasse",
}

ENTRIES: dict[str, str] = {
    # requirements.py
    "{model} — classification": "{model} — Klassifikation",
    "{model} — segmentation": "{model} — Segmentation",
    "RF-DETR starts from COCO detection and adapts in a few epochs, so it needs far less than "
    "a head trained from scratch, but not nothing.": (
        "RF-DETR startet von der COCO-Detection und passt sich in wenigen Epochs an. Es "
        "braucht also viel weniger als ein Head, der von null lernt – aber nicht nichts."
    ),
    "Any size; resized (stretched) to 384 px. Small objects need tiles (see Prepare data → "
    "What the model sees).": (
        "Jede Größe; wird auf 384 px verkleinert (gestreckt). Kleine Objekte brauchen Tiles "
        "(siehe Daten vorbereiten → Was das Modell sieht)."
    ),
    "One box per object: a tight rectangle around each object, with its class name. Every "
    "object of a trained class in every image must be boxed, or the missing ones are taught "
    "as background. Mark boxes you are unsure of 'unclear'.": (
        "Eine Box pro Objekt: ein enges Rechteck um jedes Objekt, mit seinem Klassennamen. "
        "Jedes Objekt einer trainierten Klasse muss in jedem Bild eine Box haben, sonst werden "
        "die fehlenden als Hintergrund gelernt. Markiere Boxen, bei denen du unsicher bist, als "
        "„unklar“."
    ),
    "The projector and the detection decoder; the DINOv2 backbone stays frozen unless you "
    "unfreeze its last blocks.": (
        "Der Projektor und der Detection-Decoder; das DINOv2-Backbone bleibt eingefroren, außer "
        "du gibst seine letzten Blöcke frei."
    ),
    "SAM already segments almost anything; fine-tuning teaches it where your objects' edges "
    "are. Fifty outlines per class show it enough of them.": (
        "SAM umreißt schon fast alles; das Fine-Tuning zeigt ihm, wo die Ränder deiner Objekte "
        "liegen. Fünfzig Umrisse pro Klasse zeigen ihm genug davon."
    ),
    "Any size; resized (stretched) to 1024 px. Outlines are learned at 256 px, so detail finer "
    "than about 4 input pixels cannot improve.": (
        "Jede Größe; wird auf 1024 px verkleinert (gestreckt). Umrisse werden bei 256 px "
        "gelernt, also kann Detail feiner als etwa 4 Eingabepixel nicht besser werden."
    ),
    _MASKS: _MASKS_DE,
    _MASKS + " The prompt for each mask is made from the mask itself (its box, jittered), so "
    "you do not provide prompts.": _MASKS_DE
    + " Der Prompt für jeden Umriss entsteht aus dem Umriss selbst (seiner Box, leicht "
    "verschoben), du musst also keine Prompts angeben.",
    _MASKS + " The class name is the noun phrase SAM 3 is prompted with, so name classes the "
    "way you would ask for them ('rail signal', not 'class_3'). Images where a phrase has no "
    "instance are useful: they teach 'none here'.": _MASKS_DE
    + " Der Klassenname ist die Phrase, mit der SAM 3 gefragt wird. Benenne Klassen also so, "
    "wie du danach fragen würdest („Bahnsignal“, nicht „class_3“). Bilder, in denen eine "
    "Phrase nicht vorkommt, sind nützlich: Sie bringen „keins hier“ bei.",
    "The mask decoder only. The image encoder stays frozen, which keeps it fast and saves the "
    "result in a few megabytes.": (
        "Nur der Mask-Decoder. Der Image-Encoder bleibt eingefroren; das hält es schnell und "
        "speichert das Ergebnis in wenigen Megabyte."
    ),
    "SAM 3 finds every instance of a phrase; it needs enough images per phrase to learn both "
    "what the phrase means here and where its edges are.": (
        "SAM 3 findet jedes Vorkommen einer Phrase; es braucht genug Bilder pro Phrase, um zu "
        "lernen, was die Phrase hier bedeutet und wo ihre Ränder liegen."
    ),
    "Any size; resized to 1008 px.": "Jede Größe; wird auf 1008 px verkleinert.",
    "The detection and mask decoders and the scoring head (15 M of 840 M parameters); the "
    "image and text encoders stay frozen. About 6 s per picture the first round on an M1, "
    "then about 1 s.": (
        "Die Detection- und Mask-Decoder und der Scoring-Head (15 M von 840 M Parametern); "
        "Image- und Text-Encoder bleiben eingefroren. Etwa 6 s pro Bild in der ersten Epoch "
        "auf einem M1, danach etwa 1 s."
    ),
    "Gated on HuggingFace: Meta approves access by hand.": (
        "Auf HuggingFace zugangsbeschränkt: Meta gibt den Zugang von Hand frei."
    ),
    "About 3.2 GB of weights; training needs roughly 16 GB of memory.": (
        "Etwa 3.2 GB Weights; das Training braucht ungefähr 16 GB Arbeitsspeicher."
    ),
    "Unfreezing part of a backbone changes features every other head relies on; with less "
    "data it forgets more than it learns.": (
        "Einen Teil des Backbones freizugeben verändert Features, auf die sich jeder andere Head "
        "verlässt; mit weniger Daten vergisst es mehr, als es lernt."
    ),
    "Any size; letterboxed to 448 px (224 for classification).": (
        "Jede Größe; mit Rand auf 448 px eingepasst (224 für Klassifikation)."
    ),
    "One class per image: each image has boxes of exactly one class (the class of the image). "
    "Images with several classes are skipped.": (
        "Eine Klasse pro Bild: Jedes Bild hat Boxen genau einer Klasse (der Klasse des Bildes). "
        "Bilder mit mehreren Klassen werden übersprungen."
    ),
    "The last blocks of the backbone together with a task head, saved as a new backbone "
    "variant with its own id. Heads trained on the original backbone never run on the "
    "variant.": (
        "Die letzten Blöcke des Backbones zusammen mit einem Aufgaben-Head, gespeichert als neue "
        "Backbone-Variante mit eigener ID. Heads, die auf dem ursprünglichen Backbone trainiert "
        "wurden, laufen nie auf der Variante."
    ),
    "Gated on HuggingFace: accept the DINOv3 licence and set a token.": (
        "Auf HuggingFace zugangsbeschränkt: Akzeptiere die DINOv3-Lizenz und hinterlege ein Token."
    ),
    # preflight.py — the model
    "This model can be fine-tuned here": "Dieses Modell lässt sich hier fine-tunen",
    "Yes.": "Ja.",
    "{+label} is installed": "{+label} ist installiert",
    "Installed.": "Installiert.",
    "Not downloaded yet.": "Noch nicht heruntergeladen.",
    "Download it in Admin / Models.": "Lade es unter Verwaltung / Modelle herunter.",
    "Download it in Admin / Models (it is gated: set a HuggingFace token first).": (
        "Lade es unter Verwaltung / Modelle herunter (es ist zugangsbeschränkt: hinterlege "
        "zuerst ein HuggingFace-Token)."
    ),
    # preflight.py — the data
    "The dataset has boxes": "Der Datensatz hat Boxen",
    "The dataset has instance masks": "Der Datensatz hat Masks pro Objekt",
    "The dataset has phrase masks": "Der Datensatz hat Masks pro Phrase",
    "The dataset has image labels": "Der Datensatz hat Klassen pro Bild",
    "{#count} found.": "{count} gefunden.",
    "No boxes found.": "Keine Boxen gefunden.",
    "No instance masks found.": "Keine Masks pro Objekt gefunden.",
    "No phrase masks found.": "Keine Masks pro Phrase gefunden.",
    "No image labels found.": "Keine Klassen pro Bild gefunden.",
    "At least {#count} images with boxes": "Mindestens {count} Bilder mit Boxen",
    "At least {#count} images with instance masks": (
        "Mindestens {count} Bilder mit Masks pro Objekt"
    ),
    "At least {#count} images with phrase masks": (
        "Mindestens {count} Bilder mit Masks pro Phrase"
    ),
    "At least {#count} images with image labels": "Mindestens {count} Bilder mit Klassen pro Bild",
    "{#count} images.": "{count} Bilder.",
    "Annotate more images.": "Annotiere mehr Bilder.",
    "Annotate more images. {*why}": "Annotiere mehr Bilder. {*why}",
    "At least {#count} per class": "Mindestens {count} pro Klasse",
    "No classes.": "Keine Klassen.",
    "Annotate more of: {+names}, or leave those classes out in Prepare data → Fix. {*why}": (
        "Annotiere mehr von: {+names} – oder lass diese Klassen unter Daten vorbereiten → "
        "Sicher korrigieren weg. {*why}"
    ),
    # The same fix inside a refusal, where it follows the check's detail (preflight.refusal).
    "Annotate more of: {+names}, or leave those classes out in Prepare data → Fix.": (
        "Annotiere mehr von: {+names} – oder lass diese Klassen unter Daten vorbereiten → "
        "Sicher korrigieren weg."
    ),
    "{counts} Annotate more of: {+names}, or leave those classes out in Prepare data → Fix.": (
        "{counts} Annotiere mehr von: {+names} – oder lass diese Klassen unter Daten "
        "vorbereiten → Sicher korrigieren weg."
    ),
    # preflight.py — the recipe
    "A preparation recipe": "Ein Vorbereitungsrezept",
    "A preparation recipe (required)": "Ein Vorbereitungsrezept (erforderlich)",
    "None given.": "Keins angegeben.",
    "Prepare data → save a recipe, then choose it here. Its leak-free split is what the base "
    "and fine-tuned models are compared on.": (
        "Daten vorbereiten → speichere ein Rezept und wähle es dann hier. Auf seinem Split "
        "ohne Überschneidungen werden Foundation Model und fine-getuntes Modell verglichen."
    ),
    "No such recipe.": "Dieses Rezept gibt es nicht.",
    "'{name}' v{#version}.": "„{name}“ v{version}.",
    "'{name}' v{#version}: {*reasons}": "„{name}“ v{version}: {*reasons}",
    "Save the recipe again in Prepare data.": "Speichere das Rezept unter Daten vorbereiten neu.",
}

__all__ = ["ENTRIES", "FRAGMENTS"]
