import {describe,expect,it} from 'vitest';
import raw from '../../content/journey1-prerequisites-v1.json';
import {FIRST_EXPRESSION_GROUPS} from './foundation-first-expressions';
import {NEXT_WORD_GROUPS} from './foundation-next-words';
import {SENTENCE_PATTERN_SOURCE} from './foundation-sentence-patterns';
import {orderedFoundationGroups} from './foundation-progression';
import {
 JOURNEY1_PREREQUISITES,validateJourney1Prerequisites,prerequisiteCompletePath
} from './journey1-prerequisites';

const orig=orderedFoundationGroups(FIRST_EXPRESSION_GROUPS,NEXT_WORD_GROUPS);
const patterns=SENTENCE_PATTERN_SOURCE.map(x=>({...x,examples:x.examples.map(e=>({
 itemId:e.sourceLesson+':'+e.index,polish:e.polish,english:e.english,focus:e.focus,
 audio:'generated/audio/'+encodeURIComponent(e.sourceLesson)+'/'+e.index+'.mp3'
}))}));
const build=(
 first=orig.firstWords,basic=orig.basicVocabulary,
 grammar=patterns,apply=orig.firstSentences
)=>prerequisiteCompletePath(first,basic,grammar,apply);
const clone=<T,>(v:T):T=>structuredClone(v);

describe('C-13: no assumed out-of-app prerequisite curriculum',()=>{
 it('validates the exact 16-unit teaching dependency path, no future knowledge allowed',()=>{
  expect(validateJourney1Prerequisites(raw)).toEqual(JOURNEY1_PREREQUISITES);
  expect(JOURNEY1_PREREQUISITES).toHaveLength(16);
  expect(JOURNEY1_PREREQUISITES.map(x=>x.id)).toEqual([
   'simple-replies','politeness','greetings',
   'street-words','transport-words','everyday-replies',
   'grammar:requests','grammar:where','grammar:permission','grammar:prices',
   'grammar:yes-no-questions','grammar:negative','grammar:one-two',
   'food-requests','shopping-questions','location-questions'
  ]);
  expect(JOURNEY1_PREREQUISITES.find(x=>x.id==='shopping-questions')?.requires)
    .toEqual(expect.arrayContaining(['request-poprosze','where-is','can-i','how-much','is-this']));
 });
 it('resolves full source-backed path with 40 unique first/basics/sentence focus recordings and seven grammar lessons',()=>{
  const path=build();
  expect(path.blocked).toEqual([]);
  expect(path.firstWords.flatMap(g=>g.itemIds)).toHaveLength(8);
  expect(path.basicVocabulary.flatMap(g=>g.itemIds)).toHaveLength(17);
  expect(path.firstSentences.flatMap(g=>g.itemIds)).toHaveLength(15);
  expect(path.patterns.map(x=>x.id)).toEqual([
   'requests','where','permission','prices','yes-no-questions','negative','one-two'
  ]);
  expect(path.patterns.flatMap(x=>x.examples)).toHaveLength(28);
  const originalIds=[...path.firstWords,...path.basicVocabulary,...path.firstSentences]
    .flatMap(g=>g.itemIds);
  expect(new Set(originalIds).size).toBe(40);
 });
 it('withholds every dependent application when an earlier introducing lesson is missing',()=>{
  const withoutPoliteness=build(
   orig.firstWords.filter(g=>g.id!=='politeness'));
  expect(withoutPoliteness.blocked.map(x=>x.id)).toContain('grammar:requests');
  expect(withoutPoliteness.blocked.map(x=>x.id)).toContain('grammar:permission');
  expect(withoutPoliteness.firstSentences.map(x=>x.id))
    .not.toContain('shopping-questions');
  expect(withoutPoliteness.patterns.map(x=>x.id)).not.toContain('requests');

  const withoutPrices=build(
   orig.firstWords,orig.basicVocabulary,patterns.filter(g=>g.id!=='prices'));
  expect(withoutPrices.firstSentences.map(g=>g.id)).not.toContain('shopping-questions');
  expect(withoutPrices.firstSentences.map(g=>g.id)).not.toContain('location-questions');
  expect(withoutPrices.blocked.find(g=>g.id==='shopping-questions')?.missing)
    .toContain('how-much');

  const noTransport=build(orig.firstWords,orig.basicVocabulary.filter(g=>g.id!=='transport-words'));
  expect(noTransport.patterns.map(g=>g.id)).not.toContain('prices');
  expect(noTransport.patterns.map(g=>g.id)).not.toContain('one-two');
 });
 it('rejects any forward, missing, duplicate or newly invented curriculum concept with no introduction',()=>{
  const bad=clone(raw);
  bad.steps[1].requires=['how-much'];
  expect(()=>validateJourney1Prerequisites(bad)).toThrow();
  const duplicate=clone(raw);
  duplicate.steps[2].introduces=['politeness'];
  expect(()=>validateJourney1Prerequisites(duplicate)).toThrow();
  const forged=clone(raw);
  Object.assign(forged,{nativeCertified:true});
  expect(()=>validateJourney1Prerequisites(forged)).toThrow();
  const rearrange=clone(raw);
  [rearrange.steps[0],rearrange.steps[14]]=[rearrange.steps[14],rearrange.steps[0]];
  expect(()=>validateJourney1Prerequisites(rearrange)).toThrow();
 });
});
