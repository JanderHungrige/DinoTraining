/**
 * Colour for class indices and for depth, in one place.
 *
 * The palette is generated rather than listed: ADE20k alone has 150 classes, and a
 * hand-written table would have to grow every time a head with a different class count
 * is imported. A generated one is stable (index N is always the same colour, so two
 * runs of the same head are comparable) without anyone maintaining it.
 */

export interface Rgb {
  readonly r: number;
  readonly g: number;
  readonly b: number;
}

/**
 * The golden-angle hue step. Successive indices land far apart on the colour wheel, so
 * neighbouring class ids — which is what adjacent regions of a segmentation usually are —
 * never come out as neighbouring colours.
 */
const HUE_STEP = 137.508;

function hslToRgb(h: number, s: number, l: number): Rgb {
  const chroma = (1 - Math.abs(2 * l - 1)) * s;
  const secondary = chroma * (1 - Math.abs(((h / 60) % 2) - 1));
  const match = l - chroma / 2;

  const sector = Math.floor(h / 60) % 6;
  const [r, g, b] = (
    [
      [chroma, secondary, 0],
      [secondary, chroma, 0],
      [0, chroma, secondary],
      [0, secondary, chroma],
      [secondary, 0, chroma],
      [chroma, 0, secondary],
    ] as const
  )[sector] ?? [0, 0, 0];

  return {
    r: Math.round((r + match) * 255),
    g: Math.round((g + match) * 255),
    b: Math.round((b + match) * 255),
  };
}

/**
 * Stable colour for a class index.
 *
 * Index 0 is treated like any other class: in ADE20k class 0 is "wall", not "background",
 * so dimming it would hide a real prediction. A head that wants a transparent background
 * says so through opacity, not through the palette.
 */
export function classColour(index: number): Rgb {
  const hue = (index * HUE_STEP) % 360;
  // Alternating lightness gives adjacent indices a second axis of separation, which
  // matters once a palette wraps past ~40 classes and hues start repeating visually.
  const lightness = index % 2 === 0 ? 0.55 : 0.42;
  return hslToRgb(hue, 0.68, lightness);
}

export function toCssColour({ r, g, b }: Rgb, alpha = 1): string {
  return alpha >= 1 ? `rgb(${r} ${g} ${b})` : `rgb(${r} ${g} ${b} / ${alpha})`;
}

/**
 * Depth 0..1 (near..far) → colour, on a perceptually monotonic ramp.
 *
 * Deliberately not a rainbow: hue-cycling maps make non-existent boundaries look like
 * real ones, because the eye reads a hue change as an edge. This ramp only ever gets
 * lighter and warmer, so the only edges visible are edges in the data.
 */
export function depthColour(normalised: number): Rgb {
  const t = Math.min(Math.max(normalised, 0), 1);
  // Deep blue (near) → teal → sand (far).
  const stops: readonly (readonly [number, Rgb])[] = [
    [0.0, { r: 22, g: 32, b: 78 }],
    [0.5, { r: 33, g: 145, b: 140 }],
    [1.0, { r: 245, g: 226, b: 168 }],
  ];

  for (let i = 0; i < stops.length - 1; i += 1) {
    const current = stops[i];
    const next = stops[i + 1];
    if (!current || !next) break;
    const [fromT, from] = current;
    const [toT, to] = next;
    if (t > toT) continue;

    const span = toT - fromT;
    const k = span === 0 ? 0 : (t - fromT) / span;
    return {
      r: Math.round(from.r + (to.r - from.r) * k),
      g: Math.round(from.g + (to.g - from.g) * k),
      b: Math.round(from.b + (to.b - from.b) * k),
    };
  }

  return stops[stops.length - 1]?.[1] ?? { r: 0, g: 0, b: 0 };
}
