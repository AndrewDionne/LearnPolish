import {describe,it,expect} from 'vitest';
import type {StarterGroup} from './foundation-first-expressions';
import {FIRST_EXPRESSION_GROUPS} from './foundation-first-expressions';
import {NEXT_WORD_GROUPS} from './foundation-next-words';
import {
 FOUNDATION_STAGES,FIRST_WORD_ORDER,BASIC_VOCABULARY_ORDER,FIRST_SENTENCE_PRACTICE_ORDER,orderedFoundationGroups
} from './foundation-progression';

describe('C-12: explicitly sequenced foundational study',()=>{
 it('delivers the requested visible learning progression in order',()=>{
  expect(FOUNDATION_STAGES).toEqual([
   'First words','Basic vocabulary','First sentences / basic grammar'
  ]);
  expect(FIRST_WORD_ORDER).toEqual(['simple-replies','politeness','greetings']);
  expect(BASIC_VOCABULARY_ORDER).toEqual([
   'street-words','transport-words','everyday-replies'
  ]);
  expect(FIRST_SENTENCE_PRACTICE_ORDER).toEqual([
   'food-requests','shopping-questions','location-questions'
  ]);
 });
 it('reorders only original source-backed C05 and C06 groups, without altering 40 source IDs, titles or recordings',()=>{
  const first=[...FIRST_EXPRESSION_GROUPS];
  const expanded=[...NEXT_WORD_GROUPS];
  const ordered=orderedFoundationGroups(first,expanded);
  expect(ordered.firstWords.map(x=>x.id)).toEqual(FIRST_WORD_ORDER);
  expect(ordered.basicVocabulary.map(x=>x.id)).toEqual(BASIC_VOCABULARY_ORDER);
  expect(ordered.firstSentences.map(x=>x.id)).toEqual(FIRST_SENTENCE_PRACTICE_ORDER);
  expect(ordered.firstWords.flatMap(x=>x.itemIds)).toHaveLength(8);
  expect(ordered.basicVocabulary.flatMap(x=>x.itemIds)).toHaveLength(17);
  expect(ordered.firstSentences.flatMap(x=>x.itemIds)).toHaveLength(15);
  expect(ordered.firstWords.every(x=>first.includes(x))).toBe(true);
  expect(ordered.basicVocabulary.every(x=>expanded.includes(x))).toBe(true);
  expect(ordered.firstSentences.every(x=>expanded.includes(x))).toBe(true);
  const sourceKeys=[...first,...expanded].flatMap(x=>x.itemIds);
  const reordered=[...ordered.firstWords,...ordered.basicVocabulary,...ordered.firstSentences].flatMap(x=>x.itemIds);
  expect(new Set(sourceKeys)).toEqual(new Set(reordered));
  expect(new Set(reordered).size).toBe(40);
 });
 it('fails closed on duplicated or unknown group aliases; missing recordings only remove their actual group',()=>{
  expect(()=>orderedFoundationGroups(FIRST_EXPRESSION_GROUPS,
   [...NEXT_WORD_GROUPS,FIRST_EXPRESSION_GROUPS[0]])).toThrow(/Duplicate/);
  const alien:StarterGroup={id:'unreviewed-lesson',title:'Not in course',
   lessonId:'personal_random',itemIds:['fake:1']};
  expect(()=>orderedFoundationGroups([...FIRST_EXPRESSION_GROUPS,alien],NEXT_WORD_GROUPS))
   .toThrow(/Unrecognized/);
  const reduced=orderedFoundationGroups(FIRST_EXPRESSION_GROUPS.slice(1),NEXT_WORD_GROUPS.slice(1));
  expect(reduced.firstWords.map(g=>g.id)).toEqual(['simple-replies','politeness']);
  expect(reduced.basicVocabulary.map(g=>g.id)).toEqual(BASIC_VOCABULARY_ORDER.filter(id=>id!=='everyday-replies'));
  expect(reduced.firstSentences.map(g=>g.id)).toEqual(FIRST_SENTENCE_PRACTICE_ORDER);
 });
});
