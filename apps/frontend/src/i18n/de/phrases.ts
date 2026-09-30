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
  'phrases.bar.addPlaceholder': 'signal, railway signal, light signal',
  'phrases.bar.addButton': 'Hinzufügen',
  'phrases.bar.addHint': 'Kommas trennen die Varianten einer Phrase. Schreib Phrasen auf Englisch — SAM 3 liest Englisch.',
  'phrases.bar.classLabel': 'gehört zu',
  'phrases.bar.ownClass': 'eigene Klasse (neu)',
  'phrases.bar.ownClassHint': ' Sie wird eine neue Klasse: Umrisse, die du mit ihr verknüpfst, trainieren als „{name}“.',
  'phrases.bar.joinsClass': ' Sie kommt zur Klasse {name}: eine genauere Art, SAM 3 nach einigen ihrer Umrisse zu fragen. Damit verknüpfte Umrisse trainieren für Boxen und Heads weiter als {name}.',
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
  'phrases.checks.restHint':
    'Jedes Vorkommen einer Phrase im ganzen Datensatz annotiert? Dann musst du nicht jedes Bild einzeln prüfen: Am Ende markiert „Den Rest markieren“ unter „Phrasen verwalten“ alle übrigen Bilder in einem Schritt.',
  'phrases.checks.clearLabel': 'Prüfung für {phrase} zurücksetzen',

  // Phrasen verwalten
  'phrases.manage.title': 'Phrasen verwalten',
  'phrases.manage.variations': 'Varianten',
  'phrases.manage.variationsPlaceholder': 'railway signal, light signal',
  'phrases.manage.confusable': 'Nicht zu verwechseln mit',
  'phrases.manage.confusablePlaceholder': 'street lamp, traffic sign',
  'phrases.manage.save': 'Speichern',
  'phrases.manage.confusableHint':
    'Nur Namen, und nur für Dinge, die selten mit ihr im selben Bild sind. SAM 3 wird auf Bildern mit „alles markiert“ danach gefragt und lernt, nichts zu finden. Etwas, das im selben Bild ist (eine Spiegelung, ein Schatten): Lehn stattdessen seinen Umriss ab — siehe „So funktionieren Phrasen“.',
  'phrases.manage.delete': 'Löschen',
  'phrases.manage.deleteConfirm': '„{phrase}“ wirklich löschen?',
  'phrases.manage.deleteHint': 'Entfernt die Phrase, ihre Verknüpfungen mit Umrissen und ihre Bildprüfungen. Die Umrisse selbst bleiben, mit ihrer Klasse.',
  'phrases.manage.implicit': 'Die eigene Phrase einer Klasse: Sie besteht, solange es Umrisse der Klasse {name} gibt.',
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
  'phrases.help.classesTerm': 'Phrasen und Klassen',
  'phrases.help.classesText':
    'Eine *Klasse* ist das, was Boxen und Heads lernen, und jeder Klassenname ist auch eine Phrase. „+ Phrase“ fragt, wozu die neue Phrase *gehört*: *eigene Klasse* macht ein neues Ding, das gefunden werden soll (es bekommt eigene Umrisse); eine bestehende Klasse macht eine genauere Formulierung für einige Umrisse dieser Klasse, z. B. „red car“ in der Klasse car — wähl einen Umriss und füg ihm die Phrase hinzu. Kommas geben einer Phrase mehrere Formulierungen, nicht mehrere Phrasen.',
  'phrases.help.lookalikesTerm': 'Verwechslungen und falsche Vorschläge',
  'phrases.help.lookalikesText':
    '*Zwei Dinge, die beide gefunden werden sollen* (Signal und Straßenlaterne): Gib jedem eine eigene Klasse und umreiß beide. Dann ist jedes automatisch ein Negative für das andere; unter „nicht zu verwechseln mit“ gehört nichts. *Ein falscher Vorschlag* (eine Spiegelung, als Flamme vorgeschlagen): Lehn ihn ab (✗) und markier das Bild für Flamme als *Alles markiert*. Die Flammen-Umrisse sind dann die ganze Antwort auf diesem Bild, also lernt das Modell, dass die Spiegelung keine ist — keine neue Klasse nötig. Leg eine Klasse „flame reflection“ nur an, wenn auch Spiegelungen gefunden werden sollen. *Nicht zu verwechseln mit* ist für Namen von Dingen, die selten mit der Phrase im selben Bild sind; auf einem Bild, auf dem du einen Umriss der Phrase abgelehnt hast, wird nie danach gefragt.',
  'phrases.help.negativesTerm': 'Hard Negatives',
  'phrases.help.negativesText':
    'Bilder, die als *nicht in diesem Bild* markiert sind, sind die stärksten Lektionen – besonders, wenn etwas Ähnliches *doch* da ist. Das Training fügt außerdem allgemeine, unverwandte Phrasen hinzu (Generic Negatives, `num_negatives`) und andere Phrasen deines Datensatzes (Cross Negatives, `num_cross_negatives`) – siehe die Trainingseinstellungen von SAM 3.',

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
