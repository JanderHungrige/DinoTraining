/**
 * `intro` texts (doc 112): the Intro tab, the model guide's content, and the dataset-format
 * guide. English is the source; the current UI text, exactly.
 */

export const introEn = {
  'intro.title': 'What this is',
  'intro.lead':
    'DinoTraining turns a folder of images into a model that finds things in them. You label some images, train a small model on top of a large pretrained one, look at what it predicts, and use it to label the next batch faster. Everything runs on this machine: your images are never uploaded anywhere.',
  'intro.loop.heading': 'The loop',
  'intro.loop.note':
    'The tabs are in the order you use them. You will go round more than once — that is the point, not a sign you did it wrong the first time.',
  'intro.loop.open': 'Open {tab}',
  'intro.loop.whyHere': 'Why here:',

  'intro.stage.studio.title': 'Annotate',
  'intro.stage.studio.what':
    'Point at a folder of images and get boxes to accept, reject or correct. Two ways to get them: describe what you are looking for in words, and Grounding DINO proposes boxes — or pick a head you already trained, and it proposes boxes for its own classes.',
  'intro.stage.studio.why':
    'Nothing can be trained until something is labelled. Starting from proposals rather than a blank canvas is the difference between an afternoon and a week.',
  'intro.stage.prepare.title': 'Prepare',
  'intro.stage.prepare.what':
    'Check a dataset before training on it: what is wrong with it, what can be fixed safely, a split that keeps near-identical pictures together, and your pictures exactly as the model will see them. Each step recommends a setting and says why.',
  'intro.stage.prepare.why':
    'Most failed training runs fail here, not in training. A model cannot learn an object shrunk to two pixels, and a test score is worthless if the test pictures are near-copies of the training ones.',
  'intro.stage.trainer.title': 'Train',
  'intro.stage.trainer.what':
    'Choose a backbone and a head type, press Train, and watch the loss and metrics arrive live. A run takes seconds to minutes, not hours.',
  'intro.stage.trainer.why':
    'It is fast because only the head is trained — see "frozen backbone" below. That is also why a small dataset is enough to get something useful.',
  'intro.stage.inference.title': 'Look at what it learned',
  'intro.stage.inference.what':
    'Run one or several trained heads over an image and see their predictions side by side, against the original. Foundation models like Depth Anything run here too.',
  'intro.stage.inference.why':
    'A metric tells you a model got better. Only looking at the pictures tells you *how* it is wrong, which is what decides what to label next.',
  'intro.stage.generator.title': 'Generate more data',
  'intro.stage.generator.what':
    'Run a trained head — or a text-prompted segmentation model — over new images, review what comes back, and save the result as a new dataset.',
  'intro.stage.generator.why':
    'This is the step that makes the loop a loop. The model you just trained does the first pass on the next batch, and you correct it instead of starting from nothing.',
  'intro.stage.inspect.title': 'Watch what you annotated',
  'intro.stage.inspect.what':
    'Open a dataset and play its videos and image folders back with every stored box and mask drawn on, with a coloured bar per class showing where each one appears.',
  'intro.stage.inspect.why':
    'A dataset is easier to trust once you have watched it. Gaps, drift and a class that only ever appears in one stretch of a ride show up in seconds on a timeline and take an afternoon to find image by image.',
  'intro.stage.library.title': 'Keep track of it all',
  'intro.stage.library.what':
    'Every dataset, trained head and fine-tuned model in one list, with what it holds, what it learned from, and a way to delete it.',
  'intro.stage.library.why':
    'The loop above makes things quickly, and most of them are experiments. This is where you see what you actually have, and throw away what you do not.',
  'intro.stage.admin.title': 'Models and settings',
  'intro.stage.admin.what':
    'Download model weights, remove them, set your HuggingFace token, and see where the cache lives. Every entry states its licence before you download it.',
  'intro.stage.admin.why':
    'No weights ship with the app — the installer would be gigabytes and most of them would be ones you never use. You download exactly what you need.',
  'intro.stage.api.title': 'Or let your own AI do all of it',
  'intro.stage.api.what':
    'Everything above happens through a local API, and the API tab hands you one document describing it. Paste that into ChatGPT, Claude or anything else and say what you want — "download this dataset, fine-tune RF-DETR on it, then annotate my images" — and it can carry out the whole loop for you.',
  'intro.stage.api.why':
    'Not a step in the loop; a different way to run it. Listed here because a feature nobody finds may as well not exist, and this one is easy to walk past.',

  'intro.concepts.heading': 'Two words this app uses constantly',
  'intro.concept.backbone.term': 'A frozen backbone',
  'intro.concept.backbone.body':
    'The backbone (DINOv2, DINOv3) is a large model already trained on millions of images. It turns a picture into numbers that describe what is in it — edges, textures, objects, materials. "Frozen" means we never change it: we run it, keep the numbers, and leave its weights exactly as they came. That is why training here takes seconds rather than days, and why it works on a few hundred images instead of a few hundred thousand. It also means the backbone can never overfit to your data, because it never learns from it.',
  'intro.concept.head.term': 'A head',
  'intro.concept.head.body':
    'The head is the small model you actually train. It reads the backbone’s numbers and turns them into the answer you want: a label, a box, a mask, a depth map. It is small — often a single layer — because the backbone has already done the hard part. One backbone can carry many heads, each doing a different job, and the Inference Viewer runs several of them over one image in a single pass.',
  'intro.concept.preprocessing.term': 'Why you are never asked about preprocessing',
  'intro.concept.preprocessing.body':
    'Resizing, cropping and normalising an image has to match what the backbone expects and what the head was trained on. Get it wrong by a few pixels and the model still runs — it just quietly gets worse, with nothing to tell you. So the app derives it from the backbone and head you picked, and does not offer it as a setting. There is no correct value for you to choose.',

  'intro.model.heading': 'Choosing a model',
  'intro.model.note':
    'Every model here does something the others do badly. The numbers in this panel were all measured in this app, on the datasets in it.',

  'intro.limits.heading': 'What it cannot do yet',
  'intro.limits.note': 'Listed because being told is better than concluding it is broken.',
  'intro.limit.stillImages': 'Still images only. Video and webcam input are not built.',
  'intro.limit.masks':
    'Masks are reviewed, not drawn. You can accept, reject or flag a proposed mask, but there is no brush or polygon editor to correct one by hand.',
  'intro.limit.detector':
    'No pretrained DINO detector exists to install. Classification, segmentation and depth have ready-made heads; for boxes you train your own in Training, or fine-tune RF-DETR there — see "Which model should I use?" above.',
  'intro.limit.dragDrop':
    'Drag-and-drop works in the desktop app only. In a browser a dropped file has no path the backend can read, so use the folder field there.',
  'intro.limit.noise':
    'Two identical training runs give slightly different numbers. The data split is fixed, but the starting weights are not, so treat a small metric difference as noise.',

  'intro.guide.lead':
    'A DINO head shares one backbone pass with every other head, which is what makes comparing models cheap — but the backbone stays frozen, so its features were never adapted to your task. That is a good trade for classification and segmentation, and a poor one for detection, where a purpose-built detector wins by a wide margin. Use the DINO heads to explore and compare; use RF-DETR when the number matters.',

  'intro.guide.classifier.name': 'Linear classifier (DINO head)',
  'intro.guide.classifier.bestFor': 'One label for a whole image — is this frame a defect or not?',
  'intro.guide.classifier.strength1': 'Trains in seconds on a few hundred images.',
  'intro.guide.classifier.strength2':
    'The strongest thing you can do with a frozen backbone, and the closest to what DINOv2 was designed for.',
  'intro.guide.classifier.weakness1':
    'Says nothing about where. An image with two different things in it cannot be trained on at all — it is skipped, and the counter tells you how many.',

  'intro.guide.segmenter.name': 'Linear segmenter (DINO head)',
  'intro.guide.segmenter.bestFor': 'Which pixels are the thing — rails, sky, vegetation.',
  'intro.guide.segmenter.strength1':
    'Trains on the masks a concept segmenter produces in the Studio, so annotation and training are the same loop.',
  'intro.guide.segmenter.strength2':
    'Frozen DINOv2 features are genuinely strong at this — it is one of the tasks the backbone was shown to do well with only a linear head.',
  'intro.guide.segmenter.weakness1':
    'Needs masks. A box-annotated dataset cannot train one, and images nobody segmented are skipped rather than treated as empty.',
  'intro.guide.segmenter.weakness2':
    'Does not separate two touching objects of the same class — it labels pixels, not instances.',

  'intro.guide.detector.name': 'Anchor-free detector (DINO head)',
  'intro.guide.detector.bestFor': 'Boxes, cheaply, alongside other heads on one backbone pass.',
  'intro.guide.detector.strength1':
    'Shares its backbone pass with every other head, so comparing seven models costs two passes rather than seven.',
  'intro.guide.detector.strength2':
    'Trains in minutes on cached features. Good when objects are a reasonable size and you want an answer today.',
  'intro.guide.detector.weakness1':
    'Predicts at one scale. Small far-field objects are not merely hard — below about 7 px at the model input they are not in the tensor at all. Tiling in the Inference Viewer is the fix; a feature pyramid would be the other one, and is not built.',
  'intro.guide.detector.weakness2':
    'The backbone is frozen, so its features were never adapted to localise. They tell you what is there better than exactly where.',
  'intro.guide.detector.measured':
    'mAP 0.61 on chess pieces, 0.55 on blood cells, 0.50-0.58 on OSDaR23 rail — against 0.96 for a fine-tuned RF-DETR on that same rail data. Those splits were random; on a leak-free split (Prepare data) blood cells scored 0.41 on test pictures.',

  'intro.guide.rfdetr.name': 'RF-DETR (fine-tuned)',
  'intro.guide.rfdetr.bestFor': 'Detection where the number matters. This is the one to use for real work.',
  'intro.guide.rfdetr.strength1':
    'Multi-scale by design, and fine-tuned end to end rather than probed — which is exactly the gap the DINO detector head cannot close while its backbone is frozen.',
  'intro.guide.rfdetr.strength2': 'Unfreezing a few blocks costs 19% more time and tightens boxes noticeably.',
  'intro.guide.rfdetr.weakness1':
    'A whole model per run — it cannot share a backbone pass, so comparing several is several full passes.',
  'intro.guide.rfdetr.weakness2': 'Slower to train than a linear head, and there is more of it to go wrong.',
  'intro.guide.rfdetr.measured':
    'mAP 0.96 on OSDaR23 rail, against 0.50-0.58 for a DINO detector head on the same data (random splits). On blood cells with a leak-free split: 0.62 test mAP after 2 rounds, against 0.41 for a DINO head. Unfreezing 4 blocks moved the holdout from 0.78 to 0.84.',

  'intro.guide.sam.name': 'Grounded SAM / SAM 3 (no training)',
  'intro.guide.sam.bestFor': 'Getting annotations at all, with nothing trained yet.',
  'intro.guide.sam.strength1':
    'Type what you are looking for and get masks and boxes back. This is how a dataset starts when you have none.',
  'intro.guide.sam.strength2':
    'Grounded SAM is Apache-2.0 and needs no account; SAM 3 is gated behind a Meta access request.',
  'intro.guide.sam.weakness1':
    'Slow — several seconds per image, so it is a review tool rather than a detector you would run over a folder in a hurry.',
  'intro.guide.sam.weakness2':
    'It finds what you name, in general terms. A head trained on your own data will beat it on your own classes.',

  'intro.format.toggle': 'What must a dataset look like?',
  'intro.format.leadBefore': 'Anything in this shape can be imported from',
  'intro.format.leadPlace': 'Datasets → Import',
  'intro.format.leadAfter': '. Most Roboflow and HuggingFace detection exports already are.',

  'intro.format.disk.heading': 'The shape on disk',
  'intro.format.disk.body1':
    'Point the importer at a folder. It looks for a file called {file} in that folder and in each folder directly inside it — one level, not a full walk, so pointing it at your home directory does not enumerate your whole disk.',
  'intro.format.disk.body2':
    'Each annotation file sits beside the images it describes. A split per folder is the layout Roboflow and most HuggingFace exports already unpack to, so in practice this needs no rearranging.',
  'intro.format.file.heading': 'The annotation file',
  'intro.format.file.body1':
    'Standard COCO detection JSON: an `images` list, an `annotations` list, and a `categories` list. Nothing else is read.',
  'intro.format.file.body2':
    'Each image needs `id` and `file_name`. The file name is resolved relative to the folder the annotation file is in, so it must not be an absolute path from whoever exported it.',
  'intro.format.file.body3': 'Each annotation needs `image_id`, `category_id` and `bbox`.',
  'intro.format.boxes.heading': 'Boxes',
  'intro.format.boxes.body1':
    '`bbox` is `[x, y, width, height]` in **absolute pixels from the top-left** — plain COCO, not normalised, and not `[x1, y1, x2, y2]`.',
  'intro.format.boxes.body2':
    'That is the same convention this app stores, so boxes are copied rather than converted and there is no transform to get wrong. A YOLO export (normalised centre-x, centre-y, width, height, in one `.txt` per image) is a different format and is not read — convert it first.',
  'intro.format.boxes.body3':
    'A box with zero or negative width or height is skipped, and the import tells you how many it skipped.',
  'intro.format.classes.heading': 'Classes',
  'intro.format.classes.body1':
    'Class names come from the `categories` list, resolved through each annotation’s `category_id`. **Names, never ids** — so gaps, an unused placeholder, or ids that do not start at zero are all fine.',
  'intro.format.classes.body2':
    'Do not assume category 0 is a placeholder and delete it. Of the three reference datasets here, two have a placeholder at id 0 and the third’s id 0 is the real class `platelets`. The importer never filters by id for exactly this reason.',
  'intro.format.carry.heading': 'What the import does not carry',
  'intro.format.carry.body1':
    'Everything imported is marked **positive**, with provenance `imported`. A published dataset asserts that something is present; it has no equivalent of this app’s negative and unclear verdicts, and inventing one would put a judgement in the store that nobody made.',
  'intro.format.carry.body2':
    'Segmentation masks, keypoints, crowd flags and captions are ignored. This importer reads detection boxes.',
  'intro.format.trouble.heading': 'If it will not import',
  'intro.format.trouble.body1':
    'No annotation file found — check the name is exactly {file}, and that it is at most one folder deep from where you pointed.',
  'intro.format.trouble.body2':
    'Images imported but no boxes — usually `category_id` values that no `categories` entry matches, or `bbox` in the wrong convention.',
  'intro.format.trouble.body3':
    'Fewer images than expected — a `file_name` that does not resolve beside its annotation file. The import reports the count it skipped rather than failing, so check that number.',
} as const;
