import { useEffect, useMemo, useState } from 'react';
import type { Lesson, LessonItem, LessonKind } from './model';
import { lessonLabel, parseManifest } from './model';
import { useLessonAudio } from './audio';
import { parseProgress, recallRate, recordAttempt, STORAGE_KEY } from './progress';
import type { Progress } from './progress';
import { PERSONAL_STORAGE_KEY, importPersonalLesson, makePersonalLesson, parsePersonalLessons, toPortableLesson, upsertPersonalLesson } from './personal';
import type { DraftItem } from './personal';
import { availableModes, comprehensionChoices, itemPractised, itemsForMode, progressKey } from './modes';
import type { LearningMode } from './modes';
import { READING_POSITION_KEY, parseReadingPositions, safeReadingPosition } from './reading-position';

type Page = 'home' | 'library' | 'practice' | 'profile';
type KindFilter = 'all' | LessonKind;

const nav: { id: Page; label: string; symbol: string }[] = [
  { id: 'home', label: 'Home', symbol: '⌂' },
  { id: 'library', label: 'Library', symbol: '▦' },
  { id: 'practice', label: 'Practice', symbol: '◎' },
  { id: 'profile', label: 'My progress', symbol: '◷' },
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
      <span className="tile-detail">{lesson.items.length} {lesson.kind === 'reading' ? 'passages' : 'items'} · {completed} practised</span>
      <span className="meter" aria-hidden="true"><span style={{ width: (100 * completed / lesson.items.length) + '%' }} /></span>
    </span>
    <span className="tile-arrow" aria-hidden="true">↗</span>
  </button>;
}

