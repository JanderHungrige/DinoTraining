# Background loop — provenance (doc 76; forest since doc 163)

`particles-loop.mp4` and `particles-poster.jpg` are a **forest** since 2026-10-02. The file
names are kept on purpose: the download site's updater copies exactly these names, and a
renamed file would stop its first deploy (doc 160's lesson).

- **Source:** a forest clip from **Pexels**, found by Jan and made into a boomerang loop by
  him (forwards, then backwards): `forrestfordinoreverst.mp4`, 1920×1080, 23.976 fps,
  67.2 s, sha256 `2196660b8625c09402851d53e79e47daf032b8fa7f22755bad6e9e6c103eec09`.
  - Pexels page: **Trees in the forest**, https://www.pexels.com/video/trees-in-the-forest-5121476/
- **Licence:** the **Pexels License** (https://www.pexels.com/license/): free to use and
  modify, also commercially, no attribution required. Not to be sold or redistributed
  unaltered on its own.
- **Current: the plain video (experiment, Jan 2026-10-02):** only re-encoded, no blur, no
  curves, full 1080p, and in the app no scrim and no panel blur:

  ```
  ffmpeg -i forrestfordinoreverst.mp4 -an -frames:v 1611 \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -preset slow -crf 33 -tune film \
    -movflags +faststart particles-loop.mp4
  ffmpeg -i particles-loop.mp4 -frames:v 1 -q:v 7 particles-poster.jpg
  ```

  7.5 MB (CRF 28 would be 17.6 MB; a 1:1 crop at CRF 33 is hard to tell from the source).
  Text over the brightest frames is below AA here; doc 163 says why and what is kept.
- **Earlier versions**, kept as git tags: `background-forest-blur3` (blurred) and
  `background-forest-curve-a` (tone-mapped, 720p, thin scrim):

  ```
  ffmpeg -i forrestfordinoreverst.mp4 -an -frames:v 1611 \
    -vf "scale=1280:720:flags=lanczos,curves=all='0/0 0.25/0.30 0.5/0.55 1/0.72'" \
    -c:v libx264 -profile:v main -pix_fmt yuv420p -preset slow -crf 32 -tune film \
    -movflags +faststart particles-loop.mp4
  ffmpeg -i particles-loop.mp4 -frames:v 1 -q:v 4 particles-poster.jpg
  ```

  - `-frames:v 1611` drops the last frame, which nearly repeats the first (a stall at the
    seam).
  - **No blur** (Jan: the first, blurred version looked much darker than the original).
    It is kept as the git tag `background-forest-blur3`.
  - **`curves`:** the highlights are tone-mapped (the sky between the trees to ~72 %, the
    brightest pixel 183) and the midtones lifted a little. The near-white sky made a thin
    scrim illegible; tamed, the app's scrim drops from 0.5/0.45 to 0.25/0.2, so the forest
    stays bright. `scripts/check_background_contrast.py` passes (lowest: 4.64:1).
  - CRF 32: 3.5 MB.

Until 2026-10-02 the loop was *Octagon, Abstract, Lights, Particle* by tommyvideo on
Pixabay (#5192), built by `scripts/build_background_video.py`.
