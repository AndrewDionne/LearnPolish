import {TOURIST_UNITS} from './tourist-units';
import type {TouristUnit,TouristUnitStep} from './tourist-units';

export const TOURIST_ACTIVITY_KEY='ptp-v2-tourist-activity';
export type TouristMode=TouristUnitStep['mode'];
export type TouristCursor={mode:TouristMode;itemId:string};
export type TouristActivity={cursor?:TouristCursor;tried:Partial<Record<TouristMode,string[]>>};
export type TouristActivities={version:1;units:Record<string,TouristActivity>};

export const emptyTouristActivities=():TouristActivities=>({version:1,units:{}});

const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const exactKeys=(x:Record<string,unknown>,allowed:string[])=>Object.keys(x).every(key=>allowed.includes(key));
const stepFor=(unit:TouristUnit,mode:string)=>unit.steps.find(s=>s.mode===mode);

export function validateTouristActivities(input:unknown,units:readonly TouristUnit[]=TOURIST_UNITS):TouristActivities{
  if(!object(input)||input.version!==1||!object(input.units)||
    !exactKeys(input,['version','units'])||Object.keys(input.units).length>units.length)
    throw new Error('Invalid tourist activity record');
  const validated:TouristActivities=emptyTouristActivities();
  for(const [unitId,raw] of Object.entries(input.units)){
    const unit=units.find(u=>u.id===unitId);
    if(!unit||!object(raw)||!object(raw.tried)||
      !exactKeys(raw,['tried','cursor'])||
      !exactKeys(raw.tried,unit.steps.map(s=>s.mode)))
      throw new Error('Invalid tourist unit activity');
    const tried:TouristActivity['tried']={};
    for(const [mode,ids] of Object.entries(raw.tried)){
      const step=stepFor(unit,mode);
      if(!step||!Array.isArray(ids)||ids.length>step.itemIds.length||
        ids.some(id=>typeof id!=='string'||!step.itemIds.includes(id))||
        new Set(ids).size!==ids.length)
        throw new Error('Invalid tourist source item evidence');
      tried[step.mode]=[...ids];
    }
    let cursor:TouristCursor|undefined;
    if(raw.cursor!==undefined){
      if(!object(raw.cursor)||!exactKeys(raw.cursor,['mode','itemId'])||
        typeof raw.cursor.mode!=='string'||typeof raw.cursor.itemId!=='string'){
        throw new Error('Invalid tourist resume position');
      }
      const step=stepFor(unit,raw.cursor.mode);
      if(!step||!step.itemIds.includes(raw.cursor.itemId))throw new Error('Tourist resume source changed');
      cursor={mode:step.mode,itemId:raw.cursor.itemId};
    }
    validated.units[unitId]={tried,...(cursor?{cursor}:{})};
  }
  return validated;
}

/** No legacy inference: old per-source Learn/Read/Listen progress can originate
 * from another unit or normal Library. Only deliberate unit activity belongs here.
 */
export function parseTouristActivities(raw:string|null,units:readonly TouristUnit[]=TOURIST_UNITS):TouristActivities{
  if(!raw||raw.length>100_000)return emptyTouristActivities();
  try{return validateTouristActivities(JSON.parse(raw),units);}
  catch{return emptyTouristActivities();}
}

export function unitActivityCounts(state:TouristActivities,unit:TouristUnit){
  const total=unit.steps.reduce((sum,step)=>sum+step.itemIds.length,0);
  const tried=unit.steps.reduce((sum,step)=>
    sum+(state.units[unit.id]?.tried[step.mode]?.length??0),0);
  return {total,tried};
}

export function resumeTouristUnit(state:TouristActivities,unit:TouristUnit):
    {stepIndex:number;itemIndex:number}|null{
  const entry=state.units[unit.id];
  if(!entry?.cursor||unitActivityCounts(state,unit).tried===unitActivityCounts(state,unit).total)return null;
  const stepIndex=unit.steps.findIndex(s=>s.mode===entry.cursor?.mode);
  const itemIndex=unit.steps[stepIndex]?.itemIds.indexOf(entry.cursor.itemId)??-1;
  return stepIndex>=0&&itemIndex>=0?{stepIndex,itemIndex}:null;
}

/** Navigation only — never increments progress, scores, reviews or XP. */
export function positionTouristUnit(state:TouristActivities,unit:TouristUnit,
  stepIndex:number,itemId:string):TouristActivities{
  const step=unit.steps[stepIndex];
  if(!step||!step.itemIds.includes(itemId))return state;
  const prior=state.units[unit.id]??{tried:{}};
  return {...state,units:{...state.units,[unit.id]:{
    tried:prior.tried,cursor:{mode:step.mode,itemId}
  }}};
}

/** Record ONE real response / finished microphone take, not a play, reveal, skip
 * or an unrecorded Speak Next. Does not classify answer correctness or accent.
 */
export function triedTouristItem(state:TouristActivities,unit:TouristUnit,
  stepIndex:number,itemId:string):TouristActivities{
  const step=unit.steps[stepIndex];
  if(!step||!step.itemIds.includes(itemId))return state;
  const prior=state.units[unit.id]??{tried:{}};
  const seen=prior.tried[step.mode]??[];
  const tried={...prior.tried,[step.mode]:seen.includes(itemId)?seen:[...seen,itemId]};
  // Prefer the next untried item of the same mode; then the remainder of the
  // path, wrapping once to earlier modes. Skipped cards stay untried.
  const pending=(s:TouristUnitStep)=>s.itemIds.filter(id=>!(tried[s.mode]??[]).includes(id));
  const after=step.itemIds.slice(step.itemIds.indexOf(itemId)+1).filter(id=>pending(step).includes(id));
  const candidates:TouristCursor[]=[
    ...after.map(id=>({mode:step.mode,itemId:id})),
    ...pending(step).map(id=>({mode:step.mode,itemId:id})),
    ...[...unit.steps.slice(stepIndex+1),...unit.steps.slice(0,stepIndex)]
      .flatMap(s=>pending(s).map(id=>({mode:s.mode,itemId:id})))
  ];
  const cursor=candidates[0];
  return {...state,units:{...state.units,[unit.id]:{tried,...(cursor?{cursor}:{})}}};
}
