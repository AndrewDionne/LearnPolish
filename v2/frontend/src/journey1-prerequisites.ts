import raw from '../../content/journey1-prerequisites-v1.json';
import type {StarterGroup} from './foundation-first-expressions';
import type {SentencePattern} from './foundation-sentence-patterns';

type Step={id:string;requires:string[];introduces:string[]};
const IDS=[
 'simple-replies','politeness','greetings',
 'street-words','transport-words','everyday-replies',
 'grammar:requests','grammar:where','grammar:permission','grammar:prices',
 'grammar:yes-no-questions','grammar:negative','grammar:one-two',
 'food-requests','shopping-questions','location-questions'
];
const STATUS='authoritative_dependency_inventory_requires_independent_full_lexical_review';
const isObject=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const validKeys=(x:Record<string,unknown>,k:readonly string[])=>
 Object.keys(x).sort().join('|')===[...k].sort().join('|');
const stop=():never=>{throw Error('Invalid Journey 1 prerequisite map');};

/** Reject forward prerequisites, duplicate concept introductions and reordered
 * entries even if their source lesson IDs still exist. No numeric stage quotas. */
export function validateJourney1Prerequisites(value:unknown):Step[]{
 if(!isObject(value)||!validKeys(value,['schemaVersion','status','notes','steps'])||
    value.schemaVersion!==1||value.status!==STATUS||
    typeof value.notes!=='string'||value.notes.length<180||
    !Array.isArray(value.steps)||value.steps.length!==IDS.length)return stop();
 const taught=new Set<string>();
 return value.steps.map((s,i)=>{
  if(!isObject(s)||!validKeys(s,['id','requires','introduces'])||
     s.id!==IDS[i]||!Array.isArray(s.requires)||!Array.isArray(s.introduces)||
     s.introduces.length===0)return stop();
  const requires=s.requires, introduces=s.introduces;
  if(!requires.every(x=>typeof x==='string'&&/^[a-z][a-z0-9-]+$/.test(x))||
     !introduces.every(x=>typeof x==='string'&&/^[a-z][a-z0-9-]+$/.test(x))||
     new Set(requires).size!==requires.length||new Set(introduces).size!==introduces.length||
     !requires.every(x=>taught.has(x))||introduces.some(x=>taught.has(x)))return stop();
  introduces.forEach(x=>taught.add(x));
  return {id:s.id,requires:[...requires] as string[],introduces:[...introduces] as string[]};
 });
}
export const JOURNEY1_PREREQUISITES:readonly Step[]=validateJourney1Prerequisites(raw);

export type CompleteFoundationPath={
 firstWords:StarterGroup[];
 basicVocabulary:StarterGroup[];
 patterns:SentencePattern[];
 firstSentences:StarterGroup[];
 blocked:{id:string;missing:string[]}[];
};

/** If the original audio/source validator removes an introduction, dependent
 * lessons are not silently moved forward. An unavailable dependency prevents
 * the later lesson from masquerading as prerequisite complete. */
export function prerequisiteCompletePath(
 firstWords:readonly StarterGroup[],
 basicVocabulary:readonly StarterGroup[],
 patterns:readonly SentencePattern[],
 firstSentences:readonly StarterGroup[],
):CompleteFoundationPath{
 const available=new Map<string,StarterGroup|SentencePattern>();
 for(const [prefix,groups] of [
  ['',firstWords],['',basicVocabulary],['grammar:',patterns],['',firstSentences]
 ] as const){
  for(const group of groups){
   const id=prefix+group.id;
   if(available.has(id))throw Error('Duplicate learner prerequisite unit: '+id);
   available.set(id,group);
  }
 }
 const sourceIds=new Set(JOURNEY1_PREREQUISITES.map(x=>x.id));
 if([...available.keys()].some(x=>!sourceIds.has(x)))
   throw Error('Untracked learner lesson has no prerequisite definition');
 const seen=new Set<string>(),blocked:{id:string;missing:string[]}[]=[];
 const ok=new Map<string,StarterGroup|SentencePattern>();
 for(const step of JOURNEY1_PREREQUISITES){
  const group=available.get(step.id);
  if(!group)continue;
  const missing=step.requires.filter(id=>!seen.has(id));
  if(missing.length){blocked.push({id:step.id,missing});continue;}
  ok.set(step.id,group);
  step.introduces.forEach(id=>seen.add(id));
 }
 const selectGroup=(ids:readonly StarterGroup[])=>
  ids.filter(g=>ok.get(g.id)===g);
 return {
  firstWords:selectGroup(firstWords),
  basicVocabulary:selectGroup(basicVocabulary),
  patterns:patterns.filter(p=>ok.get('grammar:'+p.id)===p),
  firstSentences:selectGroup(firstSentences),
  blocked
 };
}
