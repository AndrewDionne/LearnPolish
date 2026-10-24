import type {StarterGroup} from './foundation-first-expressions';

/** Visible educational stages, NOT the hidden journey position/3x3 tier model.
 * The order is independent of the original lesson/catalog order and never
 * creates a duplicate source item or a new progress identity. */
export const FIRST_WORD_ORDER=['simple-replies','politeness','greetings'] as const;
export const BASIC_VOCABULARY_ORDER=[
 'street-words','transport-words','everyday-replies'
] as const;
export const FIRST_SENTENCE_PRACTICE_ORDER=[
 'food-requests','shopping-questions','location-questions'
] as const;
export const FOUNDATION_STAGES=['First words','Basic vocabulary','First sentences / basic grammar'] as const;

const order=(groups:readonly StarterGroup[],ids:readonly string[]):StarterGroup[]=>{
 const byId=new Map(groups.map(g=>[g.id,g]));
 return ids.flatMap(id=>{
  const item=byId.get(id);
  return item?[item]:[];
 });
};

export function orderedFoundationGroups(first:readonly StarterGroup[],vocabulary:readonly StarterGroup[]){
 // Only known groups from their existing strict source/audio validators enter
 // the learner path. One group must never appear twice or shadow another.
 const seen=new Set<string>();
 for(const group of [...first,...vocabulary]){
  if(seen.has(group.id))throw Error('Duplicate foundation group '+group.id);
  seen.add(group.id);
  if(![...FIRST_WORD_ORDER,...BASIC_VOCABULARY_ORDER,...FIRST_SENTENCE_PRACTICE_ORDER].includes(
    group.id as typeof FIRST_WORD_ORDER[number] | typeof BASIC_VOCABULARY_ORDER[number] | typeof FIRST_SENTENCE_PRACTICE_ORDER[number]
  ))throw Error('Unrecognized foundation group '+group.id);
 }
 return {
  firstWords:order(first,FIRST_WORD_ORDER),
  basicVocabulary:order(vocabulary,BASIC_VOCABULARY_ORDER),
  firstSentences:order(vocabulary,FIRST_SENTENCE_PRACTICE_ORDER)
 };
}
