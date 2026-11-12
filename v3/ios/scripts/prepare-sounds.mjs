// V3 source-only Polish alphabet and sound-recognition compiler.
// Not isolated letter/phoneme audio, no generated recordings or phonetic grades.
import fs from 'node:fs';
import path from 'node:path';

export const ALPHABET = 'A Ą B C Ć D E Ę F G H I J K L Ł M N Ń O Ó P R S Ś T U W Y Z Ź Ż'.split(' ');
export const COMBINATIONS = 'CZ SZ RZ CH SI ZI DZI NI SZCZ TRZ PRZ KRZ DZ'.split(' ');
const A_STATUS = 'inherited_whole_word_recordings_not_independently_native_certified';
const S_STATUS = 'existing_recorded_whole_word_sound_examples_editorial_not_native_certified';
const error = (message) => { throw Error('V3 sound source invalid: ' + message); };
const unique = xs => new Set(xs).size === xs.length;

export function readSoundSources(repo) {
  const read=name=>JSON.parse(fs.readFileSync(path.join(repo,'v2/content',name),'utf8'));
  return {alphabet:read('alphabet-recorded-examples-v1.json'),
    listening:read('sound-listening-v1.json')};
}

export function compileSoundStudio(manifest, sources) {
  if(manifest?.schemaVersion!==1 || !Array.isArray(manifest.lessons)) error('lesson catalog');
  const {alphabet,listening}=sources;
  if(alphabet?.schemaVersion!==1||alphabet.status!==A_STATUS||
      typeof alphabet.note!=='string'||alphabet.note.length<60||
      !Array.isArray(alphabet.letters)||alphabet.letters.length!==32||
      !Array.isArray(alphabet.combinations)||alphabet.combinations.length!==13||
      listening?.schemaVersion!==1||listening.status!==S_STATUS||
      !Array.isArray(listening.lessons)||listening.lessons.length!==5||
      typeof listening.notes!=='string'||listening.notes.length<40) error('editorial schema');
  const lessons = new Map(manifest.lessons.map(l=>[l.id,l]));
  const audioFor=(lessonID,index)=>'generated/audio/'+encodeURIComponent(lessonID)+'/'+index+'.mp3';
  const resolveAlphabet=(rows,expectedLabels)=>{
    return rows.map((r,i)=>{
      const source=lessons.get(r.sourceLesson);
      const id=r.sourceLesson+':'+r.index;
      const item=source?.items.find(x=>x.id===id);
      if(r.label!==expectedLabels[i] || !Number.isSafeInteger(r.index) || r.index<0 ||
        typeof r.polish!=='string'||typeof r.english!=='string'||typeof r.focus!=='string'||
        !r.focus || r.polish.split(r.focus).length!==2 ||
        r.focus.toLocaleUpperCase('pl-PL')!==r.label ||
        r.polish!==r.polish.normalize('NFC')||r.focus!==r.focus.normalize('NFC')||
        source?.source!=='legacy'||source?.kind!=='vocabulary'||
        !item||item.polish!==r.polish||item.english!==r.english||
        item.referenceReview==='practice_only'||item.audio!==audioFor(r.sourceLesson,r.index)){
        error('changed or unreviewed recorded alphabet '+r.label);
      }
      return {label:r.label,id,polish:item.polish,english:item.english,
        focus:r.focus,audio:item.audio};
    });
  };
  const letters=resolveAlphabet(alphabet.letters,ALPHABET);
  const combinations=resolveAlphabet(alphabet.combinations,COMBINATIONS);
  if(!unique(letters.map(x=>x.label))||!unique(combinations.map(x=>x.label)))error('alphabet labels');

  const soundLessons=[];let total=0;const seen=new Set();
  for(const entry of listening.lessons) {
    if(!entry.lessonId?.startsWith('contrast_')||seen.has(entry.lessonId)||
      !Array.isArray(entry.questions)||entry.questions.length<4||entry.questions.length>8) {
      error('sound lesson inventory');
    }
    seen.add(entry.lessonId);
    const lesson=lessons.get(entry.lessonId);
    if(lesson?.source!=='curated'||lesson.kind!=='sounds'||
       !Array.isArray(lesson.soundGroups)||lesson.soundGroups.length<2) error('sound lesson unavailable');
    const groups=new Map(lesson.soundGroups.map(g=>[g.id,g]));
    const groupKeys=[...groups.keys()];
    if(!unique(groupKeys))error('duplicate sound group');
    const questions=[];
    const used=new Set();const covered=new Set();
    for(const q of entry.questions){
      const item=lesson.items.find(x=>x.id===q.itemId);
      const group=groups.get(q.groupId);
      if(used.has(q.itemId)||!item||!group||!group.itemIds.includes(item.id)||
         !item.id.startsWith(entry.lessonId+':'+q.groupId+':')||
         item.soundGroupId!==q.groupId||item.polish!==q.expectedPolish||
         item.soundFocus!==q.expectedFocus||!q.expectedFocus||q.expectedFocus.length>8||
         !item.polish.includes(q.expectedFocus)||
         item.polish.indexOf(q.expectedFocus)!==item.polish.lastIndexOf(q.expectedFocus)||
         item.referenceReview==='practice_only'||!item.audio||
         !/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(item.audio)){
        error('changed or unsafe original sound card '+q.itemId);
      }
      used.add(q.itemId);covered.add(q.groupId);
      questions.push({id:item.id,polish:item.polish,english:item.english,
        audio:item.audio,focus:item.soundFocus,groupId:q.groupId});
    }
    if(covered.size<2)error('single-group sound quiz');
    soundLessons.push({lessonId:entry.lessonId,title:lesson.title,
      intro:lesson.intro??'',
      groups:lesson.soundGroups.map(g=>({id:g.id,label:g.label,
        ipa:g.ipa,hint:g.hint,itemIds:g.itemIds})),questions});
    total+=questions.length;
  }
  if(total!==25)error('sound quiz count '+total);
  return {schemaVersion:1,editorialStatus:'source_only_no_isolated_letter_audio_or_acoustic_certification',
    letters,combinations,soundLessons};
}
