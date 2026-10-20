import fs from 'node:fs';
import {attachPronunciationSegments,parsePronunciationOverrides} from './pronunciation-segments.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const legacySets = path.join(root, 'docs/sets');
const legacyAudio = path.join(root, 'docs/static');
const outRoot = path.join(root, 'v2/frontend/public/generated');
const curatedSoundsFile = path.join(root, 'v2/content/sound-contrasts.json');
const readingChecksFile = path.join(root, 'v2/content/reading-checks.json');
const microDialoguesFile = path.join(root, 'v2/content/micro-dialogues.json');
const pronunciationGuideFile = path.join(root, 'v2/content/pronunciation-swietokrzyska.json');
const pronunciationOverridesFile = path.join(root, 'v2/content/pronunciation-segment-overrides.json');
const voiceProductionFile = path.join(root, 'v2/content/voice-production.json');
const otherReferenceBlockersFile = path.join(root, 'v2/content/additional-speak-reference-blockers.json');
const UNSCORABLE_REFERENCE = /\/|[0-9]|…|\.{3,}/u;
const retiredGroupedSoundSets = new Set(['letter_recognition_1', 'letter_recognition_2', 'letter_recognition_3']);

export function migrateLesson(filename, source) {
  const id = path.basename(filename, '.json');
  const isReading = Array.isArray(source.passages);
  const isVocabulary = Array.isArray(source.cards);
  if (!isReading && !isVocabulary) throw new Error(id + ': missing cards/passages');
  const rows = isReading ? source.passages : source.cards;
  if (rows.length === 0) throw new Error(id + ': lesson is empty');
  const sounds = id.startsWith('letter_recognition_');
  const kind = isReading ? 'reading' : sounds ? 'sounds' : 'vocabulary';
  const title = id.replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim();
  const items = rows.map((row, index) => {
    const polish = (isReading ? row.polish : row.phrase);
    const english = (isReading ? row.english : row.meaning);
    if (typeof polish !== 'string' || !polish.trim() || typeof english !== 'string' || !english.trim()) {
      throw new Error(id + ': item ' + index + ' missing Polish/English');
    }
    return {
      id: id + ':' + index,
      polish: polish.trim(),
      english: english.trim(),
      ...(typeof row.pronunciation === 'string' && row.pronunciation.trim() ? { pronunciation: row.pronunciation.trim() } : {}),
      ...(typeof row.title === 'string' && row.title.trim() ? { title: row.title.trim() } : {}),
    };
  });
  return { schemaVersion: 1, id, title, kind, items, source: 'legacy', needsReview: sounds };
}

function copyAudio(setId, lesson) {
  const audioDir = path.join(legacyAudio, setId, lesson.kind === 'reading' ? 'reading' : 'audio');
  if (!fs.existsSync(audioDir)) return 0;
  const entries = fs.readdirSync(audioDir).filter(name => name.toLowerCase().endsWith('.mp3'));
  let copied = 0;
  lesson.items.forEach((item, index) => {
    const original = entries.find(name => name === index + '.mp3' || name.startsWith(index + '_'));
    if (!original) return;
    const relative = 'generated/audio/' + encodeURIComponent(setId) + '/' + index + '.mp3';
    const destination = path.join(outRoot, 'audio', setId, index + '.mp3');
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(path.join(audioDir, original), destination);
    item.audio = relative;
    copied++;
  });
  return copied;
}

