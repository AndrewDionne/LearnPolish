import {describe,expect,test} from 'vitest';
import {awardGold,parseGold,goldSummary,DEFAULT_GOLD,setGoal,selectAvatar} from './gold';

describe('earned, non-gameable Gold',()=>{
 test('awards completed Learn/Read/Listen/Speak once per item/mode/day, never from score',()=>{
   let state=awardGold(DEFAULT_GOLD,'words:0','learn','2026-10-16T10:00:00.000Z');
   state=awardGold(state,'words:0','learn','2026-10-16T12:00:00.000Z');
   expect(state.events).toHaveLength(1);
   state=awardGold(state,'words:0','speak','2026-10-16T10:00:00.000Z');
   expect(state.events).toHaveLength(2);
   expect(goldSummary(state,'2026-10-16T12:00:00.000Z').total).toBe(20);
 });
 test('weekly total and goals reflect earned ledger',()=>{
   let state=DEFAULT_GOLD;
   for(let i=0;i<50;i++) state=awardGold(state,'cards:'+i,'learn','2026-10-16T12:00:00.000Z');
   expect(goldSummary(state,'2026-10-16T12:00:00.000Z')).toMatchObject({total:500,weekly:500,goal:500,reachedGoal:true,remaining:0});
   const custom=setGoal(state,'self',250);
   expect(goldSummary(custom,'2026-10-16T12:00:00.000Z').goal).toBe(250);
 });
 test('invalid and tampered events cannot be restored as awards',()=>{
   const state=awardGold(DEFAULT_GOLD,'a:1','learn','2026-10-16T12:00:00.000Z');
   const corrupt={...state,events:[...state.events,{...state.events[0],gold:100000}]};
   expect(parseGold(JSON.stringify(corrupt)).events).toHaveLength(1);
   expect(parseGold('invalid').events).toHaveLength(0);
   expect(setGoal(state,'self',5)).toEqual(state);
 });
});


test('legacy Pierogi selection survives Gold parsing',()=>{
 const s=selectAvatar(DEFAULT_GOLD,'tall');
 expect(parseGold(JSON.stringify(s)).avatar).toBe('tall');
});
