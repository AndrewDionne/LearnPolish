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
  onPlayExcerpt: (path:string,startMs:number,endMs:number) => void;
  onStopReference: () => void;
  onNext: (completedTake: boolean) => void;
  guideVisible: boolean;
  onGuideChange: (visible: boolean) => void;
  onPracticeSound?: () => void;
  blended?: boolean;
  onAssess?: (capture: AssessmentReadyCapture, signal: AbortSignal) => Promise<SpeechFeedback>;
};

export default function SpeakPanel({item, playing, onPlayReference, onPlayExcerpt, onStopReference, onNext, guideVisible, onGuideChange, onPracticeSound, blended=false, onAssess}: Props) {
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
    // A React state update is not synchronous. Claim the request via the
    // ref before any await, so two clicks in the same event loop cannot
    // abort/restart a provider-bound upload and consume a second allowance.
    if(!onAssess || !prepared || assessmentBusy || activeRequest.current)return;
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
    if (item.audio && item.referenceReview !== 'practice_only') onPlayReference(item.audio);
  };

  const guideParts=item.syllableAudio?.segments??item.pronunciationSegments?.segments;
  const hasGuide = Boolean(item.pronunciationGuide || item.pronunciation || (guideParts?.length??0)>1);
  const expandedGuide = guideVisible && hasGuide;
  const guide = item.pronunciationGuide;
  // The learner surface never converts experimental syllable scores into per-part grades.
  // Exact-match blended colour hints are displayed on the word itself, without diagnostic panels.
  const hintResult = feedback?.status === 'ok' && feedback.engine === 'azure-whisper-blend-v1'
    ? feedback.colourHints : null;
  // The server groups must match exactly the SAME authored/draft V2 item.
  // Do not colour if a response belongs to a different word or segmentation.
  const colourParts = hintResult && item.pronunciationSegments &&
    hintResult.reference === item.polish &&
    hintResult.segments.length === item.pronunciationSegments.segments.length &&
    hintResult.segments.every((part,i)=>part.polish === item.pronunciationSegments?.segments[i])
    ? hintResult.segments : null;

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
        {colourParts ? <span className="speak-blended-word" aria-label={item.polish}>
          {colourParts.map((part,i)=><span key={i}
            className={'speak-blended-segment'+(guide?.stressIndex===i?' stressed':'')}>
            <span className={'speak-blended-part '+part.hint} aria-label={part.polish}>{part.polish}</span>
            {expandedGuide && guide?.syllables[i]?.polish===part.polish &&
              <span className="speak-word-english" lang="en">{guide.syllables[i].englishCue}</span>}
          </span>)}
        </span> : expandedGuide && guide ? <span className="speak-guided-word" aria-label={item.polish}>
          {guide.syllables.map((part, index) => {
            return <span className={'speak-word-segment' + (index === guide.stressIndex ? ' stressed' : '')} key={index}>
              <span className="speak-word-polish">{part.polish}</span>
              <span className="speak-word-english" lang="en">{part.englishCue}</span>
            </span>;
          })}
        </span> : expandedGuide && guideParts && guideParts.length>1
          ? <span className="speak-guided-word" aria-label={item.polish}>
            {guideParts.map((part,index)=>{
              const value=typeof part==='string'?part:part.polish;
              return <span className="speak-word-segment" key={index}>
                <span className="speak-word-polish">{value}</span>
              </span>;
            })}
          </span>
          : item.polish}
      </h2>
      {expandedGuide && item.syllableAudio && item.audio===item.syllableAudio.audio &&
        <div className="syllable-audio-controls" role="group" aria-label="Recorded syllable playback">
          {item.syllableAudio.segments.map((part,index)=><button type="button" key={index}
            className="pronunciation-audio-part"
            aria-label={'Play syllable '+(index+1)+': '+part.polish.trim()}
            disabled={capture.phase==='requesting'||capture.phase==='recording'||capture.phase==='processing'}
            onClick={()=>{
              preview.current?.pause();
              onPlayExcerpt(item.syllableAudio!.audio,part.startMs,part.endMs);
            }}>{part.polish}</button>)}
        </div>}
      {expandedGuide && !guide && item.pronunciation && <p className="speak-english-fallback">{item.pronunciation}</p>}
    </div>
    {item.referenceReview === 'practice_only' && <p className="speak-reference-pending">Reference audio unavailable.</p>}
    {item.audio && item.referenceReview !== 'practice_only' && <button type="button" className="audio-btn speak-audio-button"
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
        <audio id="personal-speech-replay" aria-label="Replay your recording" ref={preview} src={capture.previewUrl} controls preload="metadata"/>
      </div>}
      {capture.phase === 'inconclusive' && <p role="status" className="capture-warning">Recording inconclusive: {capture.message || 'Try again.'}</p>}
      {capture.phase === 'ready' && prepared && <p role="status" className="capture-valid">Recording ready</p>}
      {onAssess && prepared && capture.phase === 'ready' && <div className="speak-feedback">
        <button type="button" className="secondary-action" disabled={assessmentBusy} onClick={() => void assessTake()}>
          {assessmentBusy ? 'Checking pronunciation…' : 'Check my pronunciation'}
        </button>
        <p className="speak-assessment-consent">Sends this take to {blended ? 'Azure and Groq Whisper' : 'Azure'} only when selected. Audio and scores are not saved.</p>
        {assessmentBusy && <p role="status">Sending this take to {blended ? 'Azure and Groq Whisper' : 'Azure'}…</p>}
        {assessmentError && <p role="alert" className="capture-warning">{assessmentError}</p>}
        {feedback?.status === 'inconclusive' && <p role="status" className="capture-warning">{feedback.reason} This is not a score of zero.</p>}
        {feedback?.status === 'ok' && feedback.engine === 'azure-whisper-blend-v1' && <div className="speak-scores speak-blend-result" role="status">
          <div className="speak-word-score-primary" aria-label={'Experimental combined score: '+feedback.combined+' out of 100'}>
            <strong>{feedback.combined}</strong><span>/100</span>
          </div>
        </div>}
        {feedback?.status === 'ok' && feedback.engine === 'azure-pl-PL-scripted' && <div className="speak-scores" role="status">
          <span className="speak-score-heading">Pronunciation estimate</span>
          <div className="speak-word-score-primary" aria-label={`Azure word pronunciation accuracy estimate: ${Math.round(feedback.scores.accuracy)} out of 100`}>
            <strong>{Math.round(feedback.scores.accuracy)}</strong><span>/100</span>
          </div>
        </div>}
      </div>}
    </div>
    {onPracticeSound && item.soundPractice && capture.phase === 'ready' && <button type="button" className="sound-practice-link" onClick={onPracticeSound}>Practise {item.soundPractice.label} sounds →</button>}
    <button type="button" className="primary-action speak-next" onClick={() => {abortAssessment(); preview.current?.pause(); onNext(capture.phase === 'ready' && !!prepared);}}>Next</button>
    <details className="speak-private-details">
      <summary>Privacy &amp; options</summary>
      <p>Recordings stay temporarily on this device while you practise. Nothing is uploaded unless you choose Check my pronunciation, which sends one take to {blended ? 'Azure and Groq Whisper' : 'Azure'}. No recording or score is kept in your family history.</p>
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
