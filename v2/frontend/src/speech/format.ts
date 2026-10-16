/**
 * Speech capture interchange contract: local-only, not a pronunciation score.
 * Encoders may emit WebM/Opus, Ogg, or MP4/AAC; browser-decoded PCM is
 * deterministically resampled to mono PCM16 16 kHz for future engine adapters.
 */
export type CaptureQuality = 'usable' | 'inconclusive';
export type AcousticCheck = {
  quality: CaptureQuality;
  reason: string;
  seconds: number;
  rms: number;
  clippedFraction: number;
  sampleRate: 16000;
};

export function preferredRecordingMime(available: (mime: string) => boolean): string {
  // Safari generally favours MP4, Chromium generally favours WebM.
  const options = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm', 'audio/ogg;codecs=opus'];
  return options.find(available) ?? '';
}

export function inspectPcm16(samples: Int16Array, sampleRate = 16000): AcousticCheck {
  if (sampleRate <= 0 || !Number.isFinite(sampleRate)) throw new Error('Invalid sample rate');
  const seconds = samples.length / sampleRate;
  let power = 0;
  let clipped = 0;
  for (const pcm of samples) {
    const normalized = pcm / 32768;
    power += normalized * normalized;
    if (Math.abs(pcm) >= 32500) clipped++;
  }
  const rms = samples.length ? Math.sqrt(power / samples.length) : 0;
  const clippedFraction = samples.length ? clipped / samples.length : 0;
  let reason = '';
  if (seconds < 0.6) reason = 'Recording is too short. Say the full phrase and try again.';
  else if (seconds > 12) reason = 'Recording is too long. Try a shorter phrase.';
  else if (rms < 0.008) reason = 'Very little sound was detected. Move closer to your microphone.';
  else if (clippedFraction > 0.02) reason = 'Recording is distorted. Move farther from the microphone.';
  return { quality: reason ? 'inconclusive' : 'usable', reason, seconds, rms, clippedFraction, sampleRate: 16000 };
}

export function monoPcm16(buffer: AudioBuffer): Int16Array {
  if (!buffer.numberOfChannels || !buffer.length || !buffer.sampleRate) return new Int16Array(0);
  const length = Math.round(buffer.duration * 16000);
  const channels = Array.from({length: buffer.numberOfChannels}, (_, c) => buffer.getChannelData(c));
  const result = new Int16Array(length);
  for (let i = 0; i < length; i++) {
    const position = i * buffer.sampleRate / 16000;
    const left = Math.min(Math.floor(position), buffer.length - 1);
    const right = Math.min(left + 1, buffer.length - 1);
    const fraction = position - left;
    let mixed = 0;
    for (const channel of channels) {
      mixed += channel[left] * (1 - fraction) + channel[right] * fraction;
    }
    const scaled = Math.min(1, Math.max(-1, mixed / channels.length));
    result[i] = scaled < 0 ? Math.round(scaled * 32768) : Math.round(scaled * 32767);
  }
  return result;
}

export function encodePcm16Wav(samples: Int16Array): Blob {
  const bytes = new ArrayBuffer(44 + 2 * samples.length);
  const view = new DataView(bytes);
  const name = 'RIFF';
  for (let i = 0; i < 4; i++) view.setUint8(i, name.charCodeAt(i));
  view.setUint32(4, bytes.byteLength - 8, true);
  'WAVE'.split('').forEach((c, i) => view.setUint8(8 + i, c.charCodeAt(0)));
  'fmt '.split('').forEach((c, i) => view.setUint8(12 + i, c.charCodeAt(0)));
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, 16000, true);
  view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  'data'.split('').forEach((c, i) => view.setUint8(36 + i, c.charCodeAt(0)));
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, i) => view.setInt16(44 + i * 2, sample, true));
  return new Blob([bytes], {type: 'audio/wav'});
}

export async function normalizeRecording(blob: Blob): Promise<{ wav: Blob; check: AcousticCheck }> {
  const context = new AudioContext();
  try {
    const bytes = await blob.arrayBuffer();
    const decoded = await context.decodeAudioData(bytes);
    const pcm = monoPcm16(decoded);
    return {wav: encodePcm16Wav(pcm), check: inspectPcm16(pcm)};
  } finally {
    await context.close();
  }
}

/** Frozen initial contract. A remote provider adapter is deliberately absent. */
export type AssessmentReadyCapture = {
  schemaVersion: 1;
  itemId: string;
  referencePolish: string;
  wav: Blob;
  check: AcousticCheck;
};

export function prepareAssessmentInput(itemId: string, referencePolish: string, normalized: {wav: Blob; check: AcousticCheck}): AssessmentReadyCapture | null {
  if (!itemId || !referencePolish.trim() || normalized.check.quality !== 'usable') return null;
  if (normalized.wav.type !== 'audio/wav') return null;
  return {schemaVersion: 1, itemId, referencePolish, wav: normalized.wav, check: normalized.check};
}
