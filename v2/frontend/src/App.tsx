import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Lesson, LessonItem, LessonKind } from './model';
import { lessonLabel, parseManifest } from './model';
import { AUDIO_RATES, useLessonAudio } from './audio';
import OfflineDownloadControl from './OfflineDownloadControl';
import SpeakPanel from './speech/SpeakPanel';
import {requestSpeechFeedback, SPEECH_ASSESSMENT_AVAILABLE, SPEECH_BLEND_AVAILABLE} from './speech/assessment';
import SoundContrastDeck from './SoundContrastDeck';
import MicroDialoguePanel from './MicroDialoguePanel';
import { groupLibraryLessons, libraryMatches, inLibraryView, libraryViewCount, LIBRARY_STAGES } from './library-curriculum';
import type { LibraryView } from './library-curriculum';
import { parseProgress, recallRate, recordAttempt, STORAGE_KEY } from './progress';
import type { Progress } from './progress';
import { PERSONAL_STORAGE_KEY, importPersonalLesson, makePersonalLesson, parsePersonalLessons, toPortableLesson, upsertPersonalLesson } from './personal';
import type { DraftItem } from './personal';
import { availableModes, comprehensionChoices, correctComprehensionAnswer, itemPractised, itemsForMode, progressKey, readingStage } from './modes';
import type { LearningMode } from './modes';
import { READING_POSITION_KEY, parseReadingPositions, safeReadingPosition } from './reading-position';
import { firstUnvisitedBatch, practiceBatchCount, practiceBatchItems, practiceBatchLabel, usesPracticeBatches } from './practice-batches';
import { REVIEW_STORAGE_KEY, countDue, dueItems, nextDue, parseReviewSchedule, recordReview } from './review';
import type { ReviewSchedule } from './review';
import { MAX_BACKUP_BYTES, makeBackup, parseBackup } from './backup';
import { persistRestoredBackup } from './restore-storage';
import { claimCompletion } from './completion-guard';
import { GOLD_STORAGE_KEY, parseGold } from './gold';
import type { RewardMode } from './gold';
import ExpeditionMap from './expedition/ExpeditionMap';
import FamilyPanel from './family/FamilyPanel';
import ProfilePanel from './family/ProfilePanel';
import {shareFamilyActivity} from './family/api';
import type {FamilyConnection,FamilySummary} from './family/api';
import { EXPEDITION_STORAGE_KEY, awardXp, emptyExpedition, nextRegionCost,
  parseExpedition, regionTotal, setXpGoal, unlockedRegions, xpSummary } from './expedition/expedition';
import type { LearningTier, VerifiedOutcome } from './expedition/expedition';

type Page = 'home' | 'library' | 'practice' | 'expedition' | 'groups' | 'profile';
type KindFilter = 'all' | LessonKind;
type SoundPracticeReturn = {
  sourceLessonId:string;sourceItemId:string;sourceIndex:number;
  sourceGuideVisible:boolean;sourceReviewOnly:string[]|null;sourceSessionStartXp:number;
  sourceBatchIndex:number;
  practiceLessonId:string;practiceGroupId:string;sourceWord:string;
};

const nav: { id: Page; label: string; symbol: string }[] = [
  { id: 'home', label: 'Home', symbol: '⌂' },
  { id: 'library', label: 'Library', symbol: '▦' },
  { id: 'practice', label: 'Practice', symbol: '◎' },
  { id: 'expedition', label: 'Expedition', symbol: '◇' },
  { id: 'profile', label: 'Profile', symbol: '◷' },
];

function storedLastLesson(): string | null {
  try { return localStorage.getItem('ptp-v2-last-lesson'); } catch { return null; }
}

function saveLastLesson(id: string) {
  try { localStorage.setItem('ptp-v2-last-lesson', id); } catch { /* browser may block storage */ }
}

function Counter({ value, label }: { value: string | number; label: string }) {
  return <div className="stat"><strong>{value}</strong><span>{label}</span></div>;
}

function LessonTile({ lesson, completed, onOpen }: { lesson: Lesson; completed: number; onOpen: () => void }) {
  const symbol = lesson.kind === 'reading' ? '✳' : lesson.kind === 'sounds' ? '♫' : 'Aa';
  return <button type="button" className="lesson-tile" onClick={onOpen}>
    <span className={'lesson-art ' + lesson.kind}>{symbol}</span>
    <span className="lesson-tile-body">
      <span className="eyebrow">{lessonLabel(lesson.kind)}</span>
      <strong>{lesson.title}</strong>
      {lesson.description && <span className="tile-description">{lesson.description}</span>}
      {lesson.progression && <span className="reading-stage">Step {lesson.progression.order} · {readingStage(lesson.progression.stage)}</span>}
      <span className="tile-detail">{lesson.items.length} {lesson.kind === 'reading' ? 'passages' : 'items'} · {completed} practised</span>
      <span className="meter" aria-hidden="true"><span style={{ width: (100 * completed / lesson.items.length) + '%' }} /></span>
    </span>
    <span className="tile-arrow" aria-hidden="true">↗</span>
  </button>;
}

function AudioButton({ item, playing, onPlay }: {
  item: LessonItem; playing: string | null; onPlay: (path: string) => void;
}) {
  const available=!!item.audio && item.referenceReview !== 'practice_only';
  return <button type="button" className="audio-btn" disabled={!available}
    title={!available ? 'Verified reference recording unavailable' : 'Play Polish recording'}
    onClick={() => available && item.audio && onPlay(item.audio)}>
    <span aria-hidden="true">{available && playing === item.audio ? '◼' : '▶'}</span> {available && playing === item.audio ? 'Playing audio' : available ? 'Play audio' : item.referenceReview === 'practice_only' ? 'Reference pending' : 'No audio'}
  </button>;
}

