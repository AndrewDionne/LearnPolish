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
  guideVisible: boolean;
  onGuideChange: (visible: boolean) => void;
  onAssess?: (capture: AssessmentReadyCapture, signal: AbortSignal) => Promise<SpeechFeedback>;
};

export default function SpeakPanel({item, playing, onPlayReference, onStopReference, onNext, guideVisible, onGuideChange, onAssess}: Props) {
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

  const hasGuide = Boolean(item.pronunciationGuide || item.pronunciation);
  const expandedGuide = guideVisible && hasGuide;
  const guide = item.pronunciationGuide;

  return <section className="flashcard speak-panel" aria-live="polite">
    <div className="speak-card-top">
      <p className="speak-meaning">{item.english}</p>
      {hasGuide && <button
        type="button"
        className="speak-guide-toggle"
        aria-pressed={expandedGuide}
        aria-controls="speak-word-guide"
        onClick={() => onGuideChange(!guideVisible)}
      >Pronunciation guide <span aria-hidden="true">{expandedGuide ? 'On' : 'Off'}</span></button>}
    </div>
    <div id="speak-word-guide" className="speak-word-stage">
      <h2 lang="pl" className={'speak-prompt' + (expandedGuide && guide ? ' with-guide' : '')}>
        {expandedGuide && guide ? <span className="speak-guided-word" aria-label={item.polish}>
          {guide.syllables.map((part, index) => <span className={'speak-word-segment' + (index === guide.stressIndex ? ' stressed' : '')} key={index}>
            <span className="speak-word-polish">{part.polish}</span>
            <span className="speak-word-english" lang="en">{part.englishCue}</span>
          </span>)}
        </span> : item.polish}
      </h2>
      {expandedGuide && !guide && item.pronunciation && <p className="speak-english-fallback">Approximate English sounds: <strong>{item.pronunciation}</strong></p>}
      {expandedGuide && guide && <p className="speak-guide-caption">English approximation · Emphasis marks the stressed syllable</p>}
    </div>
    {item.audio && <button type="button" className="audio-btn speak-audio-button"
      disabled={capture.phase === 'requesting' || capture.phase === 'recording' || capture.phase === 'processing'}
      onClick={onReference}>{playing === item.audio ? 'Playing example' : '▶ Hear example'}</button>}
    <div className="speak-record-actions">
      {capture.phase === 'idle' || capture.phase === 'error' || capture.phase === 'inconclusive' || capture.phase === 'ready'
        ? <button type="button" className="record-button" onClick={startNewTake}>● {capture.previewUrl ? 'Record another take' : 'Start recording'}</button>
        : null}
      {capture.phase === 'requesting' && <p role="status" className="speak-status">Requesting microphone permission…</p>}
      {capture.phase === 'recording' && <>
        <p role="status" className="speak-status recording-dot">● Recording…</p>
        <button type="button" className="record-button stop-button" onClick={capture.stop}>■ Stop recording</button>
      </>}
      {capture.phase === 'processing' && <p role="status" className="speak-status">Checking recording…</p>}
      {capture.phase === 'error' && <p role="alert" className="capture-error">{capture.message}</p>}
      {capture.previewUrl && <div className="speak-replay">
        <label htmlFor="personal-speech-replay">Replay your recording</label>
        <audio id="personal-speech-replay" ref={preview} src={capture.previewUrl} controls preload="metadata"/>
      </div>}
      {capture.phase === 'inconclusive' && <p role="status" className="capture-warning">Recording inconclusive: {capture.message || 'Try again.'}</p>}
      {capture.phase === 'ready' && prepared && <p role="status" className="capture-valid">Recording captured ({capture.check?.seconds.toFixed(1)} s).</p>}
      {onAssess && prepared && capture.phase === 'ready' && <div className="speak-feedback">
        <button type="button" className="secondary-action" disabled={assessmentBusy} onClick={() => void assessTake()}>
          {assessmentBusy ? 'Checking with Azure…' : 'Check my pronunciation'}
        </button>
        <p className="speak-assessment-consent">Optional. Sends this recording to Azure for estimated feedback; no score history is saved.</p>
        {assessmentBusy && <p role="status">Sending this take to Azure…</p>}
        {assessmentError && <p role="alert" className="capture-warning">{assessmentError}</p>}
        {feedback?.status === 'inconclusive' && <p role="status" className="capture-warning">{feedback.reason} This is not a score of zero.</p>}
        {feedback?.timing && <p className="speak-latency" role="status">
          Feedback arrived in {(feedback.timing.roundTripMs / 1000).toFixed(1)} s
          {feedback.timing.sdkMs !== undefined ? ' (Azure SDK call ' + (feedback.timing.sdkMs / 1000).toFixed(1) + ' s)' : ''}.
          {feedback.timing.roundTripMs >= 10000 ? ' That delay is longer than our target; recording and replay still work.' : ''}
        </p>}
        {feedback?.status === 'ok' && <div className="speak-scores" role="status">
          <strong>Azure pronunciation estimate</strong>
          <dl>
            <div><dt>Accuracy</dt><dd>{feedback.scores.accuracy.toFixed(1)} / 100</dd></div>
            <div><dt>Fluency</dt><dd>{feedback.scores.fluency.toFixed(1)} / 100</dd></div>
            <div><dt>Completeness</dt><dd>{feedback.scores.completeness.toFixed(1)} / 100</dd></div>
          </dl>
          <details className="speak-score-explanation"><summary>About these scores</summary>
            <p>Provider estimates are not calibrated against Polish speakers, are not pass/fail grades, and do not identify which Polish sound needs improvement.</p>
          </details>
        </div>}
      </div>}
    </div>
    <button type="button" className="primary-action speak-next" disabled={capture.phase === 'recording' || capture.phase === 'requesting' || capture.phase === 'processing'} onClick={() => {abortAssessment(); preview.current?.pause(); onNext(!!prepared);}}>Next</button>
    <details className="speak-private-details">
      <summary>Privacy &amp; options</summary>
      <p>Recordings stay temporarily on this device while you practise. Nothing is uploaded unless you choose Check my pronunciation, which sends one take to Azure. No recording or score is kept in your family history.</p>
      {!item.audio && <p>No native example is available for this word yet.</p>}
      {prepared && <button type="button" className="benchmark-export" onClick={() => {
        // Explicit private research download; never upload or retain silently.
        const url = URL.createObjectURL(prepared.wav);
        const a = document.createElement('a');
        a.href = url;
        a.download = researchWavFilename(prepared.itemId, new Date().toISOString());
        document.body.appendChild(a); a.click(); a.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 0);
      }}>Save private WAV</button>}
    </details>
  </section>;
}
