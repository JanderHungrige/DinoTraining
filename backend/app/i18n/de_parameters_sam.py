"""German for the SAM 2.1 and SAM 3 parameters (doc 99: params/sam.py)."""

from __future__ import annotations

_RAISING = " Raising it makes training care more about this than the rest."

ENTRIES: dict[str, str] = {
    # Loss weights: the explanation, then one shared sentence.
    "{+what}" + _RAISING: (
        "{+what} Erhöhst du ihn, achtet das Training mehr darauf als auf den Rest."
    ),
    "The weight from the model's own published training recipe.": (
        "Das Loss-Gewicht aus dem veröffentlichten Trainingsrezept des Modells selbst."
    ),
    "Pixel focus": "Pixel-Fokus",
    "focal loss": "focal loss",
    "Counts wrong pixels, weighting the hard ones (edges, thin parts) most.": (
        "Zählt falsche Pixel und gewichtet die schwierigen (Ränder, dünne Stellen) am stärksten."
    ),
    "Overlap": "Überdeckung",
    "dice loss": "dice loss",
    "Rewards the predicted outline covering the true one as a whole.": (
        "Belohnt es, wenn der Umriss der Prediction den echten als Ganzes abdeckt."
    ),
    "Self-rating": "Selbsteinschätzung",
    "IoU-head loss": "IoU-head loss",
    "Teaches SAM to rate its own outline honestly, which its score uses.": (
        "Bringt SAM bei, seinen eigenen Umriss ehrlich zu bewerten – das nutzt sein Score."
    ),
    "Found or not": "Gefunden oder nicht",
    "classification loss": "classification loss",
    "Teaches which of SAM 3's guesses are real objects of the phrase.": (
        "Bringt bei, welche der Vermutungen von SAM 3 echte Objekte der Phrase sind."
    ),
    "Box position": "Box-Position",
    "L1 box loss": "L1 box loss",
    "Pulls each found object's box towards the true box.": (
        "Zieht die Box jedes gefundenen Objekts zur echten Box hin."
    ),
    "Box overlap": "Box-Überdeckung",
    "GIoU loss": "GIoU loss",
    "Rewards boxes that overlap the true box well, whatever their size.": (
        "Belohnt Boxen, die die echte Box gut überdecken, egal wie groß sie sind."
    ),
    "mask focal loss": "mask focal loss",
    "Counts wrong pixels in each outline, weighting the hard ones most.": (
        "Zählt falsche Pixel in jedem Umriss und gewichtet die schwierigen am stärksten."
    ),
    "Rewards each outline covering the true one as a whole.": (
        "Belohnt es, wenn jeder Umriss den echten als Ganzes abdeckt."
    ),
    # SAM 2.1
    "Only the small mask decoder trains; six rounds took the filled-ring convention from 0.80 "
    "to 0.96 mIoU.": (
        "Nur der kleine Mask-Decoder trainiert; sechs Epochs brachten die Filled-Ring-"
        "Konvention von 0.80 auf 0.96 mIoU."
    ),
    "The rate SAM's decoder tolerates without forgetting how to outline things in general.": (
        "Die Learning Rate, die SAMs Decoder verträgt, ohne zu vergessen, wie man Dinge allgemein "
        "umreißt."
    ),
    "Box looseness": "Box-Lockerheit",
    "box jitter": "box jitter",
    "During training each object's box is moved by up to this share of its size, so the model "
    "learns to cope with a loosely drawn box.": (
        "Beim Training wird die Box jedes Objekts um bis zu diesen Anteil seiner Größe "
        "verschoben, damit das Modell lernt, mit einer locker gezogenen Box zurechtzukommen."
    ),
    "A tenth matches how far a hand-drawn or detected box is usually off. 0 trains on exact "
    "boxes only.": (
        "Ein Zehntel entspricht dem, wie weit eine von Hand gezogene oder erkannte Box meist "
        "daneben liegt. 0 trainiert nur auf exakten Boxen."
    ),
    "Objects per step": "Objekte pro Schritt",
    "objects per image": "objects per image",
    "A crowded picture is trained on this many of its objects per step, chosen at random "
    "each round, to keep memory in check.": (
        "Bei einem vollen Bild wird pro Schritt mit so vielen seiner Objekte trainiert, in "
        "jeder Epoch zufällig ausgewählt, damit der Speicher im Rahmen bleibt."
    ),
    "Sixteen fits a 16 GB Mac comfortably and still covers most pictures fully.": (
        "Sechzehn passt bequem auf einen Mac mit 16 GB und deckt die meisten Bilder trotzdem "
        "ganz ab."
    ),
    "Click prompts per object": "Klick-Prompts pro Objekt",
    "point prompts": "point prompts",
    "In half the training steps each object's box comes with this many clicks inside it, so "
    "the fine-tuned SAM still answers the Studio's ⊕/⊖ clicks. 0 trains on boxes only.": (
        "In der Hälfte der Trainingsschritte kommt die Box jedes Objekts mit so vielen Klicks "
        "darin, damit das fine-getunte SAM weiter auf die ⊕/⊖-Klicks im Studio antwortet. 0 "
        "trainiert nur mit Boxen."
    ),
    "One click is what the Studio's outline tool sends first; half the steps keep box-only "
    "prompts as good as before (doc 108).": (
        "Ein Klick ist das, was das Umriss-Werkzeug im Studio zuerst schickt; die Hälfte der "
        "Schritte hält reine Box-Prompts so gut wie vorher (Dok. 108)."
    ),
    # SAM 3
    "Each round is slow on a laptop (every picture against every phrase); four rounds is a "
    "first result in reasonable time.": (
        "Jede Epoch ist auf einem Laptop langsam (jedes Bild gegen jede Phrase); vier Epochs "
        "geben ein erstes Ergebnis in vernünftiger Zeit."
    ),
    "Measured on the filled-ring set: one round at 1e-5 took held-out mIoU from 0.434 to "
    "0.603, while 1e-4 fell below the base model. SAM 3's decoders are sensitive.": (
        "Gemessen auf dem Filled-Ring-Set: Eine Epoch mit 1e-5 hob die mIoU auf den "
        "Held-out-Bildern von 0.434 auf 0.603, während 1e-4 unter das Foundation Model fiel. "
        "Die Decoder von SAM 3 sind empfindlich."
    ),
    "Generic negatives": "Generic Negatives",
    "Per picture and round, this many unrelated everyday phrases (car, person, dog, …) are "
    "asked and must find nothing — so SAM 3 does not answer every phrase with your objects. "
    "Phrases sharing a word with yours are left out. 0 turns it off.": (
        "Pro Bild und Epoch werden so viele fremde Alltagsphrasen (Auto, Person, Hund, …) "
        "gefragt, die nichts finden dürfen – damit SAM 3 nicht auf jede Phrase mit deinen "
        "Objekten antwortet. Phrasen, die ein Wort mit deinen teilen, bleiben außen vor. 0 "
        "schaltet es ab."
    ),
    "Two to four works well in published SAM 3 fine-tuning (SAM3_LoRA); each adds one query "
    "per picture, so more also means slower rounds.": (
        "Zwei bis vier funktionieren im veröffentlichten SAM-3-Fine-Tuning (SAM3_LoRA) gut; "
        "jedes fügt eine Query pro Bild hinzu, mehr heißt also auch langsamere Epochs."
    ),
    "Cross negatives": "Cross Negatives",
    "Your own phrases known to be absent from a picture ('not in this picture', or another "
    "class) are asked there and must find nothing. With more than 50 phrases only this many "
    "are sampled per picture; below that all are used.": (
        "Deine eigenen Phrasen, von denen bekannt ist, dass sie in einem Bild fehlen („nicht in "
        "diesem Bild“ oder eine andere Klasse), werden dort gefragt und dürfen nichts finden. "
        "Bei mehr als 50 Phrasen werden pro Bild nur so viele gezogen; darunter alle."
    ),
    "SAM3_LoRA's default: enough to learn which description is meant, without one picture "
    "turning into hundreds of queries on a large vocabulary.": (
        "Die Voreinstellung von SAM3_LoRA: genug, um zu lernen, welche Beschreibung gemeint "
        "ist, ohne dass ein Bild bei großem Wortschatz zu Hunderten von Queries wird."
    ),
    "Every wording each round": "Jede Formulierung in jeder Epoch",
    "all variations": "all variations",
    "On: each variation of a phrase is its own query every round (more steps). Off: one "
    "wording is picked at random each round, so all are seen over the rounds.": (
        "An: Jede Variante einer Phrase ist in jeder Epoch eine eigene Query (mehr Schritte). "
        "Aus: In jeder Epoch wird zufällig eine Formulierung gewählt, sodass über die Epochs "
        "alle vorkommen."
    ),
    "Off keeps a round as long as before while every wording is still learnt.": (
        "Aus hält eine Epoch so lang wie vorher, und trotzdem wird jede Formulierung gelernt."
    ),
    "Rejected outlines as negatives": "Abgelehnte Umrisse als Negatives",
    "hard negatives from rejections": "hard negatives from rejections",
    "A picture where you rejected the model's outline for a phrase, and accepted none, "
    "teaches 'not here' for that phrase even if it was not checked.": (
        "Ein Bild, in dem du den Umriss des Modells für eine Phrase abgelehnt und keinen "
        "angenommen hast, bringt für diese Phrase „nicht hier“ bei – auch wenn es nicht geprüft "
        "wurde."
    ),
    "A rejection is the most specific lesson there is: the model thought it was there, and it "
    "was not.": (
        "Eine Ablehnung ist die genaueste Lektion, die es gibt: Das Modell dachte, es wäre da, "
        "und es war nicht da."
    ),
    "Evaluation score threshold": "Score-Threshold bei der Bewertung",
    "score threshold": "score threshold",
    "When scoring the model, a guess counts as found only above this confidence. It changes "
    "the reported number, not the training.": (
        "Beim Bewerten des Modells zählt eine Vermutung erst oberhalb dieser Confidence als "
        "gefunden. Das ändert die gemeldete Zahl, nicht das Training."
    ),
    "0.5 is SAM 3's own default when it is used for annotation in this app.": (
        "0.5 ist die eigene Voreinstellung von SAM 3, wenn es in dieser App zum Annotieren "
        "benutzt wird."
    ),
}

__all__ = ["ENTRIES"]
