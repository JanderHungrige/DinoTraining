/**
 * The picker is a text field first and a native dialog second.
 *
 * Under Tauri the dialog plugin gives a real picker; in the `web` dev mode and in Wave 6
 * there is none, so the field must stay usable on its own — the same rule
 * `SessionSetup` established in Wave 1.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ImageSourcePicker } from './ImageSourcePicker';

describe('ImageSourcePicker', () => {
  it('submits a typed path', () => {
    const onPick = vi.fn();
    render(<ImageSourcePicker onPick={onPick} />);

    fireEvent.change(screen.getByLabelText(/image or folder/i), {
      target: { value: '/Users/you/photos' },
    });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    expect(onPick).toHaveBeenCalledWith('/Users/you/photos');
  });

  it('trims whitespace a paste brought along', () => {
    const onPick = vi.fn();
    render(<ImageSourcePicker onPick={onPick} />);

    fireEvent.change(screen.getByLabelText(/image or folder/i), {
      target: { value: '  /Users/you/photos  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    expect(onPick).toHaveBeenCalledWith('/Users/you/photos');
  });

  it('does not submit an empty path', () => {
    const onPick = vi.fn();
    render(<ImageSourcePicker onPick={onPick} />);

    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    expect(onPick).not.toHaveBeenCalled();
  });

  it('hides the native browse buttons when there is no dialog', () => {
    render(<ImageSourcePicker onPick={vi.fn()} />);

    expect(screen.queryByRole('button', { name: /folder…/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /image…/i })).toBeNull();
  });

  it('keeps the field editable while a source is loading', () => {
    render(<ImageSourcePicker onPick={vi.fn()} busy />);

    // Typing the next path while the current one loads is not a mistake to prevent;
    // only the submit is held back.
    expect(screen.getByLabelText(/image or folder/i)).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /load/i })).toBeDisabled();
  });

  it('shows the path it was given without waiting for a keystroke', () => {
    render(<ImageSourcePicker onPick={vi.fn()} value="/photos" />);

    expect(screen.getByLabelText(/image or folder/i)).toHaveValue('/photos');
  });
});
