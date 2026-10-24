import {useState} from 'react';
import {focusedPolishParts,soundListeningCards} from './sound-listening';
export {focusedPolishParts} from './sound-listening';
import SoundEarQuiz from './SoundEarQuiz';
import type { Lesson } from './model';

type Props = {
  lesson: Lesson;
  focusGroupId?: string;
  currentId: string;
  playing: string | null;
  onSelect: (itemId: string) => void;
  onPlay: (audioPath: string) => void;
  onQuizChange: (active:boolean) => void;
};

/** Compare short individual recordings side by side; no automatic phonetic grading. */
export default function SoundContrastDeck({ lesson, focusGroupId, currentId, playing, onSelect, onPlay,onQuizChange }: Props) {
  const [view,setView]=useState<'compare'|'recognize'>('compare');
  if (!lesson.soundGroups?.length) return null;
  const byId = new Map(lesson.items.map(item => [item.id, item]));
  const cards= soundListeningCards(lesson);
  const groups = focusGroupId ? lesson.soundGroups.filter(g => g.id === focusGroupId) : lesson.soundGroups;
  return <section className="contrast-deck" aria-label="Compare Polish sounds">
    <div className="contrast-intro">
      <div><span className="eyebrow">SOUND LAB · LISTEN AND COMPARE</span><h2>Hear sounds in real words</h2><p>{lesson.intro}</p></div>
      <span className="sound-note">Audio from existing lessons · native review pending</span>
    </div>
    {cards.length>0 && <div className="sound-ear-switch" role="group" aria-label="Sound learning activity">
      <button type="button" aria-pressed={view==='compare'} onClick={()=>{setView('compare');onQuizChange(false);}}>Compare words</button>
      <button type="button" aria-pressed={view==='recognize'} onClick={()=>{setView('recognize');onQuizChange(true);}}>Test my ear</button>
    </div>}
    {view==='recognize' && cards.length>0
      ? <SoundEarQuiz key={lesson.id} lesson={lesson} cards={cards} playing={playing}
          onPlay={onPlay} onCompare={()=>{setView('compare');onQuizChange(false);}}/>
      : <div className="contrast-groups">
      {groups.map(group => <article key={group.id} className="contrast-group">
        <div className="contrast-group-label">
          <strong lang="pl">{group.label}{(()=>{
            const example=group.itemIds.map(id=>byId.get(id)).find(item=>
              item!==undefined && !!item.audio && !!focusedPolishParts(item));
            return example ? <>, like in {example.polish}</> : null;
          })()}</strong><span>{group.ipa}</span>
        </div>
        <p>{group.hint}</p>
        <div className="contrast-examples">
          {group.itemIds.map(id => {
            const item = byId.get(id);
            if (!item) return null;
            return <div key={item.id} className={'contrast-example ' + (currentId === item.id ? 'chosen' : '')}>
              <button type="button" className="contrast-focus" aria-pressed={currentId === item.id} onClick={() => onSelect(item.id)}>
                <strong lang="pl">{(() => {
                  const parts=focusedPolishParts(item);
                  return parts ? <>{parts.before}<span className="sound-focus-letters">{parts.focus}</span>{parts.after}</> : item.polish;
                })()}</strong><small>{item.english}</small>
              </button>
              <button className="contrast-play" type="button" aria-label={'Play ' + item.polish} disabled={!item.audio} onClick={() => {
                onSelect(item.id);
                if (item.audio) onPlay(item.audio);
              }}>{item.audio && playing === item.audio ? '◼' : '▶'}</button>
            </div>;
          })}
        </div>
      </article>)}
    </div>}
    {view==='compare' && <p className="sound-caption">Listen to each complete example word, with its sound highlighted.</p>}
  </section>;
}
