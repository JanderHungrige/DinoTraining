# Microsoft Store listing (doc 154)

What Partner Center asks for, kept in the repo so each release can carry it.

- `listing-en.md`, `listing-de.md`: the Store listing texts per language.
- The privacy policy: `website/privacy.html`, served at https://dino.w3rth.de/privacy.html.

## Properties (Partner Center → Properties)

| Field | Value |
|---|---|
| Category | Developer tools |
| Subcategory | — |
| Privacy policy URL | https://dino.w3rth.de/privacy.html |
| Website | https://dino.w3rth.de |
| Support contact | https://github.com/JanderHungrige/DinoTraining/issues |
| Collects personal information | No |
| Product declarations | "This app depends on non-Microsoft drivers or NT services": no. "Has been tested to meet accessibility guidelines": no |
| System requirements | Memory 8 GB minimum, 16 GB recommended; DirectX not required; GPU: NVIDIA optional |

## Age rating (IARC questionnaire)

- Category: "App (not a game)" → Productivity / utility.
- Violence, sexual content, language, drugs, gambling: none.
- Users interact or share content with each other: no.
- Shares the user's location: no.
- Allows purchases: no.
- Unrestricted internet access: no (downloads only from the named servers; the user's own
  cloud storage). Expected result: 3+ / USK 0 / PEGI 3.

## Pricing and availability

- Price: free. Markets: all. Visibility: public (or "private, link only" for the first
  submission while testing).

## Licence terms

- The repo's MIT licence: https://github.com/JanderHungrige/DinoTraining/blob/main/LICENSE
  (Store listing → "Additional license terms").

## Screenshots (at least one, 1366×768 or larger, PNG)

Taken from the running app (Windows, after the first start), window 1920×1080, the same set
in English and German:

1. **Models & Datasets:** the dataset list with a few datasets and the models tab.
2. **Studio:** a picture with Grounding DINO boxes and SAM masks being accepted.
3. **Training:** a head training with its loss curve.
4. **Inference:** a trained model's results on new pictures.
5. *(optional)* **Cloud:** a dataset linked from cloud storage.

Store logos come from the MSIX (doc 151); a 1:1 "box art" of 1080×1080 or larger, made from
the emblem, is optional.

## Notes for certification (Submission options → Notes for certification)

> V-Rex is a desktop app (full trust). Its first start downloads Python and PyTorch
> (about 1 GB, CPU) from GitHub, PyPI and pytorch.org into the app's local data folder; this
> takes a few minutes and is shown with progress. If the Microsoft Visual C++ runtime on the
> test machine is older than 14.40, the app asks to install Microsoft's signed redistributable
> (one UAC prompt). No account or sign-in is needed. To test: start the app, choose "CPU" at the
> first start, wait for the setup to finish, then open Models & Datasets.
