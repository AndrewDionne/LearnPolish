import raw from '../../content/tourist-units-v1.json';
import type {Lesson} from './model';
import type {LearningMode} from './modes';
import {availableModes} from './modes';

export type TouristUnitStep={mode:'listen'|'speak'|'read';lessonId:string;itemIds:string[]};
export type TouristUnit={
  id:string;title:string;journey:1;position:'beginning';order:number;
  outcome:string;steps:TouristUnitStep[];gaps?:string[];
};

/** The unit metadata is a *path through existing source*, not new lesson data.
 * No XP, assessment, audio, or completion state is defined here. */
export function validateTouristUnits(input:unknown):TouristUnit[]{
  if(!input||typeof input!=='object')throw new Error('Missing tourist unit manifest');
  const data=input as Record<string,unknown>;
  if(data.schemaVersion!==1||data.editorialStatus!=='source_refs_only_native_review_pending'
    ||!Array.isArray(data.units)||data.units.length!==3)throw new Error('Invalid tourist unit schema');
  const out:TouristUnit[]=[];
  for(let i=0;i<data.units.length;i++){
    const unit=data.units[i] as Partial<TouristUnit>|null;
    if(!unit||unit.id!==`T0${i+1}`||unit.journey!==1||
      unit.position!=='beginning'||unit.order!==i+1||
      typeof unit.title!=='string'||unit.title.trim().length<5||
      typeof unit.outcome!=='string'||unit.outcome.trim().length<12||
      !Array.isArray(unit.steps)||unit.steps.length<2||unit.steps.length>3||
      (unit.gaps!==undefined&&(!Array.isArray(unit.gaps)||unit.gaps.some(x=>typeof x!=='string'))))
      throw new Error('Invalid tourist unit');
    const used=new Set<string>();
    const modes=new Set<string>();
    for(const step of unit.steps){
      if(!step||!['listen','speak','read'].includes(step.mode)||
        modes.has(step.mode)||typeof step.lessonId!=='string'||!step.lessonId||
        step.lessonId.startsWith('personal_')||step.lessonId==='speak_swietokrzyska'||
        !Array.isArray(step.itemIds)||step.itemIds.length<1||
        step.itemIds.some(x=>typeof x!=='string'||!x.startsWith(step.lessonId+':')||
          !/^.+:\d+$/.test(x)||used.has(step.mode+':'+x))||
        new Set(step.itemIds).size!==step.itemIds.length)
        throw new Error('Invalid tourist step');
      modes.add(step.mode);
      step.itemIds.forEach(id=>used.add(step.mode+':'+id));
    }
    if(unit.steps[0].mode!=='listen'||unit.steps[1].mode!=='speak'||
      (unit.steps[2]&&unit.steps[2].mode!=='read'))throw new Error('Unordered tourist modes');
    out.push(unit as TouristUnit);
  }
  return out;
}

export const TOURIST_UNITS:readonly TouristUnit[]=validateTouristUnits(raw);

/** Reject whole units with missing/unsafe references; ordinary Library stays usable.
 * Only original / curated built-ins, no personal lessons or artificial scores.
 */
export function unitStepSource(lessons:Lesson[],step:TouristUnitStep):Lesson|null {
  const lesson=lessons.find(x=>x.id===step.lessonId && x.source!=='personal');
  if(!lesson||!availableModes(lesson).includes(step.mode as LearningMode)||
    (step.mode==='read' && lesson.kind!=='reading')||
    (step.mode==='speak' && lesson.kind==='reading'))return null;
  const referenced=step.itemIds.map(id=>lesson.items.find(x=>x.id===id));
  if(referenced.some(item=>!item || item.referenceReview==='practice_only' ||
    !item.audio))return null;
  // Subsets must retain source order, so cross-modal sessions follow the recording.
  const indices=step.itemIds.map(id=>lesson.items.findIndex(item=>item.id===id));
  return indices.every((index,i)=>i===0||index>indices[i-1])?lesson:null;
}

export function availableTouristUnits(lessons:Lesson[]):TouristUnit[]{
  return TOURIST_UNITS.filter(unit=>unit.steps.every(step=>!!unitStepSource(lessons,step)));
}

export function unitStepItems(lesson:Lesson,step:TouristUnitStep){
  const allowed=new Set(step.itemIds);
  return lesson.items.filter(item=>allowed.has(item.id));
}
