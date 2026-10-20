import assert from 'node:assert/strict';
import {test} from 'node:test';
import {draftWordParts,pronunciationSegmentsFor,attachPronunciationSegments,parsePronunciationOverrides} from './pronunciation-segments.mjs';

test('normal Speak source words receive reversible draft sound groups',()=>{
  assert.deepEqual(draftWordParts('ulica'),['u','li','ca']);
  for(const polish of ['Dzień dobry','Proszę bardzo','Cześć!','Krzysztof Wiśniewski','Czy mogę to przymierzyć?']){
    const parts=pronunciationSegmentsFor({polish});
    assert.ok(parts,polish);
    assert.equal(parts.segments.join(''),polish);
    assert.equal(parts.method,'draft-orthographic-v1');
    assert.ok(parts.segments.every(p=>p.trim().length));
  }
});
test('authored Świętokrzyska boundaries take precedence over draft heuristic',()=>{
  const item={polish:'Świętokrzyska',pronunciationGuide:{
    syllables:['Świę','to','krzy','ska'].map(polish=>({polish}))}};
  assert.deepEqual(pronunciationSegmentsFor(item),{
    method:'authored-v1',segments:['Świę','to','krzy','ska']});
});
test('does not invent groups for unsupported or overlong items',()=>{
  assert.equal(pronunciationSegmentsFor({polish:' '.repeat(5)}),undefined);
  assert.equal(pronunciationSegmentsFor({polish:'abc'.repeat(101)}),undefined);
  assert.equal(pronunciationSegmentsFor({polish:'123-45'}),undefined);
});
test('backfills every eligible lesson item deterministically and preserves exact text',()=>{
  const lessons=[{items:[{polish:'ulica'},{polish:'Dzień dobry'},
     {polish:'Świętokrzyska',pronunciationGuide:{syllables:['Świę','to','krzy','ska'].map(polish=>({polish}))}}]}];
  assert.deepEqual(attachPronunciationSegments(lessons),{total:3,drafts:2,authored:1,editorial:0});
  assert.deepEqual(lessons[0].items[0].pronunciationSegments.segments,['u','li','ca']);
  for(const item of lessons[0].items)assert.equal(item.pronunciationSegments.segments.join(''),item.polish);
});

test('editable pronunciation boundaries override the generated draft without ever changing original word',()=>{
  const entries={schemaVersion:1,reviewStatus:'needs_native_speaker_review',
    items:[{polish:'ulica',segments:['u','li','ca']},
           {polish:'Dzień dobry',segments:['Dzień ','do','bry']}]};
  const dictionary=parsePronunciationOverrides(entries);
  const lessons=[{items:[{polish:'ulica'},{polish:'Dzień dobry'},{polish:'Rondo'}]}];
  const result=attachPronunciationSegments(lessons,dictionary);
  assert.deepEqual(result,{total:3,drafts:1,authored:0,editorial:2});
  assert.deepEqual(lessons[0].items[1].pronunciationSegments,{
    method:'editorial-draft-v1',segments:['Dzień ','do','bry']});
  assert.equal(lessons[0].items[0].polish,'ulica');
  for(const item of lessons[0].items)assert.equal(
    item.pronunciationSegments.segments.join(''),item.polish);
  for(const malformed of [
    {...entries,items:[{polish:'ulica',segments:['ul','WRONG']}]},
    {...entries,items:[...entries.items,entries.items[0]]},
    {...entries,reviewStatus:'verified-native'}
  ])assert.throws(()=>parsePronunciationOverrides(malformed));
  assert.throws(()=>attachPronunciationSegments([{items:[{polish:'abc'}]}],dictionary),
                /Orphaned pronunciation override/);
});
