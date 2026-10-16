/**
 * Private research recording filenames bridge browser WAV capture to the offline
 * reference-verified corpus builder. No voice data is persisted automatically.
 */
const ITEM_ID = /^[A-Za-z0-9_.:-]{1,180}$/;
const ISO_UTC = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/;

export function researchWavFilename(itemId: string, capturedAt: string): string {
  if (!ITEM_ID.test(itemId) || !ISO_UTC.test(capturedAt) ||
      !Number.isFinite(Date.parse(capturedAt))) {
    throw new Error('Invalid private speech recording identity');
  }
  const timestamp = capturedAt.replace(/[-:.]/g, '');
  return 'ptp-speech-v1--' + encodeURIComponent(itemId) + '--' + timestamp + '.wav';
}
