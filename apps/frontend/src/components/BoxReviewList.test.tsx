/**
 * The box review list (doc 47).
 *
 * What matters here is that a verdict is **one** click rather than a cycle, that the number
 * shown matches the number drawn on the box, and that hiding and removing stay two
 * different things — the slider is reversible and the button is not.
 */

import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { numbered } from '../lib/boxReview';
import type { CanvasBox } from '../types/annotation';
import { BoxReviewList } from './BoxReviewList';

function box(id: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return {
    id,
    label: 'positive',
    provenance: 'foundation-model',
    x: 0,
    y: 0,
    w: 10,
    h: 10,
    ...over,
  };
}

const BOXES = [
  box('a', { text: 'person', score: 0.91 }),
  box('b', { text: 'person', score: 0.42, label: 'negative' }),
  box('c', { text: 'dog', score: 0.12 }),
];

function renderList(over: Partial<Parameters<typeof BoxReviewList>[0]> = {}) {
  const handlers = {
    onSelect: vi.fn(),
    onLabel: vi.fn(),
    onRename: vi.fn(),
    onRemove: vi.fn(),
    onThreshold: vi.fn(),
    onRemoveHidden: vi.fn(),
    // Doc 60: the class is chosen from a vocabulary now, not typed. `create` resolves to
    // the name as stored, which is what the picker selects on success.
    onCreateClass: vi.fn(async (name: string) => name),
    onRenameClass: vi.fn(),
  };
  render(
    <BoxReviewList
      boxes={numbered(BOXES)}
      hidden={new Set()}
      selectedId={null}
      threshold={0}
      classes={['dog', 'person']}
      {...handlers}
      {...over}
    />,
  );
  return { ...handlers, user: userEvent.setup() };
}

