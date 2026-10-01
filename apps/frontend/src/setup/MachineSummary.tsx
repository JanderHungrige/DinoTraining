/** What the setup found on this machine, and what each install choice means (doc 127). */

import type { JSX } from 'react';

import { useT, type Language, type Translator } from '../i18n';
import type { Choice, Machine } from './shell';

const CUDA_NAMES: Record<string, string> = { cu126: '12.6', cu130: '13.0' };

/** Gigabytes in the app's language: "3.5" in English, "3,5" in German. */
export function formatGb(value: number, lang: Language): string {
  return value.toLocaleString(lang === 'de' ? 'de-DE' : 'en-GB', { maximumFractionDigits: 1 });
}

/** The button text for one choice: what it installs and roughly how much it downloads. */
export function variantLabel(t: Translator['t'], lang: Language, choice: Choice, machine: Machine): string {
  const gb = formatGb(choice.download_gb, lang);
  const cuda = CUDA_NAMES[choice.variant];
  if (cuda) return t('setup.choice.gpu', { cuda, gb });
  return machine.choices.length > 1 ? t('setup.choice.cpuOnly', { gb }) : t('setup.choice.install', { gb });
}

function foundLine(t: Translator['t'], machine: Machine): string {
  if (machine.apple_silicon) return t('setup.found.appleSilicon');
  if (machine.gpu) return t('setup.found.nvidia', { name: machine.gpu.name, driver: machine.gpu.driver });
  if (machine.choices.length > 0) return t('setup.found.cpu');
  return '';
}

function noteLine(t: Translator['t'], machine: Machine): string | null {
  const note = machine.note;
  if (!note) return null;
  switch (note.kind) {
    case 'intel_mac':
      return t('setup.note.intelMac');
    case 'unsupported_platform':
      return t('setup.note.unsupported', { os: note.os, arch: note.arch });
    case 'driver_too_old':
      return t('setup.note.driverTooOld', { driver: note.driver, needed: String(note.needed) });
    default:
      throw new Error(`Unhandled note: ${note satisfies never}`);
  }
}

export function MachineSummary({ machine }: { readonly machine: Machine }): JSX.Element {
  const { t } = useT();
  const found = foundLine(t, machine);
  const note = noteLine(t, machine);
  const refused = machine.choices.length === 0;
  return (
    <div className="firstrun__machine">
      {found && <p>{found}</p>}
      {note && <p className={refused ? 'firstrun__refused' : 'firstrun__note'}>{note}</p>}
    </div>
  );
}
