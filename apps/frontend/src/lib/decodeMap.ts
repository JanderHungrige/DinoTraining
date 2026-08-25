/**
 * Decoding a data PNG back to the bytes the backend put in it.
 *
 * **This is the fix for the "fizzle".** A mask travels as a greyscale PNG whose pixel
 * values are *data*, not colour — a class index, or 0/255 for a binary mask. The obvious
 * way to read it back is `new Image()` → `drawImage` → `getImageData`, and that is what
 * this app did. The obvious way is wrong, because drawing an image to a canvas runs it
 * through **colour management**: the browser converts from the image's colour space to the
 * canvas's, and when that conversion cannot land on an exact integer it *dithers*.
 *
 * Dithering a photograph is invisible. Dithering data is not. A background of 0 comes back
 * as a scatter of 0s and 1s, and any test of the form `value > 0` then lights up half the
 * frame in a fine speckle — over the sky, over the trees, everywhere the mask is not. It
 * is worse for the Inference Viewer's composited map, whose classes are literally 0, 1, 2:
 * a one-level error there is a different class.
 *
 * Chromium happens not to dither these; WKWebView, which is what the packaged desktop app
 * runs on, does. So it reproduces in the shipped app and not in a dev browser — which is
 * exactly how it was reported.
 *
 * Two defences, because one of them depends on a browser flag:
 *
 * 1. `createImageBitmap(blob, { colorSpaceConversion: 'none' })` — the standard way to say
 *    "these are bytes, do not convert them". Where it is supported this is exact.
 * 2. A `{ colorSpace: 'srgb' }` 2D context and `imageSmoothingEnabled = false`, so nothing
 *    downstream of the decode resamples or re-converts.
 *
 * Callers add the third: threshold rather than test for non-zero. See `MaskLayer`.
 */

export interface DecodedMap {
  /** One byte per pixel — the red channel, which is the value for a greyscale source. */
  readonly values: Uint8ClampedArray;
  readonly width: number;
  readonly height: number;
}

function contextFor(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null {
  // `willReadFrequently` matters: these canvases exist only to be read back, and without
  // it a GPU-backed canvas pays a full readback stall per frame.
  const context = canvas.getContext('2d', {
    colorSpace: 'srgb',
    willReadFrequently: true,
  }) as CanvasRenderingContext2D | null;
  if (context) context.imageSmoothingEnabled = false;
  return context;
}

/** base64 PNG → an ImageBitmap decoded without colour conversion, where that is offered. */
async function toBitmap(encoded: string): Promise<ImageBitmap | HTMLImageElement> {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: 'image/png' });

  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(blob, {
        colorSpaceConversion: 'none',
        premultiplyAlpha: 'none',
      });
    } catch {
      // Older WebKit rejects the options bag rather than ignoring it. Fall through to the
      // <img> path, which still benefits from the srgb context below.
    }
  }

  const url = URL.createObjectURL(blob);
  try {
    return await new Promise<HTMLImageElement>((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('Could not decode the map'));
      image.src = url;
    });
  } finally {
    // Revoked after onload has fired, so the decode has already read it.
    URL.revokeObjectURL(url);
  }
}

/**
 * Decode a base64 greyscale PNG to its raw values.
 *
 * `width`/`height` come from the payload rather than the image, so a mismatch between what
 * the backend said and what it sent is visible as a wrong-sized result instead of silently
 * reading a partly-blank canvas.
 */
export async function decodeMap(
  encoded: string,
  width: number,
  height: number,
): Promise<DecodedMap | null> {
  if (width <= 0 || height <= 0) return null;

  const source = await toBitmap(encoded);
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = contextFor(canvas);
  if (!context) return null;

  context.drawImage(source as CanvasImageSource, 0, 0);
  const { data } = context.getImageData(0, 0, width, height, { colorSpace: 'srgb' });

  // One byte per pixel from the red channel: the source is greyscale, so the other two
  // repeat it and alpha is 255 throughout.
  const values = new Uint8ClampedArray(width * height);
  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) values[p] = data[i] ?? 0;

  if ('close' in source) source.close();
  return { values, width, height };
}
