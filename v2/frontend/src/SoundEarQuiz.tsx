import {useState} from 'react';
import type {Lesson} from './model';
import type {SoundListeningCard} from './sound-listening';
import {focusedPolishParts} from './sound-listening';

export default function SoundEarQuiz({lesson,cards,playing,onPlay,onCompare}:{
 lesson:Lesson;
 cards:SoundListeningCard[];
 playing:string|null;
 onPlay:(audio:string)=>void;
 onCompare:()=>void;
}){
 const [index,setIndex]=useState(0);
 const [choice,setChoice]=useState<string|null>(null);
 const done=index>=cards.length;
 const card=cards[index];
 const correct=card?.groupId===choice;
 const answer=card?lesson.soundGroups?.find(group=>group.id===card.groupId):undefined;
 const parts=card?focusedPolishParts(card.item):null;
 return <div className="sound-ear-quiz">
   {done ? <div className="sound-ear-finish" role="status">
     <strong>All recorded examples complete.</strong>
     <div className="sound-ear-actions">
       <button type="button" className="primary-action" onClick={()=>{
         setIndex(0);setChoice(null);
       }}>Practise again</button>
       <button type="button" className="secondary-action" onClick={onCompare}>Compare sounds</button>
     </div>
   </div> : <>
     <div className="sound-ear-progress">{index+1} / {cards.length}</div>
     <p className="sound-ear-prompt">Listen to the recording. Which sound is this example teaching?</p>
     <button type="button" className="audio-btn sound-ear-play" onClick={()=>{
       if(card.item.audio)onPlay(card.item.audio);
     }}>{playing===card.item.audio?'Playing word':'▶ Hear word'}</button>
     <div className="sound-ear-choices" role="group" aria-label="Choose the sound">
       {lesson.soundGroups?.map(group=><button type="button"
         key={group.id} aria-pressed={choice===group.id} disabled={choice!==null}
         className={'sound-ear-choice'+(choice===group.id?' selected':'')}
         onClick={()=>setChoice(group.id)}>{group.label}</button>)}
     </div>
     {choice!==null && <div className="sound-ear-answer" role="status">
       <p>{correct?'Correct.':'This recording demonstrates:'} <strong>{answer?.label}</strong></p>
       <p className="sound-ear-word" lang="pl">
         {parts?<>{parts.before}<strong className="sound-focus-letters">{parts.focus}</strong>{parts.after}</>:card.item.polish}
       </p>
       <button className="primary-action" type="button" onClick={()=>{
         setIndex(i=>i+1);setChoice(null);
       }}>{index===cards.length-1?'Finish':'Next word →'}</button>
     </div>}
   </>}
 </div>;
}
