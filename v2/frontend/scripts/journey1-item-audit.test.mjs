import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {verifyItemAudit,BASIC,READING} from './journey1-item-audit.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const saved=JSON.parse(fs.readFileSync(
 path.join(root,'v2/content/journey1-item-prerequisite-audit-v1.json'),'utf8'));
const clone=()=>structuredClone(saved);

test('C-15 covers all 172 original basic and 51 original Read utterances without certifying grammar',()=>{
 assert.equal(BASIC.length,7);
 assert.equal(READING.length,6);
 assert.deepEqual(verifyItemAudit(),{
  basic:172,reading:51,total:223,firstObservedWordForms:292,grammarReviewApproved:0
 });
 assert.equal(saved.rows.filter(x=>x.kind==='basic').length,172);
 assert.equal(saved.rows.filter(x=>x.kind==='reading').length,51);
 assert.equal(new Set(saved.rows.map(x=>x.id)).size,223);
 assert.equal(saved.rows.find(x=>x.id==='Basic_01R:0').polish,'Cześć! Jak się masz?');
 assert.equal(saved.rows.find(x=>x.id==='Asking_the_tram_driver_for_directions:3').polish,
  'Na którym przystanku powinienem wysiąść?');
});

test('C-15 cannot silently change original Polish, English, source identities or verified MP3 mapping',()=>{
 for(const [edit,expected] of [
  [(x)=>x.rows[0].polish='wrong','Polish text drift'],
  [(x)=>x.rows[0].english='wrong','English text drift'],
  [(x)=>x.rows[0].id='fake:0','Expected values to be strictly equal'],
  [(x)=>x.rows[0].existingWholeRecording='invented.mp3','Expected values to be strictly equal'],
  [(x)=>x.rows.pop(),'Expected values to be strictly equal'],
  [(x)=>x.rows[0].lexicalAndGrammarReview='approved','silently approved'],
  [(x)=>x.rows[0].firstObservedWrittenForms=[],'written-form first occurrence drift'],
  [(x)=>x.rows[0].structuralReviewPrompts=['native-certified'],'review prompt drift'],
 ]){
  const x=clone();edit(x);
  assert.throws(()=>verifyItemAudit(x,{checkAudio:false}),new RegExp(expected));
 }
});

test('C-15 records lexical forms and structural flags as review prompts, never a grammar grade',()=>{
 const x=clone();
 assert.equal(x.counts.openReviewRows,223);
 assert.ok(x.method.includes('not lexical lemmas'));
 assert.ok(x.method.includes('not verified grammatical classifications'));
 const price=x.rows.find(row=>row.id==='Conversation_-_shopping:0');
 assert.ok(price.structuralReviewPrompts.includes('quantity-ile'));
 const no=x.rows.find(row=>row.id==='Basic_01R:5');
 assert.ok(no.structuralReviewPrompts.includes('negation'));
 assert.ok(x.rows.every(row=>row.lexicalAndGrammarReview==='open_not_native_certified'));
});
