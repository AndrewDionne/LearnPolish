import raw from '../../content/alphabet-recorded-examples-v1.json';
import type {Lesson} from './model';

export type RecordedGlyph={label:string;polish:string;english:string;focus:string;audio:string;itemId:string};
export type AlphabetRecord={label:string;sourceLesson:string;index:number;polish:string;english:string;focus:string};
type AlphabetPlan={letters:AlphabetRecord[];combinations:AlphabetRecord[]};

export const POLISH_ALPHABET='A Ą B C Ć D E Ę F G H I J K L Ł M N Ń O Ó P R S Ś T U W Y Z Ź Ż'.split(' ');
export const RECORDED_COMBINATIONS='CZ SZ RZ CH SI ZI DZI NI SZCZ TRZ PRZ KRZ DZ'.split(' ');
const STATUS='inherited_whole_word_recordings_not_independently_native_certified';
const isObject=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const keys=(x:Record<string,unknown>,k:string[])=>Object.keys(x).sort().join('|')===k.slice().sort().join('|');
const fail=():never=>{throw Error('Invalid source-backed Polish alphabet examples');};

/** No letter-name phonemes, invented voice paths or educational certification. */
export function validateAlphabetPlan(value:unknown):AlphabetPlan{
 if(!isObject(value)||!keys(value,['schemaVersion','status','note','letters','combinations'])||
  value.schemaVersion!==1||value.status!==STATUS||typeof value.note!=='string'||
  value.note.length<60||!Array.isArray(value.letters)||!Array.isArray(value.combinations)||
  value.letters.length!==POLISH_ALPHABET.length||
  value.combinations.length!==RECORDED_COMBINATIONS.length)return fail();
 const parse=(rows:unknown[],labels:string[]):AlphabetRecord[]=>rows.map((rawRow,i)=>{
  if(!isObject(rawRow)||!keys(rawRow,['label','sourceLesson','index','polish','english','focus'])||
   rawRow.label!==labels[i]||typeof rawRow.sourceLesson!=='string'||
   !/^[A-Za-z0-9_-]+$/.test(rawRow.sourceLesson)||
   !Number.isSafeInteger(rawRow.index)||Number(rawRow.index)<0||
   typeof rawRow.polish!=='string'||!rawRow.polish||
   typeof rawRow.english!=='string'||!rawRow.english||
   typeof rawRow.focus!=='string'||!rawRow.focus||
   rawRow.polish.split(rawRow.focus).length!==2||
   rawRow.focus.normalize('NFC')!==rawRow.focus||
   rawRow.polish.normalize('NFC')!==rawRow.polish||
   rawRow.focus.toLocaleUpperCase('pl-PL')!==labels[i])return fail();
  return {label:labels[i],sourceLesson:rawRow.sourceLesson,
   index:Number(rawRow.index),polish:rawRow.polish,english:rawRow.english,focus:rawRow.focus};
 });
 return {letters:parse(value.letters,POLISH_ALPHABET),
  combinations:parse(value.combinations,RECORDED_COMBINATIONS)};
}
export const RECORDED_ALPHABET_PLAN:AlphabetPlan=validateAlphabetPlan(raw);

/** Fail closed on every drifted original source item.
 * There are no new lesson IDs or persisted XP/progress keys. */
export function availableRecordedAlphabet(lessons:readonly Lesson[]):{letters:RecordedGlyph[];combinations:RecordedGlyph[]}{
 const sources=new Map(lessons.filter(l=>l.source==='legacy'&&l.kind==='vocabulary').map(l=>[l.id,l]));
 const resolve=(entry:AlphabetRecord):RecordedGlyph|null=>{
  const source=sources.get(entry.sourceLesson);
  const item=source?.items.find(x=>x.id===entry.sourceLesson+':'+entry.index);
  const audio='generated/audio/'+encodeURIComponent(entry.sourceLesson)+'/'+entry.index+'.mp3';
  if(!item||item.polish!==entry.polish||item.english!==entry.english||
    item.referenceReview==='practice_only'||item.audio!==audio)return null;
  return {label:entry.label,polish:item.polish,english:item.english,
   focus:entry.focus,audio,itemId:item.id};
 };
 return {
  letters:RECORDED_ALPHABET_PLAN.letters.map(resolve).filter((e):e is RecordedGlyph=>!!e),
  combinations:RECORDED_ALPHABET_PLAN.combinations.map(resolve).filter((e):e is RecordedGlyph=>!!e),
 };
}
