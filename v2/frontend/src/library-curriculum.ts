import type { CurriculumStage, CurriculumTrack, Lesson } from './model';

type TrackDefinition = {id:CurriculumTrack; label:string};
type StageDefinition = {
  id: CurriculumStage; heading:string; description:string;
  tracks:TrackDefinition[];
};

export const LIBRARY_STAGES: readonly StageDefinition[] = [
  {id:'fundamentals',heading:'Fundamentals',
    description:'Train your ear, learn the first words, then expand your vocabulary.',
    tracks:[
      {id:'sounds',label:'Polish sounds'},
      {id:'first-words',label:'First words'},
      {id:'expanded-words',label:'Expand vocabulary'},
    ]},
  {id:'basic',heading:'Basic',
    description:'Put words together, from familiar expressions to practical sentences.',
    tracks:[
      {id:'first-phrases',label:'Everyday expressions'},
      {id:'sentences',label:'Useful phrases and short sentences'},
    ]},
  {id:'learning',heading:'Learning',
    description:'Use Polish in short conversations and reading situations.',
    tracks:[{id:'conversations-reading',label:'Conversations and reading'}]},
  {id:'practice',heading:'Practice tools',
    description:'Optional experiments and pronunciation practice outside the learning path.',
    tracks:[{id:'lab',label:'Pronunciation lab'}]},
] as const;

export type LibrarySection = {
  id:string; heading:string; description:string;
  tracks:{id:string;heading:string;lessons:Lesson[]}[];
};

export function groupLibraryLessons(lessons:Lesson[]): LibrarySection[] {
  const sections: LibrarySection[]=LIBRARY_STAGES.map(stage=>({
    id:stage.id,heading:stage.heading,description:stage.description,
    tracks:stage.tracks.map(track=>({
      id:track.id,heading:track.label,
      lessons:lessons.filter(lesson=>lesson.curriculum?.stage===stage.id &&
        lesson.curriculum.track===track.id).sort((a,b)=>
        (a.curriculum?.order??0)-(b.curriculum?.order??0) || a.id.localeCompare(b.id)),
    })).filter(track=>track.lessons.length>0),
  })).filter(section=>section.tracks.length>0);
  const personal=lessons.filter(lesson=>!lesson.curriculum)
    .sort((a,b)=>a.title.localeCompare(b.title));
  if(personal.length)sections.push({
    id:'personal',heading:'Your lessons',
    description:'Your imported and created lessons, separate from the built-in learning path.',
    tracks:[{id:'personal',heading:'Personal collection',lessons:personal}],
  });
  return sections;
}

function normalizeSearch(value:string):string {
  return value.normalize('NFKD').toLowerCase().replace(/[_–—-]+/g,' ')
    .replace(/\s+/g,' ').trim();
}

/** Search both curated copy and stable original filenames, so old searches work. */
export function libraryMatches(lesson:Lesson,search:string):boolean {
  const normalized=normalizeSearch(search);
  if(!normalized)return true;
  return [lesson.title,lesson.description??'',lesson.id,
    ...lesson.items.map(item=>item.polish)]
    .some(value=>normalizeSearch(value).includes(normalized));
}
