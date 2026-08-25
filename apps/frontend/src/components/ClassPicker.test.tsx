/**
 * The class picker (doc 60).
 *
 * The properties worth holding are the ones a free-text field never had to think about:
 * a class can be **created** rather than only typed, the value a box already carries is
 * always selectable even when the vocabulary does not know it, and "no class" stays
 * reachable after the first choice.
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ClassPicker } from './ClassPicker';

function renderPicker(over: Partial<Parameters<typeof ClassPicker>[0]> = {}) {
  const onChange = vi.fn<(name: string) => void>();
  const onCreate = vi.fn<(name: string) => Promise<string | null>>(async (name) => name);
  const onRename = vi.fn<(from: string, to: string) => void>();
  render(
    <ClassPicker
      value=""
      options={['dog', 'person']}
      label="Class of box 1"
      onChange={onChange}
      onCreate={onCreate}
      onRename={onRename}
      {...over}
    />,
  );
  return { onChange, onCreate, onRename, user: userEvent.setup() };
}

function optionTexts(): (string | null)[] {
  return within(screen.getByLabelText('Class of box 1') as HTMLElement)
    .getAllByRole('option')
    .map((option) => option.textContent);
}

describe('choosing', () => {
  it('offers unnamed, every class, and a way to make one', () => {
    renderPicker();
    expect(optionTexts()).toEqual(['— unnamed —', 'dog', 'person', 'New class…']);
  });

  it('shows the class the box carries', () => {
    renderPicker({ value: 'person' });
    expect(screen.getByLabelText('Class of box 1')).toHaveValue('person');
  });

  it('reports the chosen class', async () => {
    const { onChange, user } = renderPicker();
    await user.selectOptions(screen.getByLabelText('Class of box 1'), 'dog');
    expect(onChange).toHaveBeenCalledWith('dog');
  });

  it('keeps no-class reachable after a choice', async () => {
    // A hand-drawn box starts with no class. A picker with no empty option would make
    // "not decided yet" unrepresentable the moment anything was picked.
    const { onChange, user } = renderPicker({ value: 'dog' });
    await user.selectOptions(screen.getByLabelText('Class of box 1'), '');
    expect(onChange).toHaveBeenCalledWith('');
  });

  it('lists a class the vocabulary does not know but the box carries', () => {
    // A proposal whose class was never saved, or one deleted from the vocabulary while
    // boxes still carry it. Without this the select shows the *first* option instead —
    // silently claiming the box is something it is not.
    renderPicker({ value: 'signal', options: ['dog', 'person'] });

    expect(screen.getByLabelText('Class of box 1')).toHaveValue('signal');
    expect(optionTexts()).toContain('signal');
  });
});

describe('creating', () => {
  it('opens a field when New class is chosen', async () => {
    const { user } = renderPicker();

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');

    expect(screen.getByLabelText('New class for Class of box 1')).toBeInTheDocument();
  });

  it('creates the class and selects it', async () => {
    const { onCreate, onChange, user } = renderPicker();

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');
    await user.type(screen.getByLabelText('New class for Class of box 1'), 'signal');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(onCreate).toHaveBeenCalledWith('signal');
    expect(onChange).toHaveBeenCalledWith('signal');
  });

  it('selects the stored spelling, not the typed one', async () => {
    // The first spelling of a class wins server-side, so typing `Signal` where `signal`
    // exists must select `signal` — selecting the typed one would show an option that
    // is not in the list and lose it on the next load.
    const { onChange, user } = renderPicker({ onCreate: async () => 'signal' });

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');
    await user.type(screen.getByLabelText('New class for Class of box 1'), 'Signal');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(onChange).toHaveBeenCalledWith('signal');
  });

  it('does not select anything when the class could not be created', async () => {
    const { onChange, user } = renderPicker({ onCreate: async () => null });

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');
    await user.type(screen.getByLabelText('New class for Class of box 1'), 'signal');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('commits on Enter', async () => {
    const { onCreate, user } = renderPicker();

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');
    await user.type(screen.getByLabelText('New class for Class of box 1'), 'signal{Enter}');

    expect(onCreate).toHaveBeenCalledWith('signal');
  });

  it('abandons on Escape without creating anything', async () => {
    const { onCreate, user } = renderPicker();

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');
    await user.type(screen.getByLabelText('New class for Class of box 1'), 'signal{Escape}');

    expect(onCreate).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Class of box 1')).toBeInTheDocument();
  });

  it('refuses to add a blank name', async () => {
    // Blur-to-commit would create a class every time a reviewer tabbed past the control,
    // which is why there is an explicit button and why it stays dead until there is a name.
    const { user } = renderPicker();

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');
    await user.type(screen.getByLabelText('New class for Class of box 1'), '   ');

    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
  });

  it('cancels back to the picker', async () => {
    const { onCreate, user } = renderPicker();

    await user.selectOptions(screen.getByLabelText('Class of box 1'), ' new');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onCreate).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Class of box 1')).toBeInTheDocument();
  });
});

describe('renaming', () => {
  it('is not offered on a box with no class', () => {
    renderPicker({ value: '' });
    expect(screen.queryByRole('button', { name: /^Rename/ })).not.toBeInTheDocument();
  });

  it('is not offered when the caller cannot act on it', () => {
    render(
      <ClassPicker
        value="dog"
        options={['dog']}
        label="Class of box 1"
        onChange={vi.fn()}
        onCreate={vi.fn(async (name: string) => name)}
      />,
    );
    expect(screen.queryByRole('button', { name: /^Rename/ })).not.toBeInTheDocument();
  });

  it('reports the old and new names', async () => {
    const { onRename, user } = renderPicker({ value: 'dog' });

    await user.click(
      screen.getByLabelText('Rename dog on every box in this image, Class of box 1'),
    );
    const field = screen.getByLabelText('Rename dog, Class of box 1');
    await user.clear(field);
    await user.type(field, 'hound');
    await user.click(screen.getByRole('button', { name: 'Rename' }));

    expect(onRename).toHaveBeenCalledWith('dog', 'hound');
  });

  it('does not create a class when renaming', async () => {
    // A rename is a local box edit that rides out with the next save. Calling the classes
    // API here would add the new name to the vocabulary before any box carried it.
    const { onCreate, user } = renderPicker({ value: 'dog' });

    await user.click(
      screen.getByLabelText('Rename dog on every box in this image, Class of box 1'),
    );
    await user.type(screen.getByLabelText('Rename dog, Class of box 1'), '{Enter}');

    expect(onCreate).not.toHaveBeenCalled();
  });

  it('starts from the current name so a small correction is a small edit', async () => {
    const { user } = renderPicker({ value: 'pedestrain' });

    await user.click(
      screen.getByLabelText('Rename pedestrain on every box in this image, Class of box 1'),
    );

    expect(screen.getByLabelText('Rename pedestrain, Class of box 1')).toHaveValue(
      'pedestrain',
    );
  });
});

describe('when disabled', () => {
  it('cannot be changed', () => {
    renderPicker({ value: 'dog', disabled: true });
    expect(screen.getByLabelText('Class of box 1')).toBeDisabled();
    expect(
      screen.getByLabelText('Rename dog on every box in this image, Class of box 1'),
    ).toBeDisabled();
  });
});
