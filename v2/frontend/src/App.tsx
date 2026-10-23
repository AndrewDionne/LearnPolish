import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Lesson, LessonItem, LessonKind } from './model';
import { lessonLabel, parseManifest } from './model';
import { AUDIO_RATES, useLessonAudio } from './audio';
import OfflineDownloadControl from './OfflineDownloadControl';
import SpeakPanel from './speech/SpeakPanel';
import UIIcon from './UIIcon';
import BrandMark from './BrandMark';
import type {UIIconName} from './UIIcon';
import {requestSpeechFeedback, SPEECH_ASSESSMENT_AVAILABLE, SPEECH_BLEND_AVAILABLE} from './speech/assessment';
import SoundContrastDeck from './SoundContrastDeck';
import MicroDialoguePanel from './MicroDialoguePanel';
import {libraryMatches} from './library-curriculum';
import {groupJourneyLibrary,journeyPlacement,nextCoreLesson} from './core-journey';
import {CORE_CONTINUE_KEY,parseCoreContinueId,resolveCourseContinuation} from './core-continuation';
import JourneyMarker from './JourneyMarker';
import TouristUnitCards from './TouristUnitCards';
import Journey1Guide from './Journey1Guide';
import {availableJourney1Guide} from './journey1-guide';
import {availableStarterGroups,starterSessionItems} from './foundation-first-expressions';
import {availableTouristUnits,unitStepSource,unitStepItems} from './tourist-units';
import {TOURIST_ACTIVITY_KEY,emptyTouristActivities,parseTouristActivities,
  positionTouristUnit,triedTouristItem} from './tourist-activity';
import { parseProgress, recallRate, recordAttempt, STORAGE_KEY } from './progress';
import type { Progress } from './progress';
import { PERSONAL_STORAGE_KEY, importPersonalLesson, makePersonalLesson, parsePersonalLessons, toPortableLesson, upsertPersonalLesson } from './personal';
import type { DraftItem } from './personal';
import { availableModes, comprehensionChoices, correctComprehensionAnswer, itemPractised, itemsForMode, progressKey } from './modes';
import type { LearningMode } from './modes';
import { READING_POSITION_KEY, parseReadingPositions, safeReadingPosition } from './reading-position';
import { firstUnvisitedBatch, practiceBatchCount, practiceBatchItems, practiceBatchLabel, usesPracticeBatches } from './practice-batches';
import {nextLessonResume} from './lesson-resume';
import { REVIEW_STORAGE_KEY, countDue, dueItems, nextDue, parseReviewSchedule, recordReview } from './review';
import {partitionDueReviews,dueLaneCount,startCoreReviewRun,nextCoreReviewRunStep} from './core-review';
import type {CoreReviewRun} from './core-review';
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

