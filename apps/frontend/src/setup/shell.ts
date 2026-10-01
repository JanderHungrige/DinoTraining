/**
 * The setup screen's line to the Tauri shell (doc 127): the only place the frontend
 * calls `setup_status` / `setup_install` or listens to `setup-progress`.
 *
 * Types mirror `setup.rs` and `progress.rs`. Outside the shell (the web dev mode) there
 * is nothing to install, and `setupStatus()` says so.
 */

export type Variant = 'cpu' | 'cu126' | 'cu130';

export interface Choice {
  readonly variant: Variant;
  readonly download_gb: number;
  readonly disk_gb: number;
}

export type Note =
  | { readonly kind: 'intel_mac' }
  | { readonly kind: 'unsupported_platform'; readonly os: string; readonly arch: string }
  | { readonly kind: 'driver_too_old'; readonly driver: string; readonly needed: number };

export interface Machine {
  readonly os: string;
  readonly arch: string;
  readonly apple_silicon: boolean;
  readonly gpu: { readonly name: string; readonly driver: string } | null;
  /** Recommended first; empty when the machine is refused. */
  readonly choices: readonly Choice[];
  readonly note: Note | null;
}

export interface SetupStatus {
  readonly needed: boolean;
  readonly machine: Machine | null;
  /** `DINO_SETUP_AUTO`: install this variant without waiting for a click. */
  readonly auto: Variant | null;
  /** Doc 129: an environment from an older lock exists; its variant. */
  readonly update: Variant | null;
}

export type SetupFailure =
  | { readonly kind: 'unsupported' }
  | { readonly kind: 'disk'; readonly needed_gb: number; readonly free_gb: number; readonly path: string }
  | { readonly kind: 'offline' }
  | { readonly kind: 'failed'; readonly message: string }
  /** Doc 128: a switch failed and the previous variant was put back. */
  | { readonly kind: 'rolled_back'; readonly to: Variant; readonly reason: SetupFailure }
  /** Doc 141: Windows' Visual C++ runtime is too old for PyTorch and was not installed. */
  | {
      readonly kind: 'vc_runtime';
      readonly found: string | null;
      readonly reason: VcRuntimeReason;
      readonly code: number | null;
    };

export type VcRuntimeReason = 'declined' | 'unsigned' | 'download' | 'installer' | 'still_old';

/** Doc 141: what PyTorch needs, and where Microsoft offers it. */
export const VC_RUNTIME = { minimum: '14.40', url: 'https://aka.ms/vs/17/release/vc_redist.x64.exe' } as const;

/** Doc 128: what is installed, and what this machine could take. */
export interface RuntimeStatus {
  readonly variant: Variant | null;
  readonly machine: Machine;
}

/** CUDA version per GPU variant, for labels. */
export const CUDA_VERSION: Readonly<Record<Variant, string | null>> = { cpu: null, cu126: '12.6', cu130: '13.0' };

export type Phase = 'runtime' | 'python' | 'packages' | 'installing' | 'done';

export interface Progress {
  readonly phase: Phase;
  readonly done_mb: number;
  readonly total_mb: number;
  readonly current: string | null;
}

export const PROGRESS_EVENT = 'setup-progress';

/** True inside the desktop app's webview. */
export function inShell(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

const NOT_NEEDED: SetupStatus = { needed: false, machine: null, auto: null, update: null };

export async function setupStatus(): Promise<SetupStatus> {
  if (!inShell()) return NOT_NEEDED;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<SetupStatus>('setup_status');
}

function isSetupFailure(value: unknown): value is SetupFailure {
  return typeof value === 'object' && value !== null && 'kind' in value;
}

async function invokeInstall(command: string, variant: Variant): Promise<void> {
  const { invoke } = await import('@tauri-apps/api/core');
  try {
    await invoke(command, { variant });
  } catch (error) {
    if (isSetupFailure(error)) throw error;
    const failure: SetupFailure = { kind: 'failed', message: String(error) };
    throw failure;
  }
}

/** Resolves when the backend answers; rejects with a {@link SetupFailure}. */
export function setupInstall(variant: Variant): Promise<void> {
  return invokeInstall('setup_install', variant);
}

/** Doc 128: exchange PyTorch for `variant`; resolves when the backend answers again. */
export function switchVariant(variant: Variant): Promise<void> {
  return invokeInstall('switch_variant', variant);
}

/** Doc 129: start on the previous packages after a failed update. */
export async function startPrevious(): Promise<void> {
  const { invoke } = await import('@tauri-apps/api/core');
  try {
    await invoke('start_previous');
  } catch (error) {
    if (isSetupFailure(error)) throw error;
    const failure: SetupFailure = { kind: 'failed', message: String(error) };
    throw failure;
  }
}

/** Doc 128: null outside the packaged app (a checkout manages its own environment). */
export async function runtimeStatus(): Promise<RuntimeStatus | null> {
  if (!inShell()) return null;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<RuntimeStatus | null>('runtime_status');
}

export type Step = 'shown' | 'installing' | 'starting' | 'resuming' | 'ready' | 'opened' | 'failed';

/** Note a step of the setup screen in the app log. Never fails the screen. */
export function report(step: Step): void {
  if (!inShell()) return;
  void import('@tauri-apps/api/core')
    .then(({ invoke }) => invoke('setup_report', { step }))
    .catch((error: unknown) => console.warn('setup_report failed', error));
}

/** Subscribe to install progress; returns the unsubscribe function. */
export async function onProgress(handler: (progress: Progress) => void): Promise<() => void> {
  const { listen } = await import('@tauri-apps/api/event');
  return listen<Progress>(PROGRESS_EVENT, (event) => handler(event.payload));
}

/** Python comes first and alone, before uv announces the packages: its own first slice. */
const PYTHON_SHARE = 10;

/**
 * 0–100, for the bar. Python fills the first tenth; after it, megabytes done of all
 * announced — which starts near the same point, because Python is part of that total.
 */
export function percent(progress: Progress | null): number {
  if (progress === null || progress.total_mb <= 0) return 0;
  if (progress.phase === 'done') return 100;
  if (progress.phase === 'installing') return 97;
  const share = progress.done_mb / progress.total_mb;
  if (progress.phase === 'python') return Math.round(share * PYTHON_SHARE);
  return Math.min(95, Math.max(PYTHON_SHARE, Math.round(share * 95)));
}
