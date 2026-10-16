import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const legacySets = path.join(root, 'docs/sets');
const legacyAudio = path.join(root, 'docs/static');
const outRoot = path.join(root, 'v2/frontend/public/generated');
const curatedSoundsFile = path.join(root, 'v2/content/sound-contrasts.json');
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
        const id = definition.id + ':' + group.id + ':' + i;
        itemIds.push(id);
        items.push({
          id, polish: matched.polish, english: matched.english,
          audio: matched.audio, soundGroupId: group.id,
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
  const soundDefinitions = JSON.parse(fs.readFileSync(curatedSoundsFile, 'utf8'));
  if (!Array.isArray(soundDefinitions) || soundDefinitions.length === 0) throw new Error('Missing curated sound definitions');
  const curatedSounds = buildSoundCurriculum(lessons, soundDefinitions);
  lessons.push(...curatedSounds);
  fs.writeFileSync(path.join(outRoot, 'lessons.json'), JSON.stringify({ schemaVersion: 1, lessons }, null, 2) + '\n');
  const report = {
    lessons: lessons.length,
    vocabulary: lessons.filter(x => x.kind === 'vocabulary').length,
    reading: lessons.filter(x => x.kind === 'reading').length,
    sounds: lessons.filter(x => x.kind === 'sounds').length,
    items: lessons.reduce((a, b) => a + b.items.length, 0),
    audioCopied: audioCount,
    curatedAudioReferences: curatedSounds.reduce((count, lesson) => count + lesson.items.filter(item => !!item.audio).length, 0),
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