const nav: { id: Page; label: string; icon: UIIconName }[] = [
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'library', label: 'Library', icon: 'library' },
  { id: 'practice', label: 'Practice', icon: 'practice' },
  { id: 'expedition', label: 'Expedition', icon: 'expedition' },
  { id: 'profile', label: 'Profile', icon: 'profile' },
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
  const symbol = lesson.kind === 'reading' ? <UIIcon name="reading" size={31}/> : lesson.kind === 'sounds' ? <UIIcon name="sounds" size={31}/> : 'Aa';
  const placement=journeyPlacement(lesson);
  return <button type="button" className="lesson-tile" onClick={onOpen}>
    <span className={'lesson-art ' + lesson.kind}>{symbol}
      {placement && <JourneyMarker placement={placement}/>}
    </span>
    <span className="lesson-tile-body">
      <span className="eyebrow">{lessonLabel(lesson.kind)}</span>
      <strong>{lesson.title}</strong>
      {lesson.description && <span className="tile-description">{lesson.description}</span>}
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
  const [lessonLoadAttempt,setLessonLoadAttempt]=useState(0);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<KindFilter>('all');
  const [lessonId, setLessonId] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [batchIndex,setBatchIndex] = useState(0);
  const [microDialogueId,setMicroDialogueId] = useState<string|null>(null);
  const [sessionStartXp, setSessionStartXp] = useState(0);
  const [mode, setMode] = useState<LearningMode>('learn');
  const [unitSession,setUnitSession]=useState<{unitId:string;stepIndex:number}|null>(null);
  const [starterGroupId,setStarterGroupId]=useState<string|null>(null);
  const [touristActivity,setTouristActivity]=useState(()=>{
    try{return parseTouristActivities(localStorage.getItem(TOURIST_ACTIVITY_KEY));}
    catch{return emptyTouristActivities();}
  });
  // One deliberate choice for the current Speak session, OFF at lesson start.
  // Keeps the guide open if the learner advances, without a persistent gate.
  const [guideVisible,setGuideVisible] = useState(false);
  const [soundReturn,setSoundReturn] = useState<SoundPracticeReturn|null>(null);
  const [reviewOnly, setReviewOnly] = useState<string[] | null>(null);
  const [coreReviewRun,setCoreReviewRun]=useState<CoreReviewRun|null>(null);
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
  const [coreLessonId,setCoreLessonId]=useState<string|null>(()=>{
    try{return parseCoreContinueId(localStorage.getItem(CORE_CONTINUE_KEY));}
    catch{return null;}
  });
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
    setLoading(true);
    setLoadError('');
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
  }, [lessonLoadAttempt]);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(progress)); } catch { /* local progress is best effort */ }
  }, [progress]);
  useEffect(()=>{
    try{localStorage.setItem(TOURIST_ACTIVITY_KEY,JSON.stringify(touristActivity));}
    catch{/* local-only activity, never account mastery */}
  },[touristActivity]);
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
  const touristUnits=useMemo(()=>availableTouristUnits(builtIn),[builtIn]);
  const foundationGuide=useMemo(()=>availableJourney1Guide(builtIn,touristUnits),[builtIn,touristUnits]);
  const starterGroups=useMemo(()=>availableStarterGroups(builtIn),[builtIn]);
  const starterGroup=starterGroups.find(group=>group.id===starterGroupId);
  const currentUnit=unitSession?touristUnits.find(x=>x.id===unitSession.unitId):undefined;
  const unitStep=currentUnit?.steps[unitSession?.stepIndex??-1];
  const nextUnitStep=currentUnit?.steps[(unitSession?.stepIndex??-1)+1];
  const upcomingLesson=active && !reviewOnly && !soundReturn && !unitSession
    ? nextCoreLesson(lessons,active.id) : null;
  const activeMicroDialogue=active?.microDialogues?.find(dialogue=>dialogue.id===microDialogueId);
  const focusedGroup = soundReturn && soundReturn.practiceLessonId === active?.id ? soundReturn.practiceGroupId : null;
  const batched = !!active && usesPracticeBatches(active) && !reviewOnly && !starterGroup && !focusedGroup && !unitStep;
  const totalBatches = batched && active ? practiceBatchCount(active) : 1;
  const sessionItems = active
    ? focusedGroup ? itemsForMode(active, mode).filter(item => item.soundGroupId === focusedGroup)
      : unitStep && unitStep.lessonId===active.id && unitStep.mode===mode
        ? unitStepItems(active,unitStep)
      : starterGroup && starterGroup.lessonId===active.id && !unitStep && !reviewOnly
        ? starterSessionItems(active,starterGroup,mode==='read'?'learn':mode)
      : reviewOnly && mode === 'learn' ? active.items.filter(item => reviewOnly.includes(item.id))
      : batched ? practiceBatchItems(active, mode, batchIndex)
      : itemsForMode(active, mode)
    : [];
  const current = sessionItems[index];
  // A rapid repeat activation of the same visible answer must not create a
  // second recall/review attempt. This lock is specific to a lesson step, NOT
  // a permanent per-item lock: intentional repeat sessions remain available.
  const completionGuard=useRef<{step:string|null}>({step:null});
  const completionStep=[lessonId,mode,batchIndex,index,current?.id,unitSession?.unitId,unitSession?.stepIndex,starterGroupId].join('|');
  useEffect(()=>{completionGuard.current.step=null;},
    [lessonId,mode,batchIndex,index,current?.id,finished]);
  const claimCurrentCompletion=()=>!!current&&!finished&&
    claimCompletion(completionGuard.current,completionStep);
  const listeningChoices = active && current && mode === 'listen' ? comprehensionChoices(active.items, current, index, active.kind === 'reading') : [];
  const correctAnswer = current ? correctComprehensionAnswer(current) : null;
  const chosenAnswer = correctAnswer || current?.english || '';
  const listenAnsweredCorrectly = listenGuess !== null && listenGuess === chosenAnswer;
  const last = lessons.find(x => x.id === lastLesson);
  const lastResume = last ? nextLessonResume(last,progress,readingPositions) : null;
  const courseContinue=resolveCourseContinuation(builtIn,progress,coreLessonId,lastLesson);
  const coreLesson=courseContinue.lesson;
  const coreResume=coreLesson?nextLessonResume(coreLesson,progress,readingPositions):null;
  const showRecent=!!last && last.id!==coreLesson?.id;
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
  const dueLanes=partitionDueReviews(lessons,reviews,nowIso);
  const coreReviewDue=dueLaneCount(dueLanes.core);
  const otherReviewDue=dueLaneCount(dueLanes.personal)+dueLaneCount(dueLanes.explore);
  const nextCoreReview=coreReviewRun?nextCoreReviewRunStep(coreReviewRun):null;

  const filtered = useMemo(() => lessons.filter(x =>
    (filter === 'all' || x.kind === filter) && libraryMatches(x,query)
  ), [lessons, filter, query]);
  // Core is ordered independently of legacy Library tracks and personal lessons.
  // The marker taxonomy stays invisible in headings, labels and spoken help.
  const librarySections=useMemo(()=>groupJourneyLibrary(filtered),[filtered]);

  const stopAudio = () => { audio.stop(); };
  const goTo = (destination: Page) => {
    stopAudio(); setUnitSession(null); setStarterGroupId(null); setCoreReviewRun(null); setLessonId(null); setGuideVisible(false); setSoundReturn(null); setEditorOpen(false); setReviewOnly(null); setBatchIndex(0); setMicroDialogueId(null); setPage(destination); setRevealed(false); setFinished(false);
  };
  const openLesson = (lesson: Lesson, resume=false, updateCourseCursor=true) => {
    stopAudio();setUnitSession(null);setStarterGroupId(null);setCoreReviewRun(null);
    const resumeAt=resume ? nextLessonResume(lesson,progress,readingPositions) : null;
    setSoundReturn(null);
    setReviewOnly(null);
    setMicroDialogueId(null);
    setSessionStartXp(expedition.events.length);
    setLessonId(lesson.id); setGuideVisible(false); setMode(lesson.kind === 'reading' ? 'read' : 'learn');
    setBatchIndex(resumeAt?.batchIndex ?? firstUnvisitedBatch(lesson, progress));
    setIndex(resumeAt?.index ?? (lesson.kind === 'reading' ? safeReadingPosition(readingPositions, lesson.id, lesson.items.length) : 0));
    setRevealed(false); setTranslationOpen(false); setListenGuess(null); setReadGuess(null); setListenRevealed(false); setFinished(false);
    setLastLesson(lesson.id); saveLastLesson(lesson.id);
    // The user's personal/optional recent lesson never redirects the core path.
    if(updateCourseCursor && journeyPlacement(lesson)){
      setCoreLessonId(lesson.id);
      try{localStorage.setItem(CORE_CONTINUE_KEY,lesson.id);}catch{/* best effort */}
    }
  };
  const openStarterGroup=(id:string)=>{
    const group=starterGroups.find(g=>g.id===id);
    const source=group&&builtIn.find(lesson=>lesson.id===group.lessonId);
    if(!group||!source||starterSessionItems(source,group,'learn').length!==group.itemIds.length)return;
    // No new content, XP rules or records: only original source items in short batches.
    openLesson(source,false,false);
    setStarterGroupId(group.id);
    setMode('learn');
    setIndex(0);
    setBatchIndex(0);
  };
  const openTouristUnitStep=(unitId:string,stepIndex:number,resumeItemId?:string)=>{
    const unit=touristUnits.find(x=>x.id===unitId);
    const step=unit?.steps[stepIndex];
    const destination=step&&unitStepSource(builtIn,step);
    if(!unit||!step||!destination)return;
    // A source excerpt may originate in a later journey (e.g. T05 grocery
    // reading). Do not overwrite an explicitly chosen core course position.
    openLesson(destination,false,false);
    setUnitSession({unitId,stepIndex});
    setMode(step.mode);
    const itemIndex=resumeItemId?step.itemIds.indexOf(resumeItemId):-1;
    const startIndex=itemIndex>=0?itemIndex:0;
    setIndex(startIndex);
    setTouristActivity(previous=>positionTouristUnit(previous,unit,stepIndex,step.itemIds[startIndex]));
    setBatchIndex(0);
    setRevealed(false);setTranslationOpen(false);
    setReadGuess(null);setListenGuess(null);setListenRevealed(false);
  };
  const openSoundPractice = () => {
    if (!active || !current?.soundPractice || mode !== 'speak' || soundReturn) return;
    const focus = current.soundPractice;
    const destination = lessons.find(lesson => lesson.id === focus.lessonId && lesson.kind === 'sounds');
    const group = destination?.soundGroups?.find(g => g.id === focus.groupId);
    if (!destination || !group?.itemIds.length) return;
    stopAudio();setUnitSession(null);setStarterGroupId(null);
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
  const openDueReview = (lesson: Lesson, snapshotIds?: string[], run:CoreReviewRun|null=null) => {
    const due = snapshotIds ?? dueItems(lesson, reviews, new Date().toISOString()).map(item => item.id);
    if (!due.length || lesson.kind === 'reading' ||
      due.some(id=>!lesson.items.some(item=>item.id===id))) return;
    // Reviewing an earlier source must not silently move the user's Home course cursor.
    openLesson(lesson,false,false);
    setReviewOnly([...due]); setCoreReviewRun(run);
    setMode('learn'); setIndex(0); setBatchIndex(0);
  };
  const startCoreReview=()=>{
    const run=startCoreReviewRun(dueLanes.core);
    const first=run?.steps[0];
    const lesson=first&&lessons.find(item=>item.id===first.lessonId);
    if(!run||!first||!lesson)return;
    openDueReview(lesson,first.itemIds,run);
  };
  const continueCoreReview=()=>{
    if(!nextCoreReview)return;
    const step=nextCoreReview.steps[nextCoreReview.position];
    const lesson=lessons.find(item=>item.id===step.lessonId);
    if(!lesson){goTo('practice');return;}
    openDueReview(lesson,step.itemIds,nextCoreReview);
  };
  const jump = (target: number,trackUnitPosition=true) => {
    if (!active) return;
    stopAudio();
    const next = Math.max(0, Math.min(sessionItems.length - 1, target));
    setIndex(next);
    if(trackUnitPosition && unitSession && currentUnit && unitStep && sessionItems[next])
      setTouristActivity(previous=>positionTouristUnit(previous,currentUnit,unitSession.stepIndex,sessionItems[next].id));
    if (mode === 'read' && !unitSession) setReadingPositions(previous => ({ ...previous, [active.id]: next }));
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
    stopAudio();setUnitSession(null);setCoreReviewRun(null);
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
    if(unitSession && currentUnit && unitStep)
      setTouristActivity(previous=>triedTouristItem(previous,currentUnit,unitSession.stepIndex,current.id));
    if (mode === 'learn') setReviews(previous => recordReview(previous, current.id, remembered, at));
    if (index < sessionItems.length - 1) jump(index + 1,false);
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
        personalLessons: personal, progress, reviews, readingPositions, lastLessonId: lastLesson,
        lastCoreLessonId:courseContinue.origin==='start' || !coreLesson ? null : coreLesson.id,
        touristActivity,expedition,
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
        'This will replace ALL personal lessons, unit activity, practice history, scheduled reviews and reading positions saved in this browser. The current local data will be lost. Export a backup first if you need it.'
      );
      if (!confirmed) {setBackupStatus('Restore cancelled. Your existing data was not changed.');return;}
      // Commit all validated records to storage FIRST. On quota/permission errors,
      // roll back earlier keys and do not mutate the live learning session.
      const restoredExpedition=persistRestoredBackup(data,localStorage);
      stopAudio();
      setPersonal(data.personalLessons);
      setProgress(data.progress);
      setReviews(data.reviews);
      setTouristActivity(data.touristActivity??emptyTouristActivities());
      setExpedition(restoredExpedition);
      setReadingPositions(data.readingPositions);
      setLastLesson(data.lastLessonId);
      // Missing in old exports: infer from restored practice only, never stale device data.
      setCoreLessonId(data.lastCoreLessonId??null);
      setLessonId(null); setUnitSession(null); setCoreReviewRun(null); setEditorOpen(false); setReviewOnly(null); setPage('profile');
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
        <span className="brand-symbol"><BrandMark size={53}/></span>
        <span className="brand-name">path to <strong>polish</strong></span>
      </button>
      <nav className="side-links" aria-label="Main navigation">
        {nav.map(item => <button key={item.id} className={'nav-link ' + (!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'selected' : '')} type="button" aria-current={!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'page' : undefined} onClick={() => goTo(item.id)}><span className="nav-icon"><UIIcon name={item.icon}/></span>{item.label}</button>)}
      </nav>

    </aside>

    <div className="main-shell">
      <header className="topbar">
        <div className="crumb"><span className="mobile-brand"><BrandMark size={30}/></span><span>PATH TO POLISH</span><span className="crumb-slash">/</span><strong>{active ? active.title : page === 'groups' ? 'Learning groups' : nav.find(x => x.id === page)?.label}</strong></div>
        
      </header>
      <main className="page-content" id="main-content" ref={mainRef} tabIndex={-1}>
        {loading && <section className="empty-state" role="status"><h2>Gathering your lessons…</h2><p>Preparing your Polish library.</p></section>}
        {!loading && loadError && <section className="empty-state" role="alert"><h2>Lessons could not load</h2><p>{loadError}</p><p>Check your connection and try again. Your progress and personal lessons remain stored in this browser.</p><button className="primary-action" type="button" onClick={()=>setLessonLoadAttempt(x=>x+1)}>Retry loading lessons</button></section>}

        {!loading && !loadError && active && current && <div className={'learning' + (mode === 'speak' ? ' speak-focused' : '')}>
          <div className="lesson-tools"><button type="button" className="back-link" onClick={soundReturn && active.id === soundReturn.practiceLessonId ? returnFromSoundPractice : () => goTo('library')}>{soundReturn && active.id === soundReturn.practiceLessonId ? '← Back to ' + soundReturn.sourceWord : '← Back to library'}</button>{mode !== 'speak' && <div><button type="button" onClick={() => exportFile(active)}>Export JSON</button><OfflineDownloadControl lesson={active}/>{active.source === 'personal' && <><button type="button" onClick={() => beginEdit(active)}>Edit lesson</button><button type="button" className="delete-link" onClick={() => deletePersonalLesson(active)}>Delete</button></>}</div>}</div>
          {mode === 'speak'
            ? <div className="learning-head speak-compact-head"><span className="item-count">{index + 1} <span>/ {sessionItems.length}</span></span></div>
            : <div className="learning-head">
            <div><span className="eyebrow">{reviewOnly ? 'Due review' : mode === 'listen' ? 'Listen' : mode === 'read' ? 'Read' : mode === 'learn' && active.kind === 'sounds' ? 'Sounds' : 'Learn'}</span><h1>{active.title}</h1></div>
            <span className="item-count">{activeMicroDialogue && mode === 'read' ? 'Dialogue' : index + 1} {!activeMicroDialogue && <span>/ {sessionItems.length}</span>}</span>
          </div>}
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
          {starterGroup && active.id===starterGroup.lessonId && <div className="unit-practice-head">
            <strong>{starterGroup.title}</strong><span>Original recorded expressions · {index+1}/{sessionItems.length}</span>
          </div>}
          {currentUnit && unitStep && <div className="unit-practice-head">
            <strong>{currentUnit.title}</strong>
            <span>{unitStep.mode==='listen'?'Listen':unitStep.mode==='speak'?'Speak':'Read'} · {unitSession!.stepIndex+1}/{currentUnit.steps.length}</span>
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
            <p>You made it through {sessionItems.length} {sessionItems.length === 1 ? 'item' : 'items'}.</p>
            <p className="reward-note" aria-live="polite">{sessionXp ? '+' + sessionXp + ' XP earned' : 'No XP earned this session'}</p>
            {!reviewOnly && availableModes(active).some(candidate => candidate !== mode) && <div className="mode-handoff" role="group" aria-label="Continue learning in another mode">
              <div>
              {availableModes(active).filter(candidate => candidate !== mode).map(candidate => <button type="button" key={candidate} className="handoff-button" onClick={() => switchMode(candidate)}>
                {candidate === 'learn' ? 'Learn' : candidate === 'read' ? 'Read' : candidate === 'speak' ? 'Speak' : 'Listen'} →
              </button>)}</div>
            </div>}
            <div className="answer-actions"><button type="button" className="secondary-action" onClick={() => jump(0)}>Practise again</button>
              {nextUnitStep && currentUnit && <button type="button" className="primary-action"
                onClick={()=>openTouristUnitStep(currentUnit.id,(unitSession?.stepIndex??0)+1)}>
                Continue with {nextUnitStep.mode==='listen'?'Listen':nextUnitStep.mode==='speak'?'Speak':'Read'} →
              </button>}
              {batched && batchIndex < totalBatches - 1
                ? <button type="button" className="primary-action" onClick={() => changeBatch(batchIndex + 1)}>Continue to {practiceBatchLabel(active, batchIndex + 1)} →</button>
                : soundReturn && active.id === soundReturn.practiceLessonId ? <button type="button" className="primary-action" onClick={returnFromSoundPractice}>Return to {soundReturn.sourceWord} →</button>
                : coreReviewRun ? <button type="button" className="primary-action" onClick={()=>nextCoreReview?continueCoreReview():goTo('practice')}>{nextCoreReview?'Continue scheduled review →':'Back to practice →'}</button>
                : reviewOnly ? <button type="button" className="primary-action" onClick={()=>goTo('practice')}>Back to practice →</button>
                : <>
                  {upcomingLesson && <button type="button" className="primary-action"
                    aria-label={'Continue to '+upcomingLesson.title}
                    onClick={() => openLesson(upcomingLesson)}>Next: {upcomingLesson.title} →</button>}
                  <button type="button" className={upcomingLesson ? 'secondary-action' : 'primary-action'}
                    onClick={() => goTo('library')}>Back to library →</button>
                </>}
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
            if (completedTake){
              earn(current.id, 'speak');
              if(unitSession && currentUnit && unitStep)
                setTouristActivity(previous=>triedTouristItem(previous,currentUnit,unitSession.stepIndex,current.id));
            }
            // An unrecorded Speak Next is navigation only: preserve the
            // resume cursor without crediting a pronunciation attempt.
            if (index < sessionItems.length - 1) jump(index + 1,!completedTake);
            else { stopAudio(); setFinished(true); }
          }} /> : mode === 'listen' ? <section className="flashcard listening-card" aria-live="polite">
            
            <div className="listening-symbol" aria-hidden="true"><UIIcon name="sounds" size={42}/></div>
            <h2>{current.comprehension ? 'Listen for a detail' : 'What did you hear?'}</h2>
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
              {listenGuess !== null && <p role="status" className={listenAnsweredCorrectly ? 'answer-good' : 'answer-review'}>{listenAnsweredCorrectly ? 'Correct!' : 'Not quite'}</p>}
              <p lang="pl" className="listen-transcript">{current.polish}</p>
              <p className="listen-english">{current.english}</p>
              {listenGuess !== null ? <button type="button" className="primary-action" onClick={() => record(listenAnsweredCorrectly)}>Continue →</button> : <div className="answer-actions">
                <button type="button" className="secondary-action" onClick={() => record(false)}>Needs practice</button>
                <button type="button" className="primary-action" onClick={() => record(true)}>Got it →</button>
              </div>}
            </div>}
          </section> : <section className="flashcard" aria-live="polite">
            {mode === 'read' && current.title && <span className="card-label">{current.title}</span>}
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
              <p className={readGuess === correctAnswer ? 'answer-good' : 'answer-review'}>{readGuess === correctAnswer ? 'Correct!' : 'Not quite'}</p>
            </div>}
            {(revealed || translationOpen) && <div className="translation"><p>{current.english}</p></div>}
            {!revealed && !translationOpen && (mode !== 'read' || !current.comprehension) && <button type="button" className="reveal" onClick={() => mode === 'read' ? setTranslationOpen(true) : setRevealed(true)}>Reveal meaning <span>↗</span></button>}
            {mode === 'read' && current.comprehension && !translationOpen && <button type="button" className="reveal" onClick={() => setTranslationOpen(true)}>Reveal translation without answering</button>}
            {(revealed || translationOpen) && (mode === 'read' && readGuess !== null ? <button type="button" className="primary-action reading-continue" onClick={() => record(readGuess === correctAnswer)}>Continue →</button> : <div className="answer-actions">
              <button type="button" className="secondary-action" onClick={() => record(false)}>Needs practice</button>
              <button type="button" className="primary-action" onClick={() => record(true)}>Got it →</button>
            </div>)}
          </section>}
          {mode !== 'speak' && !(activeMicroDialogue && mode === 'read') && <div className="lesson-footer">
            <button type="button" onClick={() => jump(index - 1)} disabled={index === 0}>← Previous</button>
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
            <div className="welcome-copy"><h1>Small steps.<br/><em>Real progress.</em></h1><button type="button" className="hero-button" onClick={() => courseContinue.origin==='start' || !coreLesson ? goTo('library') : openLesson(coreLesson,true)}>{courseContinue.origin==='start' || !coreLesson ? 'Explore lessons' : 'Continue course'} <span aria-hidden="true">→</span></button></div>
            <div className="welcome-art" aria-hidden="true"><div className="type-card type-card-back">ł</div><div className="type-card type-card-front"><span className="type-card-caption">POLSKI</span><span className="type-card-glyph">ą</span><span className="type-card-rule"/></div><div className="type-card type-card-small">ś</div></div>
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
          {totalDue > 0 && <button type="button" className="review-home"
            onClick={() => coreReviewDue ? startCoreReview() : goTo('practice')}>
            <span className="review-home-number">{totalDue}</span>
            <span><strong>{coreReviewDue?'Review your path':'Ready to review'}</strong>
              <small>{coreReviewDue} due on your path{otherReviewDue? ' · '+otherReviewDue+' in other lessons':''}</small></span>
            <span aria-hidden="true">{coreReviewDue?'Start →':'Practice →'}</span>
          </button>}
          <div className="section-heading"><div><span className="eyebrow">TODAY'S PATH</span><h2>Pick up where you left off</h2></div><button className="text-link" type="button" onClick={() => goTo('library')}>Browse library →</button></div>
          {coreLesson && <button type="button" className="resume-card core-resume-card" onClick={() => openLesson(coreLesson,true)}>
            <span className="resume-icon">↗</span><span><small>{courseContinue.origin==='start'?'START YOUR COURSE':'CONTINUE YOUR COURSE'}</small><strong>{coreLesson.title}</strong><span>{completedIn(coreLesson)} of {coreLesson.items.length} explored · {coreResume?.hasNewItem ? 'Next: item '+(coreResume.overallIndex+1) : 'Ready to revisit'}</span></span><span className="resume-arrow">→</span>
          </button>}
          {showRecent && last && <button type="button" className="resume-card recent-resume-card" onClick={() => openLesson(last,true)}>
            <span className="resume-icon">↗</span><span><small>RECENT PRACTICE</small><strong>{last.title}</strong><span>{completedIn(last)} of {last.items.length} explored · {lastResume?.hasNewItem ? 'Next: item '+(lastResume.overallIndex+1) : 'Ready to revisit'}</span></span><span className="resume-arrow">→</span>
          </button>}
          {!coreLesson && <div className="start-card"><div><strong>Your lessons are ready.</strong><p>Choose a lesson from your library.</p></div><button type="button" className="primary-action" onClick={() => goTo('library')}>Open library →</button></div>}
          <div className="section-heading lower"><div><span className="eyebrow">BUILD YOUR ROUTINE</span><h2>Explore a little more</h2></div></div>
          <div className="feature-grid">
            <button type="button" className="feature-card mint" onClick={() => { setFilter('vocabulary'); goTo('library'); }}><span className="feature-symbol">Aa</span><strong>Words & phrases</strong><span>Learn expressions you can use today.</span><span className="feature-next">Explore →</span></button>
            <button type="button" className="feature-card peach" onClick={() => { setFilter('reading'); goTo('library'); }}><span className="feature-symbol"><UIIcon name="reading" size={25}/></span><strong>Reading practice</strong><span>Understand Polish in context.</span><span className="feature-next">Explore →</span></button>
            <button type="button" className="feature-card blue" onClick={() => { setFilter('sounds'); goTo('library'); }}><span className="feature-symbol"><UIIcon name="sounds" size={25}/></span><strong>Polish sounds</strong><span>Discover sounds unlike English.</span><span className="feature-next">Explore →</span></button>
          </div>
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'library' && <>
          <section className="page-title"><h1>Lesson library<span className="title-dot">.</span></h1></section>
          <div className="author-actions library-author-actions"><button type="button" className="secondary-action" onClick={beginNew}>+ Create lesson</button><label className="import-button">Import JSON<input aria-label="Import lesson JSON" type="file" accept=".json,application/json" onChange={e => { const file = e.currentTarget.files?.[0]; void importFile(file); e.currentTarget.value = ''; }} /></label></div>{importError && <p className="author-error" role="alert">{importError}</p>}
          <div className="library-controls"><label className="search-wrap"><span aria-hidden="true">⌕</span><input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search lessons or Polish phrases" aria-label="Search lessons" /></label><div className="filter-buttons" role="group" aria-label="Filter lessons">{(['all','vocabulary','reading','sounds'] as KindFilter[]).map(kind => <button type="button" key={kind} className={filter === kind ? 'chosen' : ''} onClick={() => setFilter(kind)}>{kind === 'all' ? 'All lessons' : lessonLabel(kind)}</button>)}</div></div>
          <div className="curriculum-sections">{librarySections.map(section=>
            <section className="curriculum-section" aria-label={section.heading} key={section.id}>
              <div className="curriculum-stage-heading"><h2>{section.heading}</h2></div>
              {section.id==='core' && filter==='all' && !query.trim() && <>
                <Journey1Guide steps={foundationGuide} starterGroups={starterGroups}
                  onStarter={openStarterGroup}
                  onLesson={id=>{const found=builtIn.find(x=>x.id===id);if(found)openLesson(found);}}
                  onUnit={id=>openTouristUnitStep(id,0)}/>
                <TouristUnitCards units={touristUnits} activity={touristActivity} onStart={openTouristUnitStep}/>
              </>}
              <div className="lesson-grid">{section.lessons.map(lesson=>
                <LessonTile key={lesson.id} lesson={lesson} completed={completedIn(lesson)}
                  onOpen={() => openLesson(lesson)}/>)}</div>
            </section>)}</div>
          {filtered.length === 0 && <div className="empty-state"><h2>No matching lessons</h2><p>Try another search or select a different category.</p><button type="button" className="secondary-action" onClick={()=>{setQuery('');setFilter('all');}}>Show all lessons</button></div>}
          
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'practice' && <>
          <section className="page-title"><h1>Practice<span className="title-dot">.</span></h1></section>
          <section className="due-panel" aria-label="Core course scheduled review">
            <div className="due-heading"><h2>On your path</h2><span>{coreReviewDue} due now</span></div>
            {coreReviewDue ? <>
              <button type="button" className="primary-action" onClick={startCoreReview}>
                Review {coreReviewDue} {coreReviewDue===1?'expression':'expressions'} →
              </button>
              <div className="due-list">{dueLanes.core.map(({lesson,itemIds})=>
                <button type="button" className="due-row" key={lesson.id} onClick={()=>openDueReview(lesson)}>
                  <strong>{lesson.title}</strong><span>{itemIds.length} {itemIds.length===1?'expression':'expressions'} due</span><span>Review →</span>
                </button>)}</div>
            </> : <p>{totalDue===0?'No expressions are due right now.':'No course expressions are due right now.'}</p>}
          </section>
          {dueLanes.personal.length>0 && <section className="due-panel" aria-label="Personal lesson scheduled review">
            <div className="due-heading"><h2>Your lessons</h2><span>{dueLaneCount(dueLanes.personal)} due now</span></div>
            <div className="due-list">{dueLanes.personal.map(({lesson,itemIds})=>
              <button type="button" className="due-row" key={lesson.id} onClick={()=>openDueReview(lesson)}>
                <strong>{lesson.title}</strong><span>{itemIds.length} {itemIds.length===1?'expression':'expressions'} due</span><span>Review →</span>
              </button>)}</div>
          </section>}
          {dueLanes.explore.length>0 && <section className="due-panel" aria-label="Other lesson scheduled review">
            <div className="due-heading"><h2>Explore more</h2><span>{dueLaneCount(dueLanes.explore)} due now</span></div>
            <div className="due-list">{dueLanes.explore.map(({lesson,itemIds})=>
              <button type="button" className="due-row" key={lesson.id} onClick={()=>openDueReview(lesson)}>
                <strong>{lesson.title}</strong><span>{itemIds.length} {itemIds.length===1?'expression':'expressions'} due</span><span>Review →</span>
              </button>)}</div>
          </section>}
          {totalDue===0 && scheduledNext && <p>Next scheduled review: {new Date(scheduledNext).toLocaleDateString()}.</p>}
                    {practisedCount > 0 && <><div className="section-heading lower"><div><h2>Continue learning</h2></div><button className="text-link" type="button" onClick={() => goTo('library')}>All lessons →</button></div>
          <div className="lesson-grid">{lessons.filter(x => completedIn(x) > 0).sort((a,b)=>completedIn(b)-completedIn(a)).slice(0,4).map(x => <LessonTile key={x.id} lesson={x} completed={completedIn(x)} onOpen={() => openLesson(x)}/>)}</div></>}
          {practisedCount === 0 && <div className="start-card"><p>Practice progress will appear here after your first lesson.</p><button className="primary-action" type="button" onClick={() => goTo('library')}>Choose a lesson →</button></div>}
          
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'expedition' && <>
          <section className="page-title"><h1>Your Poland expedition<span className="title-dot">.</span></h1></section>
          <div className="expedition-quick-access">
            
            <button type="button" className="secondary-action" onClick={()=>goTo('groups')}>Learning groups &amp; scoreboards →</button>
          </div>
          <ExpeditionMap state={expedition} onChange={setExpedition} shared={familySummary}/>
          <FamilyPanel onConnection={changeFamilyConnection} onSummary={setFamilySummary} syncMessage={familySyncStatus} syncVersion={familySyncVersion}/>
        </>}
        {!loading && !loadError && !active && !editorOpen && page === 'groups' && <>
          <section className="page-title"><h1>Learning groups<span className="title-dot">.</span></h1></section>
          <button className="secondary-action group-map-return" type="button" onClick={()=>goTo('expedition')}>← Back to Poland map</button>
          <FamilyPanel onConnection={changeFamilyConnection} onSummary={setFamilySummary}
            syncMessage={familySyncStatus} syncVersion={familySyncVersion}/>
          
        </>}
        {!loading && !loadError && !active && !editorOpen && page === 'profile' && <>
          <section className="page-title"><h1>Your profile<span className="title-dot">.</span></h1></section>
          <ProfilePanel onOpenGroups={()=>goTo('groups')}/>
          <div className="stats-row"><Counter value={lessons.length} label="Lessons available"/><Counter value={practisedCount} label="Items encountered"/><Counter value={recallRate(progress) + '%'} label="Self-rated recall"/></div>
          <section className="xp-rewards" aria-label="Your learning XP">
            <div className="xp-rewards-heading"><div><h2>Learning XP</h2></div>
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
          </section>
          <section className="preferences"><h2>Your local learning data</h2><p>Lessons, unit activity, progress, and review schedules are stored only in this browser. Export a full backup before clearing browser data or changing devices.</p>
            <div className="backup-actions"><button type="button" className="primary-action" onClick={downloadBackup}>Export full backup</button>
              <label className="import-button">Restore from backup<input type="file" aria-label="Restore from backup" accept=".json,application/json" onChange={e => {
                const file = e.currentTarget.files?.[0]; void restoreBackup(file); e.currentTarget.value='';
              }}/></label>
            </div>
            {backupStatus && <p className="backup-success" role="status">{backupStatus}</p>}
            {backupError && <p className="author-error" role="alert">{backupError}</p>}
            <p className="backup-hint">A restore replaces the local lessons, unit activity, all practice history, scheduled reviews and reading positions. Built-in lessons and downloadable audio are part of the app, not this backup. No recordings are included.</p>
            <button type="button" className="danger-action" onClick={() => { if (window.confirm('Erase local practice history, review dates AND earned XP? Personal lessons will be kept. This cannot be undone.')) {
              setProgress({}); setReviews({}); setTouristActivity(emptyTouristActivities()); setExpedition(emptyExpedition()); setBackupStatus('Practice, review schedules and earned XP cleared. Personal lessons are unchanged.');
            } }}>Clear practice and reviews</button></section>
        </>}
      </main>
    </div>

    <nav className="mobile-nav" aria-label="Mobile navigation">{nav.map(item => <button type="button" key={item.id} className={!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'selected' : ''} aria-current={!lessonId && (page === item.id || (page === 'groups' && item.id === 'expedition')) ? 'page' : undefined} onClick={() => goTo(item.id)}><UIIcon name={item.icon} size={21}/><small>{item.label}</small></button>)}</nav>
  </div>;
}
