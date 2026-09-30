import type { prepareEn } from '../en/prepare';
import type { Catalogue } from '../types';

export const prepareDe: Catalogue<typeof prepareEn> = {
  // The tab and its pickers
  'prepare.tab.title': 'Daten vorbereiten',
  'prepare.tab.lead':
    'Mach einen Datensatz Schritt für Schritt bereit fürs Training. Jeder Schritt empfiehlt eine Einstellung und sagt, warum; du kannst sie ändern oder vorspringen, wenn du weißt, was du brauchst.',
  'prepare.tab.dataset': 'Datensatz',
  'prepare.tab.noDatasets': 'Noch keine Datensätze mit Bildern',
  'prepare.tab.datasetOption_one': '{name} ({count} Bild)',
  'prepare.tab.datasetOption_other': '{name} ({count} Bilder)',
  'prepare.tab.model': 'Zu trainierendes Modell',

  // The steps
  'prepare.nav.label': 'Vorbereitungsschritte',
  'prepare.nav.unused': ' (nicht genutzt)',
  'prepare.step.audit': 'Daten prüfen',
  'prepare.step.fix': 'Sicher korrigieren',
  'prepare.step.split': 'Aufteilung',
  'prepare.step.input': 'Was das Modell sieht',
  'prepare.step.balance': 'Ungleiche Klassen',
  'prepare.step.augment': 'Veränderte Kopien',
  'prepare.step.save': 'Rezept speichern',
  'prepare.unused.balance':
    'Beim Fine-Tuning dieses Modells werden Klassen nicht ausgeglichen: Jedes Bild zählt einmal. Das Rezept hält trotzdem eine Wahl fest; sie gilt, wenn du damit einen DINO-Head trainierst.',
  'prepare.unused.augment':
    'Beim Fine-Tuning lernt dieses Modell die Bilder so, wie sie sind: Es macht keine veränderten Kopien. Das Rezept hält trotzdem eine Wahl fest; sie gilt, wenn du damit einen DINO-Head trainierst.',
  'prepare.option.recommended': 'empfohlen',

  // Shared table headings
  'prepare.table.class': 'Klasse',
  'prepare.table.examples': 'Beispiele',
  'prepare.table.pictures': 'Bilder',

  // Check the data
  'prepare.audit.why':
    'Die Prüfung öffnet jedes Bild, liest jede Annotation und sagt dir, was das Training schiefgehen lassen würde – beurteilt für {model}, denn was „zu klein“ ist, hängt vom Modell ab. Sie ändert nichts.',
  'prepare.audit.run': 'Prüfung starten',
  'prepare.audit.runAgain': 'Prüfung erneut starten',
  'prepare.audit.progress': 'Prüfe jedes Bild … {done} von {total} ({share} %)',
  'prepare.audit.otherModel':
    'Diese Prüfung wurde für ein anderes Modell gemacht. Starte sie erneut, um die Bilder für {model} zu beurteilen.',
  'prepare.audit.summary':
    '{images} Bilder, {annotations} Annotationen, {classes} Klassen · {problems} Problem(e), {warnings} zum Ansehen{excluded}.',
  'prepare.audit.excluded': ' · {count} durch eine Korrektur ausgelassen',
  'prepare.audit.nothing': 'Nichts zu melden. Die Daten sehen bereit aus.',
  'prepare.audit.failed': 'Die Prüfung ist fehlgeschlagen.',

  // One finding
  'prepare.finding.problem': 'Fehler',
  'prepare.finding.warn': 'Besser beheben',
  'prepare.finding.info': 'Gut zu wissen',
  'prepare.finding.ok': 'In Ordnung',
  'prepare.finding.why': 'Warum das wichtig ist: ',
  'prepare.finding.action': 'Was du tun kannst: ',
  'prepare.finding.examples': 'Bilder zum Ansehen',

  // Fix what is safe
  'prepare.fix.why':
    'Diese Korrekturen sind sicher: Nichts wird gelöscht, und alles lässt sich rückgängig machen. Ermessensfragen – unscharfe oder falsch beschriftete Bilder – entscheidest du; die Prüfung zeigt dir, wo du hinschauen solltest.',
  'prepare.fix.copies_one': 'Von jeder Kopie eine behalten ({count} Gruppe)',
  'prepare.fix.copies_other': 'Von jeder Kopie eine behalten ({count} Gruppen)',
  'prepare.fix.unreadable': 'Unlesbare Bilder auslassen ({count})',
  'prepare.fix.putBack_one': 'Das ausgelassene Bild zurückholen ({count})',
  'prepare.fix.putBack_other': 'Alle {count} ausgelassenen Bilder zurückholen',
  'prepare.fix.leftOut_one': '{count} Bild ausgelassen.',
  'prepare.fix.leftOut_other': '{count} Bilder ausgelassen.',
  'prepare.fix.putBackDone_one': '{count} Bild zurückgeholt.',
  'prepare.fix.putBackDone_other': '{count} Bilder zurückgeholt.',
  'prepare.fix.again': 'Starte die Prüfung erneut, um die Wirkung zu sehen.',
  'prepare.fix.auditFirst': 'Starte zuerst die Prüfung: Die Korrekturen wirken auf das, was sie gefunden hat.',
  'prepare.fix.classesLegend': 'Klassen, wie das Training sie sieht',
  'prepare.fix.classesHint':
    'Führe eine Klasse mit einer anderen zusammen, indem du ihr deren Namen gibst, oder lass sie aus. Die gespeicherten Annotationen behalten ihre Namen, du kannst das also jederzeit zurückändern.',
  'prepare.fix.trainAs': 'Trainieren als',
  'prepare.fix.leaveOut': 'Auslassen',
  'prepare.fix.trainNameAs': '{name} trainieren als',
  'prepare.fix.leaveOutName': '{name} auslassen',
  'prepare.fix.saveClasses': 'Klassenänderungen speichern',

  // Split
  'prepare.split.why':
    'Das Modell lernt aus den Trainingsbildern und wird an Bildern bewertet, die es nie gesehen hat. Steckt eine Beinahe-Kopie eines Testbilds im Training – das nächste Bild eines Videos, ein weiteres Foto derselben Szene –, misst der Wert Erinnerung statt Lernen. Deshalb bleiben Videobilder und Szenen zusammen, und Bilder direkt an einer Grenze werden beiseitegelegt.',
  'prepare.split.auto': 'Automatisch aufteilen (empfohlen)',
  'prepare.split.again': 'Neu aufteilen',
  'prepare.split.keep': 'Die Aufteilung behalten, die der Datensatz mitbringt',
  'prepare.split.train': 'Training',
  'prepare.split.val': 'Validierung',
  'prepare.split.test': 'Test',
  'prepare.split.buffer':
    '{count} Bild(er) direkt an einer Grenze werden beiseitegelegt: zu nah an den Bildern der anderen Seite, um so oder so fair zu sein.',

  // What the model sees
  'prepare.input.why':
    'Jedes Modell verkleinert ein Bild auf eine feste Größe, bevor es hinschaut. Unten siehst du deine eigenen Bilder genau so, wie dieses Modell sie bekommt. Wenn du ein Objekt hier nicht erkennen kannst, kann das Modell es auch nicht.',
  'prepare.input.preparing': 'Bereite die Bilder vor …',
  'prepare.input.sizes':
    '{label}: Ein typisches Objekt ist {median} groß, das kleinste Zehntel {p10} px. Dieses Modell braucht etwa {needed} px – {share} sind kleiner.',
  'prepare.input.whole': 'Ganze Bilder',
  'prepare.input.onTiles': 'Auf Kacheln',
  'prepare.input.tiles': 'In Kacheln schneiden',
  'prepare.input.recommended': 'Empfohlen',
  'prepare.input.off': 'Aus – ganze Bilder',
  'prepare.input.grid': '{count} Kacheln entlang der langen Seite',
  'prepare.input.seenAlt': 'So sieht das Modell {path}',
  'prepare.input.objects_one': '{count} Objekt',
  'prepare.input.objects_other': '{count} Objekte',
  'prepare.input.tooSmall': ', {count} zu klein (rot)',
  'prepare.input.cutOff': ', {count} abgeschnitten',
  'prepare.input.oneTile': ' · eine Kachel',

  // Unequal classes
  'prepare.balance.counting': 'Zähle die Klassen …',
  'prepare.balance.why':
    'Ein Modell belohnt sich dafür, oft richtig zu liegen. Ist eine Klasse viel häufiger, kann es genau wirken, während es die seltenen meist übersieht – oft gerade die, auf die es ankommt.',
  'prepare.balance.ratio': 'Die größte Klasse hat {ratio} so viele Beispiele wie die kleinste.',
  'prepare.balance.label': 'Wie mit ungleichen Klassen umgehen',
  'prepare.balance.countsAs': 'Zählt als',
  'prepare.balance.perRound': 'Gezeigt pro Durchgang',
  'prepare.balance.notApplied':
    'Beim Fine-Tuning dieses Modells wird die Wahl noch nicht angewendet; sie wird im Rezept gespeichert, für später.',

  // Changed copies
  'prepare.augment.looking': 'Sehe mir die Klassen an …',
  'prepare.augment.why':
    'Sieht ein Modell in jedem Durchgang dieselben Bilder, lernt es genau diese Bilder. Jedes ein wenig zu verändern – Licht, ein Ausschnitt, ein Spiegelbild – bringt ihm bei, was gleich bleibt: das Objekt. Boxen bewegen sich immer mit dem Bild.',
  'prepare.augment.label': 'Wie die Bilder verändert werden',
  'prepare.augment.noMirroring': 'nicht spiegeln',
  'prepare.augment.originalAlt': 'Das Ausgangsbild',
  'prepare.augment.changedAlt': 'Veränderte Kopie {n}',
  'prepare.augment.original': 'Ausgangsbild',
  'prepare.augment.version': 'Kopie {n}',

  // Save the recipe
  'prepare.save.why':
    'Das Rezept hält alles fest, was hier entschieden wurde. So nutzt das Training genau diese Vorbereitung, und ein trainiertes Modell kann sagen, wie seine Daten vorbereitet wurden. Speichern unter demselben Namen legt eine neue Version an; nichts wird überschrieben.',
  'prepare.save.model': 'Modell: {model}',
  'prepare.save.tiles': 'Kacheln: {tiles}',
  'prepare.save.tilesRecommended': 'wie empfohlen',
  'prepare.save.tilesOff': 'aus',
  'prepare.save.tilesGrid': '{count} entlang der langen Seite',
  'prepare.save.balance': 'Ungleiche Klassen: {value}',
  'prepare.save.augment': 'Veränderte Kopien: {value}',
  'prepare.save.augmentNone': 'keine',
  'prepare.save.strategyNone': 'bleiben, wie sie sind',
  'prepare.save.strategyWeighted': 'seltene Klassen zählen mehr',
  'prepare.save.strategyBalanced': 'seltene Klassen öfter gezeigt',
  'prepare.save.name': 'Name des Rezepts',
  'prepare.save.defaultName': '{dataset} für {model}',
  'prepare.save.button': 'Rezept speichern',
  'prepare.save.recipeLine': '– {target}, {train}/{val}/{test} Bilder, {imbalance}, {augmentation}',
  'prepare.save.outOfDate': ' Veraltet: {reasons}',
  'prepare.save.train': 'Mit {name} · v{version} trainieren',
};
