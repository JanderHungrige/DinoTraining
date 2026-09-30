# Background loop — provenance (doc 76)

`particles-loop.mp4` and `particles-poster.jpg` are derived from:

- **Octagon, Abstract, Lights, Particle** by *tommyvideo* on Pixabay (video #5192, 2016)
  https://pixabay.com/videos/octagon-abstract-lights-particle-5192/
- Source file: `https://cdn.pixabay.com/video/2016/09/13/5192-183786490_large.mp4`,
  sha256 `233e123d9e5c25c1b7ca375ef0db6760be235ae4b5c135ea52b1a1f02de73349`
- Licence: **Pixabay Content License** (https://pixabay.com/service/license-summary/) —
  free to use in this application without attribution; the file may not be redistributed
  on its own, outside the application.

Derived by `scripts/build_background_video.py`: downscaled to 1280×720, mirror-stitched
(forwards, then backwards without repeating the turn-around frames) into a seamless 58 s
loop, H.264 Main. Rebuild from the same bytes with that script.
