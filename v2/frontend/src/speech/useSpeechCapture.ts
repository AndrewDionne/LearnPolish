import { useEffect, useRef, useState } from 'react';
import { normalizeRecording, preferredRecordingMime } from './format';
import type { AcousticCheck } from './format';
import { microphoneFailureMessage, readMicrophonePermission } from './microphoneError';

export type CapturePhase = 'idle' | 'requesting' | 'recording' | 'processing' | 'ready' | 'inconclusive' | 'error';
export type SpeechCapture = {
  phase: CapturePhase;
  previewUrl: string | null;
  check: AcousticCheck | null;
  wav: Blob | null;
  message: string;
  start: () => Promise<void>;
  stop: () => void;
  reset: () => void;
};

const MAX_RECORDING_MS = 10_000;

export function useSpeechCapture(beforeStart: () => void): SpeechCapture {
  const [phase, setPhase] = useState<CapturePhase>('idle');
  const [message, setMessage] = useState('');
  const [check, setCheck] = useState<AcousticCheck | null>(null);
  const [wav, setWav] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const previewRef = useRef<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<number | null>(null);
  const generation = useRef(0);
  const alive = useRef(true);
  const requesting = useRef(false);

  const closeStream = () => {
    for (const track of streamRef.current?.getTracks() ?? []) track.stop();
    streamRef.current = null;
  };

  const clearTimer = () => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    timerRef.current = null;
  };

  const release = () => {
    generation.current++;
    clearTimer();
    if (recorderRef.current) {
      const recorder = recorderRef.current;
      recorderRef.current = null;
      recorder.ondataavailable = null;
      recorder.onstop = null;
      recorder.onerror = null;
      if (recorder.state !== 'inactive') {
        try { recorder.stop(); } catch { /* device disconnected */ }
      }
    }
    closeStream();
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = null;
    requesting.current = false;
  };

  const reset = () => {
    release();
    setPhase('idle'); setPreviewUrl(null); setMessage(''); setCheck(null); setWav(null);
  };

  const stop = () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === 'inactive') return;
    clearTimer();
    setPhase('processing');
    try { recorder.stop(); }
    catch {
      release();
      setPhase('error');
      setMessage('Recording stopped unexpectedly. Please try again.');
    }
  };

  const start = async () => {
    if (requesting.current || recorderRef.current) return;
    reset();
    const myGeneration = generation.current;
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
        throw new Error('Microphone recording is not supported here. Open this page over HTTPS or localhost in a current browser.');
      }
      beforeStart();
      requesting.current = true;
      setPhase('requesting');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
        video: false,
      });
      if (!alive.current || generation.current !== myGeneration) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      requesting.current = false;
      streamRef.current = stream;
      const mime = preferredRecordingMime(type => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      recorderRef.current = recorder;
      const fragments: Blob[] = [];
      recorder.ondataavailable = event => {
        if (event.data.size) fragments.push(event.data);
      };
      recorder.onerror = () => {
        if (generation.current !== myGeneration || !alive.current) return;
        release(); setPhase('error');
        setMessage('Microphone recording failed. Check permissions and try again.');
      };
      recorder.onstop = () => {
        clearTimer();
        closeStream();
        recorderRef.current = null;
        if (!alive.current || generation.current !== myGeneration) return;
        const blob = new Blob(fragments, {type: recorder.mimeType || fragments[0]?.type || 'application/octet-stream'});
        if (!blob.size) {
          setPhase('inconclusive');
          setMessage('No audio was captured. Try recording again.');
          return;
        }
        const url = URL.createObjectURL(blob);
        previewRef.current = url;
        setPreviewUrl(url);
        setPhase('processing');
        void normalizeRecording(blob).then(output => {
          if (generation.current !== myGeneration || !alive.current) return;
          setCheck(output.check);
          setWav(output.check.quality === 'usable' ? output.wav : null);
          setPhase(output.check.quality === 'usable' ? 'ready' : 'inconclusive');
          setMessage(output.check.reason);
        }).catch(() => {
          if (generation.current !== myGeneration || !alive.current) return;
          setWav(null);
          setPhase('inconclusive');
          setMessage('Your recording can be replayed, but its sound quality could not be verified in this browser.');
        });
      };
      recorder.start();
      setPhase('recording');
      timerRef.current = window.setTimeout(() => stop(), MAX_RECORDING_MS);
    } catch (error) {
      if (!alive.current || generation.current !== myGeneration) return;
      closeStream();
      requesting.current = false;
      const name = error instanceof Error ? error.name : '';
      // NotAllowedError can occur even AFTER site permission was granted,
      // e.g. when macOS denies browser microphone access. Resolve the
      // permission state without opening another mic or prompting again.
      const sitePermission = name === 'NotAllowedError' || name === 'PermissionDeniedError'
        ? await readMicrophonePermission() : 'unknown';
      if (!alive.current || generation.current !== myGeneration) return;
      setPhase('error');
      setMessage(name === 'Error' && error instanceof Error
        ? error.message : microphoneFailureMessage(name, sitePermission));
    }
  };

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      release();
    };
    // The teardown is intentionally tied to this mounted recording session only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {phase, previewUrl, check, wav, message, start, stop, reset};
}
