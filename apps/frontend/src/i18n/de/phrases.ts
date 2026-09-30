import type { phrasesEn } from '../en/phrases';
import type { Catalogue } from '../types';

export const phrasesDe: Catalogue<typeof phrasesEn> = {
  // Die Phrasenleiste (Doc 116): ein Überblick; hier entsteht keine Klasse
  'phrases.bar.title': 'Phrasen',
  'phrases.bar.titleOptional': 'Phrasen (optional)',
  'phrases.bar.chipsLabel': 'Klassen und Oberbegriffe, mit ihren Umrissen',
  'phrases.bar.also': 'Auch: {variants}',
  'phrases.bar.noVariations': 'Noch keine Varianten',
  'phrases.bar.over': 'Oberbegriff über {members}',

  // + Oberbegriff (Doc 115)
  'phrases.umbrella.addLabel': '+ Oberbegriff',
  'phrases.umbrella.placeholder': 'screw',
  'phrases.umbrella.classesLabel': 'über die Klassen',
  'phrases.umbrella.add': 'Hinzufügen',
  'phrases.umbrella.hint': 'Ein allgemeiner Name über mehrere Klassen, z. B. „screw“ für m8 und m9. Jeder Umriss dieser Klassen gehört dazu. Schreib ihn auf Englisch — SAM 3 liest Englisch.',
  'phrases.umbrella.needTwo': 'Wähl mindestens zwei Klassen.',
  'phrases.umbrella.noClasses': 'Ein Oberbegriff braucht zwei Klassen. Leg zuerst Klassen in der Annotationsliste an.',

  // Phrasen verwalten
  'phrases.manage.title': 'Phrasen verwalten',
  'phrases.manage.variations': 'Varianten',
  'phrases.manage.variationsPlaceholder': 'm8 bolt, hex screw m8',
  'phrases.manage.confusable': 'Nicht zu verwechseln mit',
  'phrases.manage.confusablePlaceholder': 'nail, rivet',
  'phrases.manage.save': 'Speichern',
  'phrases.manage.confusableHint':
    'Nur Namen, und nur für Dinge, die selten mit ihr im selben Bild sind. SAM 3 wird auf vollständigen Bildern danach gefragt und lernt, nichts zu finden. Etwas, das im selben Bild ist (eine Spiegelung, ein Schatten): Lehn stattdessen seinen Umriss ab — siehe „So funktionieren Phrasen“.',
  'phrases.manage.delete': 'Löschen',
  'phrases.manage.deleteConfirm': '„{phrase}“ wirklich löschen?',
  'phrases.manage.deleteHint': 'Entfernt die Phrase, ihre Verknüpfungen mit Umrissen und ihre Bildprüfungen. Die Umrisse selbst bleiben, mit ihrer Klasse.',
  'phrases.manage.implicit': 'Die eigene Phrase einer Klasse: Sie besteht, solange es Umrisse der Klasse {name} gibt.',
  'phrases.manage.umbrella': 'Oberbegriff über {members}',
  'phrases.manage.legacy': 'Ältere Unterphrase der Klasse {name}, mit einzelnen Umrissen verknüpft. Sie trainiert weiter; eine neue Unterart legst du als eigene Klasse an.',

  // Bildprüfungen — eingeklappt (Doc 116)
  'phrases.checks.section': 'Nur für importierte oder teilweise annotierte Datensätze',
  'phrases.checks.intro': 'Ein Bild, das du speicherst, gilt als vollständig für die Klassen, die es dann gibt. Prüf nur von Hand, wo das nicht stimmt — etwa bei einem importierten Datensatz, in dem manche Klassen fehlen.',
  'phrases.checks.caption': 'Dieses Bild',
  'phrases.checks.complete': 'alles markiert',
  'phrases.checks.absent': 'nicht in diesem Bild',
  'phrases.checks.unchecked': 'nicht geprüft',
  'phrases.checks.markComplete': 'Alles markiert',
  'phrases.checks.markAbsent': 'Nicht in diesem Bild',
  'phrases.checks.clear': 'zurücksetzen',
  'phrases.checks.clearLabel': 'Prüfung für {phrase} zurücksetzen',
  'phrases.checks.keys': 'Tasten, solange das offen ist: 1–9 wählen eine Phrase · A alles markiert · N nicht in diesem Bild.',
  'phrases.checks.markRest': 'Den Rest markieren',
  'phrases.checks.markRestFor': 'Den Rest markieren für',
  'phrases.checks.markRestHint':
    'Nur wenn jedes Bild für diese Phrase vollständig annotiert ist: Jedes ungeprüfte Bild wird „alles markiert“, wo es einen Umriss davon hat, und „nicht in diesem Bild“, wo es keinen hat.',
  'phrases.checks.marked': 'Markiert: {complete} alles markiert, {absent} nicht in diesem Bild.',

  // So funktionieren Phrasen — *Betonung* und `Code` werden als solche dargestellt.
  'phrases.help.title': 'So funktionieren Phrasen',
  'phrases.help.classesTerm': 'Klassen sind Phrasen',
  'phrases.help.classesText':
    'SAM 3 wird nach Namen gefragt: Jeder Klassenname ist eine Phrase, und ihre Umrisse sind die Antwort. Klassen legst du unten in der Annotationsliste an — auch für Unterarten, also *m8* und *m9* statt einer Klasse „screw“. Ein Bild, das du speicherst, gilt als vollständig für die Klassen, die es dann gibt.',
  'phrases.help.umbrellaTerm': 'Oberbegriffe',
  'phrases.help.umbrellaText':
    'Ein allgemeiner Name über mehrere Klassen: *screw* über *m8* und *m9*. SAM 3 lernt beide Ebenen aus denselben Umrissen — „screw“ findet jede m8 und m9, „m8“ nur die m8. Boxen und Heads lernen weiter m8 und m9.',
  'phrases.help.variationsTerm': 'Varianten',
  'phrases.help.variationsText':
    'Andere Formulierungen einer Klasse — Fachvokabular, 2–4 reichen, durch Kommas getrennt, auf Englisch. Das Modell lernt sie als einen Begriff und verallgemeinert von da aus.',
  'phrases.help.lookalikesTerm': 'Verwechslungen',
  'phrases.help.lookalikesText':
    '*Nicht zu verwechseln mit* nennt Dinge, die ähnlich aussehen, aber selten mit der Klasse im selben Bild sind: ein *nail* bei einer Schraube. SAM 3 wird danach gefragt und lernt, nichts zu finden – das schärft die Grenze. Etwas Falsches *im selben Bild* (eine Spiegelung, als Flamme vorgeschlagen) lehnst du stattdessen ab (✗): Die gespeicherten Umrisse sind dann die ganze Antwort. Soll die Verwechslung auch gefunden werden, mach eine Klasse daraus.',
  'phrases.help.negativesTerm': 'Hard Negatives',
  'phrases.help.negativesText':
    'Das Training fragt außerdem nach unverwandten Alltagsbegriffen (Generic Negatives, `num_negatives`) und nach deinen anderen Klassen auf Bildern ohne sie (Cross Negatives, `num_cross_negatives`) – siehe die Trainingseinstellungen von SAM 3.',

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
