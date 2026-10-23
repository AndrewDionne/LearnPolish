import type {Lesson} from './model';
import type {ReviewSchedule} from './review';
import {dueItems} from './review';
import {journeyPlacement,orderedCoreLessons} from './core-journey';

export type DueLesson={lesson:Lesson;itemIds:string[]};
export type DueLanes={core:DueLesson[];personal:DueLesson[];explore:DueLesson[]};
export type CoreReviewRun={steps:{lessonId:string;itemIds:string[]}[];position:number};

const pending=(lesson:Lesson,schedule:ReviewSchedule,nowIso:string):DueLesson|null=>{
  // Existing reading items do not use spaced scheduling. Never invent a due event.
  if(lesson.kind==='reading')return null;
  const itemIds=dueItems(lesson,schedule,nowIso).map(item=>item.id);
  return itemIds.length?{lesson,itemIds}:null;
};

/** Derived only from existing Learn review dates. No new scheduler, mastery,
 * XP events, storage keys or pronunciation evidence.
 */
export function partitionDueReviews(lessons:Lesson[],schedule:ReviewSchedule,nowIso:string):DueLanes{
  const core=orderedCoreLessons(lessons).map(lesson=>pending(lesson,schedule,nowIso))
    .filter((entry):entry is DueLesson=>!!entry);
  const remainder=lessons.filter(lesson=>!journeyPlacement(lesson));
  const personal=remainder.filter(lesson=>lesson.source==='personal')
    .map(lesson=>pending(lesson,schedule,nowIso)).filter((entry):entry is DueLesson=>!!entry)
    .sort((a,b)=>a.lesson.title.localeCompare(b.lesson.title)||a.lesson.id.localeCompare(b.lesson.id));
  const explore=remainder.filter(lesson=>lesson.source!=='personal')
    .map(lesson=>pending(lesson,schedule,nowIso)).filter((entry):entry is DueLesson=>!!entry)
    .sort((a,b)=>a.lesson.title.localeCompare(b.lesson.title)||a.lesson.id.localeCompare(b.lesson.id));
  return {core,personal,explore};
}

export const dueLaneCount=(entries:DueLesson[])=>entries.reduce((sum,entry)=>sum+entry.itemIds.length,0);

/** Immutable snapshot of exactly the core due items at the user's click.
 * A failed recall remains due in the scheduler but will not loop forever
 * inside the same voluntary session. Revisit is available later.
 */
export function startCoreReviewRun(entries:DueLesson[]):CoreReviewRun|null {
  const steps=entries.filter(e=>e.lesson.kind!=='reading' && journeyPlacement(e.lesson) &&
    e.itemIds.length && e.itemIds.every(id=>e.lesson.items.some(item=>item.id===id)))
    .map(entry=>({lessonId:entry.lesson.id,itemIds:[...new Set(entry.itemIds)]}));
  return steps.length?{steps,position:0}:null;
}

export function nextCoreReviewRunStep(run:CoreReviewRun):CoreReviewRun|null {
  if(!run||!Number.isInteger(run.position)||run.position<0||
    run.position>=run.steps.length||!run.steps[run.position]||
    run.position+1>=run.steps.length)return null;
  return {steps:run.steps,position:run.position+1};
}
