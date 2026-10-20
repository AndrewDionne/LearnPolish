import { useState } from 'react';
import type { Lesson, MicroDialogue } from './model';
import { AUDIO_RATES } from './audio';
import type { AudioRate } from './audio';

type Props = {
  lesson: Lesson;
  dialogue: MicroDialogue;
  playing: string | null;
  rate: AudioRate;
  audioError: string;
  onRateChange: (rate: AudioRate) => void;
  onPlay: (audio: string) => void;
  onStop: () => void;
  onClose: () => void;
};

/** Manual per-turn playback is deliberate: no spliced audio or invented actor voices. */
export default function MicroDialoguePanel({
  lesson,dialogue,playing,rate,audioError,onRateChange,onPlay,onStop,onClose,
}: Props) {
  const [view,setView] = useState<'read'|'listen'>('read');
  const [revealed,setRevealed] = useState(false);
  const [translated,setTranslated] = useState(false);
  const [answer,setAnswer] = useState<number|null>(null);
  const byId=new Map(lesson.items.map(item=>[item.id,item]));
  const turns=dialogue.turns.map(turn=>({speaker:turn.speaker,item:byId.get(turn.itemId)}));
  if (turns.some(turn=>!turn.item?.audio || turn.item.referenceReview === 'practice_only')) return null;
  const revealPolish=view==='read'||revealed;
  const showTranslationControl=view==='read'||revealed||answer!==null;
  const check=dialogue.comprehension;
  return <section className="micro-dialogue-panel" aria-label={'Short dialogue: '+dialogue.title}>
    <div className="micro-dialogue-heading">
      <div><span className="eyebrow">SHORT CONVERSATION</span><h2>{dialogue.title}</h2>
        <p>{turns.length} turns · two speakers · original recorded lines</p></div>
      <button type="button" className="secondary-action" onClick={()=>{onStop();onClose();}}>Back to reading</button>
    </div>
    <div className="micro-dialogue-view" role="group" aria-label="Dialogue practice style">
      <button type="button" aria-pressed={view==='read'} onClick={()=>{onStop();setView('read');setRevealed(false);setTranslated(false);setAnswer(null);}}>Read dialogue</button>
      <button type="button" aria-pressed={view==='listen'} onClick={()=>{onStop();setView('listen');setRevealed(false);setTranslated(false);setAnswer(null);}}>Listen first</button>
    </div>
    <fieldset className="speed-picker"><legend>Playback speed</legend>
      {AUDIO_RATES.map(speed=><button type="button" key={speed} aria-pressed={rate===speed}
        className={rate===speed?'chosen':''} onClick={()=>onRateChange(speed)}>{speed}×</button>)}
    </fieldset>
    <ol className="micro-dialogue-turns">
      {turns.map(({speaker,item},i)=>item && <li key={item.id} className={'micro-dialogue-turn speaker-'+speaker.toLowerCase()}>
        <div className="micro-dialogue-speaker">{dialogue.speakers[speaker]}</div>
        {revealPolish
          ? <p lang="pl" className="micro-dialogue-polish">{item.polish}</p>
          : <p className="micro-dialogue-hidden">Listen before revealing the words.</p>}
        {translated && <p className="micro-dialogue-english">{item.english}</p>}
        <button type="button" className="audio-btn"
          aria-label={'Play '+dialogue.speakers[speaker]+' turn '+(i+1)}
          onClick={()=>item.audio&&onPlay(item.audio!)}>
          <span aria-hidden="true">{playing===item.audio?'◼':'▶'}</span> {playing===item.audio?'Playing':'Play turn '+(i+1)}
        </button>
      </li>)}
    </ol>
    {audioError && <p role="alert" className="audio-error">{audioError}</p>}
    <fieldset className="micro-dialogue-check">
      <legend>Check understanding</legend>
      <p className="micro-dialogue-question">{check.prompt}</p>
      <div className="micro-dialogue-options" role="group" aria-label="Choose the dialogue answer">
        {check.options.map((option,i)=><button type="button" key={option}
          aria-pressed={answer===i} disabled={answer!==null}
          onClick={()=>{onStop();setAnswer(i);}}>{option}</button>)}
      </div>
      {answer!==null && <p className={answer===check.correctIndex?'answer-good':'answer-review'}
        role="status">{answer===check.correctIndex?'Correct!':'Not quite — listen again.'} {check.feedback}</p>}
    </fieldset>
    <div className="micro-dialogue-actions">
      {view==='listen'&&!revealed&&<button type="button" className="primary-action" onClick={()=>setRevealed(true)}>Reveal Polish dialogue</button>}
      {showTranslationControl&&!translated&&<button type="button" className="secondary-action" onClick={()=>setTranslated(true)}>Show English translations</button>}
      {showTranslationControl&&translated&&<button type="button" className="secondary-action" onClick={()=>setTranslated(false)}>Hide translations</button>}
    </div>
  </section>;
}
