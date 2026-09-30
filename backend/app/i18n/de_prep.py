"""German for Prepare data's plans: unequal classes (doc 86: balance_plan.py), changed copies
(doc 87: augment_plan.py and ml/augment.py's presets) and what the model sees (doc 85:
input_plan.py). Reasons are catalogued sentence by sentence where the code assembles them,
so every combination translates."""

from __future__ import annotations

FRAGMENTS: dict[str, str] = {
    "general photos": "Allgemeine Fotos",
    "outdoor, road and rail": "Draußen, Straße und Schiene",
    "indoor and products": "Drinnen und Produkte",
    "microscopy and top-down": "Mikroskopie und Draufsicht",
    "documents and text": "Dokumente und Text",
}

ENTRIES: dict[str, str] = {
    # Unequal classes: the options
    "Leave it": "So lassen",
    "Train on the data as it is. Right when the classes are roughly equal.": (
        "Trainiere mit den Daten, wie sie sind. Richtig, wenn die Klassen ungefähr gleich groß "
        "sind."
    ),
    "Make rare classes count more": "Seltene Klassen stärker zählen",
    "A mistake on a rare class costs the model more than one on a common class, so it cannot "
    "get away with ignoring it. Nothing is repeated, so nothing is memorised. Best for "
    "whole-image labels and outlines, and for boxes when the rare class shares its pictures "
    "with common ones.": (
        "Ein Fehler bei einer seltenen Klasse kostet das Modell mehr als einer bei einer "
        "häufigen, also kommt es nicht damit durch, sie zu übergehen. Nichts wird wiederholt, "
        "also wird nichts auswendig gelernt. Am besten für Klassen pro Bild und Umrisse – und "
        "für Boxen, wenn die seltene Klasse ihre Bilder mit häufigen teilt."
    ),
    "Show rare classes more often": "Seltene Klassen öfter zeigen",
    "Pictures with rare classes are shown several times per round of training. Best for boxes "
    "when the rare classes have pictures of their own: every picture is mostly background, "
    "which can drown out a weighted loss.": (
        "Bilder mit seltenen Klassen werden pro Trainingsdurchgang mehrmals gezeigt. Am besten "
        "für Boxen, wenn die seltenen Klassen eigene Bilder haben: Jedes Bild ist größtenteils "
        "Hintergrund, und der kann eine stärkere Gewichtung übertönen."
    ),
    # Unequal classes: the recommendation
    "The largest class has {ratio}× the examples of the smallest. That is close enough to "
    "equal that any correction would do more harm than good.": (
        "Die größte Klasse hat {ratio}× so viele Beispiele wie die kleinste. Das ist nah genug "
        "an gleich, dass jede Korrektur mehr schaden als nützen würde."
    ),
    "Classes differ by {ratio}×, and this model finds boxes. Every picture is mostly "
    "background, which would drown out a weighted loss, so showing the pictures with '{name}' "
    "more often ({repeat}× per round) works better.": (
        "Die Klassen unterscheiden sich um {ratio}×, und dieses Modell findet Boxen. Jedes Bild "
        "ist größtenteils Hintergrund, der eine stärkere Gewichtung übertönen würde – deshalb "
        "wirkt es besser, die Bilder mit „{name}“ öfter zu zeigen ({repeat}× pro Durchgang)."
    ),
    "Classes differ by {ratio}×, but '{name}' appears in {images} pictures alongside the "
    "common classes. Showing those pictures more often would show the common classes more "
    "often too. Counting each '{name}' more heavily corrects the balance instead.": (
        "Die Klassen unterscheiden sich um {ratio}×, aber „{name}“ kommt in {images} Bildern "
        "zusammen mit den häufigen Klassen vor. Diese Bilder öfter zu zeigen, würde auch die "
        "häufigen Klassen öfter zeigen. Jedes „{name}“ stärker zu zählen, gleicht stattdessen "
        "aus."
    ),
    "Classes differ by {ratio}×. Making mistakes on rare classes cost more corrects that "
    "without showing the same pictures over and over.": (
        "Die Klassen unterscheiden sich um {ratio}×. Wenn Fehler bei seltenen Klassen mehr "
        "kosten, gleicht das aus, ohne dieselben Bilder immer wieder zu zeigen."
    ),
    "No annotated objects yet.": "Noch keine annotierten Objekte.",
    "'{name}' has only {count} example(s). No setting can invent the variety that is missing: "
    "add more, or merge or leave out this class in the Fix step.": (
        "„{name}“ hat nur {count} Beispiel(e). Keine Einstellung kann die fehlende Vielfalt "
        "erfinden: Füge mehr hinzu oder leg diese Klasse im Schritt „Sicher korrigieren“ mit "
        "einer anderen zusammen oder lass sie weg."
    ),
    # Changed copies: the presets (ml/augment.py)
    "No changes": "Keine Änderungen",
    "Every picture is shown as it is.": "Jedes Bild wird so gezeigt, wie es ist.",
    "General photos": "Allgemeine Fotos",
    "Mirrored left-right, cropped a little, lighting varied. A safe start for everyday objects.": (
        "Links-rechts gespiegelt, etwas zugeschnitten, Licht verändert. Ein sicherer Anfang für "
        "Alltagsgegenstände."
    ),
    "Outdoor, road and rail": "Draußen, Straße und Schiene",
    "Lighting and weather varied strongly, slight blur and grain. Never mirrored: traffic and "
    "signals have a side.": (
        "Licht und Wetter stark verändert, leichte Unschärfe und Körnung. Nie gespiegelt: "
        "Verkehr und Signale haben eine Seite."
    ),
    "Indoor and products": "Drinnen und Produkte",
    "Mirrored left-right, cropped a little, lighting varied moderately.": (
        "Links-rechts gespiegelt, etwas zugeschnitten, Licht mäßig verändert."
    ),
    "Microscopy and top-down": "Mikroskopie und Draufsicht",
    "Turned and mirrored in every direction (a cell has no up), staining varied slightly, "
    "occasionally out of focus.": (
        "In jede Richtung gedreht und gespiegelt (eine Zelle hat kein Oben), Färbung leicht "
        "verändert, gelegentlich unscharf."
    ),
    "Documents and text": "Dokumente und Text",
    "Contrast, blur and grain varied as a scanner or camera would. Never mirrored or turned: "
    "text read backwards is not text.": (
        "Kontrast, Unschärfe und Körnung verändert, wie es ein Scanner oder eine Kamera täte. "
        "Nie gespiegelt oder gedreht: Rückwärts gelesener Text ist kein Text."
    ),
    # Changed copies: the recommendation, sentence by sentence
    "A guess from the class names ({names}): {+preset}.": (
        "Eine Vermutung anhand der Klassennamen ({names}): {+preset}."
    ),
    "Look at the preview, and pick another if your pictures are different.": (
        "Sieh dir die Vorschau an und wähle eine andere, wenn deine Bilder anders sind."
    ),
    "The class names do not suggest a particular kind of picture, so the general preset.": (
        "Die Klassennamen deuten auf keine bestimmte Art von Bild hin, also die allgemeine "
        "Voreinstellung."
    ),
    "Look at the preview, and pick one closer to your pictures if there is one.": (
        "Sieh dir die Vorschau an und wähle eine, die näher an deinen Bildern ist, falls es eine "
        "gibt."
    ),
    "Mirroring is left out because of {names}: mirrored, it may mean something else.": (
        "Spiegeln bleibt wegen {names} weg: Gespiegelt könnte es etwas anderes bedeuten."
    ),
    "Unknown augmentation preset: {preset}": (
        "Unbekannte Voreinstellung für veränderte Kopien: {preset}"
    ),
    "The dataset has no images to preview.": "Der Datensatz hat keine Bilder für eine Vorschau.",
    # What the model sees: tiling (input_plan.py)
    "Tiling is available for box targets only.": "Kacheln gibt es nur für Boxen als Ziel.",
    "A whole-image label describes the whole picture, so cutting it up would give each tile a "
    "label that may not be true for it.": (
        "Eine Klasse für das ganze Bild beschreibt das ganze Bild. Es zu zerschneiden, gäbe "
        "jeder Kachel eine Klasse, die für sie vielleicht nicht stimmt."
    ),
    "Outlines would have to be cut along with the picture, which is not supported yet.": (
        "Umrisse müssten mit dem Bild zerschnitten werden, und das geht noch nicht."
    ),
    "If objects are too small, crop the images around them before importing, or choose a "
    "model with a larger input.": (
        "Sind Objekte zu klein, schneide die Bilder vor dem Import um sie herum zu – oder wähle "
        "ein Modell mit größerer Eingabe."
    ),
    "No annotated objects to judge.": "Keine annotierten Objekte zum Beurteilen.",
    "Objects are large enough: the smallest tenth arrive at {p10} px, and the model needs "
    "about {needed} px.": (
        "Die Objekte sind groß genug: Das kleinste Zehntel kommt mit {p10} px an, und das Modell "
        "braucht etwa {needed} px."
    ),
    "Tiling is off, so {share} of objects stay below the {needed} px this model needs, and "
    "it cannot learn those.": (
        "Kacheln sind aus, also bleiben {share} der Objekte unter den {needed} px, die dieses "
        "Modell braucht – und die kann es nicht lernen."
    ),
    "Whole images shrink the smallest tenth of objects to {p10} px, below the {needed} px "
    "this model needs.": (
        "Ganze Bilder verkleinern das kleinste Zehntel der Objekte auf {p10} px, unter die "
        "{needed} px, die dieses Modell braucht."
    ),
    "Cut into a {grid} grid, they arrive at {after} px.": (
        "In ein {grid}-Raster geschnitten, kommen sie mit {after} px an."
    ),
    "Cut into a {grid} grid, they reach {after} px, still too small: this is the largest grid "
    "worth training on.": (
        "In ein {grid}-Raster geschnitten, erreichen sie {after} px – immer noch zu klein: Das "
        "ist das größte Raster, mit dem sich das Training lohnt."
    ),
    "Crop closer, or choose a model with a larger input.": (
        "Schneide enger zu oder wähle ein Modell mit größerer Eingabe."
    ),
    # What the model sees: the fit
    "The whole picture is shrunk until its long edge fits, and the rest of the square is "
    "filled with black. Nothing is cut off, and objects keep their shape.": (
        "Das ganze Bild wird verkleinert, bis seine lange Kante passt, und der Rest des "
        "Quadrats wird schwarz aufgefüllt. Nichts wird abgeschnitten, und Objekte behalten ihre "
        "Form."
    ),
    "The picture is shrunk until its short edge fits, keeping its shape. Nothing is cut off.": (
        "Das Bild wird verkleinert, bis seine kurze Kante passt, und behält seine Form. Nichts "
        "wird abgeschnitten."
    ),
    "The picture is squeezed into a square, whatever its shape. Nothing is cut off, but a "
    "wide picture's objects end up narrower than they are: a car in a 3:2 frame arrives a "
    "third slimmer. The model is used to this; it was trained the same way.": (
        "Das Bild wird in ein Quadrat gedrückt, egal welche Form es hat. Nichts wird "
        "abgeschnitten, aber die Objekte eines breiten Bildes werden schmaler, als sie sind: "
        "Ein Auto in einem 3:2-Bild kommt ein Drittel schlanker an. Das Modell ist das gewohnt; "
        "es wurde genauso trainiert."
    ),
    "The picture is shrunk until its short edge fits, and the centre square is kept. The "
    "edges are cut off, which is fine for a label that describes the whole picture, and "
    "wrong if what matters sits at the edge.": (
        "Das Bild wird verkleinert, bis seine kurze Kante passt, und das mittlere Quadrat wird "
        "behalten. Die Ränder werden abgeschnitten – gut für eine Klasse, die das ganze Bild "
        "beschreibt, und falsch, wenn das Wichtige am Rand sitzt."
    ),
    "Colours are rescaled with the statistics the model was trained on. This happens "
    "automatically; there is nothing to set.": (
        "Die Farben werden mit den Statistiken umgerechnet, mit denen das Modell trainiert "
        "wurde. Das passiert automatisch; du musst nichts einstellen."
    ),
    "Outlines are resized with the picture, pixel for pixel (no blending, which would invent "
    "classes), and the black padding is marked 'ignore', so the model is not taught that "
    "padding is background.": (
        "Umrisse werden mit dem Bild Pixel für Pixel skaliert (ohne Überblenden, das Klassen "
        "erfinden würde), und der schwarze Rand wird als „ignorieren“ markiert, damit das "
        "Modell nicht lernt, dass der Rand Hintergrund ist."
    ),
}

__all__ = ["ENTRIES", "FRAGMENTS"]
