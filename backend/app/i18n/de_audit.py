"""German for the audit's content and data-quality rules (docs 81, 82): findings.py,
findings_quality.py and intake_findings.py. Terms follow apps/frontend/src/i18n/GLOSSARY.md."""

from __future__ import annotations

FRAGMENTS: dict[str, str] = {
    "boxes": "Boxen",
    "outlines (masks)": "Umrisse (Masken)",
    "nothing usable": "nichts Brauchbares",
    "as two corners (left, top, right, bottom)": "als zwei Ecken (links, oben, rechts, unten)",
    "as fractions of the image size (0 to 1)": "als Anteile der Bildgröße (0 bis 1)",
}

ENTRIES: dict[str, str] = {
    # findings.py — size of the dataset
    "Only {count} images": "Nur {count} Bilder",
    "The dataset holds {count} images.": "Der Datensatz enthält {count} Bilder.",
    "A model learns from examples. With this few it tends to memorise these exact pictures "
    "rather than learn what the objects look like, and then fails on new ones.": (
        "Ein Modell lernt aus Beispielen. Bei so wenigen lernt es eher genau diese Bilder "
        "auswendig, statt zu lernen, wie die Objekte aussehen – und versagt dann bei neuen."
    ),
    "Add more images if you can: a few hundred varied ones is a good start. The Dataset "
    "Generator can pre-annotate new images for you to check.": (
        "Füge mehr Bilder hinzu, wenn du kannst: Ein paar hundert abwechslungsreiche sind ein "
        "guter Anfang. Der Datensatz-Generator kann neue Bilder für dich vorannotieren, und du "
        "prüfst sie nur noch."
    ),
    # thin classes
    "{count} class(es) with too few examples": "{count} Klasse(n) mit zu wenigen Beispielen",
    "Annotated examples per class: {listed}.": "Annotierte Beispiele pro Klasse: {listed}.",
    "Each class is learned from its own examples. Below about 30, the model sees too few "
    "variations (angles, lighting, sizes) to recognise that class reliably.": (
        "Jede Klasse wird aus ihren eigenen Beispielen gelernt. Unter etwa 30 sieht das Modell "
        "zu wenige Varianten (Blickwinkel, Licht, Größen), um diese Klasse zuverlässig zu "
        "erkennen."
    ),
    "Annotate more examples of these classes, merge a class into a similar one, or leave it "
    "out of this training run (Fix step).": (
        "Annotiere mehr Beispiele dieser Klassen, leg eine Klasse mit einer ähnlichen zusammen "
        "oder lass sie bei diesem Training weg (Schritt „Sicher korrigieren“)."
    ),
    # imbalance
    "Classes are very unequal ({ratio}×)": "Die Klassen sind sehr ungleich ({ratio}×)",
    "'{big}' has {most} examples, '{small}' only {least}.": (
        "„{big}“ hat {most} Beispiele, „{small}“ nur {least}."
    ),
    "A model rewards itself for being right often. With one class this common, it can look "
    "accurate while mostly ignoring the rare ones, and the rare ones are often the ones you "
    "care about.": (
        "Ein Modell belohnt sich dafür, oft richtig zu liegen. Ist eine Klasse so häufig, kann "
        "es genau wirken und die seltenen dabei fast übersehen – und gerade die seltenen sind "
        "oft die, auf die es dir ankommt."
    ),
    "The Balance step can weight the rare classes up during training. Adding examples of the "
    "rare classes helps most.": (
        "Der Schritt „Ungleiche Klassen“ kann die seltenen Klassen beim Training stärker "
        "gewichten. Am meisten hilft es, mehr Beispiele der seltenen Klassen hinzuzufügen."
    ),
    # objects too small
    "Objects are too small for this model to see": (
        "Die Objekte sind zu klein, als dass dieses Modell sie sehen könnte"
    ),
    "After resizing to {+label}'s {size} px input, the typical object is {p50} px across and "
    "the smallest tenth are under {p10} px. This model needs about {limit} px to find "
    "something.": (
        "Nach dem Verkleinern auf die Eingabe von „{+label}“ ({size} px) ist ein typisches Objekt "
        "{p50} px groß, und das kleinste Zehntel liegt unter {p10} px. Dieses Modell braucht "
        "etwa {limit} px, um etwas zu finden."
    ),
    "The model shrinks every picture to a fixed size before looking at it. Objects that end "
    "up smaller than its finest detail become invisible, so it cannot learn them, however "
    "well they are labelled.": (
        "Das Modell verkleinert jedes Bild auf eine feste Größe, bevor es hinsieht. Objekte, "
        "die dabei kleiner werden als sein feinstes Detail, werden unsichtbar – es kann sie "
        "nicht lernen, egal wie gut sie annotiert sind."
    ),
    "{*reason} The Model step sets tiling up and shows you what the model sees.": (
        "{*reason} Der Schritt „Was das Modell sieht“ richtet die Kacheln ein und zeigt dir, "
        "was das Modell sieht."
    ),
    # wrong annotation kind
    "{+label} needs boxes": "„{+label}“ braucht Boxen",
    "{+label} needs outlines (masks)": "„{+label}“ braucht Umrisse (Masken)",
    "This dataset has {+have}, and this model trains from {+need}.": (
        "Dieser Datensatz hat {+have}, aber dieses Modell braucht zum Lernen {+need}."
    ),
    "Each model learns from one kind of annotation, and cannot learn from another.": (
        "Jedes Modell lernt aus einer bestimmten Art von Annotation und kann aus einer anderen "
        "nichts lernen."
    ),
    "Choose a model that fits the annotations you have, or annotate with a tool that produces "
    "the right kind (Grounded SAM makes masks, Grounding DINO makes boxes).": (
        "Wähle ein Modell, das zu deinen Annotationen passt, oder annotiere mit einem Werkzeug, "
        "das die richtige Art erzeugt (Grounded SAM macht Masken, Grounding DINO macht Boxen)."
    ),
    # findings_quality.py
    "{count} image(s) cannot be opened": "{count} Bild(er) lassen sich nicht öffnen",
    "These files are missing, moved, or damaged.": (
        "Diese Dateien fehlen, wurden verschoben oder sind beschädigt."
    ),
    "Training stops on, or silently skips, a picture it cannot read, and its annotations are "
    "lost to the model.": (
        "Das Training bricht bei einem Bild ab, das es nicht lesen kann, oder überspringt es "
        "stillschweigend – seine Annotationen gehen dem Modell verloren."
    ),
    "Restore the files, or exclude these images in the Fix step.": (
        "Stell die Dateien wieder her oder lass diese Bilder im Schritt „Sicher korrigieren“ weg."
    ),
    "{count} copied image(s)": "{count} kopierte(s) Bild(er)",
    "{groups} group(s) of images are the same picture with the same annotations (resized or "
    "re-saved copies).": (
        "{groups} Gruppe(n) von Bildern sind dasselbe Bild mit denselben Annotationen "
        "(verkleinerte oder neu gespeicherte Kopien)."
    ),
    "Copies add no new information and make those examples count twice. If one copy is used "
    "for training and another for testing, the test only checks memory.": (
        "Kopien bringen nichts Neues und lassen diese Beispiele doppelt zählen. Landet eine "
        "Kopie im Training und eine andere im Test, prüft der Test nur das Gedächtnis."
    ),
    "Keep one image per group (Fix step).": (
        "Behalte ein Bild pro Gruppe (Schritt „Sicher korrigieren“)."
    ),
    "{count} images share a scene with others": "{count} Bilder teilen eine Szene mit anderen",
    "{groups} group(s) of images show almost the same picture, for example the same board "
    "with a different piece on it.": (
        "{groups} Gruppe(n) von Bildern zeigen fast dasselbe Bild, zum Beispiel dasselbe Brett "
        "mit einer anderen Figur darauf."
    ),
    "These are different examples and all worth keeping. But if one of them were used for "
    "testing and its twin for training, the test would be easier than new pictures are, and "
    "the score would look too good.": (
        "Das sind verschiedene Beispiele, und alle sind es wert, behalten zu werden. Käme aber "
        "eines davon in den Test und sein Zwilling ins Training, wäre der Test leichter als neue "
        "Bilder, und der Wert sähe zu gut aus."
    ),
    "Nothing to do: the split step keeps each group on one side.": (
        "Nichts zu tun: Die Aufteilung hält jede Gruppe auf einer Seite."
    ),
    "{share} of annotations are marked unclear": (
        "{share} der Annotationen sind als unklar markiert"
    ),
    "{unclear} of {total} annotations were marked 'unclear' during review.": (
        "{unclear} von {total} Annotationen wurden beim Prüfen als „unklar“ markiert."
    ),
    "Unclear areas are left out of training. A high share means a lot of the data teaches "
    "nothing, or that the classes are hard to tell apart.": (
        "Unklare Stellen werden beim Training ausgelassen. Ein hoher Anteil heißt, dass viele "
        "Daten nichts beibringen – oder dass die Klassen schwer auseinanderzuhalten sind."
    ),
    "Review the unclear ones in the Studio. Decide yes or no where you can, and consider "
    "whether two classes should be one.": (
        "Sieh dir die unklaren im Studio an. Entscheide dich für richtig oder falsch, wo du "
        "kannst, und überleg, ob zwei Klassen eigentlich eine sein sollten."
    ),
    "Some classes look like one class spelled two ways": (
        "Manche Klassen sehen aus wie eine Klasse in zwei Schreibweisen"
    ),
    "Training treats every spelling as its own class, so one kind of object is split in two "
    "and each half has fewer examples.": (
        "Das Training behandelt jede Schreibweise als eigene Klasse. So wird eine Art Objekt in "
        "zwei geteilt, und jede Hälfte hat weniger Beispiele."
    ),
    "Merge the spellings in the Fix step.": (
        "Führe die Schreibweisen im Schritt „Sicher korrigieren“ zusammen."
    ),
    "{share} of images have nothing annotated": "{share} der Bilder haben nichts annotiert",
    "{empty} of {total} images contain no annotated object.": (
        "{empty} von {total} Bildern enthalten kein annotiertes Objekt."
    ),
    "Some empty images teach the model what is *not* an object, which is useful. When they "
    "are most of the dataset, the model learns that saying 'nothing' is usually right.": (
        "Ein paar leere Bilder zeigen dem Modell, was *kein* Objekt ist – das ist nützlich. "
        "Machen sie den Großteil des Datensatzes aus, lernt das Modell, dass „nichts“ meistens "
        "die richtige Antwort ist."
    ),
    "The Balance step can sample annotated images more often. Or exclude some of the empty ones.": (
        "Der Schritt „Ungleiche Klassen“ kann annotierte Bilder öfter zeigen. Oder lass einige "
        "der leeren weg."
    ),
    "Frames from {count} video(s) or folder(s)": "Einzelbilder aus {count} Video(s) oder Ordner(n)",
    "Many images are consecutive frames, so neighbouring frames look almost identical.": (
        "Viele Bilder sind aufeinanderfolgende Einzelbilder, benachbarte sehen also fast gleich "
        "aus."
    ),
    "If neighbouring frames were split between training and testing, the test would see "
    "almost the same picture it trained on, and the score would look far too good.": (
        "Würden benachbarte Einzelbilder auf Training und Test verteilt, sähe der Test fast "
        "dasselbe Bild, auf dem trainiert wurde, und der Wert sähe viel zu gut aus."
    ),
    "Nothing to do: the split step keeps each video's frames together.": (
        "Nichts zu tun: Die Aufteilung hält die Einzelbilder jedes Videos zusammen."
    ),
}

__all__ = ["ENTRIES", "FRAGMENTS"]
