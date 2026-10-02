# Microsoft Store listing — English (en-us)

Doc 154. Copy each section into Partner Center → Store listings → English (United States).

## Product name

V-Rex

## Short description

V-Rex makes modern vision AI usable without being a data scientist. Explore your image datasets, try different vision models and see what each can do, and learn how they work along the way. Then fine-tune models to your own needs, and generate annotated datasets to train other vision models. The first start downloads Python and PyTorch (about 1–6 GB).

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

- Explore your image datasets: browse pictures, annotations and classes, and see where the data is thin or unbalanced
- Try modern vision models side by side: DINOv2/DINOv3, Grounding DINO, SAM 2 and SAM 3, RF-DETR
- Annotate by describing what you look for: the models draw boxes and masks, you accept or correct them
- Learn how the models work: plain explanations of every setting, metric and training step
- Train your own model in minutes on a frozen foundation model, no coding needed
- Fine-tune models to your specific needs, with guided data preparation and recipes
- Generate annotated datasets with a trained model to train other vision models
- Import COCO, YOLO, Pascal VOC and OpenLABEL, export COCO; work with datasets in Amazon S3, Azure or Google Cloud
- Runs on your own computer, on CPU or NVIDIA GPU; your pictures never leave it unless you choose
- English and German, free and open source (MIT)

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
