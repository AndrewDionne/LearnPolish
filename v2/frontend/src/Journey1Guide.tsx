import {useState} from 'react';
import type {Journey1GuideStep} from './journey1-guide';
import type {StarterGroup} from './foundation-first-expressions';
import type {RecordedGlyph} from './recorded-alphabet';
import type {SentencePattern} from './foundation-sentence-patterns';
import RecordedSentencePatterns from './RecordedSentencePatterns';
import RecordedAlphabetExplorer from './RecordedAlphabetExplorer';
import type {AudioRate} from './audio';

/** A quiet source-backed guide, not another proficiency or stage label.
 * Only actual existing source lesson and tourist-unit launch actions are shown. */
export default function Journey1Guide({steps,starterGroups,nextWordGroups,sentencePatterns,recordedLetters,recordedCombinations,playing,speed,onSpeed,onPlayAudio,onStarter,onLesson,onUnit}:{
  steps:Journey1GuideStep[];
  starterGroups:StarterGroup[];
  nextWordGroups:StarterGroup[];
  sentencePatterns:SentencePattern[];
  recordedLetters:RecordedGlyph[];
  recordedCombinations:RecordedGlyph[];
  playing:string|null;
  speed:AudioRate;
  onSpeed:(speed:AudioRate)=>void;
  onPlayAudio:(path:string)=>void;
  onStarter:(groupId:string)=>void;
  onLesson:(lessonId:string)=>void;
  onUnit:(unitId:string)=>void;
}){
  const [expanded,setExpanded]=useState(false);
  const [moreWordsVisible,setMoreWordsVisible]=useState(false);
  if(!steps.length)return null;
  const visible=expanded?steps:steps.slice(0,4);
  return <section className="foundation-guide" aria-label="Guided Polish foundations">
    <div className="foundation-guide-top">
      <h3>Start with the essentials</h3>
      <button type="button" className="foundation-guide-expand"
        onClick={()=>setExpanded(x=>!x)}>
        {expanded?'Show less':'See all 20 steps'} →
      </button>
    </div>
    <RecordedAlphabetExplorer letters={recordedLetters} combinations={recordedCombinations}
      playing={playing} speed={speed} onSpeed={onSpeed} onPlay={onPlayAudio}/>
    {starterGroups.length>0 && <div className="foundation-starter" role="group" aria-label="First expressions practice">
      <div className="foundation-starter-heading">Practice eight everyday expressions</div>
      <div className="foundation-starter-options">
        {starterGroups.map(group=><button type="button" key={group.id}
          className="foundation-starter-button" onClick={()=>onStarter(group.id)}>
          <strong>{group.title}</strong><span>{group.itemIds.length} phrases →</span>
        </button>)}
      </div>
    </div>}
    {nextWordGroups.length>0 && <div className="foundation-starter foundation-next-words">
      <button type="button" className="foundation-next-toggle"
        aria-expanded={moreWordsVisible}
        onClick={()=>setMoreWordsVisible(open=>!open)}>
        <span>Keep building your everyday vocabulary</span>
        <span aria-hidden="true">{moreWordsVisible?'−':'+'}</span>
      </button>
      {moreWordsVisible && <div id="foundation-next-words" className="foundation-starter-options"
        role="group" aria-label="More recorded beginner practice">
        {nextWordGroups.map(group=><button type="button" key={group.id}
          className="foundation-starter-button" onClick={()=>onStarter(group.id)}>
          <strong>{group.title}</strong><span>{group.itemIds.length} expressions →</span>
        </button>)}
      </div>}
    </div>}
    <RecordedSentencePatterns patterns={sentencePatterns} playing={playing} onPlay={onPlayAudio}/>
    <div className="foundation-guide-list">
      {visible.map((step,index)=><button type="button" key={step.id}
        className="foundation-guide-step"
        onClick={()=>step.type==='foundation'?onLesson(step.lessonId):onUnit(step.unitId)}>
        <span className="foundation-guide-number" aria-hidden="true">
          {String(index+1).padStart(2,'0')}
        </span>
        <span className="foundation-guide-title">{step.title}</span>
        <span className="foundation-guide-arrow" aria-hidden="true">→</span>
      </button>)}
    </div>
  </section>;
}
