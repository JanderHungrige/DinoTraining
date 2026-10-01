/**
 * Dino Run's rules (doc 127): something to do while PyTorch downloads.
 *
 * Pure: a state and a time step in, the next state out. The component only draws, so
 * every rule here is tested without a canvas. Units are world pixels and seconds; the
 * world is {@link WIDTH} × {@link HEIGHT} with the ground at {@link GROUND}.
 */

export const WIDTH = 600;
export const HEIGHT = 150;
export const GROUND = 128;

export const DINO_X = 48;
export const DINO_WIDTH = 40;
export const DINO_HEIGHT = 36;

const GRAVITY = 2300;
const JUMP_SPEED = 760;
const START_SPEED = 260;
const MAX_SPEED = 560;
const ACCELERATION = 5;
/** Hit boxes are a little smaller than the drawings: a graze that looks like a miss is one. */
const FORGIVE = 5;

export type ObstacleKind = 'rock' | 'fern';

export interface Obstacle {
  readonly x: number;
  readonly width: number;
  readonly height: number;
  readonly kind: ObstacleKind;
}

export interface GameState {
  /** Height of the dino's feet above the ground; 0 is standing. */
  readonly y: number;
  readonly vy: number;
  readonly obstacles: readonly Obstacle[];
  readonly speed: number;
  readonly distance: number;
  /** Distance still to run before the next obstacle appears. */
  readonly untilNext: number;
  readonly over: boolean;
  readonly best: number;
  readonly seed: number;
}

/** A small seeded random source (mulberry32): the same seed, the same course. */
export function random(seed: number): [number, number] {
  let t = (seed + 0x6d2b79f5) | 0;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  const value = ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  return [value, (seed + 0x6d2b79f5) | 0];
}

export function newGame(seed: number, best = 0): GameState {
  return {
    y: 0,
    vy: 0,
    obstacles: [],
    speed: START_SPEED,
    distance: 0,
    untilNext: WIDTH * 0.6,
    over: false,
    best,
    seed,
  };
}

export function score(state: GameState): number {
  return Math.floor(state.distance / 20);
}

export function onGround(state: GameState): boolean {
  return state.y <= 0 && state.vy <= 0;
}

/** Jump when standing; a jump in the air does nothing. After a crash, a jump restarts. */
export function jump(state: GameState): GameState {
  if (state.over) return newGame(state.seed, state.best);
  if (!onGround(state)) return state;
  return { ...state, vy: JUMP_SPEED };
}

function spawn(state: GameState): Pick<GameState, 'obstacles' | 'untilNext' | 'seed'> {
  const [kindRoll, seed1] = random(state.seed);
  const [sizeRoll, seed2] = random(seed1);
  const [gapRoll, seed3] = random(seed2);
  const kind: ObstacleKind = kindRoll < 0.5 ? 'rock' : 'fern';
  const obstacle: Obstacle =
    kind === 'rock'
      ? { x: WIDTH + 10, width: 22 + sizeRoll * 18, height: 16 + sizeRoll * 10, kind }
      : { x: WIDTH + 10, width: 14 + sizeRoll * 8, height: 28 + sizeRoll * 14, kind };
  // The gap grows with the speed, so a jump always has room to land.
  const gap = state.speed * (0.75 + gapRoll * 0.9);
  return { obstacles: [...state.obstacles, obstacle], untilNext: gap, seed: seed3 };
}

export function collides(state: GameState): boolean {
  const left = DINO_X + FORGIVE;
  const right = DINO_X + DINO_WIDTH - FORGIVE;
  return state.obstacles.some(
    (o) => o.x + FORGIVE < right && o.x + o.width - FORGIVE > left && state.y < o.height - FORGIVE,
  );
}

/**
 * The autopilot's decision: jump when the next obstacle is close enough that the jump's
 * arc clears it. Used when nobody is playing, so the dino runs on as a calm animation.
 */
export function shouldAutoJump(state: GameState): boolean {
  if (!onGround(state) || state.over) return false;
  const next = state.obstacles.find((o) => o.x + o.width > DINO_X);
  if (!next) return false;
  const gap = next.x - (DINO_X + DINO_WIDTH);
  return gap > 0 && gap < state.speed * 0.16;
}

/** Advance by `dt` seconds (clamped, so a background tab does not teleport the dino). */
export function step(state: GameState, dt: number): GameState {
  if (state.over) return state;
  const t = Math.min(Math.max(dt, 0), 0.05);
  const speed = Math.min(MAX_SPEED, state.speed + ACCELERATION * t);
  const moved = speed * t;

  let vy = state.vy - GRAVITY * t;
  let y = state.y + state.vy * t;
  if (y <= 0) {
    y = 0;
    vy = 0;
  }

  let next: GameState = {
    ...state,
    y,
    vy,
    speed,
    distance: state.distance + moved,
    untilNext: state.untilNext - moved,
    obstacles: state.obstacles
      .map((o) => ({ ...o, x: o.x - moved }))
      .filter((o) => o.x + o.width > -10),
  };
  if (next.untilNext <= 0) next = { ...next, ...spawn(next) };
  if (collides(next)) {
    return { ...next, over: true, best: Math.max(next.best, score(next)) };
  }
  return next;
}
