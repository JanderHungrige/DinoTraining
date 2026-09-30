import type { introEn } from '../en/intro';
import type { Catalogue } from '../types';

export const introDe: Catalogue<typeof introEn> = {
  'intro.title': 'Worum es hier geht',
  'intro.lead':
    'DinoTraining macht aus einem Ordner voller Bilder ein Modell, das darin Dinge findet. Du annotierst einige Bilder, trainierst ein kleines Modell auf einem großen, vortrainierten Modell, schaust dir an, was es vorhersagt, und lässt es dir helfen, die nächsten Bilder schneller zu annotieren. Alles läuft auf diesem Rechner: Deine Bilder werden nirgendwohin hochgeladen.',
  'intro.loop.heading': 'Der Kreislauf',
  'intro.loop.note':
    'Die Tabs stehen in der Reihenfolge, in der du sie benutzt. Du wirst die Runde mehr als einmal drehen – genau darum geht es, und es heißt nicht, dass du beim ersten Mal etwas falsch gemacht hast.',
  'intro.loop.open': '{tab} öffnen',
  'intro.loop.whyHere': 'Warum an dieser Stelle:',

  'intro.stage.studio.title': 'Annotieren',
  'intro.stage.studio.what':
    'Wähle einen Ordner mit Bildern und bekomm Boxen, die du annimmst, ablehnst oder korrigierst. Dafür gibt es zwei Wege: Beschreib in Worten, wonach du suchst, und Grounding DINO schlägt Boxen vor – oder wähle einen Head, den du schon trainiert hast, und er schlägt Boxen für seine eigenen Klassen vor.',
  'intro.stage.studio.why':
    'Trainieren kann man erst, wenn etwas annotiert ist. Ob du mit Vorschlägen startest oder mit einer leeren Fläche, ist der Unterschied zwischen einem Nachmittag und einer Woche.',
  'intro.stage.prepare.title': 'Vorbereiten',
  'intro.stage.prepare.what':
    'Prüfe einen Datensatz, bevor du darauf trainierst: was daran nicht stimmt, was sich gefahrlos beheben lässt, eine Aufteilung, die fast gleiche Bilder zusammenhält, und deine Bilder genau so, wie das Modell sie sehen wird. Jeder Schritt empfiehlt eine Einstellung und sagt, warum.',
  'intro.stage.prepare.why':
    'Die meisten Trainingsläufe scheitern hier, nicht im Training. Ein Modell kann kein Objekt lernen, das auf zwei Pixel geschrumpft ist, und ein Testwert ist nichts wert, wenn die Testbilder fast Kopien der Trainingsbilder sind.',
  'intro.stage.trainer.title': 'Trainieren',
  'intro.stage.trainer.what':
    'Wähle ein Backbone und eine Head-Art, drück auf Trainieren und sieh zu, wie Loss und Messwerte live eintreffen. Ein Lauf dauert Sekunden bis Minuten, nicht Stunden.',
  'intro.stage.trainer.why':
    'Das geht so schnell, weil nur der Head trainiert wird – siehe „eingefrorenes Backbone“ weiter unten. Deshalb reicht auch ein kleiner Datensatz, um etwas Brauchbares zu bekommen.',
  'intro.stage.inference.title': 'Ansehen, was es gelernt hat',
  'intro.stage.inference.what':
    'Lass einen oder mehrere trainierte Heads über ein Bild laufen und sieh ihre Vorhersagen nebeneinander, neben dem Original. Basismodelle wie Depth Anything laufen hier auch.',
  'intro.stage.inference.why':
    'Ein Messwert sagt dir, dass ein Modell besser geworden ist. Nur der Blick auf die Bilder zeigt dir, *wie* es falschliegt – und genau das entscheidet, was du als Nächstes annotierst.',
  'intro.stage.generator.title': 'Mehr Daten erzeugen',
  'intro.stage.generator.what':
    'Lass einen trainierten Head – oder ein Segmentierungsmodell mit Text-Prompt – über neue Bilder laufen, prüf, was zurückkommt, und speichere das Ergebnis als neuen Datensatz.',
  'intro.stage.generator.why':
    'Dieser Schritt macht aus dem Ablauf einen Kreislauf. Das Modell, das du gerade trainiert hast, macht den ersten Durchgang über die nächsten Bilder, und du korrigierst es, statt bei null anzufangen.',
  'intro.stage.inspect.title': 'Ansehen, was du annotiert hast',
  'intro.stage.inspect.what':
    'Öffne einen Datensatz und spiel seine Videos und Bilderordner ab, mit jeder gespeicherten Box und jedem Umriss eingezeichnet und einem farbigen Balken pro Klasse, der zeigt, wo sie vorkommt.',
  'intro.stage.inspect.why':
    'Einem Datensatz vertraust du leichter, wenn du ihn dir angesehen hast. Lücken, schleichende Veränderungen und eine Klasse, die nur in einem Abschnitt einer Fahrt vorkommt, siehst du auf einer Zeitleiste in Sekunden – Bild für Bild suchst du danach einen Nachmittag lang.',
  'intro.stage.library.title': 'Den Überblick behalten',
  'intro.stage.library.what':
    'Jeder Datensatz, jeder trainierte Head und jedes fine-getunte Modell in einer Liste – mit dem, was darin steckt, womit es gelernt hat, und einer Möglichkeit, es zu löschen.',
  'intro.stage.library.why':
    'Der Kreislauf oben erzeugt schnell neue Dinge, und die meisten davon sind Experimente. Hier siehst du, was du tatsächlich hast, und wirfst weg, was du nicht brauchst.',
  'intro.stage.admin.title': 'Modelle und Einstellungen',
  'intro.stage.admin.what':
    'Lade Modellgewichte herunter, entferne sie, hinterlege deinen HuggingFace-Token und sieh nach, wo der Cache liegt. Jeder Eintrag nennt seine Lizenz, bevor du ihn herunterlädst.',
  'intro.stage.admin.why':
    'Mit der App werden keine Gewichte ausgeliefert – das Installationsprogramm wäre Gigabytes groß, und die meisten davon würdest du nie benutzen. Du lädst genau das herunter, was du brauchst.',
  'intro.stage.api.title': 'Oder lass deine eigene KI alles erledigen',
  'intro.stage.api.what':
    'Alles oben läuft über eine lokale API, und der Tab Verbindung gibt dir ein Dokument, das sie beschreibt. Füg es in ChatGPT, Claude oder etwas anderes ein und sag, was du willst – „lade diesen Datensatz herunter, fine-tune RF-DETR darauf und annotiere dann meine Bilder“ – und die KI kann den ganzen Kreislauf für dich erledigen.',
  'intro.stage.api.why':
    'Kein Schritt im Kreislauf, sondern ein anderer Weg, ihn zu durchlaufen. Er steht hier, weil eine Funktion, die niemand findet, genauso gut nicht existieren könnte – und an dieser läuft man leicht vorbei.',

  'intro.concepts.heading': 'Zwei Begriffe, die diese App ständig benutzt',
  'intro.concept.backbone.term': 'Ein eingefrorenes Backbone',
  'intro.concept.backbone.body':
    'Das Backbone (DINOv2, DINOv3) ist ein großes Modell, das schon auf Millionen von Bildern trainiert wurde. Es verwandelt ein Bild in Zahlen, die beschreiben, was darin ist – Kanten, Texturen, Objekte, Materialien. „Eingefroren“ heißt, dass wir es nie verändern: Wir lassen es laufen, behalten die Zahlen und lassen seine Gewichte genau so, wie sie geliefert wurden. Deshalb dauert das Training hier Sekunden statt Tage, und deshalb reichen ein paar hundert Bilder statt ein paar hunderttausend. Es heißt auch, dass sich das Backbone nie zu sehr an deine Daten anpassen (überanpassen) kann, weil es nie aus ihnen lernt.',
  'intro.concept.head.term': 'Ein Head',
  'intro.concept.head.body':
    'Der Head ist das kleine Modell auf dem Backbone, das du tatsächlich trainierst. Er liest die Zahlen des Backbones und macht daraus die Antwort, die du willst: eine Klasse, eine Box, einen Umriss, eine Tiefenkarte. Er ist klein – oft nur eine einzige Schicht –, weil das Backbone den schweren Teil schon erledigt hat. Ein Backbone kann viele Heads tragen, jeder mit einer anderen Aufgabe, und die Modell-Ansicht lässt mehrere davon in einem einzigen Durchlauf über ein Bild laufen.',
  'intro.concept.preprocessing.term': 'Warum du nie nach der Vorverarbeitung gefragt wirst',
  'intro.concept.preprocessing.body':
    'Größe ändern, zuschneiden und normalisieren muss genau zu dem passen, was das Backbone erwartet und womit der Head trainiert wurde. Liegst du dabei ein paar Pixel daneben, läuft das Modell trotzdem – es wird nur still und leise schlechter, und nichts sagt es dir. Deshalb leitet die App die Vorverarbeitung aus dem Backbone und dem Head ab, die du gewählt hast, und bietet sie nicht als Einstellung an. Es gibt keinen richtigen Wert, den du wählen könntest.',

  'intro.model.heading': 'Ein Modell wählen',
  'intro.model.note':
    'Jedes Modell hier kann etwas, das die anderen schlecht können. Alle Zahlen in diesem Bereich wurden in dieser App gemessen, mit den Datensätzen darin.',

  'intro.limits.heading': 'Was es noch nicht kann',
  'intro.limits.note': 'Es steht hier, weil es besser ist, es zu wissen, als zu denken, die App sei kaputt.',
  'intro.limit.stillImages': 'Nur Standbilder. Video- und Webcam-Eingabe gibt es noch nicht.',
  'intro.limit.masks':
    'Umrisse (Masken) werden geprüft, nicht gezeichnet. Du kannst einen vorgeschlagenen Umriss annehmen, ablehnen oder markieren, aber es gibt keinen Pinsel und keinen Polygon-Editor, um ihn von Hand zu korrigieren.',
  'intro.limit.detector':
    'Es gibt keinen vortrainierten DINO-Detektor zum Installieren. Für Klassifikation, Segmentierung und Tiefe gibt es fertige Heads; für Boxen trainierst du im Tab Training deinen eigenen oder fine-tunest dort RF-DETR – siehe „Welches Modell soll ich nehmen?“ oben.',
  'intro.limit.dragDrop':
    'Drag-and-drop funktioniert nur in der Desktop-App. Im Browser hat eine hineingezogene Datei keinen Pfad, den das Backend lesen kann – nutze dort das Ordnerfeld.',
  'intro.limit.noise':
    'Zwei gleiche Trainingsläufe liefern leicht unterschiedliche Zahlen. Die Aufteilung der Daten ist fest, die Startgewichte aber nicht – sieh einen kleinen Unterschied in den Messwerten also als Zufall an.',

  'intro.guide.lead':
    'Ein DINO-Head teilt sich einen Durchlauf des Backbones mit allen anderen Heads – deshalb ist es so günstig, Modelle zu vergleichen. Aber das Backbone bleibt eingefroren, seine Merkmale wurden also nie an deine Aufgabe angepasst. Für Klassifikation und Segmentierung ist das ein guter Tausch, für Detektion ein schlechter: Dort gewinnt ein eigens dafür gebauter Detektor mit großem Abstand. Nimm die DINO-Heads zum Ausprobieren und Vergleichen; nimm RF-DETR, wenn es auf den Wert ankommt.',

  'intro.guide.classifier.name': 'Linearer Klassifikator (DINO-Head)',
  'intro.guide.classifier.bestFor': 'Eine Klasse für ein ganzes Bild – ist dieses Bild ein Defekt oder nicht?',
  'intro.guide.classifier.strength1': 'Trainiert in Sekunden auf ein paar hundert Bildern.',
  'intro.guide.classifier.strength2':
    'Das Stärkste, was du mit einem eingefrorenen Backbone machen kannst, und am nächsten an dem, wofür DINOv2 gebaut wurde.',
  'intro.guide.classifier.weakness1':
    'Sagt nichts darüber, wo. Mit einem Bild, in dem zwei verschiedene Dinge sind, kann gar nicht trainiert werden – es wird übersprungen, und der Zähler sagt dir, wie viele es waren.',

  'intro.guide.segmenter.name': 'Linearer Segmentierer (DINO-Head)',
  'intro.guide.segmenter.bestFor': 'Welche Pixel zum Ding gehören – Schienen, Himmel, Bewuchs.',
  'intro.guide.segmenter.strength1':
    'Trainiert auf den Umrissen, die ein Begriffs-Segmentierer im Studio erzeugt – Annotieren und Trainieren sind also derselbe Kreislauf.',
  'intro.guide.segmenter.strength2':
    'Eingefrorene DINOv2-Merkmale sind darin wirklich stark – es ist eine der Aufgaben, bei denen das Backbone nachweislich schon mit einem einfachen linearen Head gut abschneidet.',
  'intro.guide.segmenter.weakness1':
    'Braucht Umrisse (Masken). Mit einem Datensatz, der nur Boxen hat, lässt er sich nicht trainieren, und Bilder, die niemand segmentiert hat, werden übersprungen statt als leer behandelt.',
  'intro.guide.segmenter.weakness2':
    'Trennt zwei sich berührende Objekte derselben Klasse nicht – er ordnet Pixel zu, keine einzelnen Objekte.',

  'intro.guide.detector.name': 'Ankerfreier Detektor (DINO-Head)',
  'intro.guide.detector.bestFor': 'Boxen, günstig, neben anderen Heads in einem Durchlauf des Backbones.',
  'intro.guide.detector.strength1':
    'Teilt sich den Durchlauf des Backbones mit allen anderen Heads – sieben Modelle zu vergleichen kostet also zwei Durchläufe statt sieben.',
  'intro.guide.detector.strength2':
    'Trainiert in Minuten auf zwischengespeicherten Merkmalen. Gut, wenn die Objekte eine vernünftige Größe haben und du heute eine Antwort willst.',
  'intro.guide.detector.weakness1':
    'Sagt nur in einer Größenstufe vorher. Kleine, weit entfernte Objekte sind nicht bloß schwierig – unter etwa 7 px am Modelleingang sind sie im Tensor überhaupt nicht vorhanden. Kacheln in der Modell-Ansicht sind die Lösung; eine Merkmalspyramide wäre die andere, und die ist nicht gebaut.',
  'intro.guide.detector.weakness2':
    'Das Backbone ist eingefroren, seine Merkmale wurden also nie aufs Lokalisieren angepasst. Sie sagen dir besser, was da ist, als wo genau.',
  'intro.guide.detector.measured':
    'mAP 0.61 bei Schachfiguren, 0.55 bei Blutzellen, 0.50-0.58 bei OSDaR23-Schienen – gegenüber 0.96 für ein fine-getuntes RF-DETR auf denselben Schienendaten. Diese Aufteilungen waren zufällig; bei einer Aufteilung ohne Überschneidungen (Daten vorbereiten) erreichten die Blutzellen 0.41 auf den Testbildern.',

  'intro.guide.rfdetr.name': 'RF-DETR (fine-getunt)',
  'intro.guide.rfdetr.bestFor': 'Detektion, wenn es auf den Wert ankommt. Das ist das Modell für echte Arbeit.',
  'intro.guide.rfdetr.strength1':
    'Von Haus aus für mehrere Größenstufen gebaut und von vorne bis hinten fine-getunt statt nur abgefragt – genau die Lücke, die der DINO-Detektor-Head nicht schließen kann, solange sein Backbone eingefroren ist.',
  'intro.guide.rfdetr.strength2':
    'Ein paar Blöcke aufzutauen kostet 19% mehr Zeit und macht die Boxen spürbar genauer.',
  'intro.guide.rfdetr.weakness1':
    'Ein ganzes Modell pro Lauf – es kann sich keinen Durchlauf des Backbones teilen, mehrere zu vergleichen heißt also mehrere volle Durchläufe.',
  'intro.guide.rfdetr.weakness2': 'Langsamer zu trainieren als ein linearer Head, und es kann mehr schiefgehen.',
  'intro.guide.rfdetr.measured':
    'mAP 0.96 bei OSDaR23-Schienen, gegenüber 0.50-0.58 für einen DINO-Detektor-Head auf denselben Daten (zufällige Aufteilungen). Bei Blutzellen mit einer Aufteilung ohne Überschneidungen: 0.62 Test-mAP nach 2 Durchgängen, gegenüber 0.41 für einen DINO-Head. 4 aufgetaute Blöcke hoben den Wert auf den zurückgehaltenen Bildern von 0.78 auf 0.84.',

  'intro.guide.sam.name': 'Grounded SAM / SAM 3 (ohne Training)',
  'intro.guide.sam.bestFor': 'Überhaupt zu Annotationen kommen, wenn noch nichts trainiert ist.',
  'intro.guide.sam.strength1':
    'Tipp ein, wonach du suchst, und bekomm Umrisse und Boxen zurück. So fängt ein Datensatz an, wenn du noch keinen hast.',
  'intro.guide.sam.strength2':
    'Grounded SAM steht unter Apache-2.0 und braucht kein Konto; für SAM 3 musst du bei Meta Zugang beantragen.',
  'intro.guide.sam.weakness1':
    'Langsam – mehrere Sekunden pro Bild. Es ist also ein Werkzeug zum Prüfen, kein Detektor, den du mal eben über einen Ordner laufen lässt.',
  'intro.guide.sam.weakness2':
    'Es findet, was du benennst, ganz allgemein. Ein Head, der auf deinen eigenen Daten trainiert ist, schlägt es bei deinen eigenen Klassen.',

  'intro.format.toggle': 'Wie muss ein Datensatz aussehen?',
  'intro.format.leadBefore': 'Alles in dieser Form kannst du über',
  'intro.format.leadPlace': 'Datensätze → Importieren',
  'intro.format.leadAfter':
    ' importieren. Die meisten Detektions-Exporte von Roboflow und HuggingFace haben diese Form schon.',

  'intro.format.disk.heading': 'Die Form auf der Festplatte',
  'intro.format.disk.body1':
    'Gib dem Import einen Ordner. Er sucht in diesem Ordner und in jedem Ordner direkt darin nach einer Datei namens {file} – eine Ebene tief, nicht durch alle Unterordner. Wenn du ihn also auf deinen Benutzerordner richtest, durchsucht er nicht deine ganze Festplatte.',
  'intro.format.disk.body2':
    'Jede Annotationsdatei liegt neben den Bildern, die sie beschreibt. Ein Ordner pro Aufteilung ist genau das, was Roboflow und die meisten HuggingFace-Exporte beim Entpacken schon anlegen – in der Praxis musst du also nichts umsortieren.',
  'intro.format.file.heading': 'Die Annotationsdatei',
  'intro.format.file.body1':
    'Normales COCO-Detektions-JSON: eine `images`-Liste, eine `annotations`-Liste und eine `categories`-Liste. Sonst wird nichts gelesen.',
  'intro.format.file.body2':
    'Jedes Bild braucht `id` und `file_name`. Der Dateiname wird relativ zu dem Ordner aufgelöst, in dem die Annotationsdatei liegt – er darf also kein absoluter Pfad von dem Rechner sein, auf dem exportiert wurde.',
  'intro.format.file.body3': 'Jede Annotation braucht `image_id`, `category_id` und `bbox`.',
  'intro.format.boxes.heading': 'Boxen',
  'intro.format.boxes.body1':
    '`bbox` ist `[x, y, width, height]` in **absoluten Pixeln ab der oberen linken Ecke** – ganz normales COCO, nicht normalisiert und nicht `[x1, y1, x2, y2]`.',
  'intro.format.boxes.body2':
    'Das ist dieselbe Konvention, in der diese App speichert. Boxen werden also kopiert statt umgerechnet, und es gibt keine Umrechnung, die schiefgehen kann. Ein YOLO-Export (normalisierte Mitte-x, Mitte-y, Breite, Höhe, in einer `.txt` pro Bild) ist ein anderes Format und wird nicht gelesen – wandle ihn zuerst um.',
  'intro.format.boxes.body3':
    'Eine Box mit einer Breite oder Höhe von null oder weniger wird übersprungen, und der Import sagt dir, wie viele er übersprungen hat.',
  'intro.format.classes.heading': 'Klassen',
  'intro.format.classes.body1':
    'Die Klassennamen kommen aus der `categories`-Liste, aufgelöst über die `category_id` jeder Annotation. **Namen, nie IDs** – Lücken, ein ungenutzter Platzhalter oder IDs, die nicht bei null anfangen, sind also alle in Ordnung.',
  'intro.format.classes.body2':
    'Nimm nicht an, dass Kategorie 0 ein Platzhalter ist, und lösch sie nicht. Von den drei Referenz-Datensätzen hier haben zwei einen Platzhalter bei ID 0, beim dritten ist ID 0 die echte Klasse `platelets`. Genau deshalb filtert der Import nie nach ID.',
  'intro.format.carry.heading': 'Was der Import nicht übernimmt',
  'intro.format.carry.body1':
    'Alles Importierte wird als **richtig** markiert, mit der Herkunft `imported`. Ein veröffentlichter Datensatz sagt nur, dass etwas da ist; er hat nichts, was den Urteilen falsch und unklar dieser App entspricht. Eines zu erfinden, hieße, ein Urteil zu speichern, das niemand gefällt hat.',
  'intro.format.carry.body2':
    'Segmentierungsmasken, Keypoints, Crowd-Markierungen und Bildbeschreibungen werden ignoriert. Dieser Import liest Detektions-Boxen.',
  'intro.format.trouble.heading': 'Wenn der Import nicht klappt',
  'intro.format.trouble.body1':
    'Keine Annotationsdatei gefunden – prüfe, ob der Name genau {file} lautet und ob sie höchstens einen Ordner tiefer liegt als der, den du angegeben hast.',
  'intro.format.trouble.body2':
    'Bilder importiert, aber keine Boxen – meist gibt es `category_id`-Werte, zu denen kein Eintrag in `categories` passt, oder `bbox` hat die falsche Konvention.',
  'intro.format.trouble.body3':
    'Weniger Bilder als erwartet – ein `file_name`, der sich neben seiner Annotationsdatei nicht finden lässt. Der Import meldet, wie viele er übersprungen hat, statt abzubrechen – schau dir diese Zahl also an.',
};
