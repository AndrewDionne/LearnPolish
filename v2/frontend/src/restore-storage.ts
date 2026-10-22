import {PERSONAL_STORAGE_KEY} from './personal';
import {STORAGE_KEY} from './progress';
import {REVIEW_STORAGE_KEY} from './review';
import {READING_POSITION_KEY} from './reading-position';
import {EXPEDITION_STORAGE_KEY,parseExpedition} from './expedition/expedition';
import type {LocalBackup} from './backup';

const LAST_LESSON_KEY='ptp-v2-last-lesson';
type BrowserStore=Pick<Storage,'getItem'|'setItem'|'removeItem'>;

/**
 * Commit validated backup data before announcing a restore or mutating UI state.
 * Restore the exact previous values when any localStorage write fails (quota,
 * private mode, permission denial). This is synchronous, not a cloud operation.
 */
export function persistRestoredBackup(
  backup:LocalBackup,storage:BrowserStore,
){
  const expedition=backup.expedition??parseExpedition(null,backup.gold);
  const entries:[string,string|null][]=[
    [PERSONAL_STORAGE_KEY,JSON.stringify(backup.personalLessons)],
    [STORAGE_KEY,JSON.stringify(backup.progress)],
    [REVIEW_STORAGE_KEY,JSON.stringify(backup.reviews)],
    [READING_POSITION_KEY,JSON.stringify(backup.readingPositions)],
    [EXPEDITION_STORAGE_KEY,JSON.stringify(expedition)],
    [LAST_LESSON_KEY,backup.lastLessonId],
  ];
  const previous=new Map<string,string|null>();
  const changed:string[]=[];
  try{
    // Pre-read all keys before modifying even one of them.
    for(const [key] of entries)previous.set(key,storage.getItem(key));
    for(const [key,value] of entries){
      // Record before writing; some browser implementations can throw mid-write.
      changed.push(key);
      if(value===null)storage.removeItem(key);
      else storage.setItem(key,value);
    }
  }catch{
    let failedRollback=false;
    for(const key of changed.reverse()){
      try{
        const prior=previous.get(key);
        if(prior===null||prior===undefined)storage.removeItem(key);
        else storage.setItem(key,prior);
      }catch{failedRollback=true;}
    }
    throw new Error(failedRollback
      ? 'Browser storage failed during restore and rollback. Keep your backup file and inspect local data before continuing.'
      : 'Browser storage refused the restore. Your previous saved data was preserved; free storage or change browser settings and retry.');
  }
  return expedition;
}
