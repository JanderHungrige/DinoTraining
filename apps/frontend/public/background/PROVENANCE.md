# Background loop — provenance (doc 76; forest since doc 163)

`particles-loop.mp4` and `particles-poster.jpg` are a **forest** since 2026-10-02. The file
names are kept on purpose: the download site's updater copies exactly these names, and a
renamed file would stop its first deploy (doc 160's lesson).

- **Source:** a forest clip from **Pexels**, found by Jan and made into a boomerang loop by
  him (forwards, then backwards): `forrestfordinoreverst.mp4`, 1920×1080, 23.976 fps,
  67.2 s, sha256 `2196660b8625c09402851d53e79e47daf032b8fa7f22755bad6e9e6c103eec09`.
  - Pexels page: *to be added by Jan* (the original clip's link).
- **Licence:** the **Pexels License** (https://www.pexels.com/license/): free to use and
  modify, also commercially, no attribution required. Not to be sold or redistributed
  unaltered on its own.
- **Derived with ffmpeg** (the source is not committed):

  ```
  ffmpeg -i forrestfordinoreverst.mp4 -an -frames:v 1611 \
    -vf "scale=1280:720:flags=lanczos,gblur=sigma=3" \
    -c:v libx264 -profile:v main -pix_fmt yuv420p -preset slow -crf 30 -tune film \
    -movflags +faststart particles-loop.mp4
  ffmpeg -i particles-loop.mp4 -frames:v 1 -q:v 4 particles-poster.jpg
  ```

  - `-frames:v 1611` drops the last frame, which nearly repeats the first (a stall at the
    seam).
  - `gblur=sigma=3`: a soft focus, chosen against sharp and sigma 6. The panels blur
    again on top (10 px).
  - The file is 1.3 MB; the sharp version would be 5.7 MB.

Until 2026-10-02 the loop was *Octagon, Abstract, Lights, Particle* by tommyvideo on
Pixabay (#5192), built by `scripts/build_background_video.py`.
