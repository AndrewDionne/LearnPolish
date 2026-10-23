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
  it('retains previously saved T01–T05 attempts after T06 is appended and round-trips T06 exactly',()=>{
    const t05=TOURIST_UNITS[4];
    const t06=TOURIST_UNITS[5];
    expect(t06.id).toBe('T06');
    const old=triedTouristItem(emptyTouristActivities(),t05,0,t05.steps[0].itemIds[0]);
    const migrated=validateTouristActivities(old);
    expect(migrated.units.T05.tried.listen).toEqual([t05.steps[0].itemIds[0]]);
    expect(unitActivityCounts(migrated,t06)).toEqual({tried:0,total:16});
    const newState=triedTouristItem(migrated,t06,0,t06.steps[0].itemIds[0]);
    expect(newState.units.T05).toEqual(migrated.units.T05);
    expect(newState.units.T06.tried.listen).toEqual([t06.steps[0].itemIds[0]]);
    expect(resumeTouristUnit(newState,t06)).toEqual({stepIndex:0,itemIndex:1});
    expect(parseTouristActivities(JSON.stringify(newState))).toEqual(newState);
    const forged={...newState,units:{...newState.units,T06:{tried:{
      speak:['Getting_Around_1:23']}}}};
    expect(()=>validateTouristActivities(forged)).toThrow(/source item evidence/);
    expect(parseTouristActivities(JSON.stringify(forged))).toEqual(emptyTouristActivities());
  });

  it('adds T07 without changing prior saved unit attempts even when T06 and T07 repeat a source scene',()=>{
    const t06=TOURIST_UNITS[5],t07=TOURIST_UNITS[6];
    expect(t07.id).toBe('T07');
    expect(unitActivityCounts(emptyTouristActivities(),t07)).toEqual({tried:0,total:24});
    const repeated='Asking_the_tram_driver_for_directions:1';
    const before=triedTouristItem(emptyTouristActivities(),t06,0,repeated);
    const after=triedTouristItem(before,t07,0,repeated);
    expect(after.units.T06.tried.listen).toEqual([repeated]);
    expect(after.units.T07.tried.listen).toEqual([repeated]);
    expect(after.units.T07.tried.read).toBeUndefined();
    expect(unitActivityCounts(after,t06).tried).toBe(1);
    expect(unitActivityCounts(after,t07).tried).toBe(1);
    expect(parseTouristActivities(JSON.stringify(after))).toEqual(after);
    const old=validateTouristActivities(before);
    expect(old.units.T07).toBeUndefined();
    expect(resumeTouristUnit(old,t07)).toBeNull();
    const forged={...after,units:{...after.units,T07:{tried:{speak:['Transit_1:4']}}}};
    expect(()=>validateTouristActivities(forged)).toThrow(/source item evidence/);
  });

  it('preserves T01–T07 attempts when T08 is added and isolates reused ticket phrases from T07',()=>{
    const t07=TOURIST_UNITS[6],t08=TOURIST_UNITS[7];
    expect(t08.id).toBe('T08');
    expect(unitActivityCounts(emptyTouristActivities(),t08)).toEqual({total:25,tried:0});
    const repeated='Getting_Around_1:6';
    const old=triedTouristItem(emptyTouristActivities(),t07,1,repeated);
    expect(validateTouristActivities(old).units.T07.tried.speak).toEqual([repeated]);
    expect(validateTouristActivities(old).units.T08).toBeUndefined();
    const withNew=triedTouristItem(old,t08,1,repeated);
    expect(withNew.units.T07.tried.speak).toEqual([repeated]);
    expect(withNew.units.T08.tried.speak).toEqual([repeated]);
    expect(unitActivityCounts(withNew,t08).tried).toBe(1);
    expect(unitActivityCounts(withNew,t07).tried).toBe(1);
    expect(parseTouristActivities(JSON.stringify(withNew))).toEqual(withNew);
    const resumed=positionTouristUnit(withNew,t08,0,t08.steps[0].itemIds[4]);
    expect(resumeTouristUnit(resumed,t08)).toEqual({stepIndex:0,itemIndex:4});
    const unsafe={...withNew,units:{...withNew.units,T08:{tried:{speak:['Museum_buying_tickets_and_basic_info:4']}}}};
    expect(()=>validateTouristActivities(unsafe)).toThrow(/source item evidence/);
  });

  it('accepts a valid older empty state and refuses to mutate by bad IDs',()=>{
    const original=emptyTouristActivities();
    expect(triedTouristItem(original,unit,2,'made-up:25')).toBe(original);
    expect(positionTouristUnit(original,unit,-1,first)).toBe(original);
    expect(validateTouristActivities(original)).toEqual(original);
  });
});
