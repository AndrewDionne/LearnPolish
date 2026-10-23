import {describe,expect,it} from 'vitest';
import {TOURIST_UNITS} from './tourist-units';
import {emptyTouristActivities,parseTouristActivities,positionTouristUnit,
  resumeTouristUnit,triedTouristItem,unitActivityCounts,validateTouristActivities} from './tourist-activity';

const unit=TOURIST_UNITS[1]; // T02 has the same source rows in Listen and Read
const first=unit.steps[0].itemIds[0];
const second=unit.steps[0].itemIds[1];
const speak=unit.steps[1].itemIds[0];
const read=unit.steps[2].itemIds[0];

describe('truthful independent unit activity / resume',()=>{
  it('counts only deliberately recorded actions in each mode, not source-wide history',()=>{
    const empty=emptyTouristActivities();
    expect(unitActivityCounts(empty,unit)).toEqual({total:5,tried:0});
    const started=positionTouristUnit(empty,unit,0,first);
    expect(unitActivityCounts(started,unit).tried).toBe(0);
    expect(resumeTouristUnit(started,unit)).toEqual({stepIndex:0,itemIndex:0});
    const answered=triedTouristItem(started,unit,0,first);
    expect(unitActivityCounts(answered,unit).tried).toBe(1);
    expect(resumeTouristUnit(answered,unit)).toEqual({stepIndex:0,itemIndex:1});
    const repeat=triedTouristItem(answered,unit,0,first);
    expect(unitActivityCounts(repeat,unit).tried).toBe(1);
    expect(empty).toEqual({version:1,units:{}});
  });
  it('skipping leaves the earlier source line untried and continues to that gap',()=>{
    const started=positionTouristUnit(emptyTouristActivities(),unit,0,first);
    const skipped=positionTouristUnit(started,unit,0,second);
    expect(unitActivityCounts(skipped,unit).tried).toBe(0);
    const done=triedTouristItem(skipped,unit,0,second);
    expect(resumeTouristUnit(done,unit)).toEqual({stepIndex:0,itemIndex:0});
  });
  it('separates repeated source IDs by unit AND mode, and never equates one answer with success',()=>{
    const spoken=triedTouristItem(emptyTouristActivities(),unit,1,speak);
    const reading=triedTouristItem(spoken,unit,2,read);
    expect(reading.units.T02.tried.speak).toEqual([speak]);
    expect(reading.units.T02.tried.read).toEqual([read]);
    expect(reading.units.T02.tried.listen).toBeUndefined();
    expect(unitActivityCounts(reading,unit).tried).toBe(2);
    expect(resumeTouristUnit(reading,unit)).toEqual({stepIndex:2,itemIndex:1});
    expect(unitActivityCounts(reading,TOURIST_UNITS[0]).tried).toBe(0);
  });
  it('hides resume after every original mode item has an explicit attempt',()=>{
    let state=emptyTouristActivities();
    for(let i=0;i<unit.steps.length;i++)
      for(const id of unit.steps[i].itemIds)state=triedTouristItem(state,unit,i,id);
    expect(unitActivityCounts(state,unit)).toEqual({total:5,tried:5});
    expect(resumeTouristUnit(state,unit)).toBeNull();
    expect(validateTouristActivities(state)).toEqual(state);
  });
  it('strictly rejects tampered, unrecognized and prototype-polluting backup entries',()=>{
    const record=positionTouristUnit(emptyTouristActivities(),unit,0,first);
    const bad=[
      {...record,version:2},
      {...record,units:{T99:record.units.T02}},
      {...record,units:{T02:{tried:{listen:[first,first]}}}},
      {...record,units:{T02:{tried:{listen:['personal_bad:0']}}}},
      {...record,units:{T02:{tried:{speak:[second]}}}},
      {...record,units:{T02:{tried:{listen:[first]},cursor:{mode:'read',itemId:speak}}}},
      {...record,units:{T02:{tried:{listen:[first]},score:100}}},
      {...record,units:{T02:{tried:{listen:[first]},cursor:{mode:'listen',itemId:first,mastery:1}}}},
    ];
    for(const sample of bad){
      expect(()=>validateTouristActivities(sample)).toThrow();
      expect(parseTouristActivities(JSON.stringify(sample))).toEqual(emptyTouristActivities());
    }
    expect(parseTouristActivities('invalid-json')).toEqual(emptyTouristActivities());
    expect(parseTouristActivities(JSON.stringify(record))).toEqual(record);
  });
  it('accepts a valid older empty state and refuses to mutate by bad IDs',()=>{
    const original=emptyTouristActivities();
    expect(triedTouristItem(original,unit,2,'made-up:25')).toBe(original);
    expect(positionTouristUnit(original,unit,-1,first)).toBe(original);
    expect(validateTouristActivities(original)).toEqual(original);
  });
});
