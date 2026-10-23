import {describe,expect,it} from 'vitest';
import type {Lesson} from './model';
import source from '../../content/tourist-units-v1.json';
import greetings from '../../../docs/sets/Conversation_1.json';
import reading from '../../../docs/sets/Basic_01R.json';
import numbers from '../../../docs/sets/numbers_1-20.json';
import shopping from '../../../docs/sets/Conversation_-_shopping.json';
import {TOURIST_UNITS,validateTouristUnits,availableTouristUnits,unitStepItems,unitStepSource} from './tourist-units';

const fixture=(id:string,original:{cards?:{phrase:string;meaning:string}[];passages?:{polish:string;english:string}[]},kind:Lesson['kind']):Lesson=>{
  const items=(original.cards??original.passages??[]).map((x,index)=>({
    id:id+':'+index,polish:'phrase' in x?x.phrase:x.polish,
    english:'meaning' in x?x.meaning:x.english,
    audio:'source-reference-'+id+'-'+index+'.mp3',
    ...((id==='Conversation_1' && index>=24)?{referenceReview:'practice_only' as const}:{})
  }));
  return {schemaVersion:1,id,title:id,kind,source:'legacy',items};
};
const all=[
  fixture('Conversation_1',greetings,'vocabulary'),
  fixture('Basic_01R',reading,'reading'),
  fixture('numbers_1-20',numbers,'vocabulary'),
  fixture('Conversation_-_shopping',shopping,'vocabulary')
];

describe('Source-only T01–T03 conversational pilot',()=>{
  it('keeps exactly three ordered, original-source units and missing T03 Read honest',()=>{
    expect(validateTouristUnits(source)).toEqual(TOURIST_UNITS);
    expect(TOURIST_UNITS.map(x=>x.id)).toEqual(['T01','T02','T03']);
    expect(TOURIST_UNITS.map(x=>x.steps.map(y=>y.mode)))
      .toEqual([['listen','speak','read'],['listen','speak','read'],['listen','speak']]);
    expect(TOURIST_UNITS.every(x=>x.journey===1 && x.position==='beginning')).toBe(true);
    expect(TOURIST_UNITS[2].gaps?.join('')).toMatch(/reading passage/i);
  });

  it('references exact immutable source rows with no copy, invented recording or protected target',()=>{
    expect(availableTouristUnits(all)).toHaveLength(3);
    for(const unit of TOURIST_UNITS)for(const step of unit.steps){
      const lesson=unitStepSource(all,step);
      expect(lesson?.id).toBe(step.lessonId);
      expect(unitStepItems(lesson!,step).map(x=>x.id)).toEqual(step.itemIds);
      expect(unitStepItems(lesson!,step).every(x=>!!x.audio && x.referenceReview!=='practice_only')).toBe(true);
    }
    expect(TOURIST_UNITS[0].steps[1].itemIds).toContain('Conversation_1:20');
    expect(TOURIST_UNITS.flatMap(x=>x.steps.flatMap(y=>y.itemIds))).not.toContain('Conversation_1:25');
  });

  it('fails closed when a source loses audio, gains a practice-only restriction or becomes personal',()=>{
    const withoutAudio=all.map(x=>x.id==='Basic_01R'
      ?{...x,items:x.items.map(y=>y.id==='Basic_01R:1'?{...y,audio:undefined}:y)}:x);
    expect(availableTouristUnits(withoutAudio).map(x=>x.id)).toEqual(['T02','T03']);
    const invalid=all.map(x=>x.id==='Conversation_1'
      ?{...x,source:'personal' as const}:x);
    expect(availableTouristUnits(invalid).map(x=>x.id)).toEqual(['T03']);
    const protectedAudio=all.map(x=>x.id==='Conversation_-_shopping'
      ?{...x,items:x.items.map(y=>y.id.endsWith(':0')?{...y,referenceReview:'practice_only' as const}:y)}:x);
    expect(availableTouristUnits(protectedAudio).map(x=>x.id)).toEqual(['T01','T02']);
  });

  it('rejects malformed order, duplicate IDs, unrelated/read-mode sources and fabricated gap data',()=>{
    const bad=[
      {...source,schemaVersion:2},
      {...source,units:[source.units[0],source.units[0],source.units[2]]},
      {...source,units:[{...source.units[0],steps:[source.units[0].steps[1],source.units[0].steps[0]]},...source.units.slice(1)]},
      {...source,units:[{...source.units[0],steps:[{...source.units[0].steps[0],itemIds:['Basic_01R:0','Basic_01R:0']},...source.units[0].steps.slice(1)]},...source.units.slice(1)]},
    ];
    for(const data of bad)expect(()=>validateTouristUnits(data)).toThrow();
    expect(unitStepSource(all,{mode:'read',lessonId:'Conversation_1',itemIds:['Conversation_1:0']})).toBeNull();
    expect(unitStepSource(all,{mode:'speak',lessonId:'Basic_01R',itemIds:['Basic_01R:0']})).toBeNull();
  });
});
