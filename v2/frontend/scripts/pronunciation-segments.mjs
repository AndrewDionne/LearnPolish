/** Conservative, deterministic draft sound groups for existing Polish lessons.

This is editorial segmentation to position transcription-derived colour hints,
NOT validated Polish acoustic syllabification. One authoritative curated
Świętokrzyska guide overrides drafts. Preserve every byte of display spelling.
*/
const vowel = /[aąeęioóuy]/iu;
const digraph = /(?:dź|dż|dzi|cz|sz|rz|ch|dz|ci|si|zi|ni)$/iu;

export function draftWordParts(word) {
  const letters = Array.from(word);
  if (letters.length < 2) return [word];
  const vowels = [];
  for (let i = 0; i < letters.length; i++) {
    if (vowel.test(letters[i])) {
      // Polish "i" often just softens the next vowel (e.g. "dzie", "nie").
      if (letters[i].toLowerCase() === 'i' && i + 1 < letters.length &&
          vowel.test(letters[i+1]) && letters[i+1].toLowerCase() !== 'i') continue;
      vowels.push(i);
    }
  }
  if (vowels.length <= 1) return [word];
  const starts = [0];
  for (let n=1; n<vowels.length; n++){
    const previous=vowels[n-1], next=vowels[n];
    const consonants=letters.slice(previous+1,next).join('');
    let split;
    if(!consonants) split=next;
    else if(consonants.length===1) split=previous+1;
    else {
      // Prefer a single consonant onset or preserve a conventional digraph.
      const prefix=letters.slice(previous+1,next).join('');
      const lastTwo=prefix.slice(-2);
      split=next-(digraph.test(lastTwo)?2:1);
      if(split<=previous) split=previous+1;
    }
    if(split>starts[starts.length-1] && split<letters.length) starts.push(split);
  }
  starts.push(letters.length);
  const parts=[];
  for(let i=0;i<starts.length-1;i++)parts.push(letters.slice(starts[i],starts[i+1]).join(''));
  return parts.filter(Boolean);
}

export function pronunciationSegmentsFor(item, overrides=new Map()) {
  if(!item || typeof item.polish!=='string' || !item.polish.trim() ||
     item.polish.length>300) return undefined;
  const guide = item.pronunciationGuide;
  if(guide && Array.isArray(guide.syllables) &&
     guide.syllables.map(x=>x.polish).join('')===item.polish){
    return {method:'authored-v1',segments:guide.syllables.map(x=>x.polish)};
  }
  const authored=overrides.get(item.polish);
  if(authored){
    if(!Array.isArray(authored) || authored.length<1 || authored.length>32 ||
       authored.some(part=>typeof part!=='string'||!part) ||
       authored.join('')!==item.polish){
      throw new Error('Invalid editorial sound boundary for '+item.polish);
    }
    return {method:'editorial-draft-v1',segments:authored.slice()};
  }
  // Drafts remain marked draft rather than pretending that all Polish
  // digraph clusters and word boundaries are human-reviewed syllables.
  const tokens=item.polish.match(/\p{L}+|[^\p{L}]+/gu);
  if(!tokens)return undefined;
  const segments=[];
  for(const token of tokens){
    if(/^\p{L}+$/u.test(token)){
      segments.push(...draftWordParts(token));
    }else if(segments.length){
      segments[segments.length-1]+=token;
    }else{
      // Leading punctuation has no separately scoreable sound.
      if(!token.trim())return undefined;
      return undefined;
    }
  }
  if(segments.length<1 || segments.length>32 ||
     segments.join('')!==item.polish ||
     segments.some(s=>!/[a-ząćęłńóśźż]/iu.test(s))) return undefined;
  return {method:'draft-orthographic-v1',segments};
}

export function attachPronunciationSegments(lessons, overrides=new Map()) {
  let total=0, drafts=0, authored=0, editorial=0;
  const matched=new Set();
  for(const lesson of lessons){
    for(const item of lesson.items){
      const parts=pronunciationSegmentsFor(item, overrides);
      if(overrides.has(item.polish)) matched.add(item.polish);
      if(!parts)continue;
      item.pronunciationSegments=parts;
      total++;
      if(parts.method==='authored-v1')authored++;
      else if(parts.method==='editorial-draft-v1')editorial++;
      else drafts++;
    }
  }
  if(matched.size!==overrides.size)throw new Error('Orphaned pronunciation override');
  return {total,drafts,authored,editorial};
}

/** Exact-source editorial overrides. No NLP-generated grades or silent drift. */
export function parsePronunciationOverrides(definitions) {
  if(!definitions || definitions.schemaVersion!==1 ||
     definitions.reviewStatus!=='needs_native_speaker_review' ||
     !Array.isArray(definitions.items))throw new Error('Invalid pronunciation override catalog');
  const map=new Map();
  for(const entry of definitions.items){
    if(!entry || typeof entry.polish!=='string' || !entry.polish.trim() ||
       map.has(entry.polish) || !Array.isArray(entry.segments) ||
       !entry.segments.length || entry.segments.length>32 ||
       entry.segments.some(part=>typeof part!=='string' || !part) ||
       entry.segments.join('')!==entry.polish){
      throw new Error('Invalid, duplicate or mismatched pronunciation override');
    }
    map.set(entry.polish,entry.segments);
  }
  return map;
}
