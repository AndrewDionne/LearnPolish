import {describe,expect,it} from 'vitest';
import type {Lesson} from './model';
import source from '../../content/tourist-units-v1.json';
import greetings from '../../../docs/sets/Conversation_1.json';
import reading from '../../../docs/sets/Basic_01R.json';
import numbers from '../../../docs/sets/numbers_1-20.json';
import shopping from '../../../docs/sets/Conversation_-_shopping.json';
import restaurant from '../../../docs/sets/Conversation_-_restaurant.json';
import food from '../../../docs/sets/Food_and_Dinning.json';
import grocery from '../../../docs/sets/Grocery_store_very_basic_shopping.json';
import directions from '../../../docs/sets/Getting_Around_1.json';
import tramDriver from '../../../docs/sets/Asking_the_tram_driver_for_directions.json';
import protectedSet from '../../content/additional-speak-reference-blockers.json';
const blocked=new Set(['Conversation_1:24','Conversation_1:25',...protectedSet.sourceBlockers.map(x=>x.itemId)]);
import {TOURIST_UNITS,validateTouristUnits,availableTouristUnits,unitStepItems,unitStepSource} from './tourist-units';

const fixture=(id:string,original:{cards?:{phrase:string;meaning:string}[];passages?:{polish:string;english:string}[]},kind:Lesson['kind']):Lesson=>{
  const items=(original.cards??original.passages??[]).map((x,index)=>({
    id:id+':'+index,polish:'phrase' in x?x.phrase:x.polish,
    english:'meaning' in x?x.meaning:x.english,
    audio:'source-reference-'+id+'-'+index+'.mp3',
    ...(blocked.has(id+':'+index)?{referenceReview:'practice_only' as const}:{})
  }));
  return {schemaVersion:1,id,title:id,kind,source:'legacy',items};
};
const all=[
  fixture('Conversation_1',greetings,'vocabulary'),
  fixture('Basic_01R',reading,'reading'),
  fixture('numbers_1-20',numbers,'vocabulary'),
  fixture('Conversation_-_shopping',shopping,'vocabulary'),
  fixture('Conversation_-_restaurant',restaurant,'vocabulary'),
  fixture('Food_and_Dinning',food,'vocabulary'),
  fixture('Grocery_store_very_basic_shopping',grocery,'reading'),
  fixture('Getting_Around_1',directions,'vocabulary'),
  fixture('Asking_the_tram_driver_for_directions',tramDriver,'reading')
];

