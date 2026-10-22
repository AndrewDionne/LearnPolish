import {describe,expect,test} from 'vitest';
import {makeBackup,parseBackup} from './backup';
import {persistRestoredBackup} from './restore-storage';
import {makePersonalLesson} from './personal';
import {awardXp,emptyExpedition} from './expedition/expedition';

const lesson=makePersonalLesson({title:'Polish practice',kind:'vocabulary',
  items:[{polish:'Cześć',english:'Hello'}]},undefined,()=>'restore-stable');
const expedition=awardXp(emptyExpedition(),'basic:0','learn','2026-10-16T12:00:00.000Z');
const backup=parseBackup(makeBackup({
  personalLessons:[lesson],
  progress:{[lesson.items[0].id]:{seen:1,remembered:1,needsPractice:0,lastSeen:'2026-10-16T12:00:00Z'}},
  reviews:{},readingPositions:{Basic_01R:2},lastLessonId:lesson.id,expedition,
},'2026-10-16T12:30:00Z'));

function storage(seed:Record<string,string>={}){
  const data=new Map(Object.entries(seed));
  let failKey:string|null=null,failed=false;
  const store={
    getItem:(key:string)=>data.get(key)??null,
    setItem:(key:string,value:string)=>{
      if(key===failKey&&!failed){failed=true;throw new Error('QuotaExceededError');}
      data.set(key,value);
    },
    removeItem:(key:string)=>{data.delete(key);},
  };
  return {data,store,failOnceOn:(key:string)=>{failKey=key;failed=false;}};
}

describe('all-or-nothing local restore',()=>{
  test('commits personal lessons, reviews, progress and XP together, preserving their keys',()=>{
    const {data,store}=storage({'ptp-v2-last-lesson':'old'});
    expect(persistRestoredBackup(backup,store)).toEqual(expedition);
    expect(JSON.parse(data.get('ptp-v2-personal-lessons')||'[]')).toEqual([lesson]);
    expect(JSON.parse(data.get('ptp-v2-progress')||'{}')).toEqual(backup.progress);
    expect(JSON.parse(data.get('ptp-v2-review-schedule')||'{}')).toEqual({});
    expect(JSON.parse(data.get('ptp-v2-reading-position')||'{}')).toEqual({Basic_01R:2});
    expect(JSON.parse(data.get('ptp-v2-expedition')||'{}')).toEqual(expedition);
    expect(data.get('ptp-v2-last-lesson')).toBe(lesson.id);
  });

  test('a quota failure halfway through rolls back every touched key byte-for-byte',()=>{
    const original={'ptp-v2-personal-lessons':'[{"old":true}]',
      'ptp-v2-progress':'{"original":true}', 'ptp-v2-review-schedule':'{"old":1}',
      'ptp-v2-reading-position':'{"prior":2}','ptp-v2-last-lesson':'oldLesson',
      'ptp-v2-expedition':'{"oldExpedition":true}'};
    const {data,store,failOnceOn}=storage(original);
    failOnceOn('ptp-v2-expedition');
    expect(()=>persistRestoredBackup(backup,store)).toThrow(/previous saved data was preserved/);
    expect(Object.fromEntries(data)).toEqual(original);
  });

  test('failure after writing a missing key removes that new key on rollback',()=>{
    const {data,store,failOnceOn}=storage({'ptp-v2-progress':'prior'});
    failOnceOn('ptp-v2-review-schedule');
    expect(()=>persistRestoredBackup(backup,store)).toThrow(/previous saved data was preserved/);
    expect(Object.fromEntries(data)).toEqual({'ptp-v2-progress':'prior'});
  });

  test('clears the last lesson reference only on successful commit',()=>{
    const withoutRecent=parseBackup({...backup,lastLessonId:null});
    const {data,store}=storage({'ptp-v2-last-lesson':'outdated'});
    persistRestoredBackup(withoutRecent,store);
    expect(data.has('ptp-v2-last-lesson')).toBe(false);
  });
});
