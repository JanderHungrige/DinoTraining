"""German for the task-specific audit rules (docs 107, 109: findings_task.py) and the
import check (doc 82: intake_findings.py). Terms follow the frontend's GLOSSARY.md."""

from __future__ import annotations

ENTRIES: dict[str, str] = {
    # mixed classes (picture classifier)
    "{count} picture(s) show more than one class": "{count} Bild(er) zeigen mehr als eine Klasse",
    "{count} pictures carry annotations of two or more classes.": (
        "{count} Bilder tragen Annotationen von zwei oder mehr Klassen."
    ),
    "A picture classifier learns one class per picture, so it leaves these out: they are "
    "neither lesson nor test.": (
        "Ein Bildklassifikator lernt eine Klasse pro Bild und lässt diese deshalb weg: Sie sind "
        "weder Lektion noch Test."
    ),
    "Mark only the main object on each, or train a detector instead, which learns every "
    "object in a picture.": (
        "Markiere auf jedem nur das Hauptobjekt – oder trainiere stattdessen einen Detektor, "
        "der jedes Objekt in einem Bild lernt."
    ),
    # outlines in pieces
    "{count} outline(s) in several pieces": "{count} Umriss(e) in mehreren Teilen",
    "{count} of {total} outlines are split into separate pieces.": (
        "{count} von {total} Umrissen bestehen aus getrennten Teilen."
    ),
    "That is right for an object cut in two by something in front of it, and wrong for stray "
    "specks, which teach the model that bits of background belong to the object.": (
        "Das ist richtig bei einem Objekt, das von etwas davor in zwei Teile geschnitten wird, "
        "und falsch bei verirrten Flecken: Die bringen dem Modell bei, dass Stücke vom "
        "Hintergrund zum Objekt gehören."
    ),
    "Look at the examples; remove specks with the eraser in the Annotation Studio (outline "
    "tools).": (
        "Sieh dir die Beispiele an und entferne Flecken mit dem Radierer im Annotation Studio "
        "(Umriss-Werkzeuge)."
    ),
    # outlines twice
    "{count} object(s) outlined twice": "{count} Objekt(e) doppelt umrissen",
    "{count} pairs of outlines cover almost the same pixels (80 % or more).": (
        "{count} Paare von Umrissen bedecken fast dieselben Pixel (80 % oder mehr)."
    ),
    "One object marked twice teaches the model to find it twice, and a pair with two classes "
    "teaches it two contradictory answers.": (
        "Ein doppelt markiertes Objekt bringt dem Modell bei, es doppelt zu finden, und ein "
        "Paar mit zwei Klassen lehrt es zwei widersprüchliche Antworten."
    ),
    "In the Annotation Studio, reject one outline of each pair.": (
        "Lehne im Annotation Studio bei jedem Paar einen der Umrisse ab."
    ),
    # thin phrases
    "{count} phrase(s) with fewer than {minimum} outlines": (
        "{count} Phrase(n) mit weniger als {minimum} Umrissen"
    ),
    "Outlines per phrase: {listed}.": "Umrisse pro Phrase: {listed}.",
    "SAM 3 learns a phrase from its examples; with few it learns these pictures, not the "
    "concept.": (
        "SAM 3 lernt eine Phrase aus ihren Beispielen; bei wenigen lernt es diese Bilder, nicht "
        "den Begriff."
    ),
    "Outline more instances of these phrases, or leave the thinnest out for now.": (
        "Umreiße mehr Vorkommen dieser Phrasen oder lass die mit den wenigsten vorerst weg."
    ),
    # unchecked pictures
    "{count} of {total} pictures not checked for every phrase": (
        "{count} von {total} Bildern nicht für jede Phrase geprüft"
    ),
    "No picture has been marked for any phrase yet.": (
        "Noch kein Bild wurde für irgendeine Phrase markiert."
    ),
    "{count} pictures lack an 'all marked' or 'not in this picture' for at least one phrase.": (
        "{count} Bildern fehlt für mindestens eine Phrase ein „alles markiert“ oder „nicht in "
        "diesem Bild“."
    ),
    "SAM 3 learns 'none here' only from pictures you checked. Unchecked, a picture without an "
    "outline could simply not have been annotated yet — so it teaches nothing. A phrase never "
    "checked anywhere keeps the old rule: every picture without its outline counts as 'none "
    "here', which is right only if the dataset is fully annotated.": (
        "SAM 3 lernt „keins hier“ nur aus Bildern, die du geprüft hast. Ungeprüft könnte ein "
        "Bild ohne Umriss einfach noch nicht annotiert sein – also bringt es nichts bei. Für "
        "eine Phrase, die nirgends geprüft wurde, gilt die alte Regel: Jedes Bild ohne ihren "
        "Umriss zählt als „keins hier“. Das stimmt nur, wenn der Datensatz vollständig "
        "annotiert ist."
    ),
    "In the Annotation Studio's phrase bar, mark each picture per phrase: A for all marked, N "
    "for not in this picture. If a phrase is fully annotated, 'Mark the rest' under Manage "
    "phrases checks every remaining picture in one step.": (
        "Markiere in der Phrasenleiste des Annotation Studios jedes Bild pro Phrase: A für "
        "„alles markiert“, N für „nicht in diesem Bild“. Ist eine Phrase vollständig annotiert, "
        "prüft „Den Rest markieren“ unter „Phrasen verwalten“ alle übrigen Bilder in einem "
        "Schritt."
    ),
    # no variations
    "{count} phrase(s) without variations": "{count} Phrase(n) ohne Varianten",
    "Only one wording for: {phrases}.": "Nur eine Formulierung für: {phrases}.",
    "Two to four other wordings teach SAM 3 that the words can vary, so it also answers "
    "phrasings nobody typed.": (
        "Zwei bis vier andere Formulierungen zeigen SAM 3, dass die Worte variieren können – so "
        "antwortet es auch auf Formulierungen, die niemand eingetippt hat."
    ),
    "Add variations under Manage phrases (comma-separated).": (
        "Füge unter „Phrasen verwalten“ Varianten hinzu (durch Kommas getrennt)."
    ),
    # no confirmed negatives
    "No picture is marked 'not in this picture'": (
        "Kein Bild ist als „nicht in diesem Bild“ markiert"
    ),
    "Every check so far says 'all marked'.": "Jede Prüfung bisher sagt „alles markiert“.",
    "Confirmed negatives are the strongest lesson in what a phrase is not — especially "
    "pictures where something similar is there.": (
        "Bestätigte Negatives sind die stärkste Lektion darin, was eine Phrase nicht ist "
        "– besonders Bilder, auf denen etwas Ähnliches zu sehen ist."
    ),
    "Mark pictures without the phrase as 'not in this picture' (N), look-alikes first.": (
        "Markiere Bilder ohne die Phrase als „nicht in diesem Bild“ (N), Verwechslungen zuerst."
    ),
    # inconsistent frames
    "{count} frame(s) name an object differently from the frame before": (
        "{count} Frame(s) benennen ein Objekt anders als der Frame davor"
    ),
    "In {count} places an object keeps its place from one frame to the next but changes its "
    "class.": (
        "An {count} Stellen bleibt ein Objekt von einem Frame zum nächsten an seinem Platz, "
        "wechselt aber die Klasse."
    ),
    "The model is shown the same thing under two names, and learns neither well; every model "
    "suffers from it.": (
        "Das Modell sieht dasselbe unter zwei Namen und lernt keinen davon gut; darunter leidet "
        "jedes Modell."
    ),
    "Open the frames in Inspect datasets, decide which name is right, and write it into the "
    "dataset's annotation guideline so it stays decided.": (
        "Öffne die Frames unter „Datensätze ansehen“, entscheide, welcher Name richtig "
        "ist, und schreib ihn in die Annotationsrichtlinie des Datensatzes, damit es "
        "entschieden bleibt."
    ),
    # intake_findings.py (doc 82)
    "It is unclear how the boxes are written down": "Es ist unklar, wie die Boxen notiert sind",
    "Neither common way of reading the numbers fits all boxes ({shares}).": (
        "Keine der üblichen Lesarten der Zahlen passt auf alle Boxen ({shares})."
    ),
    "A box is four numbers, and there is more than one way to write them. Read the wrong way, "
    "boxes land in the wrong place or fall outside the picture, and the model learns from "
    "boxes around nothing.": (
        "Eine Box besteht aus vier Zahlen, und es gibt mehr als eine Art, sie zu notieren. "
        "Falsch gelesen landen Boxen an der falschen Stelle oder außerhalb des Bildes, und das "
        "Modell lernt von Boxen um nichts."
    ),
    "Check a few boxes in the source tool and choose the reading by hand. If the export is "
    "damaged, re-export it.": (
        "Prüf ein paar Boxen im Ursprungswerkzeug und wähle die Lesart von Hand. Ist der Export "
        "beschädigt, exportiere ihn neu."
    ),
    "The boxes are written differently from standard COCO": (
        "Die Boxen sind anders notiert als im Standard-COCO"
    ),
    "This export writes boxes {+reading}, although COCO expects left, top, width, height. All "
    "the evidence agrees.": (
        "Dieser Export notiert Boxen {+reading}, obwohl COCO links, oben, Breite, Höhe erwartet. "
        "Alle Hinweise stimmen darin überein."
    ),
    "Imported as if it were standard, most boxes would fall outside their pictures and be "
    "dropped, and the import would still say it succeeded.": (
        "Als Standard importiert, lägen die meisten Boxen außerhalb ihrer Bilder und würden "
        "verworfen – und der Import würde trotzdem Erfolg melden."
    ),
    "Nothing to do: the import converts them. The preview after import shows the boxes on "
    "their images, so you can check.": (
        "Nichts zu tun: Der Import rechnet sie um. Die Vorschau nach dem Import zeigt die Boxen "
        "auf ihren Bildern, damit du es prüfen kannst."
    ),
    "{count} referenced image(s) are missing": "{count} genannte(s) Bild(er) fehlen",
    "The annotation file names pictures that are not in the folder.": (
        "Die Annotationsdatei nennt Bilder, die nicht im Ordner liegen."
    ),
    "Their annotations cannot be used. A large share usually means the export was unpacked "
    "into the wrong place.": (
        "Ihre Annotationen lassen sich nicht verwenden. Ein großer Anteil heißt meist, dass der "
        "Export an die falsche Stelle entpackt wurde."
    ),
    "Check that the images sit next to the annotation file. They will be skipped otherwise.": (
        "Prüf, ob die Bilder neben der Annotationsdatei liegen. Sonst werden sie übersprungen."
    ),
    "{count} image(s) are not the size the file says": (
        "{count} Bild(er) haben nicht die Größe, die in der Datei steht"
    ),
    "The annotation file declares a different width or height than the real picture.": (
        "Die Annotationsdatei gibt eine andere Breite oder Höhe an als das echte Bild."
    ),
    "Boxes are measured against the declared size. When the picture was resized after "
    "annotating, every box is misplaced by that factor.": (
        "Boxen werden an der angegebenen Größe gemessen. Wurde das Bild nach dem Annotieren "
        "verkleinert, liegt jede Box um diesen Faktor daneben."
    ),
    "Re-export with the original images, or with annotations made on these images.": (
        "Exportiere neu mit den Originalbildern – oder mit Annotationen, die auf diesen Bildern "
        "gemacht wurden."
    ),
    "Some class names look like one class spelled differently": (
        "Manche Klassennamen sehen aus wie eine Klasse in anderer Schreibweise"
    ),
    "Proposed merges: {pairs}.": "Vorgeschlagene Zusammenführungen: {pairs}.",
    "Each spelling becomes its own class, so one kind of object is split in two and the model "
    "learns each half from fewer examples.": (
        "Jede Schreibweise wird zu einer eigenen Klasse. So wird eine Art Objekt in zwei geteilt, "
        "und das Modell lernt jede Hälfte aus weniger Beispielen."
    ),
    "Accept the merges (the default), or untick any that are really different things, like "
    "'glass' and 'glasses'.": (
        "Übernimm die Zusammenführungen (die Voreinstellung) oder nimm den Haken bei denen "
        "weg, die wirklich verschiedene Dinge sind, etwa „glass“ und „glasses“."
    ),
    "The export comes already split": "Der Export bringt schon einen Split mit",
    "It has separate folders: {folders}.": "Er hat getrennte Ordner: {folders}.",
    "Whoever published the data chose which pictures are for testing. Keeping that choice "
    "makes your results comparable with theirs.": (
        "Wer die Daten veröffentlicht hat, hat ausgewählt, welche Bilder in Test gehören. "
        "Behältst du diese Wahl, sind deine Ergebnisse mit denen vergleichbar."
    ),
    "Keep it (recommended), unless the folders mix frames of one video, which the audit will "
    "point out.": (
        "Behalte ihn (empfohlen) – außer die Ordner mischen Frames eines Videos; darauf "
        "weist die Prüfung dich hin."
    ),
}

__all__ = ["ENTRIES"]