describe('Source-only T01–T06 conversational path',()=>{
  it('keeps six ordered source-only units and T03/T04 missing Read honest',()=>{
    expect(validateTouristUnits(source)).toEqual(TOURIST_UNITS);
    expect(TOURIST_UNITS.map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T06']);
    expect(TOURIST_UNITS.map(x=>x.steps.map(y=>y.mode)))
      .toEqual([['listen','speak','read'],['listen','speak','read'],['listen','speak'],
        ['listen','speak'],['listen','speak','read'],['listen','speak','read']]);
    expect(TOURIST_UNITS.every(x=>x.journey===1)).toBe(true);
    expect(TOURIST_UNITS.map(x=>x.position)).toEqual(['beginning','beginning','beginning','middle','middle','middle']);
    expect(TOURIST_UNITS[2].gaps?.join('')).toMatch(/reading passage/i);
  });

  it('references exact immutable source rows with no copy, invented recording or protected target',()=>{
    expect(availableTouristUnits(all)).toHaveLength(6);
    for(const unit of TOURIST_UNITS)for(const step of unit.steps){
      const lesson=unitStepSource(all,step);
      expect(lesson?.id).toBe(step.lessonId);
      expect(unitStepItems(lesson!,step).map(x=>x.id)).toEqual(step.itemIds);
      expect(unitStepItems(lesson!,step).every(x=>!!x.audio && x.referenceReview!=='practice_only')).toBe(true);
    }
    expect(TOURIST_UNITS[0].steps[1].itemIds).toContain('Conversation_1:20');
    expect(TOURIST_UNITS.flatMap(x=>x.steps.flatMap(y=>y.itemIds))).not.toContain('Conversation_1:25');
    for(const id of TOURIST_UNITS.flatMap(x=>x.steps.flatMap(y=>y.itemIds)))expect(blocked.has(id)).toBe(false);
    expect(TOURIST_UNITS[3].gaps?.join('')).toMatch(/waiter reply/);
    expect(TOURIST_UNITS[4].gaps?.join('')).toMatch(/seller price/);
    expect(TOURIST_UNITS[5].gaps?.join('')).toMatch(/left, right or straight-ahead/);
  });

  it('fails closed when a source loses audio, gains a practice-only restriction or becomes personal',()=>{
    const withoutAudio=all.map(x=>x.id==='Basic_01R'
      ?{...x,items:x.items.map(y=>y.id==='Basic_01R:1'?{...y,audio:undefined}:y)}:x);
    expect(availableTouristUnits(withoutAudio).map(x=>x.id)).toEqual(['T02','T03','T04','T05','T06']);
    const invalid=all.map(x=>x.id==='Conversation_1'
      ?{...x,source:'personal' as const}:x);
    expect(availableTouristUnits(invalid).map(x=>x.id)).toEqual(['T03','T04','T05','T06']);
    const protectedAudio=all.map(x=>x.id==='Conversation_-_shopping'
      ?{...x,items:x.items.map(y=>y.id.endsWith(':0')?{...y,referenceReview:'practice_only' as const}:y)}:x);
    expect(availableTouristUnits(protectedAudio).map(x=>x.id)).toEqual(['T01','T02','T04','T06']);
    const removedGrocery=all.map(x=>x.id==='Grocery_store_very_basic_shopping'
      ?{...x,items:x.items.map(item=>item.id.endsWith(':4')?{...item,audio:undefined}:item)}:x);
    expect(availableTouristUnits(removedGrocery).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T06']);
    const unsafeRestaurant=all.map(x=>x.id==='Conversation_-_restaurant'
      ?{...x,items:x.items.map(item=>item.id.endsWith(':21')?{...item,referenceReview:'practice_only' as const}:item)}:x);
    expect(availableTouristUnits(unsafeRestaurant).map(x=>x.id)).toEqual(['T01','T02','T03','T05','T06']);
  });


  it('pins the new situations to their original Polish rather than newly generated target text',()=>{
    const expected=[
      ['Food_and_Dinning:0','Poproszę stolik dla jednej osoby','A table for one, please'],
      ['Food_and_Dinning:5','Poproszę zupę dnia','I’ll have the soup of the day'],
      ['Food_and_Dinning:17','Rachunek, proszę','The bill, please'],
      ['Conversation_-_restaurant:0','Poproszę menu','May I have the menu, please?'],
      ['Conversation_-_restaurant:7','Poproszę rachunek','The bill, please'],
      ['Conversation_-_restaurant:24','Czy mogę zapłacić kartą?','Can I pay by card?'],
      ['Grocery_store_very_basic_shopping:1','Dzień dobry, poproszę kilogram jabłek.','Good morning, I’d like a kilo of apples, please.'],
      ['Grocery_store_very_basic_shopping:2','Jakie jabłka pan lubi? Czerwone czy zielone?','Which apples do you like? Red or green?'],
      ['Grocery_store_very_basic_shopping:5','Nie, dziękuję. To wszystko.','No, thank you. That’s all.'],
      ['Conversation_-_shopping:5','Gdzie jest kasa?','Where is the checkout?'],
      ['Conversation_-_shopping:8','Poproszę paragon','Receipt, please'],
      ['Conversation_-_shopping:24','Wezmę to','I’ll take it'],
    ] as const;
    for(const [id,polish,english] of expected){
      const lesson=all.find(x=>id.startsWith(x.id+':'));
      const item=lesson?.items.find(x=>x.id===id);
      expect(item?.polish).toBe(polish);
      expect(item?.english).toBe(english);
      expect(TOURIST_UNITS.slice(3).some(u=>u.steps.some(s=>s.itemIds.includes(id)))).toBe(true);
    }
  });

  it('T06 matches exact recorded source lines and never promotes blocked directions',()=>{
    const unit=TOURIST_UNITS[5];
    expect(unit.steps.map(step=>[step.lessonId,step.itemIds.length])).toEqual([
      ['Asking_the_tram_driver_for_directions',5],['Getting_Around_1',6],
      ['Asking_the_tram_driver_for_directions',5]
    ]);
    const expected=[
      ['Getting_Around_1:0','Gdzie jest przystanek?','Where is the bus/tram stop?'],
      ['Getting_Around_1:1','Którędy do centrum?','Which way to the city center?'],
      ['Getting_Around_1:11','Jak dojechać do lotniska?','How do I get to the airport?'],
      ['Getting_Around_1:20','Czy ten tramwaj jedzie do centrum?','Does this tram go to the center?'],
      ['Getting_Around_1:22','Czy to daleko stąd?','Is it far from here?'],
      ['Asking_the_tram_driver_for_directions:1',
       'Przepraszam, czy tym tramwajem dojadę do centrum?',
       'Excuse me, does this tram go to the city centre?'],
      ['Asking_the_tram_driver_for_directions:2',
       'Tak, ten tramwaj jedzie do centrum.',
       'Yes, this tram goes to the centre.'],
      ['Asking_the_tram_driver_for_directions:4',
       'Proszę wysiąść na przystanku "Centrum".',
       'Please get off at the ‘Centrum’ stop.']
    ] as const;
    for(const [id,polish,english] of expected){
      const lesson=all.find(x=>id.startsWith(x.id+':'));
      const item=lesson?.items.find(x=>x.id===id);
      expect(item?.polish).toBe(polish);
      expect(item?.english).toBe(english);
      expect(unit.steps.some(step=>step.itemIds.includes(id))).toBe(true);
    }
    for(const step of unit.steps){
      expect(step.itemIds.every(id=>!blocked.has(id))).toBe(true);
      expect(step.itemIds).not.toContain('Getting_Around_1:23');
      expect(step.itemIds).not.toContain('Road_Terminology:10');
    }
    const missingTram=all.map(lesson=>lesson.id==='Asking_the_tram_driver_for_directions'
      ?{...lesson,items:lesson.items.map(item=>item.id.endsWith(':4')
        ?{...item,audio:undefined}:item)}:lesson);
    expect(availableTouristUnits(missingTram).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05']);
    const restricted=all.map(lesson=>lesson.id==='Getting_Around_1'
      ?{...lesson,items:lesson.items.map(item=>item.id.endsWith(':20')
        ?{...item,referenceReview:'practice_only' as const}:item)}:lesson);
    expect(availableTouristUnits(restricted).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05']);
  });

  it('rejects malformed order, duplicate IDs, unrelated/read-mode sources and fabricated gap data',()=>{
    const bad=[
      {...source,schemaVersion:2},
      {...source,units:[source.units[0],source.units[0],...source.units.slice(2)]},
      {...source,units:[{...source.units[0],steps:[source.units[0].steps[1],source.units[0].steps[0]]},...source.units.slice(1)]},
      {...source,units:[{...source.units[0],steps:[{...source.units[0].steps[0],itemIds:['Basic_01R:0','Basic_01R:0']},...source.units[0].steps.slice(1)]},...source.units.slice(1)]},
      {...source,units:[...source.units.slice(0,3),{...source.units[3],position:'beginning'},source.units[4]]},
      {...source,units:[...source.units.slice(0,4),{...source.units[4],steps:[...source.units[4].steps,{mode:'read',lessonId:'Grocery_store_very_basic_shopping',itemIds:['Grocery_store_very_basic_shopping:0']}]}]},
      {...source,units:[...source.units.slice(0,5),{...source.units[5],position:'end'}]},
      {...source,units:[...source.units.slice(0,5),{...source.units[5],steps:[...source.units[5].steps[0].itemIds.map(()=>source.units[5].steps[0])]}]},
    ];
    for(const data of bad)expect(()=>validateTouristUnits(data)).toThrow();
    expect(unitStepSource(all,{mode:'read',lessonId:'Conversation_1',itemIds:['Conversation_1:0']})).toBeNull();
    expect(unitStepSource(all,{mode:'speak',lessonId:'Basic_01R',itemIds:['Basic_01R:0']})).toBeNull();
  });
});
