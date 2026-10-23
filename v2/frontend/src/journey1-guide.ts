import raw from '../../content/journey1-foundation-guide-v1.json';
import type {Lesson} from './model';
import type {TouristUnit} from './tourist-units';

export type FoundationGuideStep={
  id:string;type:'foundation';group:'sounds'|'first-words'|'useful-words'|'short-sentences';
  lessonId:string;title:string;
};
export type ApplicationGuideStep={id:string;type:'application';unitId:string;title:string};
export type Journey1GuideStep=FoundationGuideStep|ApplicationGuideStep;
type GuideManifest={
  schemaVersion:1;status:string;journey:1;notes:string;
  allocation:{foundationSessions:number;applicationCheckpoints:number;
    foundationSharePercent:number;metric:string};
  steps:Journey1GuideStep[];
};
const isObject=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const keys=(x:Record<string,unknown>,fields:string[])=>Object.keys(x).sort().join('|')===[...fields].sort().join('|');
const groups=['sounds','first-words','useful-words','short-sentences'];
const expectedApplications=['T01','T03','T05','T08'];

export function validateJourney1Guide(value:unknown):Journey1GuideStep[]{
  if(!isObject(value)||!keys(value,['schemaVersion','status','journey','allocation','notes','steps'])||
     value.schemaVersion!==1||value.status!=='source_mapped_foundations_priority_not_native_certified'||
     value.journey!==1||typeof value.notes!=='string'||value.notes.length<25||
     !isObject(value.allocation)||!keys(value.allocation,
       ['foundationSessions','applicationCheckpoints','foundationSharePercent','metric'])||
     value.allocation.foundationSessions!==16||value.allocation.applicationCheckpoints!==4||
     value.allocation.foundationSharePercent!==80||
     value.allocation.metric!=='guided_session_slots_not_minutes_or_mastery'||
     !Array.isArray(value.steps)||value.steps.length!==20)
    throw new Error('Invalid Journey 1 foundation guide');
  const seenLessons=new Set<string>();
  const steps:Journey1GuideStep[]=[];
  for(let i=0;i<value.steps.length;i++){
    const step=value.steps[i];
    if(!isObject(step)||typeof step.title!=='string'||step.title.trim().length<6)
      throw new Error('Invalid foundation guide step');
    if(i<16){
      if(!keys(step,['id','type','group','lessonId','title'])||step.type!=='foundation'||
         step.id!=='F'+String(i+1).padStart(2,'0')||!groups.includes(String(step.group))||
         typeof step.lessonId!=='string'||!step.lessonId||
         step.lessonId.startsWith('personal_')||step.lessonId==='speak_swietokrzyska'||
         seenLessons.has(step.lessonId))
         throw new Error('Invalid foundational source step');
      seenLessons.add(step.lessonId);
    }else{
      if(!keys(step,['id','type','unitId','title'])||step.type!=='application'||
         step.id!=='A'+String(i-15).padStart(2,'0')||
         step.unitId!==expectedApplications[i-16])
         throw new Error('Invalid applied checkpoint');
    }
    steps.push(step as Journey1GuideStep);
  }
  return steps;
}

export const JOURNEY1_GUIDE:readonly Journey1GuideStep[]=validateJourney1Guide(raw);

/** Entire existing lessons are opened unmodified. No invented audio, no source
 * copying, no reshuffled Numbers 1–20 and no proficiency or mastery award. */
export function availableJourney1Guide(lessons:Lesson[],units:TouristUnit[]):Journey1GuideStep[]{
  const byLesson=new Map(lessons.filter(x=>x.source!=='personal'&&x.curriculum?.stage!=='practice')
    .map(x=>[x.id,x]));
  const byUnit=new Map(units.map(u=>[u.id,u]));
  return JOURNEY1_GUIDE.filter(step=>{
    if(step.type==='application')return byUnit.has(step.unitId);
    const source=byLesson.get(step.lessonId);
    return !!source&&source.items.length>0;
  });
}
