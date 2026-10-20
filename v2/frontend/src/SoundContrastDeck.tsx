import type { Lesson } from './model';

type Props = {
  lesson: Lesson;
  focusGroupId?: string;
  currentId: string;
  playing: string | null;
  onSelect: (itemId: string) => void;
  onPlay: (audioPath: string) => void;
};

/** Compare short individual recordings side by side; no automatic phonetic grading. */
export default function SoundContrastDeck({ lesson, focusGroupId, currentId, playing, onSelect, onPlay }: Props) {
  if (!lesson.soundGroups?.length) return null;
  const byId = new Map(lesson.items.map(item => [item.id, item]));
  const groups = focusGroupId ? lesson.soundGroups.filter(g => g.id === focusGroupId) : lesson.soundGroups;
  return <section className="contrast-deck" aria-label="Compare Polish sounds">
    <div className="contrast-intro">
      <div><span className="eyebrow">SOUND LAB · LISTEN AND COMPARE</span><h2>Hear every sound separately</h2><p>{lesson.intro}</p></div>
      <span className="sound-note">Audio from existing lessons · native review pending</span>
    </div>
    <div className="contrast-groups">
      {groups.map(group => <article key={group.id} className="contrast-group">
        <div className="contrast-group-label"><strong lang="pl">{group.label}</strong><span>{group.ipa}</span></div>
        <p>{group.hint}</p>
        <div className="contrast-examples">
          {group.itemIds.map(id => {
            const item = byId.get(id);
            if (!item) return null;
            return <div key={item.id} className={'contrast-example ' + (currentId === item.id ? 'chosen' : '')}>
              <button type="button" className="contrast-focus" aria-pressed={currentId === item.id} onClick={() => onSelect(item.id)}>
                <strong lang="pl">{item.polish}</strong><small>{item.english}</small>
              </button>
              <button className="contrast-play" type="button" aria-label={'Play ' + item.polish} disabled={!item.audio} onClick={() => {
                onSelect(item.id);
                if (item.audio) onPlay(item.audio);
              }}>{item.audio && playing === item.audio ? '◼' : '▶'}</button>
            </div>;
          })}
        </div>
      </article>)}
    </div>
    <p className="sound-caption">Play a recorded example, then try it in Speak. These are full words or phrases containing the highlighted combination—not isolated syllable recordings. Pronunciation scores are not available for these exercises yet.</p>
  </section>;
}
