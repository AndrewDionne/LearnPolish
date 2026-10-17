import {expect,test} from 'vitest';
import {rankFamily,recognitionLabel,RECOGNITION_CATEGORIES} from './recognition';
import type {FamilyMember} from './api';
const alice:FamilyMember={id:1,name:'Alice',weekly_xp:50,active_days:2,highest_tier:2,team_xp:20};
const bob:FamilyMember={id:2,name:'Bob',weekly_xp:15,active_days:4,highest_tier:4,team_xp:15};
const cara:FamilyMember={id:3,name:'Cara',weekly_xp:50,active_days:2,highest_tier:1,team_xp:40};
const empty:FamilyMember={id:4,name:'Dale',weekly_xp:0,active_days:0,highest_tier:0,team_xp:0};

test('one private family can recognize effort, consistent attendance, higher-tier exploration and team XP separately',()=>{
 expect(rankFamily([alice,bob,cara],'effort').map(x=>[x.member.name,x.rank]))
  .toEqual([['Alice',1],['Cara',1],['Bob',3]]);
 expect(rankFamily([alice,bob,cara],'consistency')[0].member.name).toBe('Bob');
 expect(rankFamily([alice,bob,cara],'difficulty')[0].member.name).toBe('Bob');
 expect(rankFamily([alice,bob,cara],'team')[0].member.name).toBe('Cara');
});
test('no earned activity never creates a fictional champion and formatting is grounded',()=>{
 expect(rankFamily([empty],'effort')[0].rank).toBeNull();
 expect(recognitionLabel('consistency',1)).toBe('1 day');
 expect(recognitionLabel('consistency',2)).toBe('2 days');
 expect(recognitionLabel('difficulty',0)).toBe('—');
 expect(recognitionLabel('team',20)).toBe('20 map XP');
});
test('most improved remains a dedicated category, without generating unvalidated scores',()=>{
 expect(RECOGNITION_CATEGORIES.find(x=>x.id==='improvement')?.label).toBe('Most improved');
 expect(RECOGNITION_CATEGORIES).toHaveLength(5);
});
