/**
 * A translated sentence with parts set in markup (doc 112): `{name}` placeholders the
 * translator left unfilled are replaced by nodes, so a language can move them.
 */

import { Fragment, type ReactNode } from 'react';

export function richText(text: string, parts: Readonly<Record<string, ReactNode>>): ReactNode[] {
  return text.split(/(\{\w+\})/).map((piece, index) => {
    const name = /^\{(\w+)\}$/.exec(piece)?.[1];
    return <Fragment key={index}>{name !== undefined && name in parts ? parts[name] : piece}</Fragment>;
  });
}
