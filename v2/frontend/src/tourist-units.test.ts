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
import museum from '../../../docs/sets/Museum_buying_tickets_and_basic_info.json';
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
  fixture('Asking_the_tram_driver_for_directions',tramDriver,'reading'),
  fixture('Museum_buying_tickets_and_basic_info',museum,'reading')
];

describe('Source-only T01–T08 conversational path',()=>{
  it('keeps eight ordered source-only units and T03/T04 missing Read honest',()=>{
    expect(validateTouristUnits(source)).toEqual(TOURIST_UNITS);
    expect(TOURIST_UNITS.map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T06','T07','T08']);
    expect(TOURIST_UNITS.map(x=>x.steps.map(y=>y.mode)))
      .toEqual([['listen','speak','read'],['listen','speak','read'],['listen','speak'],
        ['listen','speak'],['listen','speak','read'],['listen','speak','read'],['listen','speak','read'],['listen','speak','read']]);
    expect(TOURIST_UNITS.every(x=>x.journey===1)).toBe(true);
    expect(TOURIST_UNITS.map(x=>x.position)).toEqual(['beginning','beginning','beginning','middle','middle','middle','middle','middle']);
    expect(TOURIST_UNITS[2].gaps?.join('')).toMatch(/reading passage/i);
  });

  it('references exact immutable source rows with no copy, invented recording or protected target',()=>{
    expect(availableTouristUnits(all)).toHaveLength(8);
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
    expect(TOURIST_UNITS[6].gaps?.join('')).toMatch(/ticket-machine/);
    expect(TOURIST_UNITS[6].gaps?.join('')).toMatch(/timetable/);
    expect(TOURIST_UNITS[7].gaps?.join('')).toMatch(/opening time/);
  });

  it('fails closed when a source loses audio, gains a practice-only restriction or becomes personal',()=>{
    const withoutAudio=all.map(x=>x.id==='Basic_01R'
      ?{...x,items:x.items.map(y=>y.id==='Basic_01R:1'?{...y,audio:undefined}:y)}:x);
    expect(availableTouristUnits(withoutAudio).map(x=>x.id)).toEqual(['T02','T03','T04','T05','T06','T07','T08']);
    const invalid=all.map(x=>x.id==='Conversation_1'
      ?{...x,source:'personal' as const}:x);
    expect(availableTouristUnits(invalid).map(x=>x.id)).toEqual(['T03','T04','T05','T06','T07','T08']);
    const protectedAudio=all.map(x=>x.id==='Conversation_-_shopping'
      ?{...x,items:x.items.map(y=>y.id.endsWith(':0')?{...y,referenceReview:'practice_only' as const}:y)}:x);
    expect(availableTouristUnits(protectedAudio).map(x=>x.id)).toEqual(['T01','T02','T04','T06','T07','T08']);
    const removedGrocery=all.map(x=>x.id==='Grocery_store_very_basic_shopping'
      ?{...x,items:x.items.map(item=>item.id.endsWith(':4')?{...item,audio:undefined}:item)}:x);
    expect(availableTouristUnits(removedGrocery).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T06','T07','T08']);
    const unsafeRestaurant=all.map(x=>x.id==='Conversation_-_restaurant'
      ?{...x,items:x.items.map(item=>item.id.endsWith(':21')?{...item,referenceReview:'practice_only' as const}:item)}:x);
    expect(availableTouristUnits(unsafeRestaurant).map(x=>x.id)).toEqual(['T01','T02','T03','T05','T06','T07','T08']);
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
    expect(availableTouristUnits(missingTram).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T08']);
    const restricted=all.map(lesson=>lesson.id==='Getting_Around_1'
      ?{...lesson,items:lesson.items.map(item=>item.id.endsWith(':20')
        ?{...item,referenceReview:'practice_only' as const}:item)}:lesson);
    expect(availableTouristUnits(restricted).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T07','T08']);
  });

  it('T07 is exact source-backed route+ticket listening, spoken requests and reading, with no invented line reply',()=>{
    const unit=TOURIST_UNITS[6];
    expect(unit.steps.map(s=>[s.lessonId,s.itemIds.length])).toEqual([
      ['Asking_the_tram_driver_for_directions',8],
      ['Getting_Around_1',8],
      ['Asking_the_tram_driver_for_directions',8]
    ]);
    expect(unit.steps[0].itemIds).toEqual(Array.from({length:8},(_,i)=>'Asking_the_tram_driver_for_directions:'+i));
    expect(unit.steps[1].itemIds).toEqual([3,4,6,7,8,9,14,17].map(i=>'Getting_Around_1:'+i));
    const expected=[
      ['Asking_the_tram_driver_for_directions:5','Czy mogę kupić bilet w tramwaju?','Can I buy a ticket on the tram?'],
      ['Asking_the_tram_driver_for_directions:6','Tak, może pan kupić bilet w automacie.','Yes, you can buy a ticket in the machine.'],
      ['Asking_the_tram_driver_for_directions:7','Dziękuję bardzo, do widzenia.','Thank you very much, goodbye.'],
      ['Getting_Around_1:3','Na którą linię?','For which line?'],
      ['Getting_Around_1:4','Który to peron?','Which platform is this?'],
      ['Getting_Around_1:6','Jeden bilet, proszę','One ticket, please'],
      ['Getting_Around_1:7','Dwa bilety, proszę','Two tickets, please'],
      ['Getting_Around_1:8','Bilet normalny','Regular ticket'],
      ['Getting_Around_1:9','Bilet ulgowy','Discounted ticket'],
      ['Getting_Around_1:14','Ile kosztuje bilet?','How much is the ticket?'],
      ['Getting_Around_1:17','Gdzie mogę kupić bilet?','Where can I buy a ticket?']
    ] as const;
    for(const [id,polish,english] of expected){
      const lesson=all.find(x=>id.startsWith(x.id+':'));
      const item=lesson?.items.find(x=>x.id===id);
      expect(item?.polish).toBe(polish);
      expect(item?.english).toBe(english);
      expect(unit.steps.some(s=>s.itemIds.includes(id))).toBe(true);
      expect(blocked.has(id)).toBe(false);
    }
    expect(unit.steps.flatMap(s=>s.itemIds)).not.toContain('Transit_1:4');
    const missingTicket=all.map(lesson=>lesson.id==='Asking_the_tram_driver_for_directions'
      ?{...lesson,items:lesson.items.map(item=>item.id.endsWith(':6')?{...item,audio:undefined}:item)}:lesson);
    expect(availableTouristUnits(missingTicket).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T06','T08']);
    const restrictedTicket=all.map(lesson=>lesson.id==='Getting_Around_1'
      ?{...lesson,items:lesson.items.map(item=>item.id.endsWith(':17')
        ?{...item,referenceReview:'practice_only' as const}:item)}:lesson);
    expect(availableTouristUnits(restrictedTicket).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T06','T08']);
    const replacedWithPersonal=all.map(lesson=>lesson.id==='Asking_the_tram_driver_for_directions'
      ?{...lesson,source:'personal' as const}:lesson);
    expect(availableTouristUnits(replacedWithPersonal).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T08']);
  });

  it('T08 maps complete original museum exchange and generic source ticket Speak without falsely authoring museum audio',()=>{
    const unit=TOURIST_UNITS[7];
    expect(unit.steps.map(s=>[s.lessonId,s.itemIds.length])).toEqual([
      ['Museum_buying_tickets_and_basic_info',9],
      ['Getting_Around_1',7],
      ['Museum_buying_tickets_and_basic_info',9]
    ]);
    const originalIds=Array.from({length:9},(_,i)=>'Museum_buying_tickets_and_basic_info:'+i);
    expect(unit.steps[0].itemIds).toEqual(originalIds);
    expect(unit.steps[2].itemIds).toEqual(originalIds);
    expect(unit.steps[1].itemIds).toEqual([6,7,8,9,14,15,17].map(i=>'Getting_Around_1:'+i));
    const expected=[
      ['Museum_buying_tickets_and_basic_info:0','Dzień dobry, poproszę dwa bilety do muzeum.','Good morning, two tickets to the museum, please.'],
      ['Museum_buying_tickets_and_basic_info:1','Normalne czy ulgowe?','Regular or reduced tickets?'],
      ['Museum_buying_tickets_and_basic_info:3','Do której godziny muzeum jest otwarte?','Until what time is the museum open?'],
      ['Museum_buying_tickets_and_basic_info:4','Dzisiaj jesteśmy otwarci do osiemnastej.','Today we are open until six p.m.'],
      ['Museum_buying_tickets_and_basic_info:5','Gdzie jest szatnia, proszę?','Where is the cloakroom, please?'],
      ['Museum_buying_tickets_and_basic_info:6','Szatnia jest na prawo, za schodami.','The cloakroom is on the right, past the stairs.'],
      ['Museum_buying_tickets_and_basic_info:7','Pierwsza wystawa jest na pierwszym piętrze.','The first exhibition is on the first floor.'],
      ['Getting_Around_1:6','Jeden bilet, proszę','One ticket, please'],
      ['Getting_Around_1:9','Bilet ulgowy','Discounted ticket'],
      ['Getting_Around_1:15','Czy mogę zapłacić kartą?','Can I pay by card?']
    ] as const;
    for(const [id,polish,english] of expected){
      const lesson=all.find(x=>id.startsWith(x.id+':'));
      const item=lesson?.items.find(x=>x.id===id);
      expect(item?.polish).toBe(polish);
      expect(item?.english).toBe(english);
      expect(unit.steps.some(step=>step.itemIds.includes(id))).toBe(true);
      expect(blocked.has(id)).toBe(false);
    }
    const noAudio=all.map(lesson=>lesson.id==='Museum_buying_tickets_and_basic_info'
      ?{...lesson,items:lesson.items.map(item=>item.id.endsWith(':4')
        ?{...item,audio:undefined}:item)}:lesson);
    expect(availableTouristUnits(noAudio).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T06','T07']);
    const unsafeSpeak=all.map(lesson=>lesson.id==='Getting_Around_1'
      ?{...lesson,items:lesson.items.map(item=>item.id.endsWith(':15')
        ?{...item,referenceReview:'practice_only' as const}:item)}:lesson);
    expect(availableTouristUnits(unsafeSpeak).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T06','T07']);
    const personal=all.map(lesson=>lesson.id==='Museum_buying_tickets_and_basic_info'
      ?{...lesson,source:'personal' as const}:lesson);
    expect(availableTouristUnits(personal).map(x=>x.id)).toEqual(['T01','T02','T03','T04','T05','T06','T07']);
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
      {...source,units:[...source.units.slice(0,5),{...source.units[5],steps:[...source.units[5].steps[0].itemIds.map(()=>source.units[5].steps[0])]},source.units[6]]},
      {...source,units:[...source.units.slice(0,6),{...source.units[6],order:8}]},
      {...source,units:[...source.units.slice(0,6),{...source.units[6],steps:[source.units[6].steps[1],source.units[6].steps[0],source.units[6].steps[2]]},source.units[7]]},
      {...source,units:[...source.units.slice(0,7),{...source.units[7],order:9}]},
      {...source,units:[...source.units.slice(0,7),{...source.units[7],steps:[source.units[7].steps[1],source.units[7].steps[0],source.units[7].steps[2]]}]},
    ];
    for(const data of bad)expect(()=>validateTouristUnits(data)).toThrow();
    expect(unitStepSource(all,{mode:'read',lessonId:'Conversation_1',itemIds:['Conversation_1:0']})).toBeNull();
    expect(unitStepSource(all,{mode:'speak',lessonId:'Basic_01R',itemIds:['Basic_01R:0']})).toBeNull();
  });
});
