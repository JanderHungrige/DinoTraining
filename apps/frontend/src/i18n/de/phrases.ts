import type { phrasesEn } from '../en/phrases';
import type { Catalogue } from '../types';

export const phrasesDe: Catalogue<typeof phrasesEn> = {
  // Die Phrasenleiste
  'phrases.bar.title': 'Phrasen',
  'phrases.bar.titleOptional': 'Phrasen (optional)',
  'phrases.bar.chipsLabel': 'Phrasen — Tasten 1–9 wählen eine aus',
  'phrases.bar.also': 'Auch: {variants}',
  'phrases.bar.noVariations': 'Noch keine Varianten',
  'phrases.bar.addLabel': '+ Phrase',
  'phrases.bar.addPlaceholder': 'Signal, Eisenbahnsignal, Lichtsignal',
  'phrases.bar.addButton': 'Hinzufügen',
  'phrases.bar.addHint': 'Kommas trennen die Varianten einer Phrase.',
  'phrases.bar.joinsClass': ' Sie kommt zur Klasse {name}.',
  'phrases.bar.keys': 'Tasten: 1–9 wählen eine Phrase · A alles markiert · N nicht in diesem Bild.',

  // Die Phrasen des gewählten Umrisses
  'phrases.selected.needsOutline': '#{number}: Phrasen gehören an Umrisse — mach zuerst einen aus dieser Box.',
  'phrases.selected.groupLabel': 'Phrasen von Umriss {number}',
  'phrases.selected.answersTo': '#{number} passt zu',
  'phrases.selected.classAlways': 'Sein Klassenname ist immer eine seiner Phrasen',
  'phrases.selected.remove': '{phrase} von Umriss {number} entfernen',
  'phrases.selected.add': '„{phrase}“ hinzufügen',
  'phrases.selected.otherClass': '„{phrase}“ ist eine Phrase der Klasse {className}; dieser Umriss ist {outline}.',
  'phrases.selected.unnamed': 'unbenannt',

  // Die Prüfungen dieses Bildes
  'phrases.checks.caption': 'Dieses Bild',
  'phrases.checks.complete': 'alles markiert',
  'phrases.checks.absent': 'nicht in diesem Bild',
  'phrases.checks.unchecked': 'nicht geprüft',
  'phrases.checks.markComplete': 'Alles markiert',
  'phrases.checks.markAbsent': 'Nicht in diesem Bild',
  'phrases.checks.clear': 'zurücksetzen',
  'phrases.checks.clearLabel': 'Prüfung für {phrase} zurücksetzen',

  // Phrasen verwalten
  'phrases.manage.title': 'Phrasen verwalten',
  'phrases.manage.variations': 'Varianten',
  'phrases.manage.variationsPlaceholder': 'Eisenbahnsignal, Lichtsignal',
  'phrases.manage.confusable': 'Nicht zu verwechseln mit',
  'phrases.manage.confusablePlaceholder': 'Straßenlaterne, Verkehrsschild',
  'phrases.manage.save': 'Speichern',
  'phrases.manage.markRest': 'Den Rest markieren',
  'phrases.manage.markRestHint':
    'Nur wenn jedes Bild für diese Phrase vollständig annotiert ist: Jedes ungeprüfte Bild wird „alles markiert“, wo es einen Umriss davon hat, und „nicht in diesem Bild“, wo es keinen hat.',
  'phrases.manage.marked': 'Markiert: {complete} alles markiert, {absent} nicht in diesem Bild.',

  // So funktionieren Phrasen — *Betonung* und `Code` werden als solche dargestellt.
  'phrases.help.title': 'So funktionieren Phrasen',
  'phrases.help.variationsTerm': 'Varianten einer Phrase',
  'phrases.help.variationsText':
    'Schreib die Phrase so, wie du danach fragen würdest, dazu 2–4 andere Formulierungen, durch Kommas getrennt. Das Modell lernt sie als einen Begriff. Du brauchst nicht jedes Synonym: Ein paar zeigen ihm, dass die Formulierung variieren kann, und von da aus verallgemeinert es.',
  'phrases.help.checksTerm': 'Alles markiert · Nicht in diesem Bild',
  'phrases.help.checksText':
    'SAM 3 lernt aus jedem Bild, das du geprüft hast. *Alles markiert* heißt: Jedes Vorkommen dieser Phrase hier hat einen Umriss. *Nicht in diesem Bild* heißt: Es gibt hier keins – und bringt dem Modell bei, es hier *nicht* zu finden. Sobald eine Phrase auf irgendeinem Bild geprüft ist, wird ein Bild, das du nicht geprüft hast, für sie weggelassen, nie geraten. Eine nie geprüfte Phrase behält die automatische Regel – kein Umriss heißt: keins hier –, und die stimmt nur, wenn du jedes Vorkommen annotiert hast. Falls ja, prüft *Den Rest markieren* unter „Phrasen verwalten“ alle übrigen Bilder in einem Schritt.',
  'phrases.help.negativesTerm': 'Harte Negativbeispiele',
  'phrases.help.negativesText':
    'Bilder, die als *nicht in diesem Bild* markiert sind, sind die stärksten Lektionen – besonders, wenn etwas Ähnliches *doch* da ist. Trag Verwechslungen unter „Phrasen verwalten“ als „nicht zu verwechseln mit“ ein. Das Training fügt außerdem allgemeine, unverwandte Phrasen hinzu (allgemeine Negativbeispiele, `num_negatives`) und andere Phrasen deines Datensatzes (Kreuz-Negativbeispiele, `num_cross_negatives`) – siehe die Trainingseinstellungen von SAM 3.',

  // Die Annotationsrichtlinie
  'phrases.guideline.loading': 'Richtlinie wird geladen …',
  'phrases.guideline.saved': 'Gespeichert.',
  'phrases.guideline.title': 'Annotationsrichtlinie',
  'phrases.guideline.noneYet': ' (noch keine)',
  'phrases.guideline.hint':
    'Schreib die Konventionen auf, damit jedes Bild gleich annotiert wird: was zu einem Objekt gehört, wann du es als unklar markierst, welcher Name der richtige ist.',
  'phrases.guideline.placeholder': 'Ringe: Umriss mit gefülltem Loch.\nMehr als halb verdeckt: unklar.',
  'phrases.guideline.save': 'Richtlinie speichern',

  // Zweiter Blick
  'phrases.secondLook.title': 'Zweiter Blick',
  'phrases.secondLook.nothingYet': 'Noch nichts beurteilt.',
  'phrases.secondLook.figure': '{changed} von {reviewed} brauchten eine Änderung ({percent} %)',
  'phrases.secondLook.judged': '{reviewed} von {total} beurteilt',
  'phrases.secondLook.right': 'Sieht richtig aus',
  'phrases.secondLook.changed': 'Brauchte eine Änderung',
  'phrases.secondLook.end': 'Zweiten Blick beenden',
  'phrases.secondLook.startHint': 'Zeigt zufällige 5 % der annotierten Bilder noch einmal, damit du sie frisch beurteilst',
  'phrases.secondLook.lastTime': 'Letztes Mal: {figure}',
};
