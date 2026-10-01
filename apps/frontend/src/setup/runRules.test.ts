import { describe, expect, it } from 'vitest';

import {
  DINO_X,
  collides,
  jump,
  newGame,
  onGround,
  random,
  score,
  shouldAutoJump,
  step,
  type GameState,
} from './runRules';

const FRAME = 1 / 60;

function run(state: GameState, seconds: number, autopilot: boolean): GameState {
  let current = state;
  for (let i = 0; i < seconds * 60; i += 1) {
    if (autopilot && shouldAutoJump(current)) current = jump(current);
    current = step(current, FRAME);
    if (current.over) return current;
  }
  return current;
}

describe('Dino Run', () => {
  it('a jump rises and lands again', () => {
    let state = jump(newGame(1));
    expect(onGround(state)).toBe(false);
    state = step(state, 0.05);
    expect(state.y).toBeGreaterThan(30);
    for (let i = 0; i < 60; i += 1) state = step(state, FRAME);
    expect(onGround(state)).toBe(true);
  });

  it('a second jump in the air does nothing', () => {
    const airborne = step(jump(newGame(1)), 0.1);
    expect(jump(airborne)).toBe(airborne);
  });

  it('nobody playing: the autopilot runs for ten minutes without a crash', () => {
    for (const seed of [1, 2, 3, 42, 2026]) {
      const state = run(newGame(seed), 600, true);
      expect(state.over, `seed ${seed}`).toBe(false);
      expect(score(state)).toBeGreaterThan(1000);
    }
  });

  it('without jumping the dino hits the first obstacle', () => {
    const state = run(newGame(7), 30, false);
    expect(state.over).toBe(true);
    expect(state.best).toBe(score(state));
  });

  it('after a crash a jump starts a new round and keeps the best score', () => {
    const crashed = run(newGame(7), 30, false);
    const again = jump(crashed);
    expect(again.over).toBe(false);
    expect(again.distance).toBe(0);
    expect(again.best).toBe(crashed.best);
  });

  it('a standing dino touching an obstacle collides; a high one does not', () => {
    const rock = { x: DINO_X + 10, width: 30, height: 20, kind: 'rock' as const };
    expect(collides({ ...newGame(1), obstacles: [rock] })).toBe(true);
    expect(collides({ ...newGame(1), y: 30, obstacles: [rock] })).toBe(false);
  });

  it('a long pause does not teleport the dino through obstacles', () => {
    const state = step(newGame(1), 5);
    expect(state.distance).toBeLessThan(20);
  });

  it('the same seed gives the same course', () => {
    expect(random(5)).toEqual(random(5));
    expect(run(newGame(9), 20, true).obstacles).toEqual(run(newGame(9), 20, true).obstacles);
  });
});