function AudioButton({ item, playing, onPlay }: {
  item: LessonItem; playing: string | null; onPlay: (path: string) => void;
}) {
  return <button type="button" className="audio-btn" disabled={!item.audio} title={!item.audio ? 'Reference audio unavailable' : 'Play Polish recording'} onClick={() => item.audio && onPlay(item.audio)}>
    <span aria-hidden="true">{item.audio && playing === item.audio ? '◼' : '▶'}</span> {item.audio && playing === item.audio ? 'Playing audio' : item.audio ? 'Play audio' : 'No audio'}
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
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<KindFilter>('all');
  const [lessonId, setLessonId] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [mode, setMode] = useState<LearningMode>('learn');
  const [listenGuess, setListenGuess] = useState<string | null>(null);
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
  const audio = useLessonAudio();

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

  const active = lessons.find(x => x.id === lessonId);
  const sessionItems = active ? itemsForMode(active, mode) : [];
  const current = sessionItems[index];
  const listeningChoices = active && current && mode === 'listen' ? comprehensionChoices(active.items, current, index) : [];
  const last = lessons.find(x => x.id === lastLesson);
  const practisedCount = lessons.reduce((total, lesson) =>
    total + lesson.items.filter(item => itemPractised(progress, item.id)).length, 0);
  const completedIn = (lesson: Lesson) => lesson.items.filter(item => itemPractised(progress, item.id)).length;

  const filtered = useMemo(() => lessons.filter(x =>
    (filter === 'all' || x.kind === filter) &&
    (x.title.toLowerCase().includes(query.toLowerCase()) || x.items.some(i => i.polish.toLowerCase().includes(query.toLowerCase())))
  ), [lessons, filter, query]);

  const stopAudio = () => { audio.stop(); };
  const goTo = (destination: Page) => {
    stopAudio(); setLessonId(null); setEditorOpen(false); setPage(destination); setRevealed(false); setFinished(false);
  };
  const openLesson = (lesson: Lesson) => {
    stopAudio();
    setLessonId(lesson.id); setMode(lesson.kind === 'reading' ? 'read' : 'learn');
    setIndex(lesson.kind === 'reading' ? safeReadingPosition(readingPositions, lesson.id, lesson.items.length) : 0);
    setRevealed(false); setTranslationOpen(false); setListenGuess(null); setListenRevealed(false); setFinished(false);
    setLastLesson(lesson.id); saveLastLesson(lesson.id);
  };
  const jump = (target: number) => {
    if (!active) return;
    stopAudio();
    const next = Math.max(0, Math.min(sessionItems.length - 1, target));
    setIndex(next);
    if (mode === 'read') setReadingPositions(previous => ({ ...previous, [active.id]: next }));
    setRevealed(false); setTranslationOpen(false); setListenGuess(null); setListenRevealed(false); setFinished(false);
  };
  const switchMode = (next: LearningMode) => {
    if (!active || !availableModes(active).includes(next)) return;
    stopAudio();
    setMode(next);
    setIndex(next === 'read' ? safeReadingPosition(readingPositions, active.id, active.items.length) : 0);
    setRevealed(false); setTranslationOpen(false); setListenGuess(null); setListenRevealed(false); setFinished(false);
  };
  const record = (remembered: boolean) => {
    if (!current) return;
    setProgress(previous => recordAttempt(previous, progressKey(current.id, mode), remembered, new Date().toISOString()));
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
  const deletePersonalLesson = (lesson: Lesson) => {
    if (lesson.source !== 'personal' || !window.confirm('Delete this personal lesson? This cannot be undone.')) return;
    setPersonal(old => old.filter(x => x.id !== lesson.id));
    setProgress(old => {
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
    <aside className="sidebar">
      <button className="brand" type="button" onClick={() => goTo('home')} aria-label="Path to Polish home">
        <span className="brand-symbol">p<span>.</span></span>
        <span className="brand-name">path to <strong>polish</strong><small>LEARN WITH CONFIDENCE</small></span>
      </button>
      <span className="nav-heading">EXPLORE</span>
      <nav className="side-links" aria-label="Main navigation">
        {nav.map(item => <button key={item.id} className={'nav-link ' + (!lessonId && page === item.id ? 'selected' : '')} type="button" onClick={() => goTo(item.id)}><span className="nav-icon">{item.symbol}</span>{item.label}</button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="mini-mark">PL</div>
        <div><strong>A little every day.</strong><span>Keep building your Polish.</span></div>
      </div>
      <span className="sidebar-version">Path to Polish · V2 preview</span>
    </aside>

    <div className="main-shell">
      <header className="topbar">
        <div className="crumb"><span>PATH TO POLISH</span><span className="crumb-slash">/</span><strong>{active ? active.title : nav.find(x => x.id === page)?.label}</strong></div>
        <div className="top-right"><span className="local-pill">● Local preview</span><span className="initial-badge" aria-label="Local learner">P</span></div>
      </header>
      <main className="page-content">
        {loading && <section className="empty-state" role="status"><h2>Gathering your lessons…</h2><p>Preparing your Polish library.</p></section>}
        {!loading && loadError && <section className="empty-state" role="alert"><h2>Lessons could not load</h2><p>{loadError}</p><p>Run <code>npm run content</code> in v2/frontend, then reload. Your progress remains saved locally.</p></section>}

        {!loading && !loadError && active && current && <div className="learning">
          <div className="lesson-tools"><button type="button" className="back-link" onClick={() => goTo('library')}>← Back to library</button><div><button type="button" onClick={() => exportFile(active)}>Export JSON</button>{active.source === 'personal' && <><button type="button" onClick={() => beginEdit(active)}>Edit lesson</button><button type="button" className="delete-link" onClick={() => deletePersonalLesson(active)}>Delete</button></>}</div></div>
          <div className="learning-head">
            <div><span className="eyebrow">{lessonLabel(active.kind)} · {active.title}</span><h1>{mode === 'listen' ? 'Train your ear' : mode === 'read' ? 'Read & understand' : active.kind === 'sounds' ? 'Hear the difference' : 'Learn the language'}</h1><p>{mode === 'listen' ? 'Listen first, choose the meaning, then compare your answer with the Polish transcript.' : mode === 'read' ? 'Read naturally, then reveal the translation. Your reading position is remembered.' : active.kind === 'sounds' ? 'Compare the examples and listen carefully. These lessons await native-speaker review.' : 'Think of the Polish expression before revealing its meaning.'}</p></div>
            <span className="item-count">{index + 1} <span>/ {sessionItems.length}</span></span>
          </div>
          <div className="lesson-meter"><span style={{ width: (100 * (index + 1) / sessionItems.length) + '%' }} /></div>
          <div className="mode-row" aria-label="Learning modes">
            {availableModes(active).map(value => <button type="button" key={value} aria-pressed={mode === value} className={'mode ' + (mode === value ? 'active' : '')} onClick={() => switchMode(value)}>{value === 'learn' ? active.kind === 'sounds' ? 'Sounds' : 'Learn' : value === 'read' ? 'Read' : 'Listen'}</button>)}
            <span className="mode future" title="Evidence-based pronunciation assessment is being developed">Speak · upcoming</span>
          </div>
          {finished ? <section className="flashcard complete-card" aria-live="polite">
            <span className="card-label">SESSION COMPLETE</span>
            <h2>Nicely done!</h2>
            <p>You made it through {sessionItems.length} {sessionItems.length === 1 ? 'item' : 'items'} in {mode === 'listen' ? 'listening practice' : mode === 'read' ? 'reading practice' : 'learning practice'}.</p>
            <div className="answer-actions"><button type="button" className="secondary-action" onClick={() => jump(0)}>Practise again</button><button type="button" className="primary-action" onClick={() => goTo('library')}>Back to library →</button></div>
          </section> : mode === 'listen' ? <section className="flashcard listening-card" aria-live="polite">
            <span className="card-label">LISTEN WITHOUT READING</span>
            <div className="listening-symbol" aria-hidden="true">♫</div>
            <h2>What did you hear?</h2>
            <p className="listening-prompt">Play the recording. Choose the closest meaning before revealing the Polish.</p>
            <AudioButton item={current} playing={audio.playing} onPlay={play}/>
            <fieldset className="speed-picker"><legend>Playback speed</legend>
              {([0.75, 1, 1.25] as const).map(speed => <button type="button" key={speed} aria-pressed={audio.rate === speed} onClick={() => audio.setRate(speed)} className={audio.rate === speed ? 'chosen' : ''}>{speed}×</button>)}
            </fieldset>
            {audio.error && <p className="audio-error" role="alert">{audio.error}</p>}
            {!listenGuess && !listenRevealed && (listeningChoices.length > 0 ? <div className="listening-options" role="group" aria-label="Choose the meaning">
              {listeningChoices.map(choice => <button type="button" key={choice} onClick={() => { stopAudio(); setListenGuess(choice); }}>{choice}</button>)}
            </div> : <button type="button" className="reveal" onClick={() => setListenRevealed(true)}>Reveal transcript &amp; translation</button>)}
            {(listenGuess !== null || listenRevealed) && <div className="listening-answer">
              {listenGuess !== null && <p className={listenGuess === current.english ? 'answer-good' : 'answer-review'}>{listenGuess === current.english ? 'Correct meaning!' : 'Not quite. Review the expression below.'}</p>}
              <span className="card-label">POLISH TRANSCRIPT</span><p className="listen-transcript">{current.polish}</p>
              <span className="card-label">ENGLISH TRANSLATION</span><p>{current.english}</p>
              {listenGuess !== null ? <button type="button" className="primary-action" onClick={() => record(listenGuess === current.english)}>Continue →</button> : <div className="answer-actions">
                <button type="button" className="secondary-action" onClick={() => record(false)}>Needs practice</button>
                <button type="button" className="primary-action" onClick={() => record(true)}>Understood it →</button>
              </div>}
            </div>}
          </section> : <section className="flashcard" aria-live="polite">
            <span className="card-label">{mode === 'read' ? (current.title || 'POLISH PASSAGE') : active.kind === 'sounds' ? 'SOUND EXAMPLES' : 'IN POLISH'}</span>
            <div className={mode === 'read' ? 'polish-text reading-text' : 'polish-text'}>{current.polish}</div>
            {current.pronunciation && mode === 'learn' && <p className="phonetic">{current.pronunciation}</p>}
            <AudioButton item={current} playing={audio.playing} onPlay={play}/>
            {audio.error && <p className="audio-error" role="alert">{audio.error}</p>}
            {mode === 'read' && current.audio && <fieldset className="speed-picker"><legend>Playback speed</legend>
              {([0.75, 1, 1.25] as const).map(speed => <button type="button" key={speed} aria-pressed={audio.rate === speed} onClick={() => audio.setRate(speed)} className={audio.rate === speed ? 'chosen' : ''}>{speed}×</button>)}
            </fieldset>}
            {(revealed || translationOpen) && <div className="translation"><span className="card-label">IN ENGLISH</span><p>{current.english}</p></div>}
            {!revealed && !translationOpen && <button type="button" className="reveal" onClick={() => mode === 'read' ? setTranslationOpen(true) : setRevealed(true)}>Reveal meaning <span>↗</span></button>}
            {(revealed || translationOpen) && <div className="answer-actions">
              <button type="button" className="secondary-action" onClick={() => record(false)}>{mode === 'read' ? 'Review again' : 'Needs practice'}</button>
              <button type="button" className="primary-action" onClick={() => record(true)}>{mode === 'read' ? 'Finished reading →' : 'Got it →'}</button>
            </div>}
          </section>}
          <div className="lesson-footer">
            <button type="button" onClick={() => jump(index - 1)} disabled={index === 0}>← Previous</button>
            <span>{completedIn(active)} of {active.items.length} explored</span>
            <button type="button" onClick={() => jump(index + 1)} disabled={index === sessionItems.length - 1}>Skip to next →</button>
          </div>
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
          <section className="page-title"><span className="eyebrow">YOUR LEARNING COLLECTION</span><h1>Lesson library<span className="title-dot">.</span></h1><p>Real Polish, organized into small lessons you can return to whenever you like.</p></section>
          <div className="author-actions"><button type="button" className="primary-action" onClick={beginNew}>+ Create lesson</button><label className="import-button">Import lesson JSON<input aria-label="Import lesson JSON" type="file" accept=".json,application/json" onChange={e => { const file = e.currentTarget.files?.[0]; void importFile(file); e.currentTarget.value = ''; }} /></label></div>{importError && <p className="author-error" role="alert">{importError}</p>}
          <div className="library-controls"><label className="search-wrap"><span aria-hidden="true">⌕</span><input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search lessons or Polish phrases" aria-label="Search lessons" /></label><div className="filter-buttons" aria-label="Filter lessons">{(['all','vocabulary','reading','sounds'] as KindFilter[]).map(kind => <button type="button" key={kind} className={filter === kind ? 'chosen' : ''} onClick={() => setFilter(kind)}>{kind === 'all' ? 'All lessons' : lessonLabel(kind)}</button>)}</div></div>
          <div className="library-summary">{filtered.length} {filtered.length === 1 ? 'lesson' : 'lessons'} <span>· {filtered.reduce((total, lesson) => total + lesson.items.length, 0)} learning items</span></div>
          <div className="lesson-grid">{filtered.map(lesson => <LessonTile key={lesson.id} lesson={lesson} completed={completedIn(lesson)} onOpen={() => openLesson(lesson)} />)}</div>
          {filtered.length === 0 && <div className="empty-state"><h2>No matching lessons</h2><p>Try another search or select a different category.</p></div>}
          <p className="info-footnote">Built-in lessons come from the legacy collection. Personal lessons are saved to this browser only; export JSON for a portable backup.</p>
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'practice' && <>
          <section className="page-title"><span className="eyebrow">YOUR PRACTICE SPACE</span><h1>Keep it fresh<span className="title-dot">.</span></h1><p>Every phrase you revisit makes it easier to find the words next time.</p></section>
          <div className="stats-row"><Counter value={practisedCount} label="Unique items seen"/><Counter value={Object.values(progress).reduce((total, x) => total + x.seen, 0)} label="Practice attempts"/><Counter value={recallRate(progress) + '%'} label="Self-rated recall"/></div>
          <div className="section-heading lower"><div><span className="eyebrow">RETURN TO PRACTICE</span><h2>Continue your lessons</h2></div></div>
          <div className="lesson-grid">{lessons.filter(x => completedIn(x) > 0).sort((a,b)=>completedIn(b)-completedIn(a)).slice(0,8).map(x => <LessonTile key={x.id} lesson={x} completed={completedIn(x)} onOpen={() => openLesson(x)}/>)}</div>
          {practisedCount === 0 && <div className="start-card"><p>Practice progress will appear here after your first lesson.</p><button className="primary-action" type="button" onClick={() => goTo('library')}>Choose a lesson →</button></div>}
          <p className="info-footnote">These metrics reflect self-rated recall. Automated pronunciation assessment is a separate, upcoming feature.</p>
        </>}

        {!loading && !loadError && !active && !editorOpen && page === 'profile' && <>
          <section className="page-title"><span className="eyebrow">YOUR JOURNEY</span><h1>Learning progress<span className="title-dot">.</span></h1><p>Your achievements are saved in this browser while we develop secure accounts and sync.</p></section>
          <div className="stats-row"><Counter value={lessons.length} label="Lessons available"/><Counter value={practisedCount} label="Items encountered"/><Counter value={recallRate(progress) + '%'} label="Self-rated recall"/></div>
          <section className="preferences"><h2>Local data</h2><p>Progress is currently stored on this device, not in an account. Avoid clearing browser site data if you want to keep your results.</p><button type="button" className="danger-action" onClick={() => { if (window.confirm('Erase all locally saved practice progress? This cannot be undone.')) { setProgress({}); try { localStorage.removeItem(STORAGE_KEY); } catch { /* best effort */ } } }}>Clear practice progress</button></section>
        </>}
      </main>
    </div>

    <nav className="mobile-nav" aria-label="Mobile navigation">{nav.map(item => <button type="button" key={item.id} className={!lessonId && page === item.id ? 'selected' : ''} onClick={() => goTo(item.id)}><span aria-hidden="true">{item.symbol}</span><small>{item.label === 'My progress' ? 'Profile' : item.label}</small></button>)}</nav>
  </div>;
}
