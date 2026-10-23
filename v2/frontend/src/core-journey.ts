import source from '../../content/core-journey-v1.json';
import type {Lesson} from './model';

/**
 * Curriculum placement is deliberately independent of old Library stage/track
 * and of mutable learner progress. It never gates lessons or awards XP.
 */
export type Journey = 1 | 2 | 3;
export type JourneyPosition = 'beginning' | 'middle' | 'end';
export type JourneyPlacement = {
  lessonId:string; journey:Journey; position:JourneyPosition; order:number;
};
const positions:readonly JourneyPosition[]=['beginning','middle','end'];

export function validateCoreJourney(value:unknown):JourneyPlacement[] {
  if(!value || typeof value!=='object')throw new Error('Missing journey manifest');
  const data=value as {schemaVersion?:unknown;placements?:unknown;editorialStatus?:unknown};
  if(data.schemaVersion!==1 ||
    data.editorialStatus!=='source-mapped-pilot_not_native-audio-certified' ||
    !Array.isArray(data.placements))throw new Error('Invalid journey manifest');
  const seen=new Set<string>();
  const orders=new Set<string>();
  const result:JourneyPlacement[]=[];
  for(const raw of data.placements){
    if(!raw || typeof raw!=='object')throw new Error('Invalid journey placement');
    const entry=raw as Partial<JourneyPlacement>;
    if(typeof entry.lessonId!=='string' || !entry.lessonId ||
      entry.lessonId.startsWith('personal_') || entry.lessonId==='speak_swietokrzyska' ||
      ![1,2,3].includes(Number(entry.journey)) ||
      !positions.includes(entry.position as JourneyPosition) ||
      !Number.isSafeInteger(entry.order) || !entry.order || entry.order<1 ||
      seen.has(entry.lessonId) ||
      orders.has(entry.journey+':'+entry.position+':'+entry.order)){
      throw new Error('Invalid or duplicate journey placement');
    }
    seen.add(entry.lessonId);
    orders.add(entry.journey+':'+entry.position+':'+entry.order);
    result.push(entry as JourneyPlacement);
  }
  // Explicit partial programme: do NOT synthesize Journey 3 or empty nine tiers.
  for(const journey of [1,2,3] as const)for(const position of positions){
    const slice=result.filter(x=>x.journey===journey&&x.position===position)
      .map(x=>x.order).sort((a,b)=>a-b);
    if(slice.some((order,index)=>order!==index+1))
      throw new Error('Noncontiguous journey placement order');
  }
  return result;
}

export const CORE_JOURNEY_PLACEMENTS:readonly JourneyPlacement[]=validateCoreJourney(source);
const byLessonId=new Map(CORE_JOURNEY_PLACEMENTS.map(entry=>[entry.lessonId,entry]));

export function journeyPlacement(lesson:Lesson):JourneyPlacement|null {
  if(lesson.source==='personal'||lesson.curriculum?.stage==='practice')return null;
  return byLessonId.get(lesson.id)??null;
}
const positionIndex=(position:JourneyPosition)=>positions.indexOf(position);

export function orderedCoreLessons(lessons:Lesson[]):Lesson[] {
  return lessons.filter(lesson=>journeyPlacement(lesson)!==null)
    .sort((a,b)=>{
      const x=journeyPlacement(a)!;
      const y=journeyPlacement(b)!;
      return x.journey-y.journey || positionIndex(x.position)-positionIndex(y.position) ||
        x.order-y.order || a.id.localeCompare(b.id);
    });
}

/** Suggested source-based successor, never a gate or a proficiency judgment. */
export function nextCoreLesson(lessons:Lesson[],currentId:string):Lesson|null {
  const ordered=orderedCoreLessons(lessons);
  const at=ordered.findIndex(lesson=>lesson.id===currentId);
  return at<0?null:ordered[at+1]??null;
}

export type JourneyLibrarySection={
  id:'core'|'explore'|'personal'; heading:string; lessons:Lesson[];
};
/** Simple cards: NO nine-stage headings, filters, hover legend or tier labels. */
export function groupJourneyLibrary(lessons:Lesson[]):JourneyLibrarySection[] {
  const core=orderedCoreLessons(lessons);
  const explore=lessons.filter(lesson=>lesson.source!=='personal' && !journeyPlacement(lesson))
    .sort((a,b)=>a.title.localeCompare(b.title));
  const personal=lessons.filter(lesson=>lesson.source==='personal')
    .sort((a,b)=>a.title.localeCompare(b.title));
  return [
    {id:'core',heading:'Your path',lessons:core},
    {id:'explore',heading:'Explore more',lessons:explore},
    {id:'personal',heading:'Your lessons',lessons:personal},
  ].filter(section=>section.lessons.length>0) as JourneyLibrarySection[];
}
