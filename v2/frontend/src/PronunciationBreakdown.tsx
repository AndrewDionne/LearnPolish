import type {LessonItem} from './model';

type Props={
 item:LessonItem;
 visible:boolean;
 onToggle:(visible:boolean)=>void;
};

/** Optional visual spelling guide. Never play or promise syllable-only audio.
 * Automatically guessed orthographic partitions remain hidden. */
export default function PronunciationBreakdown({item,visible,onToggle}:Props){
 const grouping=item.pronunciationSegments;
 const groups=grouping?.method!=='draft-orthographic-v1' ? grouping?.segments : undefined;
 if(!groups||groups.length<2)return null;
 return <div className="pronunciation-breakdown">
   <button type="button" className="speak-guide-toggle" aria-expanded={visible}
      onClick={()=>onToggle(!visible)}>Pronunciation guide <span aria-hidden="true">{visible?'On':'Off'}</span></button>
   {visible && <div className="pronunciation-parts" lang="pl" aria-label={item.polish}>
    {groups.map((part,i)=><span className="pronunciation-text-part" key={i}>{part}</span>)}
   </div>}
 </div>;
}
