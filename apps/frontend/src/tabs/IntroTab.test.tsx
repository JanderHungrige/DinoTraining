/**
 * The Intro tab (doc 38).
 *
 * This is the one page in the app whose only job is to be *true*, and the way it stops
 * being true is that someone changes a tab and never opens this file. So most of these
 * tests assert on the relationship between the intro and the rest of the app — every stage
 * points at a real tab, every tab that exists is covered — rather than on wording, which
 * should be free to improve.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { IntroTab } from './IntroTab';
import { INTRO_CONCEPTS, INTRO_LIMITS, INTRO_STAGES } from './introContent';
import { TABS, getTab, isTabId } from './tabs';

function renderIntro() {
  const onNavigate = vi.fn();
  render(<IntroTab onNavigate={onNavigate} />);
  return { onNavigate, user: userEvent.setup() };
}

describe('staying in step with the app', () => {
  it('points every stage at a tab that exists', () => {
    for (const stage of INTRO_STAGES) {
      expect(isTabId(stage.tab)).toBe(true);
    }
  });

  it('covers every tab except itself', () => {
    // The failure this catches: a seventh tab is added in Wave 8 or 9 and the intro
    // silently keeps describing six. Nothing else in the app would notice.
    const described = new Set(INTRO_STAGES.map((stage) => stage.tab));
    const missing = TABS.map((tab) => tab.id).filter(
      (id) => id !== 'intro' && !described.has(id),
    );
    expect(missing).toEqual([]);
  });

  it('names each tab as the tab bar names it', () => {
    // Not a duplicated string: the button reads its label from `getTab`, so a rename
    // moves both together. This asserts that it kept doing so.
    renderIntro();
    for (const stage of INTRO_STAGES) {
      expect(
        screen.getByRole('button', { name: `Open ${getTab(stage.tab).label}` }),
      ).toBeInTheDocument();
    }
  });

  it('lists the stages in the order the tabs are in', () => {
    // The intro's whole claim is "the tabs are in the order you use them". If the tab bar
    // is reordered and this is not, the claim becomes false rather than merely untidy.
    const tabOrder = TABS.map((tab) => tab.id).filter((id) => id !== 'intro');
    expect(INTRO_STAGES.map((stage) => stage.tab)).toEqual(tabOrder);
  });
});

describe('reading turns into doing', () => {
  it('navigates to the tab a stage describes', async () => {
    const { onNavigate, user } = renderIntro();

    await user.click(screen.getByRole('button', { name: 'Open Head Trainer' }));

    expect(onNavigate).toHaveBeenCalledWith('trainer');
  });

  it('offers a way into every stage, not just the first', async () => {
    const { onNavigate, user } = renderIntro();

    for (const stage of INTRO_STAGES) {
      await user.click(
        screen.getByRole('button', { name: `Open ${getTab(stage.tab).label}` }),
      );
    }

    expect(onNavigate.mock.calls.map(([id]) => id)).toEqual(
      INTRO_STAGES.map((stage) => stage.tab),
    );
  });
});

describe('explaining the ideas the app assumes', () => {
  it('explains the frozen backbone and the head', () => {
    const terms = INTRO_CONCEPTS.map((concept) => concept.term.toLowerCase());
    expect(terms.some((term) => term.includes('frozen backbone'))).toBe(true);
    expect(terms.some((term) => term.includes('head'))).toBe(true);
  });

  it('renders every concept it defines', () => {
    renderIntro();
    for (const concept of INTRO_CONCEPTS) {
      expect(screen.getByText(concept.term)).toBeInTheDocument();
    }
  });

  it('gives each stage a reason for its position, not only a description', () => {
    // "Why here" is the part that is not guessable from the UI. A stage with an empty
    // `why` would render a dangling "Why here:" label.
    for (const stage of INTRO_STAGES) {
      expect(stage.why.trim().length).toBeGreaterThan(20);
    }
  });
});

describe('being honest about the gaps', () => {
  it('says what the app cannot do', () => {
    renderIntro();
    expect(screen.getByText(/What it cannot do yet/)).toBeInTheDocument();
    expect(INTRO_LIMITS.length).toBeGreaterThan(0);
  });

  it('renders every limitation', () => {
    renderIntro();
    for (const limit of INTRO_LIMITS) {
      expect(screen.getByText(limit)).toBeInTheDocument();
    }
  });
});

describe('structure a screen reader can follow', () => {
  it('uses a heading hierarchy rather than styled text', () => {
    renderIntro();
    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 3 }).length).toBeGreaterThanOrEqual(3);
  });

  it('presents the loop as an ordered list, because the order is the meaning', () => {
    // `<ol>`, not `<ul>`: the stages are a sequence, and a screen reader announcing
    // "1 of 5" is carrying real information rather than decoration. Testing Library gives
    // both the same `list` role, so this reads the tag — the one thing that distinguishes
    // them and the whole point of the assertion.
    const { container } = render(<IntroTab onNavigate={vi.fn()} />);
    const ordered = container.querySelector('ol');
    expect(ordered).not.toBeNull();
    expect(ordered?.querySelectorAll('li')).toHaveLength(INTRO_STAGES.length);
  });
});
