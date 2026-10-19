/** Microphone failures are local browser/macOS access issues, never Azure errors. */
export type MicrophonePermission = PermissionState | 'unknown';

export async function readMicrophonePermission(): Promise<MicrophonePermission> {
  try {
    // Query is silent: never triggers a permission prompt or opens a mic.
    const permission = await navigator.permissions?.query({name: 'microphone' as PermissionName});
    return permission?.state === 'granted' || permission?.state === 'denied' || permission?.state === 'prompt'
      ? permission.state : 'unknown';
  } catch {
    // Safari or managed browser configurations can reject Permission API.
    return 'unknown';
  }
}

export function microphoneFailureMessage(errorName: string, permission: MicrophonePermission): string {
  if (errorName === 'NotAllowedError' || errorName === 'PermissionDeniedError') {
    if (permission === 'granted') {
      return 'This site already has microphone permission, but the browser could not open the microphone. On macOS, check System Settings → Privacy & Security → Microphone and enable your browser. Then quit the browser completely (⌘Q), reopen it, and check System Settings → Sound → Input.';
    }
    if (permission === 'denied') {
      return 'The browser reports microphone access is blocked for this exact site. Open the address-bar Site settings for this page, change Microphone to Allow, reload, and try recording again.';
    }
    return 'The browser could not open the microphone. Check this exact site in browser Microphone settings AND your browser in macOS System Settings → Privacy & Security → Microphone. Quit and reopen the browser after changing macOS permission.';
  }
  if (errorName === 'NotFoundError' || errorName === 'DevicesNotFoundError') {
    return 'No working microphone was found. Connect one or select a microphone in macOS System Settings → Sound → Input, then try again.';
  }
  if (errorName === 'NotReadableError' || errorName === 'TrackStartError' || errorName === 'AbortError') {
    return 'The browser has access but could not start the microphone. Check macOS Sound → Input, disconnect and reconnect an external mic, and close apps that may have taken exclusive access.';
  }
  if (errorName === 'OverconstrainedError' || errorName === 'ConstraintNotSatisfiedError') {
    return 'The selected microphone could not satisfy the recording settings. Try another input device in macOS System Settings → Sound → Input.';
  }
  if (errorName === 'SecurityError') {
    return 'Microphone capture is blocked by the browser security policy. Open the app directly on http://127.0.0.1:5194 or use HTTPS, not an embedded frame.';
  }
  return 'Microphone recording could not start. Check the browser site permission and macOS Sound → Input, then try again.';
}
