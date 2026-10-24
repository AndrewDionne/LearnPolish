import {useState} from 'react';
import type {SentencePattern,RecordedSentenceExample} from './foundation-sentence-patterns';

function FocusedSentence({item}:{item:RecordedSentenceExample}){
 const index=item.polish.indexOf(item.focus);
 return <span lang="pl" className="sentence-pattern-polish" aria-label={item.polish}>
   {item.polish.slice(0,index)}<strong>{item.focus}</strong>
   {item.polish.slice(index+item.focus.length)}
 </span>;
}
export default function RecordedSentencePatterns({patterns,playing,onPlay}:{
 patterns:SentencePattern[];playing:string|null;onPlay:(audio:string)=>void;
}){
 const [expanded,setExpanded]=useState(false);
 const [chosen,setChosen]=useState(0);
 const [step,setStep]=useState(0);
 const [phase,setPhase]=useState<'study'|'check'>('study');
 const [answer,setAnswer]=useState<string|null>(null);
 if(!patterns.length)return null;
 const group=patterns[chosen];
 const example=group.examples[step];
 const other=group.examples[(step+1)%group.examples.length];
 const choices=step%2===0?[other.english,example.english]:[example.english,other.english];
 const answered=answer!==null;
 const next=()=>{
   setAnswer(null);
   if(step<group.examples.length-1){setStep(x=>x+1);return;}
   if(phase==='study'){setStep(0);setPhase('check');return;}
   setStep(0);setPhase('study');
 };
 const changeGroup=(index:number)=>{
   setChosen(index);setStep(0);setPhase('study');setAnswer(null);
 };
 return <section className="sentence-patterns" aria-label="Recorded first sentence patterns">
   <button type="button" className="sentence-pattern-toggle" aria-expanded={expanded}
     onClick={()=>setExpanded(x=>!x)}>
     <span>Build your first sentences</span><span aria-hidden="true">{expanded?'−':'+'}</span>
   </button>
   {expanded && <div className="sentence-pattern-content">
     <div className="sentence-pattern-list" role="group" aria-label="Choose a sentence pattern">
       {patterns.map((item,i)=><button type="button" key={item.id}
         aria-pressed={chosen===i} onClick={()=>changeGroup(i)}>{item.title}</button>)}
     </div>
     <div className="sentence-pattern-lesson">
       <div className="sentence-pattern-heading"><strong>{group.title}</strong>
         <span>{step+1} / {group.examples.length}</span></div>
       <p className="sentence-pattern-explanation">{group.explanation}</p>
       <div className="sentence-pattern-actions" role="group" aria-label="Pattern activity">
         <button type="button" aria-pressed={phase==='study'} onClick={()=>{
           setPhase('study');setStep(0);setAnswer(null);
         }}>Learn with examples</button>
         <button type="button" aria-pressed={phase==='check'} onClick={()=>{
           setPhase('check');setStep(0);setAnswer(null);
         }}>Check understanding</button>
       </div>
       {phase==='study' ? <div className="sentence-pattern-example">
         <FocusedSentence item={example}/>
         <div className="sentence-pattern-meaning">{example.english}</div>
         <button type="button" className="sentence-pattern-play" onClick={()=>onPlay(example.audio)}>
           {playing===example.audio?'Playing sentence':'▶ Hear sentence'}
         </button>
         <button type="button" className="sentence-pattern-next" onClick={next}>
           {step===group.examples.length-1?'Check understanding →':'Next example →'}
         </button>
       </div> : <div className="sentence-pattern-check">
         <div className="sentence-pattern-question">Listen and choose the meaning.</div>
         <button type="button" className="sentence-pattern-play" onClick={()=>onPlay(example.audio)}>
           {playing===example.audio?'Playing sentence':'▶ Hear sentence'}
         </button>
         <div className="sentence-pattern-choices" role="group" aria-label="Choose the meaning">
           {choices.map(choice=><button type="button" key={choice} disabled={answered}
             aria-pressed={answer===choice}
             onClick={()=>setAnswer(choice)}>{choice}</button>)}
         </div>
         {answered && <div className="sentence-pattern-reveal" role="status">
           <div>{answer===example.english?'Correct.':'This sentence means:'} <strong>{example.english}</strong></div>
           <FocusedSentence item={example}/>
           <button type="button" className="sentence-pattern-next" onClick={next}>
             {step===group.examples.length-1?'Practise again':'Next sentence →'}
           </button>
         </div>}
       </div>}
     </div>
   </div>}
 </section>;
}
