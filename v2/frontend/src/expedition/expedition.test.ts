import {describe,expect,test} from 'vitest';
import {awardXp,chooseRegion,emptyExpedition,migrateGold,parseExpedition,
  nextRegionCost,regionTotal,unlockedRegions,xpSummary,setXpGoal} from './expedition';
import {awardGold,DEFAULT_GOLD} from '../gold';
describe('Open-map XP expedition',()=>{
 test('every region can be chosen directly with no adjacency or sequence requirement',()=>{
  const s=chooseRegion(emptyExpedition(),'podkarpackie');
  expect(s.selectedRegion).toBe('podkarpackie');
  expect(chooseRegion(s,'fictional')).toBe(s);
 });
 test('awards effort once per mode/item/day and locks progressive region costs',()=>{
  let s=chooseRegion(emptyExpedition(),'pomorskie');
  expect(nextRegionCost(s)).toBe(300);
  for(let i=0;i<30;i++)s=awardXp(s,'word:'+i,'learn','2026-10-16T12:00:00.000Z');
  expect(regionTotal(s,'pomorskie')).toBe(300);
  expect(unlockedRegions(s)).toContain('pomorskie');
  expect(nextRegionCost(s)).toBeGreaterThan(300);
  const repeated=awardXp(s,'word:0','learn','2026-10-16T15:00:00.000Z');
  expect(repeated.events).toHaveLength(30);
  s=awardXp(chooseRegion(s,'lubelskie'),'word:1','read','2026-10-16T12:00:00.000Z');
  expect(s.regionGoals.lubelskie).toBeGreaterThan(300);
  expect(unlockedRegions(s)).toContain('pomorskie');
 });
 test('verifiable improvement depends on previous comparable attempts, not ASR guesses',()=>{
  let s=emptyExpedition();
  const o=(score:number)=>({skill:'pronunciation' as const,metric:'phoneme-v1',score,evidence:'verified' as const});
  s=awardXp(s,'a:1','speak','2026-10-15T10:00:00.000Z',1,o(.4));
  expect(s.events[0].improvementXp).toBe(0);
  s=awardXp(s,'a:1','speak','2026-10-16T10:00:00.000Z',1,o(.7));
  expect(s.events[1].improvementXp).toBe(5);
  s=awardXp(s,'a:1','speak','2026-10-17T10:00:00.000Z',1);
  expect(s.events[2].improvementXp).toBe(0);
  expect(xpSummary(s,'2026-10-17T12:00:00Z').improved).toBe(5);
 });
 test('legacy Gold is credited once and roundtrips without duplicate bonus',()=>{
  const g=awardGold(DEFAULT_GOLD,'a:1','learn','2026-10-16T11:00:00.000Z');
  const s=migrateGold(g);
  expect(s.events).toHaveLength(1);
  expect(s.events[0].source).toBe('legacy');
  const raw=JSON.stringify(s);
  expect(parseExpedition(raw,g)).toEqual(s);
  expect(awardXp(s,'a:1','learn','2026-10-16T12:00:00.000Z')).toEqual(s);
 });
 test('separate user goals, invalid snapshots, tier scaling',()=>{
  const s=setXpGoal(emptyExpedition(),'self',250);
  expect(xpSummary(s,'2026-10-16T12:00:00Z').goal).toBe(250);
  expect(awardXp(s,'a:1','read','2026-10-16T12:00:00Z',4).events[0].xp).toBe(26);
  expect(parseExpedition(JSON.stringify({...s,selectedRegion:'unreal'}))).toEqual(emptyExpedition());
 });
});
