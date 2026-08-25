/**
 * The Intro tab's prose, as data (doc 38).
 *
 * Separate from the component so the page stays under the line limit, and so a test can
 * assert on *what it claims* rather than on markup. That matters more here than elsewhere:
 * this is the one place in the app whose only job is to be true, and the fastest way for it
 * to become false is for someone to change a tab and never think about this file.
 *
 * Every `tab` reference below is a real `TabId`, checked by the compiler, so a renamed or
 * removed tab breaks the build rather than leaving the intro pointing at nothing.
 */

import type { TabId } from './tabs';

export interface IntroStage {
  readonly tab: TabId;
  readonly title: string;
  readonly what: string;
  /** Why this stage comes where it does. The order is the part nobody can guess. */
  readonly why: string;
}

export interface IntroConcept {
  readonly term: string;
  readonly body: string;
}

export const INTRO_LEAD =
  'DinoTraining turns a folder of images into a model that finds things in them. ' +
  'You label some images, train a small model on top of a large pretrained one, look at ' +
  'what it predicts, and use it to label the next batch faster. Everything runs on this ' +
  'machine: your images are never uploaded anywhere.';

/** The loop, in the order the tabs run — which is the order they appear. */
export const INTRO_STAGES: readonly IntroStage[] = Object.freeze([
  {
    tab: 'studio',
    title: 'Annotate',
    what:
      'Point at a folder of images and get boxes to accept, reject or correct. Two ways ' +
      'to get them: describe what you are looking for in words, and Grounding DINO ' +
      'proposes boxes — or pick a head you already trained, and it proposes boxes for its ' +
      'own classes.',
    why:
      'Nothing can be trained until something is labelled. Starting from proposals rather ' +
      'than a blank canvas is the difference between an afternoon and a week.',
  },
  {
    tab: 'trainer',
    title: 'Train',
    what:
      'Choose a backbone and a head type, press Train, and watch the loss and metrics ' +
      'arrive live. A run takes seconds to minutes, not hours.',
    why:
      'It is fast because only the head is trained — see "frozen backbone" below. That is ' +
      'also why a small dataset is enough to get something useful.',
  },
  {
    tab: 'inference',
    title: 'Look at what it learned',
    what:
      'Run one or several trained heads over an image and see their predictions side by ' +
      'side, against the original. Foundation models like Depth Anything run here too.',
    why:
      'A metric tells you a model got better. Only looking at the pictures tells you ' +
      '*how* it is wrong, which is what decides what to label next.',
  },
  {
    tab: 'generator',
    title: 'Generate more data',
    what:
      'Run a trained head — or a text-prompted segmentation model — over new images, ' +
      'review what comes back, and save the result as a new dataset.',
    why:
      'This is the step that makes the loop a loop. The model you just trained does the ' +
      'first pass on the next batch, and you correct it instead of starting from nothing.',
  },
  {
    tab: 'library',
    title: 'Keep track of it all',
    what:
      'Every dataset, trained head and fine-tuned model in one list, with what it holds, ' +
      'what it learned from, and a way to delete it.',
    why:
      'The loop above makes things quickly, and most of them are experiments. This is ' +
      'where you see what you actually have, and throw away what you do not.',
  },
  {
    tab: 'admin',
    title: 'Models and settings',
    what:
      'Download model weights, remove them, set your HuggingFace token, and see where the ' +
      'cache lives. Every entry states its licence before you download it.',
    why:
      'No weights ship with the app — the installer would be gigabytes and most of them ' +
      'would be ones you never use. You download exactly what you need.',
  },
]);

/** The three ideas the rest of the app assumes and never explains. */
export const INTRO_CONCEPTS: readonly IntroConcept[] = Object.freeze([
  {
    term: 'A frozen backbone',
    body:
      'The backbone (DINOv2, DINOv3) is a large model already trained on millions of ' +
      'images. It turns a picture into numbers that describe what is in it — edges, ' +
      'textures, objects, materials. "Frozen" means we never change it: we run it, keep ' +
      'the numbers, and leave its weights exactly as they came. That is why training here ' +
      'takes seconds rather than days, and why it works on a few hundred images instead ' +
      'of a few hundred thousand. It also means the backbone can never overfit to your ' +
      'data, because it never learns from it.',
  },
  {
    term: 'A head',
    body:
      'The head is the small model you actually train. It reads the backbone’s numbers ' +
      'and turns them into the answer you want: a label, a box, a mask, a depth map. It ' +
      'is small — often a single layer — because the backbone has already done the hard ' +
      'part. One backbone can carry many heads, each doing a different job, and the ' +
      'Inference Viewer runs several of them over one image in a single pass.',
  },
  {
    term: 'Why you are never asked about preprocessing',
    body:
      'Resizing, cropping and normalising an image has to match what the backbone expects ' +
      'and what the head was trained on. Get it wrong by a few pixels and the model still ' +
      'runs — it just quietly gets worse, with nothing to tell you. So the app derives it ' +
      'from the backbone and head you picked, and does not offer it as a setting. There ' +
      'is no correct value for you to choose.',
  },
]);

/**
 * What the app cannot do yet.
 *
 * Deliberately part of the intro. Someone who reads this and then goes looking for video
 * has been told; someone who is not told concludes the app is broken. Kept accurate as of
 * Wave 6 — anything fixed here should be *removed* from this list in the same commit.
 */
