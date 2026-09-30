"""German for the parameter catalogue (doc 99): the DINO head (params/heads.py), the shared
fine-tuning knobs, RF-DETR and the DINO backbone (params/finetune.py), and the checks'
refusals (params/spec.py). Labels and terms match the frontend's GLOSSARY.md."""

from __future__ import annotations

ENTRIES: dict[str, str] = {
    # Families
    "DINO head": "DINO-Head",
    "DINO backbone": "DINO-Backbone",
    "Every head trained on a frozen DINOv2/DINOv3 backbone": (
        "Jeder Head, der auf einem eingefrorenen DINOv2/DINOv3-Backbone trainiert wird"
    ),
    "dinov2-*/dinov3-* with a classification or segmentation head": (
        "dinov2-*/dinov3-* mit einem Klassifikations- oder Segmentation-Head"
    ),
    # Labels and terms
    # Jan, 2026-09-30: technical terms stay English, so each `term` equals its English.
    "Rounds": "Epochs",
    "epochs": "epochs",
    "Learning speed": "Learning Rate",
    "learning rate": "learning rate",
    "Pictures per step": "Batch Size",
    "batch size": "batch size",
    "gradient accumulation": "gradient accumulation",
    "Patience": "Geduld",
    "early stopping": "early stopping",
    "Weight shrinkage": "Weight Decay",
    "weight decay": "weight decay",
    "Speed schedule": "Learning-Rate-Verlauf",
    "learning-rate schedule": "learning-rate schedule",
    "Constant": "Gleichbleibend",
    "Slow down (cosine)": "Langsamer werden (Kosinus)",
    "Warm-up rounds": "Warm-up-Epochs",
    "warm-up": "warm-up",
    "Random seed": "Zufallsstartwert",
    "seed": "seed",
    "Validation share": "Validation-Anteil",
    "validation fraction": "validation fraction",
    "Test share": "Test-Anteil",
    "test fraction": "test fraction",
    "Memory for cached pictures": "Speicher für zwischengespeicherte Bilder",
    "feature-cache share": "feature-cache share",
    "Backbone blocks to train": "Zu trainierende Backbone-Blöcke",
    "unfreeze": "unfreeze",
    "Gradient limit": "Gradient-Grenze",
    "gradient clipping": "gradient clipping",
    "Backbone speed factor": "Backbone-Learning-Rate-Faktor",
    "backbone learning-rate scale": "backbone learning-rate scale",
    # The head's explanations (heads.py)
    "How many times training goes through all training pictures. More rounds learn more, "
    "until the model starts memorising; the best round is kept either way.": (
        "Wie oft das Training alle Trainingsbilder durchgeht. Mehr Epochs lernen mehr – bis "
        "das Modell anfängt, auswendig zu lernen (Overfitting); die beste Epoch wird so oder "
        "so behalten."
    ),
    "A head on a frozen backbone learns fast; 20 rounds is enough for a few hundred pictures, "
    "and early stopping ends sooner when nothing improves.": (
        "Ein Head auf einem eingefrorenen Backbone lernt schnell; 20 Epochs reichen für ein "
        "paar hundert Bilder, und Early Stopping hört eher auf, wenn nichts besser wird."
    ),
    "How big each correction step is. Too high and training jumps around or diverges; too low "
    "and it barely moves in the rounds you give it.": (
        "Wie groß jeder Korrekturschritt ist. Zu hoch, und das Training springt hin und her oder "
        "läuft aus dem Ruder; zu niedrig, und es kommt in den Epochs, die du ihm gibst, kaum "
        "voran."
    ),
    "A small head on fixed features tolerates a high rate; 0.001 converges in a handful of "
    "rounds.": (
        "Ein kleiner Head auf festen Features verträgt eine hohe Learning Rate; 0.001 kommt in "
        "einer Handvoll Epochs ans Ziel."
    ),
    "How many pictures are looked at before the model is corrected once. More pictures per "
    "step give calmer, averaged corrections but fewer of them per round.": (
        "Wie viele Bilder angesehen werden, bevor das Modell einmal korrigiert wird. Eine "
        "größere Batch Size gibt ruhigere, gemittelte Korrekturen, aber weniger davon pro "
        "Epoch."
    ),
    "One picture per step is how every head so far was trained, and it suits small datasets: "
    "more corrections per round. Try 4–8 if the loss curve is very jumpy.": (
        "Eine Batch Size von 1 ist, wie bisher jeder Head trainiert wurde, und sie passt zu "
        "kleinen Datensätzen: mehr Korrekturen pro Epoch. Probier 4–8, wenn die Loss-Kurve "
        "sehr sprunghaft ist."
    ),
    "Training stops when the validation score has not improved for this many rounds in a "
    "row. It saves time once the model has learned what it can.": (
        "Das Training hört auf, wenn der Validation-Score sich so viele Epochs hintereinander "
        "nicht verbessert hat. Das spart Zeit, sobald das Modell gelernt hat, was es kann."
    ),
    "Five rounds lets a noisy score recover from a dip without running on for long after the "
    "model has stopped improving.": (
        "Fünf Epochs lassen einen schwankenden Score sich von einem Einbruch erholen, ohne "
        "lange weiterzulaufen, nachdem das Modell nicht mehr besser wird."
    ),
    "Gently pulls the model's numbers towards zero, which discourages memorising individual "
    "pictures. Higher values mean a simpler, more cautious model.": (
        "Zieht die Weights des Modells sanft Richtung null; das hält es davon ab, einzelne "
        "Bilder auswendig zu lernen. Höhere Werte heißen ein einfacheres, vorsichtigeres "
        "Modell."
    ),
    "0.01 is the usual AdamW setting: enough to curb memorising without holding back learning.": (
        "0.01 ist die übliche AdamW-Einstellung: genug, um Overfitting zu bremsen, ohne das "
        "Lernen aufzuhalten."
    ),
    "Whether the learning speed stays the same every round, or slows down along a cosine "
    "curve towards the end so the last rounds make only fine adjustments.": (
        "Ob die Learning Rate in jeder Epoch gleich bleibt oder zum Ende hin entlang einer "
        "Kosinuskurve kleiner wird, sodass die letzten Epochs nur noch fein nachjustieren."
    ),
    "Constant is how every head so far was trained. Cosine often helps longer runs (30+ "
    "rounds) settle.": (
        "Gleichbleibend ist, wie bisher jeder Head trainiert wurde. Kosinus hilft längeren "
        "Läufen (30+ Epochs) oft, zur Ruhe zu kommen."
    ),
    "The first rounds start at a fraction of the learning speed and ramp up to it, so a model "
    "that has not seen your data yet is not jolted by big early steps.": (
        "Die ersten Epochs beginnen mit einem Bruchteil der Learning Rate und steigern sich "
        "dann, damit ein Modell, das deine Daten noch nicht kennt, nicht von großen frühen "
        "Schritten durchgerüttelt wird."
    ),
    "A head starts from scratch on stable features and does not need it; 1–2 rounds help when "
    "the loss spikes at the start.": (
        "Ein Head beginnt von null auf stabilen Features und braucht das nicht; 1–2 Epochs "
        "helfen, wenn der Loss am Anfang hochschießt."
    ),
    "Fixes the random choices (split, order), so the same settings give the same result "
    "again. Change it to see how much a result depends on luck.": (
        "Legt die Zufallsentscheidungen fest (Split, Reihenfolge), sodass dieselben "
        "Einstellungen wieder dasselbe Ergebnis geben. Ändere ihn, um zu sehen, wie sehr ein "
        "Ergebnis vom Glück abhängt."
    ),
    "Any fixed number works; 42 is a convention. A recipe's split has its own seed.": (
        "Jede feste Zahl funktioniert; 42 ist eine Konvention. Der Split eines Rezepts hat "
        "seinen eigenen Seed."
    ),
    "The share of pictures held back to pick the best round and to stop early. They are not "
    "trained on.": (
        "Der Anteil der Bilder, der zurückgehalten wird, um die beste Epoch auszuwählen und "
        "früh aufzuhören. Auf ihnen wird nicht trainiert."
    ),
    "A fifth is enough to judge a round on small datasets while leaving most pictures for "
    "training. A recipe's split replaces it.": (
        "Ein Fünftel reicht, um bei kleinen Datensätzen eine Epoch zu beurteilen, und lässt "
        "die meisten Bilder fürs Training. Der Split eines Rezepts ersetzt ihn."
    ),
    "The share of pictures kept out of everything until the end, for an honest final score. "
    "0 means no test score.": (
        "Der Anteil der Bilder, der bis zum Schluss aus allem herausgehalten wird, für einen "
        "ehrlichen finalen Score. 0 heißt: kein Test-Score."
    ),
    "A tenth gives a final check without starving training. A recipe's split replaces it.": (
        "Ein Zehntel gibt eine Schlussprüfung, ohne dem Training zu viel wegzunehmen. Der "
        "Split eines Rezepts ersetzt ihn."
    ),
    # Shared fine-tuning knobs (finetune.py)
    "How many times training goes through all training pictures. The original model competes "
    "as round 0 and the best round is kept, so more rounds cost time, never quality.": (
        "Wie oft das Training alle Trainingsbilder durchgeht. Das ursprüngliche Modell tritt als "
        "Epoch 0 an, und die beste Epoch wird behalten – mehr Epochs kosten also Zeit, nie "
        "Qualität."
    ),
    "How big each correction step is. A pretrained model is being adjusted, not taught from "
    "scratch: too high a speed destroys what it already knows.": (
        "Wie groß jeder Korrekturschritt ist. Ein vortrainiertes Modell wird angepasst, nicht "
        "von null unterrichtet: Eine zu hohe Learning Rate zerstört, was es schon kann."
    ),
    "Gently pulls the trained numbers towards zero, which discourages memorising individual "
    "pictures.": (
        "Zieht die trainierten Weights sanft Richtung null; das hält davon ab, einzelne Bilder "
        "auswendig zu lernen."
    ),
    "The value this model's training used before it became a setting.": (
        "Der Wert, den das Training dieses Modells verwendet hat, bevor er einstellbar wurde."
    ),
    "Fixes the random choices (order, jitter), so the same settings give the same result "
    "again. Change it to see how much a result depends on luck.": (
        "Legt die Zufallsentscheidungen fest (Reihenfolge, Jitter), sodass dieselben "
        "Einstellungen wieder dasselbe Ergebnis geben. Ändere ihn, um zu sehen, wie sehr ein "
        "Ergebnis vom Glück abhängt."
    ),
    "Any fixed number works; 42 is a convention.": (
        "Jede feste Zahl funktioniert; 42 ist eine Konvention."
    ),
    "The share of this computer's memory used to keep each picture's encoded version between "
    "rounds. More is faster; too much makes the whole computer slow.": (
        "Der Anteil des Arbeitsspeichers dieses Computers, in dem die kodierte Fassung jedes "
        "Bildes zwischen den Epochs aufbewahrt wird. Mehr ist schneller; zu viel macht den "
        "ganzen Computer langsam."
    ),
    "Measured on a 16 GB Mac: a fixed 3 GB cache beside the model pushed it into heavy "
    "swapping, so the cache is a share of memory instead.": (
        "Gemessen auf einem Mac mit 16 GB: Ein fester Cache von 3 GB neben dem Modell hat ihn "
        "stark auslagern lassen, deshalb ist der Cache stattdessen ein Anteil des Speichers."
    ),
    "How many of the backbone's last layers are adjusted too. The last layers hold the most "
    "task-specific knowledge; more layers can adapt further but need more pictures and "
    "memory.": (
        "Wie viele der letzten Layer des Backbones mit angepasst werden. Die letzten Layer "
        "tragen das meiste aufgabenspezifische Wissen; mehr Layer können sich weiter anpassen, "
        "brauchen aber mehr Bilder und Speicher."
    ),
    # RF-DETR
    "Detectors keep improving over many rounds; 10 balances time and quality on a laptop.": (
        "Detektoren werden über viele Epochs immer besser; 10 halten auf einem Laptop Zeit "
        "und Qualität im Gleichgewicht."
    ),
    "The usual DETR fine-tuning rate: fast enough to learn new classes, slow enough to keep "
    "what the model knows.": (
        "Die übliche Learning Rate fürs DETR-Fine-Tuning: hoch genug, um neue Klassen zu lernen, "
        "niedrig genug, um zu behalten, was das Modell kann."
    ),
    "How many pictures are looked at before the model is corrected once. More give calmer "
    "corrections but fewer of them per round.": (
        "Wie viele Bilder angesehen werden, bevor das Modell einmal korrigiert wird. Mehr geben "
        "ruhigere Korrekturen, aber weniger davon pro Epoch."
    ),
    "One picture per step is how RF-DETR was fine-tuned here so far (0.62 test mAP on Blood "
    "cells). Try 4 if the loss is very jumpy.": (
        "Eine Batch Size von 1 ist, wie RF-DETR hier bisher fine-getunt wurde (0.62 Test-mAP "
        "auf Blood cells). Probier 4, wenn der Loss sehr sprunghaft ist."
    ),
    "Caps how strong a single correction may be. It protects the model from one bad picture "
    "or a loss spike undoing what it learned.": (
        "Begrenzt, wie stark eine einzelne Korrektur sein darf. Das schützt das Modell davor, "
        "dass ein schlechtes Bild oder ein Loss-Ausreißer zunichtemacht, was es gelernt hat."
    ),
    "DETR losses spike in the first steps after the classifier is re-opened for your classes; "
    "0.1 is the value RF-DETR's own training uses.": (
        "Der DETR-Loss schießt in den ersten Schritten hoch, nachdem der Klassifikator für deine "
        "Klassen neu geöffnet wurde; 0.1 ist der Wert, den RF-DETRs eigenes Training verwendet."
    ),
    "0 trains the detector's own layers only, which is what RF-DETR's fine-tuning does and "
    "needs the fewest pictures.": (
        "0 trainiert nur die eigenen Layer des Detektors – so macht es das Fine-Tuning von "
        "RF-DETR, und es braucht die wenigsten Bilder."
    ),
    # DINO backbone
    "The backbone is only nudged; six rounds measured a gain on the filled-ring set (0.849 → "
    "0.869) without overfitting.": (
        "Das Backbone wird nur angestupst; sechs Epochs brachten auf dem Filled-Ring-Set "
        "messbar mehr (0.849 → 0.869), ohne Overfitting."
    ),
    "This is the head's speed; the backbone gets a fraction of it (see Backbone speed factor).": (
        "Das ist die Learning Rate des Heads; das Backbone bekommt einen Bruchteil davon "
        "(siehe Backbone-Learning-Rate-Faktor)."
    ),
    "The last four blocks carry the most task-specific features; more needs more pictures "
    "than most datasets have.": (
        "Die letzten vier Blöcke tragen die meisten aufgabenspezifischen Features; mehr braucht "
        "mehr Bilder, als die meisten Datensätze haben."
    ),
    "The backbone learns at this fraction of the head's speed. A backbone that already works "
    "is being nudged; at full speed a few hundred pictures destroy it.": (
        "Das Backbone lernt mit diesem Bruchteil der Learning Rate des Heads. Ein Backbone, "
        "das schon funktioniert, wird nur angestupst; mit der vollen Learning Rate zerstören "
        "es ein paar hundert Bilder."
    ),
    "A tenth keeps the pretrained features while letting them adapt.": (
        "Ein Zehntel bewahrt die vortrainierten Features und lässt sie sich trotzdem anpassen."
    ),
    # spec.py — refusals of a value
    "{+label} ({+term}) must be between {low} and {high}, got {value}": (
        "{+label} ({+term}) muss zwischen {low} und {high} liegen, bekommen: {value}"
    ),
    "{+label} ({+term}) must be true or false, got {value}": (
        "{+label} ({+term}) muss wahr oder falsch sein, bekommen: {value}"
    ),
    "{+label} ({+term}) must be one of {allowed}, got {value}": (
        "{+label} ({+term}) muss eins davon sein: {allowed}, bekommen: {value}"
    ),
    "{+label} ({+term}) must be a number, got {value}": (
        "{+label} ({+term}) muss eine Zahl sein, bekommen: {value}"
    ),
    "{+label} ({+term}) must be a whole number, got {value}": (
        "{+label} ({+term}) muss eine ganze Zahl sein, bekommen: {value}"
    ),
    "Unknown parameter(s) for {+title}: {unknown}. Known: {known}": (
        "Unbekannte(r) Parameter für {+title}: {unknown}. Bekannt: {known}"
    ),
    "No training parameters for {model}": "Keine Trainingsparameter für {model}",
}

__all__ = ["ENTRIES"]
