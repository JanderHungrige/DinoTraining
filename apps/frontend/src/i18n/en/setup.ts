/** `setup` texts: the first-run setup screen (doc 127). */

export const setupEn = {
  'setup.title': 'Welcome to DinoTraining',
  'setup.intro':
    'One step before the first start: DinoTraining runs its models with PyTorch, and it is downloaded now, once, from the official servers. After that the app works offline.',

  'setup.found.appleSilicon': 'Found: a Mac with Apple silicon. Its GPU is used through MPS.',
  'setup.found.nvidia': 'Found: {name}, driver {driver}.',
  'setup.found.cpu':
    'No NVIDIA graphics card found, so DinoTraining uses the CPU. Everything works; training and prescans take longer.',
  'setup.note.driverTooOld':
    'Your NVIDIA driver ({driver}) is too old for the GPU version of PyTorch, which needs {needed} or newer. Update the driver and restart DinoTraining to use the GPU. Until then it runs on the CPU.',
  'setup.note.intelMac':
    'This Mac has an Intel processor. PyTorch, which DinoTraining needs, is no longer made for Intel Macs, so DinoTraining cannot run here.',
  'setup.note.unsupported':
    'DinoTraining runs on Macs with Apple silicon and on 64-bit Intel or AMD PCs with Windows or Linux. This machine is {os} on {arch}.',

  'setup.choice.install': 'Install (about {gb} GB download)',
  'setup.choice.gpu': 'Install with GPU support (CUDA {cuda}, about {gb} GB download)',
  'setup.choice.cpuOnly': 'CPU only (smaller, about {gb} GB)',

  'setup.progress.python': 'Downloading Python…',
  'setup.progress.packages': 'Downloading PyTorch and the other packages… {done} of {total} MB',
  'setup.progress.installing': 'Installing…',
  'setup.progress.done': 'Installed.',
  'setup.progress.starting': 'Starting the AI engine…',
  'setup.progress.ready': 'Ready.',
  'setup.progress.current': '{name} downloaded',
  'setup.open': 'Open DinoTraining',

  'setup.fail.offline':
    'No internet connection. The first start downloads Python and PyTorch once; after that DinoTraining works offline.',
  'setup.fail.disk': 'This needs about {needed} GB free on {path}, and {free} GB are free. Free up some space, then try again.',
  'setup.fail.unsupported': 'This machine cannot run DinoTraining (see above).',
  'setup.fail.failed': 'The install stopped: {message}',
  'setup.fail.resume': 'What was already downloaded is kept, so trying again continues where it stopped.',
  'setup.retry': 'Try again',

  'setup.game.label': 'Dino Run: a small game while DinoTraining installs. Press Space or click to jump.',
  'setup.game.hint': 'Space or click: jump over the rocks while you wait',
  'setup.game.playing': 'Space or click: jump',
  'setup.game.over': 'Ouch. Jump to run again',
  'setup.game.score': 'Score {score}',
  'setup.game.best': 'best {best}',

  'setup.tip.label': 'Did you know?',
  'setup.tip.backbone':
    'The backbone (DINOv2 or DINOv3) is never changed. It turns each picture into features, and only the small head on top of it learns: that is why training takes minutes.',
  'setup.tip.head': 'A head is a small model on the backbone. One backbone can carry many heads: one for boxes, one for masks, one for depth.',
  'setup.tip.phrases':
    'Phrases tell Grounding DINO what to look for. Several phrases can find one class, and a look-alike phrase keeps the mistakes out.',
  'setup.tip.saved': 'A saved picture counts as complete: everything of its classes that is not marked is taught as background.',
  'setup.tip.generator': 'The Dataset Generator annotates new pictures with a head you trained. You only check what it proposes.',
  'setup.tip.export': 'A trained model can be exported as a zip with a small runtime, and as ONNX, to run it outside DinoTraining.',
  'setup.tip.offline': 'Models are downloaded once in the Admin tab. After that, DinoTraining needs no internet at all.',
} as const;
