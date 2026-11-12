#!/usr/bin/env node
// Strict native projection of the authoritative V2 C-13 foundation path.
// The original V2 content and MP3s are source; this NEVER generates Polish.
import fs from 'node:fs';
import path from 'node:path';

const IDS = [
  'simple-replies', 'politeness', 'greetings', 'street-words',
  'transport-words', 'everyday-replies', 'grammar:requests', 'grammar:where',
  'grammar:permission', 'grammar:prices', 'grammar:yes-no-questions',
  'grammar:negative', 'grammar:one-two', 'food-requests',
  'shopping-questions', 'location-questions'
];
const COUNTS = [2,3,3,6,6,5,4,5,4,3,4,4,4,5,5,5];
const STATUSES = {
  first: 'source_only_existing_recordings_not_independently_native_certified',
  next: 'source_only_original_recordings_not_independently_native_certified',
  grammar: 'source_only_recorded_utterances_grammar_not_independently_native_reviewed',
  prerequisites: 'authoritative_dependency_inventory_requires_independent_full_lexical_review'
};
const FILES = {
  first: 'foundation-first-expressions-v1.json',
  next: 'foundation-next-words-v1.json',
  grammar: 'foundation-sentence-patterns-v1.json',
  prerequisites: 'journey1-prerequisites-v1.json'
};
const STAGES = ['First words', 'Basic vocabulary', 'First sentences / basic grammar'];
const fail = message => { throw Error('V3 guided source rejected: ' + message); };
const unique = values => new Set(values).size === values.length;
const isText = value => typeof value === 'string' && value.trim().length > 0;

export function readGuidedSources(repo) {
  return Object.fromEntries(Object.entries(FILES).map(([key, filename]) =>
    [key, JSON.parse(fs.readFileSync(path.join(repo, 'v2/content', filename), 'utf8'))]));
}

