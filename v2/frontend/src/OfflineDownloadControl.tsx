import type { Lesson } from './model';
import { useOfflineLesson } from './offline';

export default function OfflineDownloadControl({ lesson }: { lesson: Lesson }) {
  const offline = useOfflineLesson(lesson);
  if (offline.total === 0) return null;
  return <div className="offline-control" aria-live="polite">
    {offline.status === 'checking' && <span className="offline-note">Checking offline files…</span>}
    {offline.status === 'unsupported' && <span className="offline-note" title={offline.message}>Offline downloads in the production preview</span>}
    {offline.status === 'downloading' && <span className="offline-note">Saving audio {offline.done}/{offline.total}…</span>}
    {offline.status === 'ready' && <><strong className="offline-ready">✓ Offline ready</strong><button type="button" onClick={() => void offline.action()}>Remove offline copy</button></>}
    {offline.status === 'absent' && <button type="button" className="offline-cta" onClick={() => void offline.action()}>↓ Download for offline</button>}
    {offline.status === 'error' && <><span className="offline-error" role="alert">{offline.message}</span><button type="button" onClick={() => void offline.action()}>Retry download</button></>}
  </div>;
}