export const INTRO_LIMITS: readonly string[] = Object.freeze([
  'Still images only. Video and webcam input are not built.',
  'Masks are reviewed, not drawn. You can accept, reject or flag a proposed mask, but ' +
    'there is no brush or polygon editor to correct one by hand.',
  'No pretrained DINO detector exists to install. Classification, segmentation and depth ' +
    'have ready-made heads; for boxes you train your own in Training, or fine-tune ' +
    'RF-DETR there — see "Which model should I use?" above.',
  'Drag-and-drop works in the desktop app only. In a browser a dropped file has no path ' +
    'the backend can read, so use the folder field there.',
  'Two identical training runs give slightly different numbers. The data split is fixed, ' +
    'but the starting weights are not, so treat a small metric difference as noise.',
]);

/**
 * Which model to reach for, and what each is actually good at.
 *
 * Added after the question was asked out loud: "is a DINOv2 head not really suitable for
 * object detection?" It is a fair question with a nuanced answer, and the nuance was
 * previously only in `.mdd/docs/` where a user never looks.
 *
 * **Every number here was measured in this app**, on the datasets in it. They are cited
 * rather than described because "better for small objects" is an opinion and "0.556 against
 * 0.957 on the same rail data" is not. Anything restated here that later changes should be
 * re-measured, not adjusted to taste.
 */
export interface ModelGuideEntry {
  readonly name: string;
  /** The one-line answer: reach for this when… */
  readonly bestFor: string;
  readonly strengths: readonly string[];
  readonly weaknesses: readonly string[];
  /** Measured in this app, with the dataset named. Empty where nothing was measured. */
  readonly measured?: string;
}

export const MODEL_GUIDE: readonly ModelGuideEntry[] = Object.freeze([
  {
    name: 'Linear classifier (DINO head)',
    bestFor: 'One label for a whole image — is this frame a defect or not?',
    strengths: [
      'Trains in seconds on a few hundred images.',
      'The strongest thing you can do with a frozen backbone, and the closest to what ' +
        'DINOv2 was designed for.',
    ],
    weaknesses: [
      'Says nothing about where. An image with two different things in it cannot be ' +
        'trained on at all — it is skipped, and the counter tells you how many.',
    ],
  },
  {
    name: 'Linear segmenter (DINO head)',
    bestFor: 'Which pixels are the thing — rails, sky, vegetation.',
    strengths: [
      'Trains on the masks a concept segmenter produces in the Studio, so annotation and ' +
        'training are the same loop.',
      'Frozen DINOv2 features are genuinely strong at this — it is one of the tasks the ' +
        'backbone was shown to do well with only a linear head.',
    ],
    weaknesses: [
      'Needs masks. A box-annotated dataset cannot train one, and images nobody segmented ' +
        'are skipped rather than treated as empty.',
      'Does not separate two touching objects of the same class — it labels pixels, not ' +
        'instances.',
    ],
  },
  {
    name: 'Anchor-free detector (DINO head)',
    bestFor: 'Boxes, cheaply, alongside other heads on one backbone pass.',
    strengths: [
      'Shares its backbone pass with every other head, so comparing seven models costs ' +
        'two passes rather than seven.',
      'Trains in minutes on cached features. Good when objects are a reasonable size and ' +
        'you want an answer today.',
    ],
    weaknesses: [
      'Predicts at one scale. Small far-field objects are not merely hard — below about ' +
        '7 px at the model input they are not in the tensor at all. Tiling in the ' +
        'Inference Viewer is the fix; a feature pyramid would be the other one, and is ' +
        'not built.',
      'The backbone is frozen, so its features were never adapted to localise. They tell ' +
        'you what is there better than exactly where.',
    ],
    measured:
      'mAP 0.61 on chess pieces, 0.55 on blood cells, 0.50-0.58 on OSDaR23 rail — against ' +
      '0.96 for a fine-tuned RF-DETR on that same rail data.',
  },
  {
    name: 'RF-DETR (fine-tuned)',
    bestFor: 'Detection where the number matters. This is the one to use for real work.',
    strengths: [
      'Multi-scale by design, and fine-tuned end to end rather than probed — which is ' +
        'exactly the gap the DINO detector head cannot close while its backbone is frozen.',
      'Unfreezing a few blocks costs 19% more time and tightens boxes noticeably.',
    ],
    weaknesses: [
      'A whole model per run — it cannot share a backbone pass, so comparing several is ' +
        'several full passes.',
      'Slower to train than a linear head, and there is more of it to go wrong.',
    ],
    measured:
      'mAP 0.96 on OSDaR23 rail, against 0.50-0.58 for a DINO detector head on the same ' +
      'data. Unfreezing 4 blocks moved the holdout from 0.78 to 0.84.',
  },
  {
    name: 'Grounded SAM / SAM 3 (no training)',
    bestFor: 'Getting annotations at all, with nothing trained yet.',
    strengths: [
      'Type what you are looking for and get masks and boxes back. This is how a dataset ' +
        'starts when you have none.',
      'Grounded SAM is Apache-2.0 and needs no account; SAM 3 is gated behind a Meta ' +
        'access request.',
    ],
    weaknesses: [
      'Slow — several seconds per image, so it is a review tool rather than a detector ' +
        'you would run over a folder in a hurry.',
      'It finds what you name, in general terms. A head trained on your own data will ' +
        'beat it on your own classes.',
    ],
  },
]);

/** The one-paragraph answer, for someone who will not read the table. */
export const MODEL_GUIDE_LEAD =
  'A DINO head shares one backbone pass with every other head, which is what makes ' +
  'comparing models cheap — but the backbone stays frozen, so its features were never ' +
  'adapted to your task. That is a good trade for classification and segmentation, and a ' +
  'poor one for detection, where a purpose-built detector wins by a wide margin. Use the ' +
  'DINO heads to explore and compare; use RF-DETR when the number matters.';
