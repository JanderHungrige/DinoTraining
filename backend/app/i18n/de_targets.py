"""German for the annotation-target matrix (doc 104: datasets/annotation_targets.py) and the
Prepare data profiles' labels (doc 81: prep/profiles.py)."""

from __future__ import annotations

_CLASS_FROM_BOXES = (
    "A classifier takes a picture's class from its annotations; a picture with two classes "
    "is skipped."
)
_BOX_FROM_OUTLINE = "Each outline's box is derived from it; nothing extra to draw."

ENTRIES: dict[str, str] = {
    # Layers
    "One class per picture": "Eine Klasse pro Bild",
    "Boxes": "Boxen",
    "Outlines (masks)": "Umrisse (Masks)",
    "Phrases": "Phrasen",
    "Checked per picture": "Pro Bild geprüft",
    "Complete when saved": "Vollständig beim Speichern",
    # Targets
    "Keep all options open": "Alle Möglichkeiten offenhalten",
    "Boxes, outlines and phrases — any model can train on it later. Recommended.": (
        "Boxen, Umrisse und Phrasen – später kann jedes Modell damit trainieren. Empfohlen."
    ),
    "Picture classifier": "Bildklassifikator",
    "One class per picture.": "Eine Klasse pro Bild.",
    "Detector (boxes)": "Detektor (Boxen)",
    "A tight box around every object.": "Eine enge Box um jedes Objekt.",
    "Instance outlines (SAM 2)": "Umrisse pro Objekt (SAM 2)",
    "One outline per object, in your convention.": "Ein Umriss pro Objekt, nach deiner Konvention.",
    "Concept outlines (SAM 3)": "Begriffs-Umrisse (SAM 3)",
    "Every instance of each phrase outlined, and each picture checked.": (
        "Jedes Vorkommen jeder Phrase umrissen und jedes Bild geprüft."
    ),
    # Why each layer
    _CLASS_FROM_BOXES: (
        "Ein Klassifikator nimmt die Klasse eines Bildes aus seinen Annotationen; ein Bild mit "
        "zwei Klassen wird übersprungen."
    ),
    "Outlines keep this dataset usable for SAM 2 and SAM 3 later — one click from your boxes.": (
        "Umrisse halten diesen Datensatz später für SAM 2 und SAM 3 nutzbar – ein Klick aus "
        "deinen Boxen."
    ),
    "Only SAM 3 reads phrases; the class name already is one.": (
        "Nur SAM 3 liest Phrasen; der Klassenname ist schon eine."
    ),
    "Only SAM 3 uses it: which pictures are complete for which class.": (
        "Nur SAM 3 nutzt das: welche Bilder für welche Klasse vollständig sind."
    ),
    (
        "A saved picture counts as complete for the classes that exist then; SAM 3 learns "
        "'not here' from it. Pictures saved before a class was added are reviewed for it."
    ): (
        "Ein gespeichertes Bild gilt als vollständig für die Klassen, die es dann gibt; SAM 3 "
        "lernt daraus „nicht hier“. Bilder, die vor einer neuen Klasse gespeichert wurden, "
        "werden für sie durchgesehen."
    ),
    "Only SAM 3 uses it: which pictures were checked for a phrase.": (
        "Nur SAM 3 nutzt das: welche Bilder für eine Phrase geprüft wurden."
    ),
    "Every model starts from knowing where the objects are.": (
        "Jedes Modell fängt damit an, zu wissen, wo die Objekte sind."
    ),
    "SAM 2 and SAM 3 need outlines; they come from your boxes in one click.": (
        "SAM 2 und SAM 3 brauchen Umrisse; die entstehen mit einem Klick aus deinen Boxen."
    ),
    "The class name is already a phrase; 2–4 variations help SAM 3 understand other wordings.": (
        "Der Klassenname ist schon eine Phrase; 2–4 Varianten helfen SAM 3, andere "
        "Formulierungen zu verstehen."
    ),
    "SAM 3 learns 'not here' only from pictures you checked, never from ones you skipped.": (
        "SAM 3 lernt „nicht hier“ nur aus Bildern, die du geprüft hast, nie aus übersprungenen."
    ),
    "Every picture's annotations name one class — mark the main object; a picture with two "
    "is skipped.": (
        "Die Annotationen jedes Bildes nennen eine Klasse – markiere das Hauptobjekt; ein Bild "
        "mit zwei wird übersprungen."
    ),
    "One box on the main object is enough to name the picture; more boxes keep it useful for "
    "a detector.": (
        "Eine Box auf dem Hauptobjekt reicht, um das Bild zu benennen; mehr Boxen halten es für "
        "einen Detektor nützlich."
    ),
    "One tight box around every object of every class you train — a missed object is taught "
    "as background.": (
        "Eine enge Box um jedes Objekt jeder Klasse, die du trainierst – ein übersehenes Objekt "
        "wird als Hintergrund gelernt."
    ),
    _BOX_FROM_OUTLINE: (
        "Die Box jedes Umrisses wird aus ihm abgeleitet; du musst nichts zusätzlich zeichnen."
    ),
    "One outline per object, drawn the way you want SAM to draw it: what counts as part of "
    "the object.": (
        "Ein Umriss pro Objekt, so gezeichnet, wie SAM ihn zeichnen soll: was als Teil des "
        "Objekts zählt."
    ),
    "Every instance of a phrase in the picture is outlined — one left out is taught as 'not "
    "this'.": (
        "Jedes Vorkommen einer Phrase im Bild ist umrissen – ein ausgelassenes wird als „das "
        "nicht“ gelernt."
    ),
    "What you would type to find it: the class name plus 2–4 variations. More synonyms are "
    "not needed.": (
        "Was du eintippen würdest, um es zu finden: der Klassenname plus 2–4 Varianten. Mehr "
        "Synonyme braucht es nicht."
    ),
    "Mark each picture 'all marked' or 'not in this picture' per phrase: an unchecked picture "
    "teaches nothing, a checked empty one teaches 'not here'.": (
        "Markiere jedes Bild pro Phrase mit „alles markiert“ oder „nicht in diesem Bild“: Ein "
        "ungeprüftes Bild bringt nichts bei, ein geprüftes leeres bringt „nicht hier“ bei."
    ),
    "Unknown annotation target: {target}. Known: {known}": (
        "Unbekanntes Annotationsziel: {target}. Bekannt: {known}"
    ),
    # Prepare data profiles (profiles.py)
    "Detection head on DINOv2": "Detection-Head auf DINOv2",
    "Detection head on DINOv3": "Detection-Head auf DINOv3",
    "Segmentation head on DINOv2": "Segmentation-Head auf DINOv2",
    "Segmentation head on DINOv3": "Segmentation-Head auf DINOv3",
    "Classification head on DINOv2": "Klassifikations-Head auf DINOv2",
    "Classification head on DINOv3": "Klassifikations-Head auf DINOv3",
    "Fine-tune {model}": "{model} fine-tunen",
}

__all__ = ["ENTRIES"]
