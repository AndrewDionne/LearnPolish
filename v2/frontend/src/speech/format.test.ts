import { describe, expect, test } from 'vitest';
import { encodePcm16Wav, inspectPcm16, preferredRecordingMime, prepareAssessmentInput } from './format';

describe('Polish speech capture format and confidence', () => {
  test('selects supported MIME type rather than hardcoding WebM for Safari', () => {
    expect(preferredRecordingMime(value => value === 'audio/mp4')).toBe('audio/mp4');
    expect(preferredRecordingMime(value => value === 'audio/webm;codecs=opus')).toBe('audio/webm;codecs=opus');
    expect(preferredRecordingMime(() => false)).toBe('');
  });
  test('short recording, silence, clipping are inconclusive, never zero points', () => {
    expect(inspectPcm16(new Int16Array(1600)).quality).toBe('inconclusive');
    expect(inspectPcm16(new Int16Array(16000)).reason).toMatch(/little sound/);
    expect(inspectPcm16(new Int16Array(16000).fill(32767)).reason).toMatch(/distorted/);
    const samples = Int16Array.from({length:16000}, (_,i)=>Math.round(5000*Math.sin(i/8)));
    const result = inspectPcm16(samples);
    expect(result.quality).toBe('usable');
    expect(result.sampleRate).toBe(16000);
    expect(result.seconds).toBe(1);
  });
  test('10-second server limit agrees with local preview before any upload', () => {
    const usable = (seconds:number) => inspectPcm16(
      Int16Array.from({length:Math.round(seconds*16000)},(_,i)=>Math.round(5000*Math.sin(i/11)))
    );
    expect(usable(0.6).quality).toBe('usable');
    expect(usable(10).quality).toBe('usable');
    expect(usable(10.01).quality).toBe('inconclusive');
    expect(usable(10.01).reason).toMatch(/too long/);
    expect(prepareAssessmentInput('lesson:0','Dzień dobry',{
      wav:encodePcm16Wav(new Int16Array([1,2])),
      check:usable(10.01),
    })).toBeNull();
  });
  test('WAV byte structure exactly matches mono 16kHz PCM16', async () => {
    const blob = encodePcm16Wav(new Int16Array([1,-2,32767,-32768]));
    const b = new DataView(await blob.arrayBuffer());
    expect(b.getUint32(24,true)).toBe(16000);
    expect(b.getUint16(22,true)).toBe(1);
    expect(b.getUint32(40,true)).toBe(8);
    expect(b.getInt16(46,true)).toBe(-2);
  });
  test('only usable captures can become future assessment input', () => {
    const wav = encodePcm16Wav(new Int16Array(16000));
    const good = {wav, check: inspectPcm16(Int16Array.from({length:16000},(_,i)=>Math.round(3000*Math.sin(i/10))))};
    expect(prepareAssessmentInput('lesson:1','cześć',good)?.schemaVersion).toBe(1);
    expect(prepareAssessmentInput('lesson:1','cześć',{wav,check:inspectPcm16(new Int16Array(16000))})).toBeNull();
  });
});