describe('what a row shows', () => {
  it('lists every box', () => {
    renderList();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
  });

  it('shows the class, editable', () => {
    renderList();
    expect(screen.getByLabelText('Class of box 1')).toHaveValue('person');
  });

  it('shows the probability as a percentage', () => {
    renderList();
    expect(screen.getByText('91%')).toBeInTheDocument();
  });

  it('shows a dash rather than 0% when there is no score', () => {
    // A hand-drawn box is not a 0%-confidence detection, and showing it as one would
    // invite the user to threshold their own work away.
    renderList({ boxes: numbered([box('hand', { text: 'mine' })]) });
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('numbers rows to match the boxes drawn on the image', () => {
    renderList();
    const rows = screen.getAllByRole('listitem');
    expect(within(rows[2] as HTMLElement).getByLabelText('Class of box 3')).toHaveValue('dog');
  });
});

describe('verdicts', () => {
  it('sets a verdict in one click rather than cycling to it', () => {
    // The old canvas cycled positive -> negative -> unclear. Reaching "unclear" on thirty
    // proposed boxes was sixty clicks.
    renderList();
    expect(screen.getByLabelText('Not sure, box 1')).toBeInTheDocument();
  });

  it('reports the chosen label', async () => {
    const { onLabel, user } = renderList();
    await user.click(screen.getByLabelText('False, box 1'));
    expect(onLabel).toHaveBeenCalledWith('a', 'negative');
  });

  it('shows which verdict a box currently has', () => {
    renderList();
    expect(screen.getByLabelText('False, box 2')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByLabelText('True, box 2')).toHaveAttribute('aria-pressed', 'false');
  });

  it('removes a box', async () => {
    const { onRemove, user } = renderList();
    await user.click(screen.getByLabelText('Remove, box 3'));
    expect(onRemove).toHaveBeenCalledWith('c');
  });

  it('does not mark remove as a verdict the box holds', () => {
    // Remove is not one of the three labels; aria-pressed would claim it is a state.
    renderList();
    expect(screen.getByLabelText('Remove, box 1')).not.toHaveAttribute('aria-pressed');
  });
});

describe('hidden versus below the cutoff', () => {
  it('does not call a concealed box "below cutoff"', () => {
    // The slider makes a claim about the score. A box the reviewer got out of the way to
    // draw on a clear image has said nothing about its score.
    renderList({ hidden: new Set(['a', 'b']), belowCutoff: new Set() });

    expect(screen.queryByText(/below cutoff/)).not.toBeInTheDocument();
    expect(screen.getByText(/2 hidden/)).toBeInTheDocument();
  });

  it('counts the two reasons separately', () => {
    renderList({ hidden: new Set(['a', 'b', 'c']), belowCutoff: new Set(['c']) });

    expect(screen.getByText(/1 below cutoff/)).toBeInTheDocument();
    expect(screen.getByText(/2 hidden/)).toBeInTheDocument();
  });

  it('will not offer to discard a box that is merely concealed', () => {
    // The load-bearing one. `Remove N below` discarding work the user only hid would be
    // the worst thing this screen can do.
    renderList({ hidden: new Set(['a', 'b', 'c']), belowCutoff: new Set() });

    expect(screen.getByRole('button', { name: /Remove 0 below/ })).toBeDisabled();
  });

  it('says how to get concealed boxes back, not how to lower a cutoff', () => {
    renderList({ hidden: new Set(['a', 'b', 'c']), belowCutoff: new Set() });

    expect(screen.getByRole('status')).toHaveTextContent(/Show them again/);
  });
});

describe('choosing a class', () => {
  it('reports the class picked for a box', async () => {
    const { onRename, user } = renderList();

    await user.selectOptions(screen.getByLabelText('Class of box 3'), 'person');

    expect(onRename).toHaveBeenCalledWith('c', 'person');
  });

  it('offers every class in the vocabulary, plus unnamed and new', () => {
    renderList();

    const options = within(screen.getByLabelText('Class of box 1') as HTMLElement)
      .getAllByRole('option')
      .map((option) => option.textContent);

    expect(options).toEqual(['— unnamed —', 'dog', 'person', 'New class…']);
  });

  it('clears a class back to unnamed', async () => {
    // A hand-drawn box starts with no class, so "no class yet" has to stay reachable
    // after the first choice.
    const { onRename, user } = renderList();

    await user.selectOptions(screen.getByLabelText('Class of box 1'), '');

    expect(onRename).toHaveBeenCalledWith('a', '');
  });

  it('renames a class across every box carrying it', async () => {
    // The reason doc 47 chose a free-text input was that a proposal run names many boxes
    // the same thing. That correction is now one decision rather than thirty.
    const { onRenameClass, user } = renderList();

    await user.click(
      screen.getByLabelText('Rename person on every box in this image, Class of box 1'),
    );
    const field = screen.getByLabelText('Rename person, Class of box 1');
    await user.clear(field);
    await user.type(field, 'pedestrian');
    await user.click(screen.getByRole('button', { name: 'Rename' }));

    expect(onRenameClass).toHaveBeenCalledWith('person', 'pedestrian');
  });

  it('offers no rename on a box with no class', () => {
    renderList({ boxes: numbered([box('a', { score: 0.9 })]) });

    expect(screen.queryByRole('button', { name: /^Rename/ })).not.toBeInTheDocument();
  });
});

describe('the threshold', () => {
  it('offers a slider when the boxes have scores', () => {
    renderList();
    expect(screen.getByRole('slider')).toBeInTheDocument();
  });

  it('hides the slider when nothing has a score', () => {
    // Every box hand-drawn: there is nothing to threshold, and a slider that does nothing
    // reads as broken.
    renderList({ boxes: numbered([box('hand')]) });
    expect(screen.queryByRole('slider')).not.toBeInTheDocument();
  });

  it("reports a new threshold as a number, not the raw input string", () => {
    // `event.target.value` is a string; a missing Number() puts "0.4" into state and the
    // comparison in `hiddenByThreshold` then does the wrong thing without complaining.
    const { onThreshold } = renderList();
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0.4' } });
    expect(onThreshold).toHaveBeenCalledWith(0.4);
  });

  it('leaves hidden boxes out of the list but says how many', () => {
    renderList({ hidden: new Set(['c']), belowCutoff: new Set(['c']), threshold: 0.3 });
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText(/1 below cutoff/)).toBeInTheDocument();
  });

  it('offers to discard exactly what is hidden', async () => {
    const { onRemoveHidden, user } = renderList({
      hidden: new Set(['b', 'c']),
      belowCutoff: new Set(['b', 'c']),
      threshold: 0.5,
    });
    const discard = screen.getByRole('button', { name: /Remove 2 below/ });
    await user.click(discard);
    expect(onRemoveHidden).toHaveBeenCalled();
  });

  it('cannot discard when nothing is hidden', () => {
    renderList();
    expect(screen.getByRole('button', { name: /Remove 0 below/ })).toBeDisabled();
  });

  it('says how to get the boxes back when everything is filtered out', () => {
    renderList({
      hidden: new Set(['a', 'b', 'c']),
      belowCutoff: new Set(['a', 'b', 'c']),
      threshold: 0.99,
    });
    expect(screen.getByRole('status')).toHaveTextContent(/Lower it/);
  });

  it('says something different when there are no boxes at all', () => {
    // "Every box is below the cutoff" would be a lie, and would send the user to the
    // slider instead of to the Run button.
    renderList({ boxes: [] });
    expect(screen.getByRole('status')).toHaveTextContent(/Run a model/);
  });
});
