import type {Lesson} from './model';
import type {Progress} from './progress';
import type {ReadingPositions} from './reading-position';
import {safeReadingPosition} from './reading-position';
import {practiceBatchCount,practiceBatchItems} from './practice-batches';

/** Home's Continue action, never the Library's explicit "start from the beginning".
 * Derive position entirely from existing reviewed progress and reading cursor.
 * No second progress database, cloud sync, XP event or invented sectioning.
 */
export type LessonResumePosition = {
  batchIndex:number;
  index:number;
  overallIndex:number;
  hasNewItem:boolean;
};

export function nextLessonResume(
  lesson:Lesson,progress:Progress,readingPositions:ReadingPositions,
):LessonResumePosition{
  if(lesson.kind==='reading'){
    const index=safeReadingPosition(readingPositions,lesson.id,lesson.items.length);
    return {batchIndex:0,index,overallIndex:index,hasNewItem:true};
  }
  // A Listen attempt does not prove a card was already encountered in Learn.
  // Only the canonical Learn key counts when finding the next new expression.
  const next=lesson.items.findIndex(item=>!progress[item.id] || progress[item.id].seen<1);
  if(next<0)return {batchIndex:0,index:0,overallIndex:0,hasNewItem:false};
  const item=lesson.items[next];
  for(let batch=0;batch<practiceBatchCount(lesson);batch++){
    const within=practiceBatchItems(lesson,'learn',batch).findIndex(x=>x.id===item.id);
    if(within>=0)return {batchIndex:batch,index:within,overallIndex:next,hasNewItem:true};
  }
  // Content-integrity gates should make this unreachable, but never open
  // outside a lesson's actual items if a personal lesson is malformed.
  return {batchIndex:0,index:0,overallIndex:0,hasNewItem:false};
}
