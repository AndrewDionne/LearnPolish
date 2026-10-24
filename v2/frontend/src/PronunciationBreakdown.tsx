import type {LessonItem} from './model';

type Props={
 item:LessonItem;
 visible:boolean;
 onToggle:(visible:boolean)=>void;
 onPlayExcerpt:(audio:string,startMs:number,endMs:number)=>void;
};

/** Small orthographic focus only. Draft partitions are NOT guaranteed Polish
 * acoustic syllables; no synthesized or guessed per-syllable sounds. */
export default function PronunciationBreakdown({item,visible,onToggle,onPlayExcerpt}:Props){
 // Auto-generated spelling divisions have NOT been reviewed as Polish syllables.
 // Keep them out of learner guidance until an editor/independent speaker checks them.
 const groups=item.syllableAudio?.segments??(
  item.pronunciationSegments?.method!=='draft-orthographic-v1'
    ? item.pronunciationSegments?.segments : undefined);
 if(!groups||groups.length<2)return null;
 const reviewed=item.syllableAudio;
 return <div className="pronunciation-breakdown">
   <button type="button" className="speak-guide-toggle" aria-expanded={visible}
      onClick={()=>onToggle(!visible)}>Pronunciation guide <span aria-hidden="true">{visible?'On':'Off'}</span></button>
   {visible && <div className="pronunciation-parts" lang="pl" aria-label={item.polish}>
    {groups.map((part,i)=>{
      const polish=typeof part==='string'?part:part.polish;
      const actual=reviewed?.segments[i];
      return actual&&reviewed&&item.audio===reviewed.audio
        ? <button type="button" className="pronunciation-audio-part" key={i}
            aria-label={'Play syllable '+(i+1)+': '+polish.trim()}
            onClick={()=>onPlayExcerpt(reviewed.audio,actual.startMs,actual.endMs)}>
            {polish}
          </button>
        : <span className="pronunciation-text-part" key={i}>{polish}</span>;
    })}
   </div>}
 </div>;
}