export function buildSoundCurriculum(sourceLessons, definitions) {
  const byId = new Map(sourceLessons.map(lesson => [lesson.id, lesson]));
  const seen = new Set(sourceLessons.map(lesson => lesson.id));
  return definitions.map(definition => {
    if (!definition.id || seen.has(definition.id) || !Array.isArray(definition.groups) || definition.groups.length < 2) {
      throw new Error('Invalid or duplicate curated sound lesson: ' + definition.id);
    }
    seen.add(definition.id);
    const groups = [];
    const items = [];
    const seenGroups = new Set();
    for (const group of definition.groups) {
      if (!group.id || seenGroups.has(group.id) || !group.label || !group.hint ||
          !Array.isArray(group.examples) || group.examples.length < 2) {
        throw new Error(definition.id + ': invalid sound group');
      }
      seenGroups.add(group.id);
      const itemIds = [];
      for (let i = 0; i < group.examples.length; i++) {
        const example = group.examples[i];
        const source = byId.get(example.set);
        if (!source || source.kind !== 'vocabulary') throw new Error('Missing source lesson: ' + example.set);
        const matched = source.items[example.index];
        if (!matched || matched.polish.normalize('NFC').trim() !== example.expected ||
            !matched.audio || !fs.existsSync(path.join(outRoot, matched.audio.replace(/^generated\//, '')))) {
          throw new Error(definition.id + ': missing or mismatched individual audio for ' + example.expected);
        }
        if (/[,\n]/.test(matched.polish) || matched.polish.includes(' / ')) {
          throw new Error(definition.id + ': bundled or alternative utterance not allowed: ' + example.expected);
        }
        // The focus is a human-authored orthographic substring, NOT an acoustic
        // phoneme score. Fail closed if it drifts out of the original source.
        const focus = example.focus;
        const start = typeof focus === 'string' && focus.length > 0 && focus.length <= 8 &&
          !/\s/u.test(focus) ? matched.polish.indexOf(focus) : -1;
        if (start < 0 || matched.polish.indexOf(focus, start + focus.length) !== -1) {
          throw new Error(definition.id + ': invalid or ambiguous focus letters in ' + example.expected);
        }
        const id = definition.id + ':' + group.id + ':' + i;
        itemIds.push(id);
        items.push({
          id, polish: matched.polish, english: matched.english,
          audio: matched.audio, soundGroupId: group.id, soundFocus: focus,
        });
      }
      groups.push({id: group.id, label: group.label, ipa: group.ipa, hint: group.hint, itemIds});
    }
    return {
      schemaVersion: 1, id: definition.id, title: definition.title, kind: 'sounds',
      source: 'curated', needsReview: true, intro: definition.intro,
      soundGroups: groups, items,
    };
  });
}


/**
 * Questions are authored against exact Polish text. A wording mismatch is an
 * editorial breakage, never a reason to invent a new distractor at runtime.
 * Missing checks remain available as ungraded reveal/self-assessment.
 */
export function attachReadingCurriculum(lessons, definitions) {
  const reading = lessons.filter(lesson => lesson.kind === 'reading');
  if (definitions?.schemaVersion !== 1 || !Array.isArray(definitions.curricula) ||
      definitions.curricula.length !== reading.length) {
    throw new Error('Reading curriculum must cover every migrated reading lesson');
  }
  const indexed = new Map(reading.map(lesson => [lesson.id, lesson]));
  const seen = new Set();
  const orders = new Set();
  let count = 0;
  for (const definition of definitions.curricula) {
    const lesson = indexed.get(definition.lesson);
    if (!lesson || seen.has(definition.lesson) || !Number.isInteger(definition.order) ||
        definition.order < 1 || orders.has(definition.order) ||
        !['foundations','daily-life','getting-around'].includes(definition.stage) ||
        typeof definition.goal !== 'string' || definition.goal.length < 10 ||
        !Array.isArray(definition.checks) || definition.checks.length < 3) {
      throw new Error('Invalid reading sequence for ' + definition.lesson);
    }
    orders.add(definition.order);
    seen.add(definition.lesson);
    lesson.progression = {order:definition.order,stage:definition.stage,goal:definition.goal};
    const checked = new Set();
    for (const check of definition.checks) {
      const item = lesson.items[check.index];
      if (!Number.isInteger(check.index) || !item || checked.has(check.index) ||
          item.polish.normalize('NFC') !== check.expected ||
          !item.audio ||
          typeof check.prompt !== 'string' || check.prompt.length < 12 ||
          !Array.isArray(check.options) || check.options.length !== 3 ||
          check.options.some(text => typeof text !== 'string' || text.trim().length < 2) ||
          new Set(check.options.map(text => text.trim().toLocaleLowerCase('en'))).size !== 3 ||
          !Number.isInteger(check.correctIndex) || check.correctIndex < 0 || check.correctIndex > 2 ||
          typeof check.feedback !== 'string' || check.feedback.length < 10) {
        throw new Error('Invalid or mismatched reading check in ' + definition.lesson + ' at ' + check.index);
      }
      checked.add(check.index);
      item.comprehension = {
        prompt:check.prompt, options:check.options,
        correctIndex:check.correctIndex, feedback:check.feedback,
      };
      count++;
    }
  }
  if (seen.size !== reading.length ||
      [...orders].sort((a,b)=>a-b).some((order,i)=>order!==i+1)) {
    throw new Error('Missing reading sequence step or lesson');
  }
  return count;
}

/**
 * Match BOTH durable editorial registries to the canonical, unedited vocabulary.
 * Previously-recorded MP3s are retained but cannot be treated as verified spoken
 * examples until a complete single-text reference and that audio are reviewed.
 * The syntax gate catches *new* slash/number/ellipsis prompts which an editor
 * forgot to register, rather than leaking them into provider scoring.
 */
export function attachReferenceReview(lessons, voiceSpecification, additional) {
  const first=voiceSpecification?.sourceBlockers;
  const rest=additional?.sourceBlockers;
  if (voiceSpecification?.schemaVersion!==1 || !Array.isArray(first) ||
      first.length!==2 || additional?.schemaVersion!==1 ||
      additional?.reviewStatus!=='source_audio_unverified_practice_only' ||
      !Array.isArray(rest) || rest.length!==12) {
    throw new Error('Expected exact original and additional Speak blocker registries');
  }
  const originalIds=['Conversation_1:24','Conversation_1:25'];
  const additionalIds=[
    'Conversation_-_restaurant:1','Conversation_-_restaurant:5',
    'Emergencies_and_Health:4','Emergencies_and_Health:5',
    'Emergencies_and_Health:15','Emergencies_and_Health:19',
    'Food_and_Dinning:2','Food_and_Dinning:4',
    'Getting_Around_1:23','Road_Terminology:10','Road_Terminology:21',
    'Transit_1:4'
  ];
  if (first.some((entry,i)=>entry.itemId!==originalIds[i]) ||
      rest.some((entry,i)=>entry.itemId!==additionalIds[i])) {
    throw new Error('Unexpected edited, missing or reordered Speak reference review');
  }
  const vocabulary=lessons.filter(lesson=>lesson.kind==='vocabulary');
  const byId=new Map(vocabulary.flatMap(lesson=>lesson.items.map(item=>[item.id,item])));
  const registered=new Set();
  for (const blocker of [...first,...rest]) {
    const item=byId.get(blocker.itemId);
    if (!item || registered.has(blocker.itemId) || item.polish!==blocker.polish ||
        !UNSCORABLE_REFERENCE.test(item.polish) || !item.audio ||
        typeof blocker.reason!=='string' || blocker.reason.trim().length<12) {
      throw new Error('Changed or missing Speak audio review: '+blocker.itemId);
    }
    registered.add(item.id);
    item.referenceReview='practice_only';
  }
  for (const item of vocabulary.flatMap(lesson=>lesson.items)) {
    if (UNSCORABLE_REFERENCE.test(item.polish) && !registered.has(item.id)) {
      throw new Error('Unreviewed new alternative, numeric or incomplete Speak reference: '+item.id);
    }
  }
  return registered.size;
}

/**
 * Optional E2 dialogue practice reuses ORIGINAL individual reading items/audio.
 * It creates no new lessons, cards, IDs, translations, XP or recorded voices.
 * Every turn must match exact ordered source text and an existing mapped MP3.
 */
export function attachMicroDialogues(lessons, specification) {
  if (specification?.schemaVersion !== 1 ||
      specification.editorialStatus !== 'draft_source_text_and_existing_audio_mapping_not_native_reviewed' ||
      !Array.isArray(specification.scenes) || specification.scenes.length !== 3) {
    throw new Error('Expected the three curated E2 pilot exchanges');
  }
  const reading = new Map(lessons.filter(lesson=>lesson.kind === 'reading')
    .map(lesson=>[lesson.id, lesson]));
  const usedScenes = new Set();
  const usedTurns = new Set();
  for (const scene of specification.scenes) {
    const lesson = reading.get(scene.lesson);
    const key = scene.lesson + ':' + scene.id;
    if (!lesson || !/^[a-z0-9-]+$/.test(scene.id ?? '') || usedScenes.has(key) ||
        typeof scene.title !== 'string' || scene.title.trim().length < 5 ||
        typeof scene.speakers?.A !== 'string' || !scene.speakers.A.trim() ||
        typeof scene.speakers?.B !== 'string' || !scene.speakers.B.trim() ||
        !Array.isArray(scene.turns) || scene.turns.length < 2 || scene.turns.length > 4 ||
        scene.turns[0]?.speaker !== 'A') {
      throw new Error('Invalid E2 micro-dialogue: ' + key);
    }
    usedScenes.add(key);
    const turns = scene.turns.map((turn, i) => {
      const item = lesson.items[turn.index];
      const expectedId = lesson.id + ':' + turn.index;
      const previous = scene.turns[i - 1];
      const expectedAudio = 'generated/audio/' + encodeURIComponent(lesson.id) + '/' + turn.index + '.mp3';
      if (!Number.isSafeInteger(turn.index) || turn.index < 0 ||
          (i > 0 && turn.index !== previous.index + 1) ||
          turn.speaker !== (i % 2 === 0 ? 'A' : 'B') ||
          !item || item.id !== expectedId || item.polish !== turn.polish ||
          item.referenceReview === 'practice_only' || item.audio !== expectedAudio ||
          !fs.existsSync(path.join(outRoot, expectedAudio.replace(/^generated\\//, ''))) ||
          usedTurns.has(expectedId)) {
        throw new Error('Invalid or mismatched original E2 recorded turn: ' + key + ':' + turn.index);
      }
      usedTurns.add(expectedId);
      return {itemId: expectedId, speaker: turn.speaker};
    });
    lesson.microDialogues ??= [];
    lesson.microDialogues.push({id:scene.id,title:scene.title,
      speakers:{A:scene.speakers.A,B:scene.speakers.B},turns});
  }
  if (reading.get('Basic_01R')?.microDialogues?.length !== 2 ||
      reading.get('Grocery_store_very_basic_shopping')?.microDialogues?.length !== 1) {
    throw new Error('Missing E2 pilot greeting or grocery exchange');
  }
  return specification.scenes.length;
}

export function buildContent() {
  if (!fs.existsSync(legacySets)) throw new Error('Legacy content directory missing: ' + legacySets);
  fs.rmSync(outRoot, { recursive: true, force: true });
  fs.mkdirSync(outRoot, { recursive: true });
  const files = fs.readdirSync(legacySets).filter(name => name.endsWith('.json')).sort();
  const lessons = [];
  let audioCount = 0;
  const retiredSoundSets = [];
  for (const filename of files) {
    const source = JSON.parse(fs.readFileSync(path.join(legacySets, filename), 'utf8'));
    const lesson = migrateLesson(filename, source);
    if (retiredGroupedSoundSets.has(lesson.id)) {
      retiredSoundSets.push(lesson.id);
      continue;
    }
    audioCount += copyAudio(lesson.id, lesson);
    lessons.push(lesson);
  }
  if (!lessons.length) throw new Error('No lessons migrated');
  // An exact, repeatable Warsaw place-name target for Speak latency testing.
  // No invented native-speaker MP3: recording/replay works without an example.
  // The server catalogs this stable ID so opt-in Azure feedback can use the
  // authoritative spelled Polish reference rather than trusting client text.
  const guide = JSON.parse(fs.readFileSync(pronunciationGuideFile, 'utf8'));
  if (guide.schemaVersion !== 1 || guide.polish !== 'Świętokrzyska' ||
      !Array.isArray(guide.syllables) || guide.syllables.length !== 4 ||
      guide.syllables.map(s => s.polish).join('') !== guide.polish ||
      !Number.isInteger(guide.stressIndex) || guide.stressIndex !== 2 ||
      guide.reviewStatus !== 'needs_native_speaker_review' ||
      typeof guide.qualification !== 'string' || !guide.qualification ||
      !guide.syllables.every(s => typeof s.englishCue === 'string' && !!s.englishCue.trim() &&
        typeof s.tip === 'string' && !!s.tip.trim() &&
        typeof s.letterFocus === 'string' && !!s.letterFocus.trim())) {
    throw new Error('Invalid syllable-aligned Świętokrzyska pronunciation guide');
  }
  lessons.push({
    schemaVersion: 1, id: 'speak_swietokrzyska',
    title: 'Speak test · Świętokrzyska',
    kind: 'vocabulary', source: 'curated',
    items: [{
      id: 'speak_swietokrzyska:0',
      polish: guide.polish,
      english: 'Street and metro station in Warsaw',
      pronunciation: guide.syllables.map(s => s.englishCue).join(' · '),
      pronunciationGuide: {
        syllables: guide.syllables,
        stressIndex: guide.stressIndex,
        qualification: guide.qualification,
        reviewStatus: guide.reviewStatus,
      },
    }],
  });
  const soundDefinitions = JSON.parse(fs.readFileSync(curatedSoundsFile, 'utf8'));
  if (!Array.isArray(soundDefinitions) || soundDefinitions.length === 0) throw new Error('Missing curated sound definitions');
  const curatedSounds = buildSoundCurriculum(lessons, soundDefinitions);
  lessons.push(...curatedSounds);
  // The link identifies EXISTING whole-phrase sound practice, never a diagnosed
  // learner error. Do not generate it from uncalibrated Whisper transcriptions.
  const cluster = curatedSounds.find(lesson => lesson.id === 'contrast_krzy_przy');
  if (!cluster?.soundGroups?.some(group => group.id === 'krzy' && group.itemIds.length >= 2)) {
    throw new Error('Missing curated KRZY audio practice');
  }
  lessons.find(lesson => lesson.id === 'speak_swietokrzyska').items[0].soundPractice = {
    lessonId: cluster.id, groupId: 'krzy', label: 'krzy',
  };
  const readingDefinitions = JSON.parse(fs.readFileSync(readingChecksFile, 'utf8'));
  const authoredReadingChecks = attachReadingCurriculum(lessons, readingDefinitions);
  const microDialogues = attachMicroDialogues(lessons,
    JSON.parse(fs.readFileSync(microDialoguesFile, 'utf8')));
  const overrides=parsePronunciationOverrides(
    JSON.parse(fs.readFileSync(pronunciationOverridesFile,'utf8')));
  const pronunciationGrouping=attachPronunciationSegments(lessons,overrides);
  const referenceReviewItems=attachReferenceReview(lessons,
    JSON.parse(fs.readFileSync(voiceProductionFile,'utf8')),
    JSON.parse(fs.readFileSync(otherReferenceBlockersFile,'utf8')));
  fs.writeFileSync(path.join(outRoot, 'lessons.json'), JSON.stringify({ schemaVersion: 1, lessons }, null, 2) + '\n');
  const report = {
    lessons: lessons.length,
    pronunciationGrouping,
    referenceReviewItems,
    vocabulary: lessons.filter(x => x.kind === 'vocabulary').length,
    reading: lessons.filter(x => x.kind === 'reading').length,
    sounds: lessons.filter(x => x.kind === 'sounds').length,
    items: lessons.reduce((a, b) => a + b.items.length, 0),
    audioCopied: audioCount,
    curatedAudioReferences: curatedSounds.reduce((count, lesson) => count + lesson.items.filter(item => !!item.audio).length, 0),
    authoredReadingChecks,
    microDialogues,
    readingPathwayLessons: lessons.filter(lesson => lesson.progression).length,
    legacyGroupedSoundSetsRetired: retiredSoundSets,
    missingAudio: lessons.reduce((a, b) => a + b.items.filter(x => !x.audio).length, 0),
    soundLessonsNeedingReview: lessons.filter(x => x.needsReview).map(x => x.id),
  };
  fs.writeFileSync(path.join(outRoot, 'migration-report.json'), JSON.stringify(report, null, 2) + '\n');
  return report;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log('Path to Polish content migration:', JSON.stringify(buildContent()));
}
