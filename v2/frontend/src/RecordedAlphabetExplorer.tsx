import {useState} from 'react';
import type {RecordedGlyph} from './recorded-alphabet';

type Props={
 letters:RecordedGlyph[];
 combinations:RecordedGlyph[];
 playing:string|null;
 speed:number;
 onSpeed:(speed:number)=>void;
 onPlay:(source:string)=>void;
};

/** Alphabet *in real words*, not spoken names of the letters or isolated sounds.
 * Reuses exactly the original full utterance and its original English meaning. */
export default function RecordedAlphabetExplorer({
 letters,combinations,playing,speed,onSpeed,onPlay
}:Props){
 const [expanded,setExpanded]=useState(false);
 const [tab,setTab]=useState<'letters'|'combinations'>('letters');
 const [selection,setSelection]=useState(0);
 if(!letters.length&&!combinations.length)return null;
 const items=tab==='letters'?letters:combinations;
 const card=items[Math.min(selection,items.length-1)];
 const selectTab=(next:'letters'|'combinations')=>{setTab(next);setSelection(0);};
 const focus=card?card.polish.indexOf(card.focus):-1;
 return <section className="alphabet-explorer" aria-label="Polish letters in recorded words">
   <button className="alphabet-explorer-toggle" type="button" aria-expanded={expanded}
     onClick={()=>setExpanded(open=>!open)}>
     <span>Explore the Polish alphabet</span>
     <span aria-hidden="true">{expanded?'−':'+'}</span>
   </button>
   {!expanded?null:<div className="alphabet-explorer-content">
     <div className="alphabet-explorer-tabs" role="group" aria-label="Letters or letter combinations">
       <button type="button" aria-pressed={tab==='letters'} onClick={()=>selectTab('letters')}>Letters ({letters.length})</button>
       <button type="button" aria-pressed={tab==='combinations'} onClick={()=>selectTab('combinations')}>Letter combinations ({combinations.length})</button>
     </div>
     <div className="alphabet-letter-grid" role="group" aria-label={tab==='letters'?'Choose a Polish letter':'Choose a Polish letter combination'}>
       {items.map((entry,i)=><button key={entry.label} type="button"
         aria-pressed={i===selection} onClick={()=>setSelection(i)}>
         {entry.label}
       </button>)}
     </div>
     {card && focus>=0 && <div className="alphabet-recorded-word">
       <div className="alphabet-position">{selection+1} / {items.length}</div>
       <div className="alphabet-focus" lang="pl" aria-label={card.polish}>
         {card.polish.slice(0,focus)}<strong>{card.focus}</strong>{card.polish.slice(focus+card.focus.length)}
       </div>
       <div className="alphabet-english">{card.english}</div>
       <button type="button" className="alphabet-play" onClick={()=>onPlay(card.audio)}>
         {playing===card.audio?'Playing word':'▶ Hear word'}
       </button>
       <fieldset className="alphabet-speeds">
         <legend>Playback speed</legend>
         {[0.75,0.85,1].map(rate=><button type="button" key={rate} aria-pressed={rate===speed}
           onClick={()=>onSpeed(rate)}>{rate}×</button>)}
       </fieldset>
       <button type="button" className="alphabet-next" onClick={()=>
         setSelection(current=>(current+1)%items.length)}>Next {tab==='letters'?'letter':'combination'} →</button>
     </div>}
   </div>}
 </section>;
}
