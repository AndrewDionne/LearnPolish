import {useState} from 'react';
import type {ReadingIntroductionTurn} from './reading-introduction';

/** Lesson-internal teaching, not graded read/listen assessment or duplicated XP.
 * Whole existing recorded lines and original meanings, sequentially introduced
 * BEFORE the same source turns are tested in Read/Listen. */
export default function RecordedReadingIntroduction({turns,playing,onPlay}:{
 turns:ReadingIntroductionTurn[];playing:string|null;onPlay:(path:string)=>void;
}){
 const [expanded,setExpanded]=useState(true);
 const [index,setIndex]=useState(0);
 if(!turns.length)return null;
 const item=turns[index];
 return <section className="reading-intro" aria-label="Learn this conversation first">
   <button type="button" className="reading-intro-toggle"
     aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>
     <span>Learn this conversation first</span>
     <span aria-hidden="true">{expanded?'−':'+'}</span>
   </button>
   {expanded && <div className="reading-intro-content">
     <div className="reading-intro-progress">{index+1} / {turns.length}</div>
     <div className="reading-intro-polish" lang="pl">{item.polish}</div>
     <div className="reading-intro-english">{item.english}</div>
     {item.teachingCue && <p className="reading-intro-cue">{item.teachingCue}</p>}
     <div className="reading-intro-actions">
       <button type="button" onClick={()=>onPlay(item.audio)} className="reading-intro-audio">
         {playing===item.audio?'Playing line':'▶ Hear line'}
       </button>
       <button type="button" className="reading-intro-next"
         onClick={()=>index===turns.length-1?setExpanded(false):setIndex(v=>v+1)}>
         {index===turns.length-1?'Start reading →':'Next line →'}
       </button>
       {index>0&&<button type="button" className="reading-intro-back"
         onClick={()=>setIndex(v=>v-1)}>Previous</button>}
     </div>
     <button type="button" className="reading-intro-skip"
       onClick={()=>setExpanded(false)}>Read conversation now</button>
   </div>}
 </section>;
}
