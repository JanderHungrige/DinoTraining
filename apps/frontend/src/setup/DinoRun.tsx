/**
 * Dino Run on a canvas (doc 127). The rules live in `runRules.ts`; this draws them and
 * turns Space, ↑ and clicks into jumps.
 *
 * Nobody has to play: until the first jump the autopilot runs the dino, and it takes
 * over again after {@link IDLE_MS} without input, so an unattended screen stays a calm
 * animation rather than a crashed game.
 */

import { useEffect, useRef, useState, type JSX } from 'react';

import { useT } from '../i18n';
import {
  DINO_HEIGHT,
  DINO_X,
  GROUND,
  HEIGHT,
  WIDTH,
  jump,
  newGame,
  score,
  shouldAutoJump,
  step,
  type GameState,
  type Obstacle,
} from './runRules';

const IDLE_MS = 12_000;

/** The dino, 20 × 18 cells of 2 px; the last three rows are the legs, two frames. */
const BODY = [
  '..........########..',
  '.........##.#######.',
  '.........##########.',
  '.........##########.',
  '.........#####......',
  '.........########...',
  '#.......######......',
  '#......#######......',
  '##....#########.....',
  '###..##########.#...',
  '###############.....',
  '.##############.....',
  '..############......',
  '...##########.......',
  '....########........',
];
const LEGS = [
  ['....###..##.........', '....##....#.........', '....#.....##........'],
  ['....###..##.........', '....#.....##........', '....##..............'],
] as const;
const CELL = 2;

function drawSprite(ctx: CanvasRenderingContext2D, rows: readonly string[], x: number, y: number): void {
  rows.forEach((row, r) => {
    for (let c = 0; c < row.length; c += 1) {
      if (row[c] === '#') ctx.fillRect(x + c * CELL, y + r * CELL, CELL, CELL);
    }
  });
}

function drawObstacle(ctx: CanvasRenderingContext2D, o: Obstacle, colours: Colours): void {
  const top = GROUND - o.height;
  if (o.kind === 'rock') {
    ctx.fillStyle = colours.dim;
    // roundRect is missing from older WebKitGTK (the Linux app); a plain block is fine.
    if (typeof ctx.roundRect === 'function') {
      ctx.beginPath();
      ctx.roundRect(o.x, top, o.width, o.height, [o.height * 0.6, o.height * 0.5, 2, 2]);
      ctx.fill();
    } else {
      ctx.fillRect(o.x, top, o.width, o.height);
    }
    return;
  }
  // A fern: three fronds from one root.
  ctx.fillStyle = colours.accent;
  const root = o.x + o.width / 2;
  for (const [lean, height] of [[-0.5, 0.75], [0, 1], [0.5, 0.8]] as const) {
    ctx.beginPath();
    ctx.moveTo(root - 3, GROUND);
    ctx.lineTo(root + lean * o.width, GROUND - o.height * height);
    ctx.lineTo(root + 3, GROUND);
    ctx.fill();
  }
}

interface Colours {
  readonly text: string;
  readonly dim: string;
  readonly accent: string;
}

function readColours(element: HTMLElement): Colours {
  const style = getComputedStyle(element);
  const read = (name: string, fallback: string): string => style.getPropertyValue(name).trim() || fallback;
  return { text: read('--text', '#e7e9ee'), dim: read('--text-dim', '#9aa2b1'), accent: read('--accent', '#4ade80') };
}

function draw(ctx: CanvasRenderingContext2D, state: GameState, colours: Colours): void {
  ctx.clearRect(0, 0, WIDTH, HEIGHT);
  // The ground, with pebbles that move at the running speed.
  ctx.fillStyle = colours.dim;
  ctx.fillRect(0, GROUND, WIDTH, 1);
  for (let i = 0; i < 14; i += 1) {
    const x = (((i * 97 - state.distance) % WIDTH) + WIDTH) % WIDTH;
    ctx.fillRect(x, GROUND + 5 + ((i * 7) % 11), 2 + (i % 3), 1);
  }
  state.obstacles.forEach((o) => drawObstacle(ctx, o, colours));

  ctx.fillStyle = colours.text;
  const top = GROUND - DINO_HEIGHT - state.y;
  drawSprite(ctx, BODY, DINO_X, top);
  const frame = state.y > 0 || state.over ? 0 : Math.floor(state.distance / 28) % 2;
  drawSprite(ctx, LEGS[frame] ?? LEGS[0], DINO_X, top + BODY.length * CELL);
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

interface DinoRunProps {
  /** Called on the player's first jump: the setup screen then waits for them to finish. */
  readonly onPlay?: () => void;
}

export function DinoRun({ onPlay }: DinoRunProps): JSX.Element | null {
  const { t } = useT();
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const game = useRef<GameState>(newGame(Date.now() % 100_000));
  const lastInput = useRef(0);
  const [shown, setShown] = useState({ score: 0, best: 0, over: false, playing: false });
  const [reduced] = useState(prefersReducedMotion);
  const onPlayRef = useRef(onPlay);
  onPlayRef.current = onPlay;
  const playerJump = useRef(() => {
    lastInput.current = performance.now();
    game.current = jump(game.current);
    onPlayRef.current?.();
  });

  useEffect(() => {
    if (reduced) return undefined;
    const ctx = canvas.current?.getContext('2d') ?? null;
    if (!canvas.current || !ctx) return undefined;
    const ratio = window.devicePixelRatio || 1;
    canvas.current.width = WIDTH * ratio;
    canvas.current.height = HEIGHT * ratio;
    ctx.scale(ratio, ratio);
    const colours = readColours(canvas.current);

    let frame = 0;
    let previous = performance.now();
    const tick = (now: number): void => {
      const playing = now - lastInput.current < IDLE_MS;
      let state = game.current;
      if (!playing && state.over) state = newGame(state.seed + 1, state.best);
      if (!playing && shouldAutoJump(state)) state = jump(state);
      state = step(state, (now - previous) / 1000);
      previous = now;
      game.current = state;
      draw(ctx, state, colours);
      setShown((old) => {
        const next = { score: score(state), best: state.best, over: state.over, playing };
        return old.score === next.score && old.over === next.over && old.best === next.best && old.playing === next.playing
          ? old
          : next;
      });
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [reduced]);

  useEffect(() => {
    if (reduced) return undefined;
    const onKey = (event: KeyboardEvent): void => {
      if (event.code !== 'Space' && event.code !== 'ArrowUp') return;
      // Space on a focused button is that button's click, not a jump.
      if (event.target instanceof HTMLButtonElement || event.target instanceof HTMLInputElement) return;
      event.preventDefault();
      playerJump.current();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [reduced]);

  if (reduced) return null;

  return (
    <figure className="dinorun">
      <canvas
        ref={canvas}
        className="dinorun__canvas"
        role="img"
        aria-label={t('setup.game.label')}
        onPointerDown={() => playerJump.current()}
      />
      <figcaption className="dinorun__caption">
        <span>{shown.over ? t('setup.game.over') : shown.playing ? t('setup.game.playing') : t('setup.game.hint')}</span>
        <span className="dinorun__score">
          {t('setup.game.score', { score: String(shown.score) })}
          {shown.best > 0 && ` · ${t('setup.game.best', { best: String(shown.best) })}`}
        </span>
      </figcaption>
    </figure>
  );
}
