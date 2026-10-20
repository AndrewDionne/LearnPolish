import { describe, expect, test } from 'vitest';
import { availableModes, comprehensionChoices, itemPractised, itemsForMode, progressKey, correctComprehensionAnswer, readingStage } from './modes';
import type { Lesson } from './model';

const lesson: Lesson = {
  schemaVersion: 1, id: 'sample', title: 'Sample', kind: 'reading', source: 'legacy',
  items: [
    { id: 'sample:0', polish: 'Tak', english: 'Yes', audio: 'generated/audio/sample/0.mp3' },
    { id: 'sample:1', polish: 'Nie', english: 'No' },
    { id: 'sample:2', polish: 'Może', english: 'Maybe', audio: 'generated/audio/sample/2.mp3' },
  ],
};

describe('learning modes', () => {
  test('reading exposes listen only when real audio is present', () => {
    expect(availableModes(lesson)).toEqual(['read', 'listen']);
    expect(availableModes({ ...lesson, items: [{ id: 'x', polish: 'Tak', english: 'Yes' }] })).toEqual(['read']);
    expect(availableModes({ ...lesson, kind: 'vocabulary' })).toEqual(['learn', 'speak', 'listen']);
    expect(availableModes({ ...lesson, kind: 'sounds', items: [{ id: 's', polish: 'cześć', english: 'hi' }] })).toEqual(['learn', 'speak']);
  });

  test('listening never queues an item without reference audio', () => {
    expect(itemsForMode(lesson, 'listen').map(x => x.id)).toEqual(['sample:0', 'sample:2']);
    expect(itemsForMode(lesson, 'read')).toHaveLength(3);
  });

  test('two pending Conversation 1 references stay in Learn and Speak but not Listen',()=>{
    const greetings: Lesson={...lesson,id:'Conversation_1',kind:'vocabulary',
      items:[{id:'Conversation_1:23',polish:'Jak masz na imię?',english:'What is your name?',
                 audio:'generated/audio/Conversation_1/23.mp3'},
             {id:'Conversation_1:24',polish:'Jak ma pan/pani na imię?',english:'Formal name question',
                 audio:'generated/audio/Conversation_1/24.mp3',referenceReview:'practice_only'},
             {id:'Conversation_1:25',polish:'Mam na imię…',english:'My name is',
                 audio:'generated/audio/Conversation_1/25.mp3',referenceReview:'practice_only'}]};
    expect(availableModes(greetings)).toEqual(['learn','speak','listen']);
    expect(itemsForMode(greetings,'listen').map(item=>item.id)).toEqual(['Conversation_1:23']);
    expect(itemsForMode(greetings,'learn')).toHaveLength(3);
    expect(itemsForMode(greetings,'speak')).toHaveLength(3);
  });

  test('only unverified recordings never expose an empty Listen tab',()=>{
    const hold:Lesson={...lesson,kind:'vocabulary',items:[
      {id:'pending:0',polish:'Co pan/pani poleca?',english:'What do you recommend?',
       referenceReview:'practice_only',audio:'generated/audio/pending/0.mp3'},
      {id:'pending:1',polish:'Jak dojść do …?',english:'How do I get to?',
       referenceReview:'practice_only',audio:'generated/audio/pending/1.mp3'},
    ]};
    expect(availableModes(hold)).toEqual(['learn','speak']);
    expect(itemsForMode(hold,'learn')).toHaveLength(2);
    expect(itemsForMode(hold,'speak')).toHaveLength(2);
    expect(itemsForMode(hold,'listen')).toHaveLength(0);
  });

  test('comprehension choices include target exactly once and unique distractors', () => {
    for (let i = 0; i < lesson.items.length; i++) {
      const choices = comprehensionChoices(lesson.items, lesson.items[i], i);
      expect(choices.filter(x => x === lesson.items[i].english)).toHaveLength(1);
      expect(new Set(choices).size).toBe(choices.length);
    }
    expect(comprehensionChoices([lesson.items[0]], lesson.items[0], 0)).toEqual([]);
  });

  test('authored dialogue questions take precedence; missing dialogue checks never invent a scored quiz', () => {
    const authored = {
      ...lesson.items[0],
      comprehension: {prompt:'What is being asked?', options:['How are you?','What is your name?','Where are you?'] as [string,string,string], correctIndex:0, feedback:'Greeting question'},
    };
    expect(comprehensionChoices(lesson.items, authored, 0, true)).toEqual(authored.comprehension.options);
    expect(correctComprehensionAnswer(authored)).toBe('How are you?');
    expect(comprehensionChoices(lesson.items, lesson.items[1], 1, true)).toEqual([]);
    expect(correctComprehensionAnswer(lesson.items[1])).toBeNull();
    expect(readingStage('getting-around')).toBe('Getting around');
  });

  test('mode-specific practice leaves Learn history intact', () => {
    expect(progressKey('sample:0', 'learn')).toBe('sample:0');
    expect(progressKey('sample:0', 'listen')).toBe('listen:sample:0');
    expect(itemPractised({ 'listen:sample:0': {} }, 'sample:0')).toBe(true);
    expect(itemPractised({}, 'sample:0')).toBe(false);
  });
});
