import type { guideEn } from '../en/guide';
import type { Catalogue } from '../types';

export const guideDe: Catalogue<typeof guideEn> = {
  'guide.layout.title': 'Wie muss ein Datensatz aussehen?',
  'guide.layout.lead':
    'Richte den Import auf den eigenen Ordner des Datensatzes. Er erkennt diese Strukturen; die Ordnernamen in den Bäumen sind Beispiele, die Dateiendungen nicht.',
  'guide.plain.title': 'Ohne Annotationen',
  'guide.plain.text':
    'Ein Ordner mit Bildern (JPEG, PNG, BMP, WebP, TIFF, GIF), bis zu fünf Ordnerebenen tief, oder ein einzelnes Video (MP4, MOV, AVI, MKV, WebM, M4V). Die Bilder werden zum Annotieren in der App importiert; ein Video wird zu seinen Frames.',
  'guide.coco.title': 'COCO (Roboflow, Hugging Face, CVAT und die meisten Tools)',
  'guide.coco.text':
    'Eine JSON-Datei pro Split mit „images“, „annotations“ und „categories“; der Dateiname ist egal. „file_name“ ist relativ zum Ordner der JSON, „bbox“ ist [x, y, w, h] in Pixeln, und „segmentation“ (Polygone oder RLE) wird zu Masks.',
  'guide.yolo.title': 'YOLO (Ultralytics, Roboflow „YOLOv5/v8“)',
  'guide.yolo.text':
    'Bilder unter images/, eine .txt pro Bild unter labels/ in denselben Unterordnern. Eine Zeile ist „class cx cy w h“, normiert auf 0–1; eine längere Zeile ist ein Polygon und wird zur Mask. Klassennamen kommen aus data.yaml (names:) oder classes.txt. Ein Bild ohne .txt enthält keine Objekte.',
  'guide.voc.title': 'Pascal VOC',
  'guide.voc.text':
    'Eine XML pro Bild in Annotations/, mit einem <object> pro Box (<name>, <bndbox>), und die Bilder in JPEGImages/ (oder neben der XML).',
  'guide.openlabel.title': 'OpenLABEL (OSDaR23)',
  'guide.openlabel.text':
    'Ein Sequenzordner mit seiner *_labels.json und einem Ordner pro Sensor. Die Bilder jeder Kamera werden importiert, Lidar und Radar ignoriert, und „track“-Polylinien weggelassen, weil eine Box um eine Schiene bis zum Horizont nichts lehrt.',
  'guide.splits':
    'Splits: Ein Ordner namens train, val (oder valid) oder test irgendwo auf dem Weg wird zum Split; ohne ihn legt die App den Split später unter Daten vorbereiten an.',
  'guide.sites.title': 'Wo es Datensätze gibt',
  'guide.sites.lead': 'In einem der Formate oben herunterladen, entpacken und den Ordner importieren.',
  'guide.sites.hf': 'Viele Bild-Datensätze; filtere nach „object detection“ oder „image segmentation“.',
  'guide.sites.roboflow': 'Von der Community annotierte Datensätze; exportiere als „COCO JSON“ oder „YOLOv8“.',
  'guide.sites.kaggle': 'Wettbewerbs- und Community-Datensätze, im Format, das ihre Autoren gewählt haben.',
  'guide.sites.openimages': 'Googles großer Datensatz mit Boxen und Masks; sein CSV muss erst nach COCO umgewandelt werden.',
  'guide.sites.coco': 'Der Referenzdatensatz, 80 Alltagsklassen mit Boxen und Masks.',
  'guide.sites.osdar':
    'Multisensor-Datensatz der Deutschen Bahn (Digitale Schiene Deutschland) von Bahnstrecken in Hamburg, mit Kameras, Lidar und Radar, in OpenLABEL; wird direkt importiert.',
  'guide.sites.osdarData': 'das Datenportal',
  'guide.sites.licence':
    'Jeder Datensatz hat seine eigene Lizenz. Prüf sie, bevor du auf einem Datensatz trainierst oder ein darauf trainiertes Modell weitergibst.',
};
