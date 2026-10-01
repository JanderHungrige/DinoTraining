/** A phrase as the backend stores it (doc 103): lower case, spaces collapsed, a trailing
 *  stop dropped. What remains of doc 105's per-outline phrase edits after doc 116. */
export function phraseKey(text: string): string {
  const key = text.trim().toLowerCase().replace(/\.+$/, '').split(/\s+/).filter(Boolean).join(' ');
  return key || 'object';
}
