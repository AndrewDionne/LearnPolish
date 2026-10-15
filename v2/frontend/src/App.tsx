import { useEffect, useMemo, useState } from 'react';
import type { Lesson, LessonItem, LessonKind } from './model';
import { lessonLabel, parseManifest } from './model';
import { useLessonAudio } from './audio';
import { parseProgress, recallRate, recordAttempt, STORAGE_KEY } from './progress';
import type { Progress } from './progress';

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
    <span aria-hidden="true">{item.audio && playing === item.audio ? '◼' : '▶'}</span> {item.audio && playing === item.audio ? 'Playing' : item.audio ? 'Listen' : 'No audio'}
  </button>;
}

export default function App() {
  const [page, setPage] = useState<Page>('home');
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<KindFilter>('all');
  const [lessonId, setLessonId] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [translationOpen, setTranslationOpen] = useState(false);
  const [audioError, setAudioError] = useState('');
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
        if (!controller.signal.aborted) { setLessons(data); setLoadError(''); }
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

  const active = lessons.find(x => x.id === lessonId);
  const current = active?.items[index];
  const last = lessons.find(x => x.id === lastLesson);
  const practisedCount = Object.keys(progress).length;
  const completedIn = (lesson: Lesson) => lesson.items.filter(item => !!progress[item.id]).length;

  const filtered = useMemo(() => lessons.filter(x =>
    (filter === 'all' || x.kind === filter) &&
    (x.title.toLowerCase().includes(query.toLowerCase()) || x.items.some(i => i.polish.toLowerCase().includes(query.toLowerCase())))
  ), [lessons, filter, query]);

  const stopAudio = () => { audio.stop(); setAudioError(''); };
  const goTo = (destination: Page) => {
    stopAudio(); setLessonId(null); setPage(destination); setRevealed(false);
  };
  const openLesson = (lesson: Lesson) => {
    stopAudio();
    setLessonId(lesson.id); setIndex(0); setRevealed(false); setTranslationOpen(false);
    setLastLesson(lesson.id); saveLastLesson(lesson.id);
  };
  const jump = (target: number) => {
    if (!active) return;
    stopAudio();
    setIndex(Math.max(0, Math.min(active.items.length - 1, target)));
    setRevealed(false); setTranslationOpen(false);
  };
  const record = (remembered: boolean) => {
    if (!current) return;
    setProgress(previous => recordAttempt(previous, current.id, remembered, new Date().toISOString()));
    if (active && index < active.items.length - 1) jump(index + 1);
    else setRevealed(false);
  };
  const play = (path: string) => {
    setAudioError('');
    void audio.play(path).catch(error => setAudioError(error instanceof Error ? error.message : 'Playback failed'));
  };

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
          <button type="button" className="back-link" onClick={() => goTo('library')}>← Back to library</button>
          <div className="learning-head">
            <div><span className="eyebrow">{lessonLabel(active.kind)} · {active.title}</span><h1>{active.kind === 'reading' ? 'Read & understand' : active.kind === 'sounds' ? 'Hear the difference' : 'Learn the language'}</h1><p>{active.kind === 'reading' ? 'Read naturally, then reveal the translation.' : active.kind === 'sounds' ? 'Compare the examples and listen carefully. These lessons await a native-speaker content review.' : 'Think of the Polish expression before revealing its meaning.'}</p></div>
            <span className="item-count">{index + 1} <span>/ {active.items.length}</span></span>
          </div>
          <div className="lesson-meter"><span style={{ width: (100 * (index + 1) / active.items.length) + '%' }} /></div>
          <div className="mode-row" aria-label="Learning modes">
            <span className="mode active">{active.kind === 'reading' ? 'Read' : active.kind === 'sounds' ? 'Sounds' : 'Learn'}</span>
            <span className="mode future" title="Available in the pronunciation tranche">Speak · soon</span>
            <span className="mode future" title="Available in the listening tranche">Listen · soon</span>
          </div>
          <section className="flashcard" aria-live="polite">
            <span className="card-label">{active.kind === 'reading' ? (current.title || 'POLISH PASSAGE') : active.kind === 'sounds' ? 'SOUND EXAMPLES' : 'IN POLISH'}</span>
            <div className={active.kind === 'reading' ? 'polish-text reading-text' : 'polish-text'}>{current.polish}</div>
            {current.pronunciation && active.kind !== 'reading' && <p className="phonetic">{current.pronunciation}</p>}
            <AudioButton item={current} playing={audio.playing} onPlay={play}/>
            {audioError && <p className="audio-error" role="alert">{audioError}</p>}
            {(revealed || translationOpen) && <div className="translation"><span className="card-label">IN ENGLISH</span><p>{current.english}</p></div>}
            {!revealed && !translationOpen && <button type="button" className="reveal" onClick={() => active.kind === 'reading' ? setTranslationOpen(true) : setRevealed(true)}>Reveal meaning <span>↗</span></button>}
            {(revealed || translationOpen) && <div className="answer-actions">
              <button type="button" className="secondary-action" onClick={() => record(false)}>{active.kind === 'reading' ? 'Review again' : 'Needs practice'}</button>
              <button type="button" className="primary-action" onClick={() => record(true)}>{active.kind === 'reading' ? 'Finished reading →' : 'Got it →'}</button>
            </div>}
          </section>
          <div className="lesson-footer">
            <button type="button" onClick={() => jump(index - 1)} disabled={index === 0}>← Previous</button>
            <span>{completedIn(active)} of {active.items.length} explored</span>
            <button type="button" onClick={() => jump(index + 1)} disabled={index === active.items.length - 1}>Skip to next →</button>
          </div>
        </div>}

        {!loading && !loadError && !active && page === 'home' && <>
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

        {!loading && !loadError && !active && page === 'library' && <>
          <section className="page-title"><span className="eyebrow">YOUR LEARNING COLLECTION</span><h1>Lesson library<span className="title-dot">.</span></h1><p>Real Polish, organized into small lessons you can return to whenever you like.</p></section>
          <div className="library-controls"><label className="search-wrap"><span aria-hidden="true">⌕</span><input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search lessons or Polish phrases" aria-label="Search lessons" /></label><div className="filter-buttons" aria-label="Filter lessons">{(['all','vocabulary','reading','sounds'] as KindFilter[]).map(kind => <button type="button" key={kind} className={filter === kind ? 'chosen' : ''} onClick={() => setFilter(kind)}>{kind === 'all' ? 'All lessons' : lessonLabel(kind)}</button>)}</div></div>
          <div className="library-summary">{filtered.length} {filtered.length === 1 ? 'lesson' : 'lessons'} <span>· {filtered.reduce((total, lesson) => total + lesson.items.length, 0)} learning items</span></div>
          <div className="lesson-grid">{filtered.map(lesson => <LessonTile key={lesson.id} lesson={lesson} completed={completedIn(lesson)} onOpen={() => openLesson(lesson)} />)}</div>
          {filtered.length === 0 && <div className="empty-state"><h2>No matching lessons</h2><p>Try another search or select a different category.</p></div>}
          <p className="info-footnote">This preview uses the 23 migrated legacy lesson sets. Personal lesson editing and import are the next capability slice.</p>
        </>}

        {!loading && !loadError && !active && page === 'practice' && <>
          <section className="page-title"><span className="eyebrow">YOUR PRACTICE SPACE</span><h1>Keep it fresh<span className="title-dot">.</span></h1><p>Every phrase you revisit makes it easier to find the words next time.</p></section>
          <div className="stats-row"><Counter value={practisedCount} label="Unique items seen"/><Counter value={Object.values(progress).reduce((total, x) => total + x.seen, 0)} label="Practice attempts"/><Counter value={recallRate(progress) + '%'} label="Self-rated recall"/></div>
          <div className="section-heading lower"><div><span className="eyebrow">RETURN TO PRACTICE</span><h2>Continue your lessons</h2></div></div>
          <div className="lesson-grid">{lessons.filter(x => completedIn(x) > 0).sort((a,b)=>completedIn(b)-completedIn(a)).slice(0,8).map(x => <LessonTile key={x.id} lesson={x} completed={completedIn(x)} onOpen={() => openLesson(x)}/>)}</div>
          {practisedCount === 0 && <div className="start-card"><p>Practice progress will appear here after your first lesson.</p><button className="primary-action" type="button" onClick={() => goTo('library')}>Choose a lesson →</button></div>}
          <p className="info-footnote">These metrics reflect self-rated recall. Automated pronunciation assessment is a separate, upcoming feature.</p>
        </>}

        {!loading && !loadError && !active && page === 'profile' && <>
          <section className="page-title"><span className="eyebrow">YOUR JOURNEY</span><h1>Learning progress<span className="title-dot">.</span></h1><p>Your achievements are saved in this browser while we develop secure accounts and sync.</p></section>
          <div className="stats-row"><Counter value={lessons.length} label="Lessons available"/><Counter value={practisedCount} label="Items encountered"/><Counter value={recallRate(progress) + '%'} label="Self-rated recall"/></div>
          <section className="preferences"><h2>Local data</h2><p>Progress is currently stored on this device, not in an account. Avoid clearing browser site data if you want to keep your results.</p><button type="button" className="danger-action" onClick={() => { if (window.confirm('Erase all locally saved practice progress? This cannot be undone.')) { setProgress({}); try { localStorage.removeItem(STORAGE_KEY); } catch { /* best effort */ } } }}>Clear practice progress</button></section>
        </>}
      </main>
    </div>

    <nav className="mobile-nav" aria-label="Mobile navigation">{nav.map(item => <button type="button" key={item.id} className={!lessonId && page === item.id ? 'selected' : ''} onClick={() => goTo(item.id)}><span aria-hidden="true">{item.symbol}</span><small>{item.label === 'My progress' ? 'Profile' : item.label}</small></button>)}</nav>
  </div>;
}
