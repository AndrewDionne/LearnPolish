import { useEffect, useRef, useState } from 'react';
import type { LessonItem } from '../model';
import { prepareAssessmentInput } from './format';
import type {AssessmentReadyCapture} from './format';
import type {SpeechFeedback} from './assessment';
import { researchWavFilename } from './research';
import { useSpeechCapture } from './useSpeechCapture';

type Props = {
  item: LessonItem;
  playing: string | null;
  onPlayReference: (path: string) => void;
  onStopReference: () => void;
  onNext: (completedTake: boolean) => void;
  onAssess?: (capture: AssessmentReadyCapture, signal: AbortSignal) => Promise<SpeechFeedback>;
};

export default function SpeakPanel({item, playing, onPlayReference, onStopReference, onNext, onAssess}: Props) {
  const preview = useRef<HTMLAudioElement | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const [feedback, setFeedback] = useState<SpeechFeedback | null>(null);
  const [assessmentBusy, setAssessmentBusy] = useState(false);
  const [assessmentError, setAssessmentError] = useState('');
  const abortAssessment = () => {
    activeRequest.current?.abort();
    activeRequest.current = null;
  };
  useEffect(() => () => { activeRequest.current?.abort(); }, []);

  const startNewTake = () => {
    abortAssessment();
    setFeedback(null);
    setAssessmentError('');
    setAssessmentBusy(false);
    void capture.start();
  };

  const capture = useSpeechCapture(() => {
    preview.current?.pause();
    onStopReference();
  });
  const prepared = capture.wav && capture.check
    ? prepareAssessmentInput(item.id, item.polish, {wav: capture.wav, check: capture.check})
    : null;

  const assessTake = async () => {
    if(!onAssess || !prepared || assessmentBusy)return;
    abortAssessment();
    const controller = new AbortController();
    activeRequest.current = controller;
    setFeedback(null);
    setAssessmentError('');
    setAssessmentBusy(true);
    try{
      const response = await onAssess(prepared,controller.signal);
      if(!controller.signal.aborted && activeRequest.current === controller){
        setFeedback(response);
      }
    }catch(error){
      if(!controller.signal.aborted && activeRequest.current === controller){
        setAssessmentError(error instanceof Error ? error.message : 'Assessment unavailable.');
      }
    }finally{
      if(!controller.signal.aborted && activeRequest.current === controller){
        activeRequest.current = null;
        setAssessmentBusy(false);
      }
    }
  };

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
      : <p className="speak-subtle">Native reference audio is not available for this word yet. You can still record and replay your pronunciation.</p>}
    <div className="speak-divider"/>
    <p className="speak-instruction">{item.audio
      ? 'Listen to the Polish example, record yourself, then replay and compare.'
      : 'Read the Polish word, record yourself, and replay to hear your attempt.'}
      {onAssess ? ' Pronunciation feedback is optional.' : ' You can practise without a grade.'}</p>
    {capture.phase === 'idle' || capture.phase === 'error' || capture.phase === 'inconclusive' || capture.phase === 'ready'
      ? <button type="button" className="record-button" onClick={startNewTake}>● {capture.previewUrl ? 'Record another take' : 'Start recording'}</button>
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
    {capture.phase === 'ready' && prepared && <p role="status" className="capture-valid">Recording captured ({capture.check?.seconds.toFixed(1)} s). You can replay it or try again.{!onAssess ? ' Pronunciation is not scored yet.' : ''}</p>}
    {onAssess && prepared && capture.phase === 'ready' && <div className="speak-feedback">
      <p className="speak-instruction">Optional: send this take to Azure Speech for an estimated Polish pronunciation assessment. Your voice is processed by Azure; this app does not keep the recording or a score history. The result is not a certified grade.</p>
      <button type="button" className="secondary-action" disabled={assessmentBusy} onClick={() => void assessTake()}>
        {assessmentBusy ? 'Checking with Azure…' : 'Check my pronunciation'}
      </button>
      {assessmentBusy && <p role="status">Sending this take for pronunciation feedback…</p>}
      {assessmentError && <p role="alert" className="capture-warning">{assessmentError}</p>}
      {feedback?.status === 'inconclusive' && <p role="status" className="capture-warning">{feedback.reason} This is not a score of zero.</p>}
      {feedback?.timing && <p className="speak-latency" role="status">
        Feedback arrived in {(feedback.timing.roundTripMs / 1000).toFixed(1)} s
        {feedback.timing.sdkMs !== undefined ? ' (Azure SDK call ' + (feedback.timing.sdkMs / 1000).toFixed(1) + ' s)' : ''}.
        {feedback.timing.roundTripMs >= 10000 ? ' That delay is longer than our target; your recording and replay still work.' : ''}
      </p>}
      {feedback?.status === 'ok' && <div className="speak-scores" role="status">
        <strong>Azure's estimated pronunciation feedback</strong>
        <dl>
          <div><dt>Accuracy <small>How closely your sounds matched</small></dt><dd>{feedback.scores.accuracy.toFixed(1)} / 100</dd></div>
          <div><dt>Fluency <small>Flow and pauses</small></dt><dd>{feedback.scores.fluency.toFixed(1)} / 100</dd></div>
          <div><dt>Completeness <small>How much of the phrase was heard</small></dt><dd>{feedback.scores.completeness.toFixed(1)} / 100</dd></div>
        </dl>
        <p>These provider scores have not been calibrated against Polish speakers or learners. They are not a pass/fail grade, and they cannot identify a specific Polish sound as incorrect.</p>
        <p className="speak-next-step">Listen to the example again, compare it with your recording, and choose whether to retry or move on.</p>
      </div>}
    </div>}
    {prepared && <button type="button" className="benchmark-export" onClick={() => {
      // Explicit learner action; no upload, no server, no silent retention.
      const url = URL.createObjectURL(prepared.wav);
      const a = document.createElement('a');
      a.href = url;
      a.download = researchWavFilename(prepared.itemId, new Date().toISOString());
      document.body.appendChild(a); a.click(); a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    }}>Save 16 kHz WAV for private AI test</button>}
    <p className="speak-privacy">Your recording remains in temporary memory and is discarded when you leave this card. It is not uploaded unless you explicitly choose Check my pronunciation (when available). That assessment sends one take to Azure for processing, not to your family leaderboard, and does not store your score. The optional private benchmark WAV download remains on your device.</p>
    <button type="button" className="primary-action speak-next" disabled={capture.phase === 'recording' || capture.phase === 'requesting' || capture.phase === 'processing'} onClick={() => {abortAssessment(); preview.current?.pause(); onNext(!!prepared);}}>Next phrase →</button>
  </section>;
}
