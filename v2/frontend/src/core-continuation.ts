import type {Lesson} from './model';
import type {Progress} from './progress';
import {orderedCoreLessons} from './core-journey';

/** Independent of the pre-existing recent-lesson key and of XP/skill labels. */
export const CORE_CONTINUE_KEY='ptp-v2-core-continue';

export function parseCoreContinueId(raw:string|null):string|null {
  return raw && /^[a-zA-Z0-9_-]{1,140}$/.test(raw) && !raw.startsWith('personal_')
    ? raw : null;
}

export type CourseContinuation={
  lesson:Lesson|null;
  origin:'selected'|'recent-core'|'practice-history'|'start'|'unavailable';
};

/**
 * Resolve the next *place to open*, not a completion or proficiency judgment.
 * Prioritize explicit core navigation, then migration from old recent-core,
 * then most recent actual recorded core activity (Learn/Listen/Read).
 * Personal and supplementary lessons never override a core cursor.
 */
export function resolveCourseContinuation(
  lessons:Lesson[],progress:Progress,selectedId:string|null,recentId:string|null,
):CourseContinuation{
  const core=orderedCoreLessons(lessons);
  if(!core.length)return {lesson:null,origin:'unavailable'};
  const selected=core.find(lesson=>lesson.id===selectedId);
  if(selected)return {lesson:selected,origin:'selected'};
  const recent=core.find(lesson=>lesson.id===recentId);
  if(recent)return {lesson:recent,origin:'recent-core'};
  let best:Lesson|null=null;
  let maxTime=-Infinity;
  for(const lesson of core){
    for(const item of lesson.items){
      for(const key of [item.id,'read:'+item.id,'listen:'+item.id]){
        const attempt=progress[key];
        if(!attempt || attempt.seen<1)continue;
        const time=Date.parse(attempt.lastSeen);
        if(Number.isFinite(time) && time>maxTime){
          maxTime=time;best=lesson;
        }
      }
    }
  }
  return best ? {lesson:best,origin:'practice-history'}
    : {lesson:core[0],origin:'start'};
}
