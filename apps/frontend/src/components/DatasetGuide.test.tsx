import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderInGerman } from '../i18n/testing';
import { DatasetGuide } from './DatasetGuide';

describe('DatasetGuide (doc 137)', () => {
  it('folds both sections, so the list stays first', () => {
    const { container } = render(<DatasetGuide />);
    const sections = container.querySelectorAll('details');
    expect(sections).toHaveLength(2);
    sections.forEach((section) => expect(section.open).toBe(false));
  });

  it('explains each format the import reads, with its folder tree', () => {
    const { container } = render(<DatasetGuide />);
    fireEvent.click(screen.getByText('How must a dataset look?'));
    for (const heading of ['Without annotations', /^COCO/, /^YOLO/, 'Pascal VOC', 'OpenLABEL (OSDaR23)']) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
    }
    const trees = [...container.querySelectorAll('pre')].map((tree) => tree.textContent ?? '');
    expect(trees).toHaveLength(5);
    expect(trees.some((tree) => tree.includes('labels/train/0001.txt'))).toBe(true);
    expect(trees.some((tree) => tree.includes('_annotations.coco.json'))).toBe(true);
    expect(screen.getByText(/folder named train, val/)).toBeInTheDocument();
  });

  it('links the dataset sites in a new window, OSDaR23 with its data portal', () => {
    render(<DatasetGuide />);
    const list = screen.getByRole('list');
    const links = within(list).getAllByRole('link');
    expect(links.map((link) => link.textContent)).toEqual([
      'Hugging Face', 'Roboflow Universe', 'Kaggle', 'Open Images V7', 'COCO', 'OSDaR23', 'the data portal',
    ]);
    for (const link of links) {
      expect(link).toHaveAttribute('target', '_blank');
      expect(link.getAttribute('rel')).toContain('noopener');
      expect(link.getAttribute('href')).toMatch(/^https:\/\//);
    }
    expect(within(list).getByRole('link', { name: 'the data portal' })).toHaveAttribute('href', 'https://data.fid-move.de/dataset/osdar23');
    expect(screen.getByText(/own licence/)).toBeInTheDocument();
  });

  it('speaks German, but keeps the folder trees as they are', () => {
    const { container } = renderInGerman(<DatasetGuide />);
    expect(screen.getByText('Wie muss ein Datensatz aussehen?')).toBeInTheDocument();
    expect(screen.getByText('Wo es Datensätze gibt')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Ohne Annotationen' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'das Datenportal' })).toBeInTheDocument();
    expect(container.textContent).toContain('images/train/0001.jpg');
  });
});