export function compileGuidedFoundations(manifest, sources) {
  if (manifest?.schemaVersion !== 1 || !Array.isArray(manifest.lessons)) fail('catalog missing');
  const byLesson = new Map(manifest.lessons.map(l => [l.id, l]));
  for (const [key, status] of Object.entries(STATUSES)) {
    if (sources[key]?.schemaVersion !== 1 || sources[key]?.status !== status) {
      fail('unexpected V2 editorial source status: ' + key);
    }
  }
  const {first, next, grammar, prerequisites} = sources;
  if (first.sourceLessonId !== 'Conversation_1' ||
      first.sourcePolicy !== 'use_full_original_recorded_utterances_exact_item_ids_no_new_audio_or_review_claims' ||
      next.sourcePolicy !== 'fixed_existing_whole_utterances_do_not_create_new_lessons_or_voice') {
    fail('source audio policy changed');
  }
  if (!Array.isArray(first.groups) || first.groups.length !== 3 ||
      !Array.isArray(next.groups) || next.groups.length !== 6 ||
      !Array.isArray(grammar.groups) || grammar.groups.length !== 7 ||
      !Array.isArray(prerequisites.steps) || prerequisites.steps.length !== IDS.length ||
      !isText(prerequisites.notes) || prerequisites.notes.length < 180) {
    fail('V2 C-13 inventory changed');
  }
  const groupMap = new Map();
  for (const group of first.groups) {
    if (!isText(group.id) || !isText(group.title) || !Array.isArray(group.itemRefs)) fail('first words');
    groupMap.set(group.id, {type:'words',stage:STAGES[0],title:group.title,
      references:group.itemRefs.map(ref => ({
        id:ref.id,polish:ref.expectedPolish,english:null
      }))});
  }
  for (const group of next.groups) {
    if (!isText(group.id) || !isText(group.title) ||
        !isText(group.lessonId) || !Array.isArray(group.itemRefs)) fail('vocabulary');
    if (groupMap.has(group.id)) fail('duplicate word-group ID');
    groupMap.set(group.id, {type:'words',
      stage:['street-words','transport-words','everyday-replies'].includes(group.id)
        ? STAGES[1] : STAGES[2],
      title:group.title,references:group.itemRefs.map(ref => ({
        id:ref.id,polish:ref.expectedPolish,english:ref.expectedEnglish
      }))});
  }
  for (const group of grammar.groups) {
    if (!isText(group.id) || !isText(group.title) || !isText(group.cue) ||
        !isText(group.explanation) || group.explanation.length < 50 ||
        !Array.isArray(group.examples)) fail('grammar metadata');
    const id='grammar:'+group.id;
    if(groupMap.has(id)) fail('duplicate grammar ID');
    groupMap.set(id,{type:'grammar',stage:STAGES[2],title:group.title,
      cue:group.cue,explanation:group.explanation,
      references:group.examples.map(ref => ({
        id:ref.sourceLesson+':'+ref.index,polish:ref.polish,
        english:ref.english,focus:ref.focus
      }))});
  }
  if (groupMap.size !== IDS.length || !unique(IDS) ||
      prerequisites.steps.map(x=>x.id).join('|') !== IDS.join('|')) {
    fail('new, missing or reordered C-13 prerequisites');
  }
  const introduced = new Set(),steps=[];
  for(let i=0;i<IDS.length;i++) {
    const entry=prerequisites.steps[i],group=groupMap.get(entry.id);
    if(!group || !Array.isArray(entry.requires) || !Array.isArray(entry.introduces) ||
      !entry.introduces.length || !unique(entry.requires) || !unique(entry.introduces) ||
      !entry.requires.every(x=>isText(x)&&introduced.has(x)) ||
      !entry.introduces.every(x=>isText(x)&&!introduced.has(x))) {
      fail('forward or invalid prerequisite at '+entry.id);
    }
    if(group.references.length!==COUNTS[i] ||
       !unique(group.references.map(x=>x.id)))fail('unexpected source counts '+entry.id);
    const resolved=group.references.map(ref=>{
      const cut=ref.id.lastIndexOf(':');
      const lessonID=ref.id.slice(0,cut),index=Number(ref.id.slice(cut+1));
      const lesson=byLesson.get(lessonID);
      const item=lesson?.items?.find(x=>x.id===ref.id);
      if (!lesson || lesson.kind!=='vocabulary' || lesson.source!=='legacy' ||
          !Number.isSafeInteger(index) || index<0 ||
          !item || item.polish!==ref.polish ||
          (ref.english !== null && item.english!==ref.english) ||
          item.referenceReview==='practice_only' ||
          item.audio!=='generated/audio/'+encodeURIComponent(lessonID)+'/'+index+'.mp3') {
        fail('uncertified or changed recorded source: '+ref.id);
      }
      if (group.type==='grammar' &&
          (!isText(ref.focus) || ref.polish.split(ref.focus).length!==2)) {
        fail('ambiguous authored grammar focus: '+ref.id);
      }
      return {id:item.id,polish:item.polish,english:item.english,audio:item.audio,
        ...(group.type==='grammar'?{focus:ref.focus}:{})};
    });
    for(const concept of entry.introduces)introduced.add(concept);
    steps.push({id:entry.id,order:i+1,stage:group.stage,type:group.type,
      title:group.title,requires:entry.requires,introduces:entry.introduces,
      ...(group.type==='grammar'?{cue:group.cue,explanation:group.explanation}:{}),
      items:resolved});
  }
  if (steps.reduce((n,s)=>n+s.items.length,0)!==68 ||
      steps.filter(x=>x.type==='grammar').length!==7) fail('source totals changed');
  return {
    schemaVersion:1,
    sourceStatus:STATUSES.prerequisites,
    lessonReviewStatus:'source_only_not_independently_native_certified',
    steps
  };
}

if (process.argv[1]?.endsWith('prepare-guided.mjs')) {
  // Test utility. Production assets are written by prepare-assets.mjs.
  const repo=path.resolve(process.cwd());
  const catalog=JSON.parse(fs.readFileSync(
    path.join(repo,'v2/frontend/public/generated/lessons.json'),'utf8'));
  const result=compileGuidedFoundations(catalog,readGuidedSources(repo));
  console.log('V3 guided source verified:',{steps:result.steps.length,
    items:result.steps.reduce((n,s)=>n+s.items.length,0)});
}
