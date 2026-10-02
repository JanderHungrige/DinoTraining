# Microsoft Store listing — English (en-us)

Doc 154. Copy each section into Partner Center → Store listings → English (United States).

## Product name

V-Rex

## Short description

V-Rex, Vision Representation & Experimentation: a free training pipeline for vision foundation models. Teach a vision model with a few hundred pictures: annotate with Grounding DINO and SAM, train small heads on frozen DINOv2/DINOv3 backbones in minutes, run them and let them annotate new data. The first start downloads Python and PyTorch (about 1–6 GB).

## Description

The first start downloads what the app runs on: Python and PyTorch from GitHub, PyPI and pytorch.org, about 1 GB for the CPU version and up to 6 GB for NVIDIA GPUs (CUDA). If Windows lacks a current Microsoft Visual C++ runtime, the app offers to install it from Microsoft. Models (DINOv2, DINOv3, Grounding DINO, SAM) download from Hugging Face when you choose them.

V-Rex (Vision Representation & Experimentation) is a training pipeline for vision foundation models. It covers the whole loop on your own computer:

- Annotate: type what you are looking for and Grounding DINO and SAM draw the boxes and masks; you accept, correct or reject them.
- Train: small heads (classification, detection, segmentation, depth) on a frozen DINOv2 or DINOv3 backbone, in minutes, on a CPU or an NVIDIA GPU.
- Infer: run a trained model on new pictures and review what it finds.
- Generate data: let a trained model annotate new pictures, review its suggestions, train again.

Your work stays yours: pictures, annotations and models stay on your computer or in cloud storage you connect yourself (Amazon S3, Azure Blob Storage, Google Cloud Storage). Annotations export to the dataset's folder or a folder you choose, on a button, when the app closes or every few minutes. No account, no telemetry.

Imports COCO, YOLO, Pascal VOC and OpenLABEL datasets; exports COCO. Open source under the MIT licence.

## What's new in this version

Release notes: https://github.com/JanderHungrige/DinoTraining/releases

## Product features

- Annotate with text prompts: Grounding DINO boxes, SAM masks
- Train classification, detection and segmentation heads on frozen DINOv2/DINOv3
- Runs on CPU or NVIDIA GPU (CUDA), switchable in the app
- Model-assisted labelling of new data
- Cloud datasets: Amazon S3, Azure Blob Storage, Google Cloud Storage
- Automatic export of annotations and models
- Imports COCO, YOLO, Pascal VOC and OpenLABEL; exports COCO
- MLflow tracking (optional)
- English and German
- No account, no telemetry, open source (MIT)

## Search terms (max. 7)

computer vision; annotation; DINOv2; object detection; segmentation; machine learning; PyTorch

## Additional system requirements

- Minimum: Windows 10 version 1809 (64-bit), 8 GB memory, 10 GB free disk space, internet connection for the first start
- Recommended: 16 GB memory, an NVIDIA GPU with 6 GB or more

## Links

- Store ID: 9PKPPDW39FCZ (https://apps.microsoft.com/detail/9PKPPDW39FCZ, live after certification)

- Privacy policy: https://dino.w3rth.de/privacy.html
- Website: https://dino.w3rth.de
- Support: https://github.com/JanderHungrige/DinoTraining/issues
- Copyright and trademark info: © 2026 JanderHungrige
