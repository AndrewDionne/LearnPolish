import { useRef } from 'react';
import type { LessonItem } from '../model';
import { prepareAssessmentInput } from './format';
import { useSpeechCapture } from './useSpeechCapture';

type Props = {
  item: LessonItem;
  playing: string | null;
  onPlayReference: (path: string) => void;
  onStopReference: () => void;
  onNext: () => void;
};

export default function SpeakPanel({item, playing, onPlayReference, onStopReference, onNext}: Props) {
  const preview = useRef<HTMLAudioElement | null>(null);
  const capture = useSpeechCapture(() => {
    preview.current?.pause();
    onStopReference();
  });
  const prepared = capture.wav && capture.check
    ? prepareAssessmentInput(item.id, item.polish, {wav: capture.wav, check: capture.check})
    : null;

  const onReference = () => {
    preview.current?.pause();
    if (item.audio) onPlayReference(item.audio);
  };

  return <section className="flashcard speak-panel" aria-live="polite">
    <span className="card-label">SAY IT IN POLISH</span>
    <h2 lang="pl" className="speak-prompt">{item.polish}</h2>
    <p className="speak-translation">{item.english}</p>
    {item.audio
      ? <button type="button" className="audio-btn" disabled={capture.phase === 'requesting' || capture.phase === 'recording' || capture.phase === 'processing'} onClick={onReference}>
          {playing === item.audio ? 'Playing example' : '▶ Hear native example'}
        </button>
      : <p className="speak-subtle">No reference audio is available for this personal lesson yet.</p>}
    <div className="speak-divider"/>
    <p className="speak-instruction">Listen to the example, then record yourself. This preview does not grade pronunciation.</p>
    {capture.phase === 'idle' || capture.phase === 'error' || capture.phase === 'inconclusive' || capture.phase === 'ready'
      ? <button type="button" className="record-button" onClick={() => void capture.start()}>● {capture.previewUrl ? 'Record another take' : 'Start recording'}</button>
      : null}
    {capture.phase === 'requesting' && <p role="status" className="speak-status">Requesting microphone permission…</p>}
    {capture.phase === 'recording' && <>
      <p role="status" className="speak-status recording-dot">● Recording… Speak clearly (maximum 10 seconds).</p>
      <button type="button" className="record-button stop-button" onClick={capture.stop}>■ Stop recording</button>
    </>}
    {capture.phase === 'processing' && <p role="status" className="speak-status">Checking the recording locally…</p>}
    {capture.phase === 'error' && <p role="alert" className="capture-error">{capture.message}</p>}
    {capture.previewUrl && <div className="speak-replay">
      <label htmlFor="personal-speech-replay">Replay your recording</label>
      <audio id="personal-speech-replay" ref={preview} src={capture.previewUrl} controls preload="metadata"/>
    </div>}
    {capture.phase === 'inconclusive' && <p role="status" className="capture-warning">Recording inconclusive: {capture.message || 'Try again.'}</p>}
    {capture.phase === 'ready' && prepared && <p role="status" className="capture-valid">Recording captured ({capture.check?.seconds.toFixed(1)} s). You can replay it or try again. Pronunciation is not scored yet.</p>}
    <p className="speak-privacy">Your recording stays in this browser's temporary memory. It is discarded when you leave this card; it is not uploaded or stored as progress.</p>
    <button type="button" className="primary-action speak-next" disabled={capture.phase === 'recording' || capture.phase === 'requesting' || capture.phase === 'processing'} onClick={() => {preview.current?.pause(); onNext();}}>Next phrase →</button>
  </section>;
}