export default function App() {
  const [page, setPage] = useState<Page>('home');
  const [builtIn, setBuiltIn] = useState<Lesson[]>([]);
  const [personal, setPersonal] = useState<Lesson[]>(() => {
    try { return parsePersonalLessons(localStorage.getItem(PERSONAL_STORAGE_KEY)); } catch { return []; }
  });
  const lessons = useMemo(() => [...builtIn, ...personal.filter(x => !builtIn.some(y => y.id === x.id))], [builtIn, personal]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftKind, setDraftKind] = useState<LessonKind>('vocabulary');
  const [draftRows, setDraftRows] = useState<DraftItem[]>([{ polish: '', english: '' }]);
  const [editorError, setEditorError] = useState('');
  const [importError, setImportError] = useState('');
  const [backupStatus, setBackupStatus] = useState('');
  const [backupError, setBackupError] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<KindFilter>('all');
  const [libraryView,setLibraryView] = useState<LibraryView>('all');
  const [lessonId, setLessonId] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [batchIndex,setBatchIndex] = useState(0);
  const [microDialogueId,setMicroDialogueId] = useState<string|null>(null);
  const [sessionStartXp, setSessionStartXp] = useState(0);
  const [mode, setMode] = useState<LearningMode>('learn');
  // One deliberate choice for the current Speak session, OFF at lesson start.
  // Keeps the guide open if the learner advances, without a persistent gate.
  const [guideVisible,setGuideVisible] = useState(false);
  const [soundReturn,setSoundReturn] = useState<SoundPracticeReturn|null>(null);
  const [reviewOnly, setReviewOnly] = useState<string[] | null>(null);
  const [listenGuess, setListenGuess] = useState<string | null>(null);
  const [readGuess, setReadGuess] = useState<string | null>(null);
  const [listenRevealed, setListenRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const [readingPositions, setReadingPositions] = useState(() => {
    try { return parseReadingPositions(localStorage.getItem(READING_POSITION_KEY)); } catch { return {}; }
  });
  const [revealed, setRevealed] = useState(false);
  const [translationOpen, setTranslationOpen] = useState(false);
  const [progress, setProgress] = useState<Progress>(() => {
    try { return parseProgress(localStorage.getItem(STORAGE_KEY)); } catch { return {}; }
  });
  const [lastLesson, setLastLesson] = useState<string | null>(storedLastLesson);
  const [expedition, setExpedition] = useState(() => {
    try { return parseExpedition(localStorage.getItem(EXPEDITION_STORAGE_KEY),
      parseGold(localStorage.getItem(GOLD_STORAGE_KEY))); }
    catch { return emptyExpedition(); }
  });
  const [selfGoalDraft, setSelfGoalDraft] = useState('500');
  const [familyConnection,setFamilyConnection] = useState<FamilyConnection|null>(null);
  const [familySummary,setFamilySummary] = useState<FamilySummary|null>(null);
  const [familySyncStatus,setFamilySyncStatus] = useState('');
  const [familySyncVersion,setFamilySyncVersion] = useState(0);
  const changeFamilyConnection = useCallback((next:FamilyConnection|null)=>setFamilyConnection(next),[]);
  const [reviews, setReviews] = useState<ReviewSchedule>(() => {
    try { return parseReviewSchedule(localStorage.getItem(REVIEW_STORAGE_KEY)); } catch { return {}; }
  });
  const audio = useLessonAudio();
  useEffect(() => { setSelfGoalDraft(String(expedition.selfGoal)); }, [expedition.selfGoal]);
  useEffect(() => {
    try { localStorage.setItem(EXPEDITION_STORAGE_KEY, JSON.stringify(expedition)); } catch { /* local only */ }
  }, [expedition]);
  const mainRef = useRef<HTMLElement>(null);
  const hasMounted = useRef(false);
  // Announce full-screen route changes to keyboard and assistive-technology users.
  // Advancing cards or switching learning modes deliberately does not steal focus.
  useEffect(() => {
    if (!hasMounted.current) { hasMounted.current = true; return; }
    mainRef.current?.focus({ preventScroll: true });
  }, [page, lessonId, editorOpen]);
  // A focused group destination must be visible immediately, even if the
  // learner came from the bottom of a long Profile or Expedition page.
  useEffect(() => {
    if (page === 'groups' || page === 'expedition') {
      window.scrollTo({top:0,behavior:'auto'});
    }
  }, [page]);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const response = await fetch(import.meta.env.BASE_URL + 'generated/lessons.json', { signal: controller.signal });
        if (!response.ok) throw new Error('Content unavailable (' + response.status + ')');
        const data = parseManifest(await response.json());
        if (!controller.signal.aborted) { setBuiltIn(data); setLoadError(''); }
      } catch (error) {
        if (!controller.signal.aborted) setLoadError(error instanceof Error ? error.message : 'Unable to load lessons');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(progress)); } catch { /* local progress is best effort */ }
  }, [progress]);
  useEffect(() => {
    try { localStorage.setItem(PERSONAL_STORAGE_KEY, JSON.stringify(personal)); } catch { /* local sets are best effort */ }
  }, [personal]);

  useEffect(() => {
    try { localStorage.setItem(READING_POSITION_KEY, JSON.stringify(readingPositions)); } catch { /* local-only progress */ }
  }, [readingPositions]);

  useEffect(() => {
    try { localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(reviews)); } catch { /* local-only review state */ }
  }, [reviews]);

  const active = lessons.find(x => x.id === lessonId);
  const activeMicroDialogue=active?.microDialogues?.find(dialogue=>dialogue.id===microDialogueId);
  const focusedGroup = soundReturn && soundReturn.practiceLessonId === active?.id ? soundReturn.practiceGroupId : null;
  const batched = !!active && usesPracticeBatches(active) && !reviewOnly && !focusedGroup;
  const totalBatches = batched && active ? practiceBatchCount(active) : 1;
  const sessionItems = active
    ? focusedGroup ? itemsForMode(active, mode).filter(item => item.soundGroupId === focusedGroup)
      : reviewOnly && mode === 'learn' ? active.items.filter(item => reviewOnly.includes(item.id))
      : batched ? practiceBatchItems(active, mode, batchIndex)
      : itemsForMode(active, mode)
    : [];
  const current = sessionItems[index];
  // A rapid repeat activation of the same visible answer must not create a
  // second recall/review attempt. This lock is specific to a lesson step, NOT
  // a permanent per-item lock: intentional repeat sessions remain available.
  const completionGuard=useRef<{step:string|null}>({step:null});
  const completionStep=[lessonId,mode,batchIndex,index,current?.id].join('|');
  useEffect(()=>{completionGuard.current.step=null;},
    [lessonId,mode,batchIndex,index,current?.id,finished]);
  const claimCurrentCompletion=()=>!!current&&!finished&&
    claimCompletion(completionGuard.current,completionStep);
  const listeningChoices = active && current && mode === 'listen' ? comprehensionChoices(active.items, current, index, active.kind === 'reading') : [];
  const correctAnswer = current ? correctComprehensionAnswer(current) : null;
  const chosenAnswer = correctAnswer || current?.english || '';
  const listenAnsweredCorrectly = listenGuess !== null && listenGuess === chosenAnswer;
  const last = lessons.find(x => x.id === lastLesson);
  const practisedCount = lessons.reduce((total, lesson) =>
    total + lesson.items.filter(item => itemPractised(progress, item.id)).length, 0);
  const completedIn = (lesson: Lesson) => lesson.items.filter(item => itemPractised(progress, item.id)).length;
  const nowIso = new Date().toISOString();
  const xpStats = xpSummary(expedition, nowIso);
  const sessionXp = expedition.events.slice(sessionStartXp).reduce((sum,event)=>sum+event.xp,0);
  const explored = unlockedRegions(expedition);
  const selectedXp = regionTotal(expedition,expedition.selectedRegion);
  const selectedTarget = expedition.regionGoals[expedition.selectedRegion] ?? nextRegionCost(expedition);
  const totalDue = countDue(lessons, reviews, nowIso);
  const scheduledNext = nextDue(lessons, reviews, nowIso);
  const dueLessons = lessons.filter(lesson => dueItems(lesson, reviews, nowIso).length > 0);

  const filtered = useMemo(() => lessons.filter(x =>
    (filter === 'all' || x.kind === filter) && libraryMatches(x,query)
  ), [lessons, filter, query]);
  const visibleLessons = useMemo(() => filtered.filter(x=>inLibraryView(x,libraryView)),
    [filtered,libraryView]);
  const librarySections = useMemo(() => groupLibraryLessons(visibleLessons),[visibleLessons]);
  const libraryViewOptions: {id:LibraryView;label:string;count:number}[] = [
    {id:'all',label:'All stages',count:lessons.length},
    ...LIBRARY_STAGES.map(stage=>({
      id:stage.id,label:stage.heading,count:libraryViewCount(lessons,stage.id),
    })),
    ...(libraryViewCount(lessons,'personal')>0 ? [{
      id:'personal' as const,label:'Your lessons',count:libraryViewCount(lessons,'personal'),
    }] : []),
  ];
  // Choosing a stage is direct navigation, not another opaque stacked filter.
  const chooseLibraryView=(next:LibraryView)=>{
    setLibraryView(next);setQuery('');setFilter('all');
  };

  const stopAudio = () => { audio.stop(); };
  const goTo = (destination: Page) => {
    stopAudio(); setLessonId(null); setGuideVisible(false); setSoundReturn(null); setEditorOpen(false); setReviewOnly(null); setBatchIndex(0); setMicroDialogueId(null); setPage(destination); setRevealed(false); setFinished(false);
  };
  const openLesson = (lesson: Lesson) => {
    stopAudio();
    setSoundReturn(null);
    setReviewOnly(null);
    setMicroDialogueId(null);
    setSessionStartXp(expedition.events.length);
    setLessonId(lesson.id); setGuideVisible(false); setMode(lesson.kind === 'reading' ? 'read' : 'learn');
    setBatchIndex(firstUnvisitedBatch(lesson, progress));
    setIndex(lesson.kind === 'reading' ? safeReadingPosition(readingPositions, lesson.id, lesson.items.length) : 0);
    setRevealed(false); setTranslationOpen(false); setListenGuess(null); setReadGuess(null); setListenRevealed(false); setFinished(false);
    setLastLesson(lesson.id); saveLastLesson(lesson.id);
  };
  const openSoundPractice = () => {
    if (!active || !current?.soundPractice || mode !== 'speak' || soundReturn) return;
    const focus = current.soundPractice;
    const destination = lessons.find(lesson => lesson.id === focus.lessonId && lesson.kind === 'sounds');
    const group = destination?.soundGroups?.find(g => g.id === focus.groupId);
    if (!destination || !group?.itemIds.length) return;
    stopAudio();
    setSoundReturn({
      sourceLessonId:active.id,sourceItemId:current.id,sourceIndex:index,
      sourceGuideVisible:guideVisible,sourceReviewOnly:reviewOnly,
      sourceBatchIndex:batchIndex,sourceSessionStartXp:sessionStartXp,practiceLessonId:destination.id,
      practiceGroupId:group.id,sourceWord:current.polish,
    });
    setLessonId(destination.id); setMode('speak'); setIndex(0); setBatchIndex(0);
    setGuideVisible(false); setReviewOnly(null);
    setSessionStartXp(expedition.events.length);
    setRevealed(false); setTranslationOpen(false); setListenGuess(null);
    setReadGuess(null); setListenRevealed(false); setFinished(false);
  };
  const returnFromSoundPractice = () => {
    if (!soundReturn || active?.id !== soundReturn.practiceLessonId) return;
    const source = lessons.find(lesson => lesson.id === soundReturn.sourceLessonId);
    const sourceItems = source && usesPracticeBatches(source) && !soundReturn.sourceReviewOnly
      ? practiceBatchItems(source, 'speak', soundReturn.sourceBatchIndex)
      : source?.items;
    if (!source || sourceItems?.[soundReturn.sourceIndex]?.id !== soundReturn.sourceItemId) {
      goTo('library'); return;
    }
    stopAudio();
    setLessonId(source.id); setMode('speak'); setIndex(soundReturn.sourceIndex);
    setGuideVisible(soundReturn.sourceGuideVisible);
    setReviewOnly(soundReturn.sourceReviewOnly);
    setBatchIndex(soundReturn.sourceBatchIndex);
    setSessionStartXp(soundReturn.sourceSessionStartXp);
    setRevealed(false); setTranslationOpen(false); setListenGuess(null);
    setReadGuess(null); setListenRevealed(false); setFinished(false);
    setSoundReturn(null);
  };
  const openDueReview = (lesson: Lesson) => {
    const due = dueItems(lesson, reviews, new Date().toISOString()).map(item => item.id);
    if (!due.length || lesson.kind === 'reading') return;
    openLesson(lesson);
    setReviewOnly(due); setMode('learn'); setIndex(0); setBatchIndex(0);
  };
  const jump = (target: number) => {
    if (!active) return;
    stopAudio();
    const next = Math.max(0, Math.min(sessionItems.length - 1, target));
    setIndex(next);
    if (mode === 'read') setReadingPositions(previous => ({ ...previous, [active.id]: next }));
    setRevealed(false); setTranslationOpen(false); setListenGuess(null); setReadGuess(null); setListenRevealed(false); setFinished(false);
  };
  const changeBatch = (target: number) => {
    if (!active || !batched || target < 0 || target >= totalBatches || target === batchIndex) return;
    stopAudio(); setBatchIndex(target); setIndex(0);
    setRevealed(false); setTranslationOpen(false); setListenGuess(null);
    setReadGuess(null); setListenRevealed(false); setFinished(false);
  };
  const switchMode = (next: LearningMode) => {
    if (!active || !availableModes(active).includes(next)) return;
    stopAudio();
    setMicroDialogueId(null);
    setMode(next);
    setSessionStartXp(expedition.events.length);
    setReviewOnly(null);
    setIndex(next === 'read' ? safeReadingPosition(readingPositions, active.id, active.items.length) : 0);
    setRevealed(false); setTranslationOpen(false); setListenGuess(null); setReadGuess(null); setListenRevealed(false); setFinished(false);
  };
  const earn = (id: string, learningMode: RewardMode, outcome?: VerifiedOutcome) => {
    const timestamp = new Date().toISOString();
    setExpedition(previous => awardXp(previous, id, learningMode, timestamp,
      (active?.difficultyTier ?? 1) as LearningTier, outcome));
    // Account holders explicitly opt in to sharing only NEW practice in their family.
    // Never transmit prior backups, audio, personal lessons or client-calculated XP.
    if (familyConnection && builtIn.some(lesson=>lesson.items.some(item=>item.id===id))) {
      void shareFamilyActivity(familyConnection,id,learningMode,expedition.selectedRegion)
        .then(accepted=>{
          setFamilySyncStatus(accepted?'Practice contributed to your family.':'Already credited today.');
          if(accepted)setFamilySyncVersion(version=>version+1);
        })
        .catch(()=>setFamilySyncStatus('Family sync unavailable. Your personal XP remains saved locally.'));
    }
  };
  const record = (remembered: boolean) => {
    if (!claimCurrentCompletion()) return;
    const at = new Date().toISOString();
    setProgress(previous => recordAttempt(previous, progressKey(current.id, mode), remembered, at));
    if (mode === 'learn' || mode === 'read' || mode === 'listen') {
      const objective = current.comprehension && (
        (mode === 'read' && readGuess !== null) ||
        (mode === 'listen' && listenGuess !== null));
      const measured: VerifiedOutcome | undefined = objective
        ? {skill:'comprehension',metric:'dialogue-v1',score:remembered?1:0,evidence:'verified'}
        : undefined;
      earn(current.id, mode, measured);
    }
    if (mode === 'learn') setReviews(previous => recordReview(previous, current.id, remembered, at));
    if (index < sessionItems.length - 1) jump(index + 1);
    else { stopAudio(); setFinished(true); }
  };
  const beginNew = () => {
    stopAudio(); setLessonId(null); setPage('library'); setEditorOpen(true);
    setEditingId(null); setDraftTitle(''); setDraftKind('vocabulary');
    setDraftRows([{ polish: '', english: '' }]); setEditorError('');
  };
  const beginEdit = (lesson: Lesson) => {
    if (lesson.source !== 'personal') return;
    stopAudio(); setLessonId(null); setPage('library'); setEditorOpen(true);
    setEditingId(lesson.id); setDraftTitle(lesson.title); setDraftKind(lesson.kind);
    setDraftRows(lesson.items.map(({ id, polish, english, pronunciation, title }) => ({ id, polish, english, pronunciation, title })));
    setEditorError('');
  };
  const changeDraftRow = (index: number, key: 'polish' | 'english', value: string) =>
    setDraftRows(old => old.map((row, i) => i === index ? { ...row, [key]: value } : row));
  const saveDraft = () => {
    try {
      const original = editingId ? personal.find(x => x.id === editingId) : undefined;
      const lesson = makePersonalLesson({ title: draftTitle, kind: draftKind, items: draftRows }, original);
      const next = upsertPersonalLesson(personal, lesson);
      setPersonal(next); setEditorOpen(false); setEditorError(''); openLesson(lesson);
    } catch (error) {
      setEditorError(error instanceof Error ? error.message : 'Unable to save lesson');
    }
  };
  const importFile = async (file: File | undefined) => {
    if (!file) return;
    try {
      if (file.size > 250_000) throw new Error('Lesson JSON exceeds the 250 KB import limit.');
      const imported = importPersonalLesson(JSON.parse(await file.text()));
      setPersonal(old => upsertPersonalLesson(old, imported));
      setImportError('');
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Unable to import lesson');
    }
  };
  const exportFile = (lesson: Lesson) => {
    const blob = new Blob([JSON.stringify(toPortableLesson(lesson), null, 2) + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = lesson.id + '.json'; document.body.appendChild(anchor);
    anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  const downloadBackup = () => {
    try {
      const data = makeBackup({
        personalLessons: personal, progress, reviews, readingPositions, lastLessonId: lastLesson, expedition,
      }, new Date().toISOString());
      const blob = new Blob([JSON.stringify(data, null, 2) + '\n'], {type:'application/json'});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.href=url; link.download='path-to-polish-v2-backup.json'; document.body.appendChild(link);
      link.click(); link.remove();
      window.setTimeout(()=>URL.revokeObjectURL(url), 0);
      setBackupError(''); setBackupStatus('Your current learning data was exported as a JSON file.');
    } catch {
      setBackupStatus(''); setBackupError('Unable to export local learning data.');
    }
  };
  const restoreBackup = async (file: File | undefined) => {
    if (!file) return;
    setBackupError(''); setBackupStatus('');
    try {
      if (file.size > MAX_BACKUP_BYTES) throw new Error('Backup exceeds the 2 MB file limit.');
      const data = parseBackup(JSON.parse(await file.text()));
      const confirmed = window.confirm(
        'Restore backup from ' + new Date(data.exportedAt).toLocaleDateString() + '?\n\n' +
        'This will replace ALL personal lessons, practice history, scheduled reviews and reading positions saved in this browser. The current local data will be lost. Export a backup first if you need it.'
      );
      if (!confirmed) {setBackupStatus('Restore cancelled. Your existing data was not changed.');return;}
      // Commit all validated records to storage FIRST. On quota/permission errors,
      // roll back earlier keys and do not mutate the live learning session.
      const restoredExpedition=persistRestoredBackup(data,localStorage);
      stopAudio();
      setPersonal(data.personalLessons);
      setProgress(data.progress);
      setReviews(data.reviews);
      setExpedition(restoredExpedition);
      setReadingPositions(data.readingPositions);
      setLastLesson(data.lastLessonId);
      setLessonId(null); setEditorOpen(false); setReviewOnly(null); setPage('profile');
      setBackupStatus('Backup restored: ' + data.personalLessons.length + ' personal lessons and their saved practice records.');
    } catch (error) {
      setBackupError(error instanceof Error ? error.message : 'Could not restore the backup.');
    }
  };
  const deletePersonalLesson = (lesson: Lesson) => {
    if (lesson.source !== 'personal' || !window.confirm('Delete this personal lesson? This cannot be undone.')) return;
    setPersonal(old => old.filter(x => x.id !== lesson.id));
    setProgress(old => {
      const next = { ...old };
      for (const item of lesson.items) delete next[item.id];
      return next;
    });
    setReviews(old => {
      const next = { ...old };
      for (const item of lesson.items) delete next[item.id];
      return next;
    });
    if (lastLesson === lesson.id) {
      setLastLesson(null);
      try { localStorage.removeItem('ptp-v2-last-lesson'); } catch { /* best effort */ }
    }
    goTo('library');
  };
  const play = (path: string) => { void audio.play(path); };

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className="sidebar">
      <button className="brand" type="button" onClick={() => goTo('home')}>
        <span className="brand-symbol">p<span>.</span></span>
        <span className="brand-name">path to <strong>polish</strong><small>LEARN WITH CONFIDENCE</small></span>
      </button>
      <span className="nav-heading">EXPLORE</span>
      <nav className="side-links" aria-label="Main navigation">
        {nav.map(item => <button key={item.id} className={'nav-link ' + (!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'selected' : '')} type="button" aria-current={!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'page' : undefined} onClick={() => goTo(item.id)}><span className="nav-icon" aria-hidden="true">{item.symbol}</span>{item.label}</button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="mini-mark">PL</div>
        <div><strong>A little every day.</strong><span>Keep building your Polish.</span></div>
      </div>
      <span className="sidebar-version">Path to Polish · V2 preview</span>
    </aside>

    <div className="main-shell">
      <header className="topbar">
        <div className="crumb"><span>PATH TO POLISH</span><span className="crumb-slash">/</span><strong>{active ? active.title : page === 'groups' ? 'Learning groups' : nav.find(x => x.id === page)?.label}</strong></div>
        <div className="top-right"><span className="local-pill">● Local preview</span><span className="initial-badge" aria-label="Local learner">P</span></div>
      </header>
      <main className="page-content" id="main-content" ref={mainRef} tabIndex={-1}>
        {loading && <section className="empty-state" role="status"><h2>Gathering your lessons…</h2><p>Preparing your Polish library.</p></section>}
        {!loading && loadError && <section className="empty-state" role="alert"><h2>Lessons could not load</h2><p>{loadError}</p><p>Run <code>npm run content</code> in v2/frontend, then reload. Your progress remains saved locally.</p></section>}

        {!loading && !loadError && active && current && <div className={'learning' + (mode === 'speak' ? ' speak-focused' : '')}>
          <div className="lesson-tools"><button type="button" className="back-link" onClick={soundReturn && active.id === soundReturn.practiceLessonId ? returnFromSoundPractice : () => goTo('library')}>{soundReturn && active.id === soundReturn.practiceLessonId ? '← Back to ' + soundReturn.sourceWord : '← Back to library'}</button>{mode !== 'speak' && <div><button type="button" onClick={() => exportFile(active)}>Export JSON</button><OfflineDownloadControl lesson={active}/>{active.source === 'personal' && <><button type="button" onClick={() => beginEdit(active)}>Edit lesson</button><button type="button" className="delete-link" onClick={() => deletePersonalLesson(active)}>Delete</button></>}</div>}</div>
          {mode === 'speak'
            ? <div className="learning-head speak-compact-head"><span className="item-count">{index + 1} <span>/ {sessionItems.length}</span></span></div>
            : <div className="learning-head">
            <div><span className="eyebrow">{reviewOnly ? 'DUE REVIEW' : lessonLabel(active.kind)} · {active.title}</span><h1>{reviewOnly ? 'Review what matters' : mode === 'listen' ? 'Train your ear' : mode === 'read' ? 'Read & understand' : active.kind === 'sounds' ? 'Hear the difference' : 'Learn the language'}</h1><p>{reviewOnly ? 'These expressions are due for recall practice. Answer honestly; missed items remain available for review.' : mode === 'listen' ? 'Listen first, choose the meaning, then compare your answer with the Polish transcript.' : mode === 'read' ? 'Read naturally, then reveal the translation. Your reading position is remembered.' : active.kind === 'sounds' ? active.soundGroups ? 'Play each recording individually and compare neighbouring sound families. Audio quality and pronunciation notes await native review.' : 'Compare the examples and listen carefully. These lessons await native-speaker review.' : 'Think of the Polish expression before revealing its meaning.'}</p></div>
            <span className="item-count">{activeMicroDialogue && mode === 'read' ? 'Dialogue' : index + 1} {!activeMicroDialogue && <span>/ {sessionItems.length}</span>}</span>
          </div>}
          {active.progression && <p className="pathway-hint">Reading pathway · Step {active.progression.order} · {readingStage(active.progression.stage)} — {active.progression.goal}</p>}
          {!(activeMicroDialogue && mode === 'read') && <div className="lesson-meter" role="progressbar" aria-label="Lesson progress" aria-valuemin={0} aria-valuemax={sessionItems.length} aria-valuenow={index + 1}><span style={{ width: (100 * (index + 1) / sessionItems.length) + '%' }} /></div>}
          <div className="mode-row" role="group" aria-label="Learning modes">
            {availableModes(active).map(value => <button type="button" key={value} aria-pressed={mode === value} className={'mode ' + (mode === value ? 'active' : '')} onClick={() => switchMode(value)}>{value === 'learn' ? active.kind === 'sounds' ? 'Sounds' : 'Learn' : value === 'read' ? 'Read' : value === 'speak' ? 'Speak' : 'Listen'}</button>)}
          </div>
          {mode === 'read' && active.microDialogues?.length && <div className="micro-dialogue-picker" role="group" aria-label="Short conversations">
            <span>Short conversations</span>
            {active.microDialogues.map(dialogue=><button type="button" key={dialogue.id}
              aria-pressed={microDialogueId===dialogue.id} onClick={()=>{
                stopAudio(); setMicroDialogueId(dialogue.id);
              }}>{dialogue.title} · {dialogue.turns.length} turns</button>)}
          </div>}
          {batched && <label className="practice-group-picker">Practice group
            <select aria-label="Practice group" value={batchIndex} onChange={event => changeBatch(Number(event.target.value))}>
              {Array.from({length:totalBatches},(_,part) => <option key={part} value={part}>{practiceBatchLabel(active,part)}</option>)}
            </select>
          </label>}
          {active.kind === 'sounds' && mode === 'learn' && !finished && active.soundGroups && <SoundContrastDeck lesson={active} focusGroupId={focusedGroup ?? undefined} currentId={current.id} playing={audio.playing} onSelect={id => {
            const target = sessionItems.findIndex(item => item.id === id);
            if (target >= 0) jump(target);
          }} onPlay={play}/>}
          {activeMicroDialogue && mode === 'read'
            ? <MicroDialoguePanel key={activeMicroDialogue.id} lesson={active} dialogue={activeMicroDialogue}
                playing={audio.playing} rate={audio.rate} audioError={audio.error}
                onRateChange={audio.setRate} onPlay={play} onStop={stopAudio}
                onClose={()=>setMicroDialogueId(null)}/>
            : finished ? <section className="flashcard complete-card" aria-live="polite">
            <span className="card-label">{reviewOnly ? 'REVIEW COMPLETE' : 'SESSION COMPLETE'}</span>
            <h2>Nicely done!</h2>
            <p>You made it through {sessionItems.length} {sessionItems.length === 1 ? 'item' : 'items'} in {mode === 'listen' ? 'listening practice' : mode === 'read' ? 'reading practice' : mode === 'speak' ? 'speaking practice (unscored)' : 'learning practice'}.</p>
            <p className="reward-note" aria-live="polite">{sessionXp ? '+' + sessionXp + ' XP earned in this session.' : 'No new XP this session — skips and repeats are not rewarded.'} Your total: {xpStats.total} XP.</p>
            {availableModes(active).some(candidate => candidate !== mode) && <div className="mode-handoff" role="group" aria-label="Continue learning in another mode">
              <strong>Keep going with another mode</strong><div>
              {availableModes(active).filter(candidate => candidate !== mode).map(candidate => <button type="button" key={candidate} className="handoff-button" onClick={() => switchMode(candidate)}>
                {candidate === 'learn' ? 'Learn' : candidate === 'read' ? 'Read' : candidate === 'speak' ? 'Speak' : 'Listen'} →
              </button>)}</div>
            </div>}
            <div className="answer-actions"><button type="button" className="secondary-action" onClick={() => jump(0)}>Practise again</button>
              {batched && batchIndex < totalBatches - 1
                ? <button type="button" className="primary-action" onClick={() => changeBatch(batchIndex + 1)}>Continue to {practiceBatchLabel(active, batchIndex + 1)} →</button>
                : soundReturn && active.id === soundReturn.practiceLessonId ? <button type="button" className="primary-action" onClick={returnFromSoundPractice}>Return to {soundReturn.sourceWord} →</button>
                : <button type="button" className="primary-action" onClick={() => goTo('library')}>Back to library →</button>}
            </div>
          </section> : mode === 'speak' ? <SpeakPanel key={current.id} item={current} playing={audio.playing} onPlayReference={play} onStopReference={stopAudio}
            guideVisible={guideVisible} onGuideChange={setGuideVisible}
            onPracticeSound={!soundReturn && current.soundPractice ? openSoundPractice : undefined}
            blended={SPEECH_BLEND_AVAILABLE && !!current.pronunciationSegments}
            onAssess={current.referenceReview !== 'practice_only' && SPEECH_ASSESSMENT_AVAILABLE && familyConnection && active.source !== 'personal'
              ? (capture, signal) => requestSpeechFeedback(capture, familyConnection.token, signal,
                  SPEECH_BLEND_AVAILABLE && !!current.pronunciationSegments)
              : undefined}
            onNext={(completedTake) => {
            if (!claimCurrentCompletion()) return;
            if (completedTake) earn(current.id, 'speak');
            if (index < sessionItems.length - 1) jump(index + 1);
            else { stopAudio(); setFinished(true); }
          }} /> : mode === 'listen' ? <section className="flashcard listening-card" aria-live="polite">
            <span className="card-label">LISTEN WITHOUT READING</span>
            <div className="listening-symbol" aria-hidden="true">♫</div>
            <h2>{current.comprehension ? 'Listen for a detail' : 'What did you hear?'}</h2>
            <p className="listening-prompt">{current.comprehension
              ? 'Listen first. Answer the question before revealing the Polish transcript.'
              : active.kind === 'reading' ? 'Listen carefully, then reveal the transcript and assess your understanding.' : 'Play the recording. Choose the closest English meaning before revealing the Polish.'}</p>
            <AudioButton item={current} playing={audio.playing} onPlay={play}/>
            <fieldset className="speed-picker"><legend>Playback speed</legend>
              {AUDIO_RATES.map(speed => <button type="button" key={speed} aria-pressed={audio.rate === speed} onClick={() => audio.setRate(speed)} className={audio.rate === speed ? 'chosen' : ''}>{speed}×</button>)}
            </fieldset>
            {audio.error && <p className="audio-error" role="alert">{audio.error}</p>}
            {listenGuess === null && !listenRevealed && (listeningChoices.length > 0 ? <div className="listening-options" role="group" aria-label={current.comprehension ? 'Answer the listening question' : 'Choose the meaning'}>
              {current.comprehension && <p className="comprehension-prompt">{current.comprehension.prompt}</p>}
              {listeningChoices.map(choice => <button type="button" key={choice} onClick={() => { stopAudio(); setListenGuess(choice); }}>{choice}</button>)}
            </div> : <button type="button" className="reveal" onClick={() => setListenRevealed(true)}>Reveal transcript &amp; translation</button>)}
            {(listenGuess !== null || listenRevealed) && <div className="listening-answer">
              {listenGuess !== null && <p className={listenAnsweredCorrectly ? 'answer-good' : 'answer-review'}>{listenAnsweredCorrectly ? 'Correct!' : 'Not quite. Review the expression below.'}</p>}
              {listenGuess !== null && current.comprehension && <p className="comprehension-feedback">{current.comprehension.feedback}</p>}
              <span className="card-label">POLISH TRANSCRIPT</span><p lang="pl" className="listen-transcript">{current.polish}</p>
              <span className="card-label">ENGLISH TRANSLATION</span><p>{current.english}</p>
              {listenGuess !== null ? <button type="button" className="primary-action" onClick={() => record(listenAnsweredCorrectly)}>Continue →</button> : <div className="answer-actions">
                <button type="button" className="secondary-action" onClick={() => record(false)}>Needs practice</button>
                <button type="button" className="primary-action" onClick={() => record(true)}>Understood it →</button>
              </div>}
            </div>}
          </section> : <section className="flashcard" aria-live="polite">
            <span className="card-label">{mode === 'read' ? (current.title || 'POLISH PASSAGE') : active.kind === 'sounds' ? 'SOUND EXAMPLES' : 'IN POLISH'}</span>
            <div lang="pl" className={mode === 'read' ? 'polish-text reading-text' : 'polish-text'}>{current.polish}</div>
            {current.pronunciation && mode === 'learn' && <p className="phonetic">{current.pronunciation}</p>}
            <AudioButton item={current} playing={audio.playing} onPlay={play}/>
            {audio.error && <p className="audio-error" role="alert">{audio.error}</p>}
            {mode === 'read' && current.audio && <fieldset className="speed-picker"><legend>Playback speed</legend>
              {AUDIO_RATES.map(speed => <button type="button" key={speed} aria-pressed={audio.rate === speed} onClick={() => audio.setRate(speed)} className={audio.rate === speed ? 'chosen' : ''}>{speed}×</button>)}
            </fieldset>}
            {mode === 'read' && current.comprehension && !translationOpen && <fieldset className="reading-check"><legend>{current.comprehension.prompt}</legend>
              <div className="reading-check-options">{current.comprehension.options.map(option =>
                <button type="button" key={option} onClick={() => {stopAudio(); setReadGuess(option); setTranslationOpen(true);}}>{option}</button>
              )}</div>
            </fieldset>}
            {readGuess !== null && current.comprehension && <div className="reading-check-result" role="status">
              <p className={readGuess === correctAnswer ? 'answer-good' : 'answer-review'}>{readGuess === correctAnswer ? 'Correct!' : 'Not quite — review the passage.'}</p>
              <p>{current.comprehension.feedback}</p>
            </div>}
            {(revealed || translationOpen) && <div className="translation"><span className="card-label">IN ENGLISH</span><p>{current.english}</p></div>}
            {!revealed && !translationOpen && (mode !== 'read' || !current.comprehension) && <button type="button" className="reveal" onClick={() => mode === 'read' ? setTranslationOpen(true) : setRevealed(true)}>Reveal meaning <span>↗</span></button>}
            {mode === 'read' && current.comprehension && !translationOpen && <button type="button" className="reveal" onClick={() => setTranslationOpen(true)}>Reveal translation without answering</button>}
            {(revealed || translationOpen) && (mode === 'read' && readGuess !== null ? <button type="button" className="primary-action reading-continue" onClick={() => record(readGuess === correctAnswer)}>Continue →</button> : <div className="answer-actions">
              <button type="button" className="secondary-action" onClick={() => record(false)}>{mode === 'read' ? 'Review again' : 'Needs practice'}</button>
              <button type="button" className="primary-action" onClick={() => record(true)}>{mode === 'read' ? 'Finished reading →' : 'Got it →'}</button>
            </div>)}
          </section>}
          {mode !== 'speak' && !(activeMicroDialogue && mode === 'read') && <div className="lesson-footer">
            <button type="button" onClick={() => jump(index - 1)} disabled={index === 0}>← Previous</button>
            <span>{completedIn(active)} of {active.items.length} explored</span>
            <button type="button" onClick={() => jump(index + 1)} disabled={index === sessionItems.length - 1}>Skip to next →</button>
          </div>}
        </div>}

        {!loading && !loadError && editorOpen && <section className="authoring">
          <button type="button" className="back-link" onClick={() => goTo('library')}>← Cancel and return to library</button>
          <div className="page-title"><span className="eyebrow">MAKE IT YOUR OWN</span><h1>{editingId ? 'Edit lesson' : 'Create a lesson'}<span className="title-dot">.</span></h1><p>Build your own vocabulary and reading sets. Content is stored locally, not deployed through GitHub.</p></div>
          <div className="author-panel">
            <div className="author-header">
              <label>Lesson name<input type="text" value={draftTitle} maxLength={100} placeholder="e.g. At the bakery" onChange={e => setDraftTitle(e.target.value)} /></label>
              <label>Lesson type<select value={draftKind} onChange={e => setDraftKind(e.target.value as LessonKind)}><option value="vocabulary">Vocabulary</option><option value="reading">Reading</option><option value="sounds">Polish sounds</option></select></label>
            </div>
            <div className="author-item-header"><h2>Learning items</h2><span>{draftRows.length} / 150</span></div>
            {draftRows.map((row, rowIndex) => <div className="author-item" key={row.id || rowIndex}>
              <span className="author-number">{rowIndex + 1}</span>
              <label>Polish text<textarea value={row.polish} rows={2} placeholder="Polish word, expression, or passage" onChange={e => changeDraftRow(rowIndex, 'polish', e.target.value)}/></label>
              <label>English meaning<textarea value={row.english} rows={2} placeholder="Translation or explanation" onChange={e => changeDraftRow(rowIndex, 'english', e.target.value)}/></label>
              <button type="button" className="remove-row" disabled={draftRows.length <= 1} title="Remove item" aria-label={'Remove item ' + (rowIndex + 1)} onClick={() => setDraftRows(old => old.filter((_, i) => i !== rowIndex))}>×</button>
            </div>)}
            <button type="button" className="add-row" disabled={draftRows.length >= 150} onClick={() => setDraftRows(old => [...old, { polish: '', english: '' }])}>+ Add another item</button>
            {editorError && <p role="alert" className="author-error">{editorError}</p>}
            <div className="author-footer"><button type="button" className="secondary-action" onClick={() => goTo('library')}>Cancel</button><button type="button" className="primary-action" onClick={saveDraft}>{editingId ? 'Save changes' : 'Create lesson'} →</button></div>
          </div>
        </section>}

        {!loading && !loadError && !active && !editorOpen && page === 'home' && <>
          <section className="welcome">
            <div><span className="eyebrow welcome-kicker">YOUR POLISH JOURNEY STARTS HERE</span><h1>Small steps.<br/><em>Real progress.</em></h1><p>Build confidence in Polish, one useful expression at a time. Listen, learn, and make it your own.</p><button type="button" className="hero-button" onClick={() => last ? openLesson(last) : goTo('library')}>{last ? 'Continue learning' : 'Explore lessons'} <span>↗</span></button></div>
            <div className="welcome-art" aria-hidden="true"><span className="art-orbit orbit-one"/><span className="art-orbit orbit-two"/><div className="art-center">ą</div><span className="art-accent a1">ł</span><span className="art-accent a2">ż</span><span className="art-accent a3">ś</span></div>
          </section>
          <div className="xp-ribbon" role="region" aria-label="Weekly XP progress">
            <div className="xp-ribbon-heading"><div><span className="eyebrow">YOUR WEEKLY EFFORT</span><strong>{xpStats.weekly} / {xpStats.goal} XP</strong>
              <span>{xpStats.weekly>=xpStats.goal ? 'Weekly goal reached!' : (xpStats.goal-xpStats.weekly)+' XP to your goal'} · {xpStats.streak} day streak</span></div>
              <button type="button" onClick={() => goTo('profile')}>My progress →</button></div>
            <div className="xp-track" role="progressbar" aria-label="Weekly XP goal" aria-valuemin={0} aria-valuemax={xpStats.goal}
              aria-valuenow={Math.min(xpStats.weekly,xpStats.goal)}><span style={{width:Math.min(100,100*xpStats.weekly/xpStats.goal)+'%'}}/></div>
            <button type="button" className="xp-expedition-link" onClick={() => goTo('expedition')}>
              Explore Poland → {explored.length} / 16 regions unlocked · {Math.min(selectedXp,selectedTarget)} / {selectedTarget} XP to current destination
            </button>
          </div>
          {totalDue > 0 && <button type="button" className="review-home" onClick={() => goTo('practice')}>
            <span className="review-home-number">{totalDue}</span><span><strong>Ready to review</strong><small>Your scheduled Polish expressions are ready.</small></span><span aria-hidden="true">Review →</span>
          </button>}
          <div className="section-heading"><div><span className="eyebrow">TODAY'S PATH</span><h2>Pick up where you left off</h2></div><button className="text-link" type="button" onClick={() => goTo('library')}>Browse library →</button></div>
          {last ? <button type="button" className="resume-card" onClick={() => openLesson(last)}>
            <span className="resume-icon">↗</span><span><small>CONTINUE YOUR LESSON</small><strong>{last.title}</strong><span>{completedIn(last)} of {last.items.length} items explored</span></span><span className="resume-arrow">→</span>
          </button> : <div className="start-card"><div><strong>Your first lesson is ready.</strong><p>Choose a topic and begin with a few simple phrases.</p></div><button type="button" className="primary-action" onClick={() => goTo('library')}>Open library →</button></div>}
          <div className="section-heading lower"><div><span className="eyebrow">BUILD YOUR ROUTINE</span><h2>Explore a little more</h2></div></div>
          <div className="feature-grid">
            <button type="button" className="feature-card mint" onClick={() => { setFilter('vocabulary'); goTo('library'); }}><span className="feature-symbol">Aa</span><strong>Words & phrases</strong><span>Learn expressions you can use today.</span><span className="feature-next">Explore →</span></button>
            <button type="button" className="feature-card peach" onClick={() => { setFilter('reading'); goTo('library'); }}><span className="feature-symbol">✳</span><strong>Reading practice</strong><span>Understand Polish in context.</span><span className="feature-next">Explore →</span></button>
            <button type="button" className="feature-card blue" onClick={() => { setFilter('sounds'); goTo('library'); }}><span className="feature-symbol">♫</span><strong>Polish sounds</strong><span>Discover sounds unlike English.</span><span className="feature-next">Explore →</span></button>
          </div>
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'library' && <>
          <section className="page-title"><span className="eyebrow">YOUR LEARNING COLLECTION</span><h1>Lesson library<span className="title-dot">.</span></h1><p>Start with sounds and words, build useful phrases, then practise conversations and reading. Choose any lesson at any time.</p></section>
          <div className="author-actions"><button type="button" className="primary-action" onClick={beginNew}>+ Create lesson</button><label className="import-button">Import lesson JSON<input aria-label="Import lesson JSON" type="file" accept=".json,application/json" onChange={e => { const file = e.currentTarget.files?.[0]; void importFile(file); e.currentTarget.value = ''; }} /></label></div>{importError && <p className="author-error" role="alert">{importError}</p>}
          <div className="library-stage-picker" role="group" aria-label="Browse learning stage">
            {libraryViewOptions.map(option=><button type="button" key={option.id}
              aria-pressed={libraryView===option.id}
              className={libraryView===option.id?'selected':''}
              onClick={()=>chooseLibraryView(option.id)}>
              {option.label} <span className="library-stage-count" aria-hidden="true">{option.count}</span>
            </button>)}
          </div>
          <div className="library-controls"><label className="search-wrap"><span aria-hidden="true">⌕</span><input type="search" value={query} onChange={e => {setQuery(e.target.value);setLibraryView('all');}} placeholder="Search lessons or Polish phrases" aria-label="Search lessons" /></label><div className="filter-buttons" role="group" aria-label="Filter lessons">{(['all','vocabulary','reading','sounds'] as KindFilter[]).map(kind => <button type="button" key={kind} className={filter === kind ? 'chosen' : ''} onClick={() => {setFilter(kind);setLibraryView('all');}}>{kind === 'all' ? 'All lessons' : lessonLabel(kind)}</button>)}</div></div>
          <div className="library-summary">{visibleLessons.length} {visibleLessons.length === 1 ? 'lesson' : 'lessons'} <span>· {visibleLessons.reduce((total, lesson) => total + lesson.items.length, 0)} learning items</span></div>
          <div className="curriculum-sections">{librarySections.map(section=>
            <section className="curriculum-section" aria-label={section.heading} key={section.id}>
              <div className="curriculum-stage-heading"><div><h2>{section.heading}</h2><p>{section.description}</p></div>
                <span>{section.tracks.reduce((total,track)=>total+track.lessons.length,0)} sets</span></div>
              {section.tracks.map(track=><div className="curriculum-track" key={track.id}>
                <h3>{track.heading}</h3>
                <div className="lesson-grid">{track.lessons.map(lesson=>
                  <LessonTile key={lesson.id} lesson={lesson} completed={completedIn(lesson)}
                    onOpen={() => openLesson(lesson)}/>)}</div>
              </div>)}
            </section>)}</div>
          {visibleLessons.length === 0 && <div className="empty-state"><h2>No matching lessons</h2><p>Try another search or select a different category.</p><button type="button" className="secondary-action" onClick={()=>chooseLibraryView('all')}>Show all stages</button></div>}
          <p className="info-footnote">Built-in lessons come from the legacy collection. Personal lessons are saved to this browser only; export JSON for a portable backup.</p>
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'practice' && <>
          <section className="page-title"><span className="eyebrow">YOUR PRACTICE SPACE</span><h1>Keep it fresh<span className="title-dot">.</span></h1><p>Every phrase you revisit makes it easier to find the words next time.</p></section>
          <section className="due-panel">
            <div className="due-heading"><h2>Scheduled review</h2><span>{totalDue} due now</span></div>
            {dueLessons.length ? <div className="due-list">{dueLessons.filter(lesson => lesson.kind !== 'reading').map(lesson => {
              const count = dueItems(lesson, reviews, nowIso).length;
              return <button type="button" className="due-row" key={lesson.id} onClick={() => openDueReview(lesson)}>
                <strong>{lesson.title}</strong><span>{count} {count === 1 ? 'expression' : 'expressions'} due</span><span>Review →</span>
              </button>;
            })}</div> : <p>No expressions are due right now. Keep learning and they will appear here automatically.{scheduledNext ? ' Your next review is scheduled for ' + new Date(scheduledNext).toLocaleDateString() + '.' : ''}</p>}
            <p className="due-explain">Remembered → 1, 3, 7, 14 days and beyond. Needs practice → available again immediately. These are self-rated recall reviews, not pronunciation grades.</p>
          </section>
          <div className="stats-row"><Counter value={practisedCount} label="Unique items seen"/><Counter value={Object.values(progress).reduce((total, x) => total + x.seen, 0)} label="Practice attempts"/><Counter value={recallRate(progress) + '%'} label="Self-rated recall"/></div>
          <div className="section-heading lower"><div><span className="eyebrow">RETURN TO PRACTICE</span><h2>Continue your lessons</h2></div></div>
          <div className="lesson-grid">{lessons.filter(x => completedIn(x) > 0).sort((a,b)=>completedIn(b)-completedIn(a)).slice(0,8).map(x => <LessonTile key={x.id} lesson={x} completed={completedIn(x)} onOpen={() => openLesson(x)}/>)}</div>
          {practisedCount === 0 && <div className="start-card"><p>Practice progress will appear here after your first lesson.</p><button className="primary-action" type="button" onClick={() => goTo('library')}>Choose a lesson →</button></div>}
          <p className="info-footnote">These metrics reflect self-rated recall. Automated pronunciation assessment is a separate, upcoming feature.</p>
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'expedition' && <>
          <section className="page-title"><span className="eyebrow">OPEN MAP · PRIVATE FAMILY EXPEDITION</span><h1>Your Poland expedition<span className="title-dot">.</span></h1>
            <p>Choose anywhere in Poland. No forced route, voting or adjacency rules. Every region you unlock stays open.</p></section>
          <div className="expedition-quick-access">
            <span>Practising with others? Open shared weekly results without scrolling past the map.</span>
            <button type="button" className="secondary-action" onClick={()=>goTo('groups')}>Learning groups &amp; scoreboards →</button>
          </div>
          <ExpeditionMap state={expedition} onChange={setExpedition} shared={familySummary}/>
          <FamilyPanel onConnection={changeFamilyConnection} onSummary={setFamilySummary} syncMessage={familySyncStatus} syncVersion={familySyncVersion}/>
          <p className="info-footnote">Your personal/offline expedition remains in this browser. If an authorized private family service is configured and you opt in, future eligible practice also contributes to your family's separate shared map and friendly weekly rankings. The two ledgers are not merged automatically.</p>
        </>}
        {!loading && !loadError && !active && !editorOpen && page === 'groups' && <>
          <section className="page-title"><span className="eyebrow">LEARN TOGETHER</span>
            <h1>Learning groups<span className="title-dot">.</span></h1>
            <p>Choose a private group, invite learners and see your group's friendly weekly scoreboards.</p>
          </section>
          <button className="secondary-action group-map-return" type="button" onClick={()=>goTo('expedition')}>← Back to Poland map</button>
          <FamilyPanel onConnection={changeFamilyConnection} onSummary={setFamilySummary}
            syncMessage={familySyncStatus} syncVersion={familySyncVersion}/>
          <p className="info-footnote">Group scores count only eligible practice shared with that group. Your local progress and Poland map remain separate.</p>
        </>}
        {!loading && !loadError && !active && !editorOpen && page === 'profile' && <>
          <section className="page-title"><span className="eyebrow">YOUR JOURNEY</span><h1>Your profile<span className="title-dot">.</span></h1><p>Manage your private learning identity and review the progress saved on this device.</p></section>
          <ProfilePanel onOpenGroups={()=>goTo('groups')}/>
          <div className="stats-row"><Counter value={lessons.length} label="Lessons available"/><Counter value={practisedCount} label="Items encountered"/><Counter value={recallRate(progress) + '%'} label="Self-rated recall"/></div>
          <section className="xp-rewards" aria-label="Your learning XP">
            <div className="xp-rewards-heading"><div><span className="eyebrow">RECOGNITION FOR YOUR WORK</span><h2>Learning XP</h2></div>
              <button type="button" onClick={() => goTo('expedition')}>Open Poland map →</button></div>
            <div className="xp-stats"><div><strong>{xpStats.total}</strong><span>Lifetime XP</span></div><div><strong>{xpStats.weekly}</strong><span>This week</span></div>
              <div><strong>{xpStats.improved}</strong><span>Improvement bonuses</span></div><div><strong>{xpStats.streak}</strong><span>Day streak</span></div></div>
            <div className="xp-track" role="progressbar" aria-label="Weekly XP goal" aria-valuemin={0} aria-valuemax={xpStats.goal}
              aria-valuenow={Math.min(xpStats.weekly,xpStats.goal)}><span style={{width:Math.min(100,100*xpStats.weekly/xpStats.goal)+'%'}}/></div>
            <p>{xpStats.weekly>=xpStats.goal ? 'Weekly effort goal reached.' : xpStats.goal-xpStats.weekly+' XP until your weekly goal.'}</p>
            <fieldset className="xp-goal"><legend>Weekly goal</legend>
              <label><input type="radio" name="xpGoalMode" checked={expedition.goalMode==='path'}
                onChange={() => setExpedition(old=>setXpGoal(old,'path',old.selfGoal))}/> Path goal (500 XP)</label>
              <label><input type="radio" name="xpGoalMode" checked={expedition.goalMode==='self'}
                onChange={() => setExpedition(old=>setXpGoal(old,'self',old.selfGoal))}/> My own goal</label>
              {expedition.goalMode==='self' && <label>XP per week
                <input aria-label="Custom weekly XP goal" type="number" min={50} max={5000} step={10} value={selfGoalDraft}
                  onChange={e=>setSelfGoalDraft(e.target.value)}/>
                <button type="button" onClick={() => setExpedition(old=>setXpGoal(old,'self',Number(selfGoalDraft)))}>Save goal</button>
              </label>}</fieldset>
            <p className="xp-note">Real completed practice earns XP; repeat farming and skips earn none. Comparable objectively verified improvement earns an additional bonus. Speech-quality bonuses use the same reward interface once phonetic assessment is validated — no transcription-only grades.</p>
          </section>
          <section className="preferences"><h2>Your local learning data</h2><p>Lessons, progress, and review schedules are stored only in this browser. Export a full backup before clearing browser data or changing devices.</p>
            <div className="backup-actions"><button type="button" className="primary-action" onClick={downloadBackup}>Export full backup</button>
              <label className="import-button">Restore from backup<input type="file" aria-label="Restore from backup" accept=".json,application/json" onChange={e => {
                const file = e.currentTarget.files?.[0]; void restoreBackup(file); e.currentTarget.value='';
              }}/></label>
            </div>
            {backupStatus && <p className="backup-success" role="status">{backupStatus}</p>}
            {backupError && <p className="author-error" role="alert">{backupError}</p>}
            <p className="backup-hint">A restore replaces the local lessons, all practice history, scheduled reviews and reading positions. Built-in lessons and downloadable audio are part of the app, not this backup. No recordings are included.</p>
            <button type="button" className="danger-action" onClick={() => { if (window.confirm('Erase local practice history, review dates AND earned XP? Personal lessons will be kept. This cannot be undone.')) {
              setProgress({}); setReviews({}); setExpedition(emptyExpedition()); setBackupStatus('Practice, review schedules and earned XP cleared. Personal lessons are unchanged.');
            } }}>Clear practice and reviews</button></section>
        </>}
      </main>
    </div>

    <nav className="mobile-nav" aria-label="Mobile navigation">{nav.map(item => <button type="button" key={item.id} className={!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'selected' : ''} aria-current={!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'page' : undefined} onClick={() => goTo(item.id)}><span aria-hidden="true">{item.symbol}</span><small>{item.label}</small></button>)}</nav>
  </div>;
}
