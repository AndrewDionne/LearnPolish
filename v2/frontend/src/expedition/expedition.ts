import regions from './regions.json';
import {calendarDay} from '../gold';
import type {GoldState, RewardMode} from '../gold';

export type RegionId = string;
export const REGION_IDS = regions.map(region=>region.id);
const VALID_REGIONS = new Set(REGION_IDS);
export const EXPEDITION_STORAGE_KEY = 'ptp-v2-expedition';
export const DEFAULT_REGION: RegionId = 'mazowieckie';
export type LearningTier = 1|2|3|4|5;
export const TIER_XP: Record<LearningTier,number> = {1:10,2:14,3:19,4:26,5:35};

export type VerifiedOutcome = {
  skill: 'comprehension'|'recall'|'pronunciation';
  metric: string;
  score: number; // comparable, verified fraction 0..1
  evidence: 'verified';
};
export type XpEvent = {
  id: string; itemId: string; mode: RewardMode; at:string; xp:number;
  baseXp:number; improvementXp:number; tier:LearningTier;
  region:RegionId; source:'practice'|'legacy'; outcome?: VerifiedOutcome;
};
export type ExpeditionState = {
  schemaVersion:1; selectedRegion:RegionId; goalMode:'path'|'self'; selfGoal:number;
  events:XpEvent[]; regionGoals:Record<string,number>;
};
export function emptyExpedition():ExpeditionState {
  return {schemaVersion:1,selectedRegion:DEFAULT_REGION,goalMode:'path',selfGoal:500,events:[],regionGoals:{}};
}
export function regionTotal(state:ExpeditionState, id:string):number {
  return state.events.filter(e=>e.region===id).reduce((sum,e)=>sum+e.xp,0);
}
export function unlockedRegions(state:ExpeditionState):string[]{
  return REGION_IDS.filter(id=>Number.isInteger(state.regionGoals[id]) &&
    state.regionGoals[id]>0 && regionTotal(state,id)>=state.regionGoals[id]);
}
/** Prices are frozen when XP is first contributed to a region; no retroactive goalposts. */
export function nextRegionCost(state:ExpeditionState):number {
  return Math.round((300*Math.pow(1+0.22*unlockedRegions(state).length,1.35))/10)*10;
}
function validGoal(n:number):boolean {return Number.isSafeInteger(n)&&n>=50&&n<=5000&&n%10===0;}
export function chooseRegion(state:ExpeditionState,id:string):ExpeditionState {
  return VALID_REGIONS.has(id)?{...state,selectedRegion:id}:state;
}
export function weeklyGoal(state:ExpeditionState):number {return state.goalMode==='path'?500:state.selfGoal;}
export function setXpGoal(state:ExpeditionState,mode:'path'|'self',goal:number):ExpeditionState{
  return (mode==='path'||mode==='self')&&validGoal(goal)?{...state,goalMode:mode,selfGoal:goal}:state;
}
export function xpSummary(state:ExpeditionState,nowIso:string){
  const now=new Date(nowIso);
  const start=new Date(now.getFullYear(),now.getMonth(),now.getDate());
  start.setDate(start.getDate()-((start.getDay()+6)%7));
  const end=new Date(start);end.setDate(end.getDate()+7);
  const weekly=state.events.filter(e=>{const d=new Date(e.at);return d>=start&&d<end}).reduce((a,e)=>a+e.xp,0);
  const total=state.events.reduce((a,e)=>a+e.xp,0);
  const improved=state.events.reduce((a,e)=>a+e.improvementXp,0);
  const days=new Set(state.events.map(e=>e.id.slice(-10)));
  const cursor=new Date(now.getFullYear(),now.getMonth(),now.getDate());
  const day=()=>[cursor.getFullYear(),String(cursor.getMonth()+1).padStart(2,'0'),String(cursor.getDate()).padStart(2,'0')].join('-');
  if(!days.has(day()))cursor.setDate(cursor.getDate()-1);
  let streak=0;
  while(days.has(day())&&streak<=days.size){streak++;cursor.setDate(cursor.getDate()-1);}
  return {weekly,total,improved,goal:weeklyGoal(state),streak};
}
/** Deliberately provider-independent: a verified phonetic result will use the same outcome API. */
export function awardXp(state:ExpeditionState,itemId:string,mode:RewardMode,at:string,
                        tier:LearningTier=1,outcome?:VerifiedOutcome):ExpeditionState {
  if(!/^[\w:.-]{1,180}$/.test(itemId)||!['learn','read','listen','speak'].includes(mode)||
    !Number.isFinite(Date.parse(at))||!(tier in TIER_XP)||state.events.length>=20000)return state;
  const id=mode+':'+itemId+':'+calendarDay(at);
  if(state.events.some(e=>e.id===id))return state;
  const prior=outcome&&outcome.evidence==='verified'
    ?state.events.filter(e=>e.itemId===itemId&&e.mode===mode&&e.outcome?.evidence==='verified'&&
      e.outcome.skill===outcome.skill&&e.outcome.metric===outcome.metric).at(-1)?.outcome
    :undefined;
  const eligible=outcome&&outcome.evidence==='verified'&&
    ['comprehension','recall','pronunciation'].includes(outcome.skill)&&
    /^[a-z0-9:_-]{1,80}$/i.test(outcome.metric)&&Number.isFinite(outcome.score)&&outcome.score>=0&&outcome.score<=1;
  const improvementXp=eligible&&prior&&outcome.score>prior.score?5:0;
  const baseXp=TIER_XP[tier];
  const next:XpEvent={id,itemId,mode,at,xp:baseXp+improvementXp,baseXp,improvementXp,tier,
    region:state.selectedRegion,source:'practice',...(eligible?{outcome}:{} )};
  const regionGoals={...state.regionGoals};
  if(regionGoals[state.selectedRegion]===undefined)regionGoals[state.selectedRegion]=nextRegionCost(state);
  return {...state,events:[...state.events,next],regionGoals};
}
export function migrateGold(gold?:GoldState):ExpeditionState{
  const state=emptyExpedition();
  if(!gold)return state;
  state.goalMode=gold.goalMode;
  state.selfGoal=gold.selfGoal;
  for(const event of gold.events){
    state.events.push({id:event.id,itemId:event.itemId,mode:event.mode,at:event.at,
      xp:10,baseXp:10,improvementXp:0,tier:1,region:DEFAULT_REGION,source:'legacy'});
  }
  if(state.events.length)state.regionGoals[DEFAULT_REGION]=300;
  return state;
}
export function parseExpedition(raw:string|null,legacy?:GoldState):ExpeditionState {
  if(!raw)return migrateGold(legacy);
  try{
    const value=JSON.parse(raw) as ExpeditionState;
    if(!value||value.schemaVersion!==1||!VALID_REGIONS.has(value.selectedRegion)||
      !['path','self'].includes(value.goalMode)||!validGoal(value.selfGoal)||
      !Array.isArray(value.events)||value.events.length>20000||
      !value.regionGoals||typeof value.regionGoals!=='object'||Array.isArray(value.regionGoals))throw Error('Invalid expedition');
    for(const [id,cost] of Object.entries(value.regionGoals)){
      if(!VALID_REGIONS.has(id)||!Number.isSafeInteger(cost)||cost<300||cost>100000)throw Error('Invalid region target');
    }
    const seen=new Set<string>();
    for(const e of value.events){
      if(!e||!VALID_REGIONS.has(e.region)||!value.regionGoals[e.region]||
        !/^[\w:.-]{1,180}$/.test(e.itemId)||!['learn','read','listen','speak'].includes(e.mode)||
        typeof e.at!=='string'||!Number.isFinite(Date.parse(e.at))||
        e.id!==e.mode+':'+e.itemId+':'+e.id.slice(-10)||
        !/^\d{4}-\d\d-\d\d$/.test(e.id.slice(-10))||seen.has(e.id)||
        ![1,2,3,4,5].includes(e.tier)||e.baseXp!==TIER_XP[e.tier]||
        ![0,5].includes(e.improvementXp)||e.xp!==e.baseXp+e.improvementXp||
        !['legacy','practice'].includes(e.source)||
        (e.outcome!==undefined && (e.outcome.evidence!=='verified'||
          !['comprehension','recall','pronunciation'].includes(e.outcome.skill)||
          !/^[a-z0-9:_-]{1,80}$/i.test(e.outcome.metric)||
          typeof e.outcome.score!=='number'||e.outcome.score<0||e.outcome.score>1))
      )throw Error('Invalid XP event');
      seen.add(e.id);
    }
    return value;
  }catch{return migrateGold(legacy);}
}
export function validateExpedition(value:unknown):value is ExpeditionState {
  if(!value||typeof value!=='object')return false;
  const s=JSON.stringify(value);
  return JSON.stringify(parseExpedition(s))===s;
}
