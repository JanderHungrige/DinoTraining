"""German for the split's warnings and refusals (doc 84: split_service.py), recipes (doc 88:
recipe.py), the default-recipe job (doc 101: default_recipe.py) and the fine-tune job's
messages and notes (doc 93: finetune/runner.py, doc 108: sam3_queries.describe)."""

from __future__ import annotations

_FIX_SCENES = "More examples, spread over more scenes, would fix that."

ENTRIES: dict[str, str] = {
    # The split's warnings, per side
    "{names} never appears in val, so results for it cannot be measured there. " + _FIX_SCENES: (
        "{names} kommt in Validation nie vor, dort lässt sich also kein Ergebnis dafür "
        "messen. Mehr Beispiele, verteilt auf mehr Szenen, würden das beheben."
    ),
    "{names} never appear in val, so results for them cannot be measured there. " + _FIX_SCENES: (
        "{names} kommen in Validation nie vor, dort lassen sich also keine Ergebnisse dafür "
        "messen. Mehr Beispiele, verteilt auf mehr Szenen, würden das beheben."
    ),
    "{names} never appears in test, so results for it cannot be measured there. " + _FIX_SCENES: (
        "{names} kommt in Test nie vor, dort lässt sich also kein Ergebnis dafür messen. Mehr "
        "Beispiele, verteilt auf mehr Szenen, würden das beheben."
    ),
    "{names} never appear in test, so results for them cannot be measured there. " + _FIX_SCENES: (
        "{names} kommen in Test nie vor, dort lassen sich also keine Ergebnisse dafür messen. "
        "Mehr Beispiele, verteilt auf mehr Szenen, würden das beheben."
    ),
    "No image ended up in val: the dataset has too few separate scenes or stretches of video "
    "to spare one. Add images from other scenes or videos.": (
        "Kein Bild ist in Validation gelandet: Der Datensatz hat zu wenige getrennte "
        "Szenen oder Videoabschnitte, um einen davon abzugeben. Füge Bilder aus anderen Szenen "
        "oder Videos hinzu."
    ),
    "No image ended up in test: the dataset has too few separate scenes or stretches of video "
    "to spare one. Add images from other scenes or videos.": (
        "Kein Bild ist in Test gelandet: Der Datensatz hat zu wenige getrennte Szenen oder "
        "Videoabschnitte, um einen davon abzugeben. Füge Bilder aus anderen Szenen oder Videos "
        "hinzu."
    ),
    "Only {#count} image(s) in val: too few to trust a score.": (
        "Nur {count} Bild(er) in Validation: zu wenige, um einem Score zu trauen."
    ),
    "Only {#count} image(s) in test: too few to trust a score.": (
        "Nur {count} Bild(er) in Test: zu wenige, um einem Score zu trauen."
    ),
    "One group holds most of the images (one long scene or video), so the sides could not be "
    "balanced. The split is still leak-free.": (
        "Eine Gruppe enthält die meisten Bilder (eine lange Szene oder ein Video), deshalb "
        "ließen sich die Seiten nicht ausgleichen. Der Split ist trotzdem ohne "
        "Überschneidungen."
    ),
    "This dataset has not been audited, so photos of the same scene could not be found and "
    "may sit on different sides. Run the audit, then split again.": (
        "Dieser Datensatz wurde noch nicht geprüft, also konnten Fotos derselben Szene nicht "
        "gefunden werden und liegen vielleicht auf verschiedenen Seiten. Starte die Prüfung und "
        "mach dann einen neuen Split."
    ),
    "The validation and test shares must be between 0 and 1 together.": (
        "Validation- und Test-Anteil müssen zusammen zwischen 0 und 1 liegen."
    ),
    "There are no images to split.": "Es gibt keine Bilder für einen Split.",
    "Not every image came with a split from its source, so it cannot be kept.": (
        "Nicht jedes Bild kam mit einem Split aus seiner Quelle, also lässt er sich nicht behalten."
    ),
    # Recipes
    "Unknown imbalance strategy: {strategy}": (
        "Unbekannte Strategie für Class Imbalance: {strategy}"
    ),
    "Unknown target: {target}": "Unbekanntes Ziel: {target}",
    "The dataset has not been split yet. Run the Split step first, so evaluation never sees "
    "pictures the model trained on.": (
        "Der Datensatz hat noch keinen Split. Führe zuerst den Schritt „Split“ aus, "
        "damit die Bewertung nie Bilder sieht, auf denen das Modell trainiert hat."
    ),
    "The dataset has not been audited yet. Run the Audit step first.": (
        "Der Datensatz wurde noch nicht geprüft. Führe zuerst den Schritt „Daten prüfen“ aus."
    ),
    "The dataset changed after its last audit (images, annotations or fixes). Run the audit "
    "again, so the recipe describes the data it will train on.": (
        "Der Datensatz hat sich seit seiner letzten Prüfung geändert (Bilder, Annotationen oder "
        "Korrekturen). Starte die Prüfung erneut, damit das Rezept die Daten beschreibt, mit "
        "denen trainiert wird."
    ),
    "The class map changed (Fix step).": (
        "Die Klassenzuordnung hat sich geändert (Schritt „Sicher korrigieren“)."
    ),
    "Images, annotations or exclusions changed since the recipe was saved.": (
        "Bilder, Annotationen oder Auslassungen haben sich geändert, seit das Rezept "
        "gespeichert wurde."
    ),
    "The split changed since the recipe was saved.": (
        "Der Split hat sich geändert, seit das Rezept gespeichert wurde."
    ),
    # The default recipe (doc 101)
    "Unknown head type: {head_type}": "Unbekannter Head-Typ: {head_type}",
    "No preparation recipe for {model}": "Kein Vorbereitungsrezept für {model}",
    "A {task} head has no preparation recipe: there is nothing to split or balance by class "
    "for it.": (
        "Ein Head für „{task}“ hat kein Vorbereitungsrezept: Es gibt nichts, was sich für ihn "
        "nach Klassen splitten oder ausgleichen ließe."
    ),
    "An up-to-date default recipe already exists.": ("Es gibt schon ein aktuelles Standardrezept."),
    "Checking the data (audit)…": "Daten werden geprüft …",
    "Splitting without leaks…": "Split ohne Überschneidungen …",
    "Choosing class balance and changed copies…": (
        "Ausgleich der Klassen und Augmentation werden gewählt …"
    ),
    "Saving the recipe…": "Rezept wird gespeichert …",
    "Saved '{name}' v{#version}.": "„{name}“ v{version} gespeichert.",
    # The fine-tune job (doc 93)
    "No test pictures: base and fine-tuned are compared on the validation side, which also "
    "picked the best epoch, so the gain is optimistic.": (
        "Keine Test-Bilder: Foundation Model und fine-getuntes Modell werden auf Validation "
        "verglichen, womit auch die beste Epoch ausgewählt wurde – der Gewinn ist also "
        "geschönt."
    ),
    "On the held-out pictures the fine-tuned model scored {after} against the baseline's "
    "{before}: it is saved, but it is not the better model here.": (
        "Auf den Held-out-Bildern erreichte das fine-getunte Modell {after} gegenüber "
        "{before} beim Ausgangsmodell: Es ist gespeichert, aber hier nicht das bessere Modell."
    ),
    "No epoch beat the base model on validation ({metric} {base} against at best {tried}), so "
    "nothing was saved: the base model is the better one for this data. More varied examples, "
    "or a lower learning rate, may change that.": (
        "Keine Epoch war auf Validation besser als das Foundation Model ({metric} {base} "
        "gegenüber höchstens {tried}), also wurde nichts gespeichert: Für diese Daten ist das "
        "Foundation Model das bessere. Abwechslungsreichere Beispiele oder eine niedrigere "
        "Learning Rate können das ändern."
    ),
    "No validation pictures to choose an epoch with; nothing was saved.": (
        "Keine Validation-Bilder, um eine Epoch auszuwählen; es wurde nichts gespeichert."
    ),
    "The base model is kept": "Das Foundation Model bleibt",
    "Finished {#count} epochs": "{count} Epochs abgeschlossen",
    "Cancelled before epoch {#epoch}": "Vor Epoch {epoch} abgebrochen",
    "Cancelled during epoch {#epoch}": "Während Epoch {epoch} abgebrochen",
    "Umbrella term {+text}: answered by every outline of {classes}.": (
        "Oberbegriff {text}: beantwortet von jedem Umriss von {classes}."
    ),
    "Pictures left out for a class, as saved before it existed: {listed}.": (
        "Bilder, die für eine Klasse ausgelassen wurden, weil sie vor ihr gespeichert "
        "wurden: {listed}."
    ),
    "SAM 3 trained on {#positives} positive queries and {#negatives} negatives per round: "
    "{#absent} absent, {#cross} cross, {#rejected} rejected, {#confusable} confusable, "
    "{#generic} generic.": (
        "SAM 3 hat pro Epoch mit {positives} Positive Queries und {negatives} Negatives "
        "trainiert: {absent} „nicht in diesem Bild“, {cross} Cross, {rejected} abgelehnt, "
        "{confusable} Verwechslungen, {generic} Generic."
    ),
}

__all__ = ["ENTRIES"]
