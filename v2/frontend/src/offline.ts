import { useEffect, useRef, useState } from 'react';
import type { Lesson } from './model';

type RequestType = 'STATUS' | 'DOWNLOAD' | 'REMOVE';
type OfflineResponse = { type: 'done'; ready: boolean; done: number; total: number };
type OfflineUpdate = OfflineResponse | { type: 'progress'; done: number; total: number } | { type: 'error'; message: string };
type OfflineStatus = 'checking' | 'unsupported' | 'absent' | 'downloading' | 'ready' | 'error';
export type OfflineAction = 'DOWNLOAD' | 'REMOVE';
export function nextOfflineAction(status: OfflineStatus, failedAction: OfflineAction | null): OfflineAction {
  // Retrying a failed removal must not silently redownload deleted material.
  return status === 'ready' || (status === 'error' && failedAction === 'REMOVE')
    ? 'REMOVE' : 'DOWNLOAD';
}

export function downloadableAudio(lesson: Lesson): string[] {
  return [...new Set(lesson.items.map(item => item.audio).filter((path): path is string => !!path))];
}

async function activeWorker(): Promise<ServiceWorker> {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) {
    throw new Error('Offline download needs the production PWA build.');
  }
  const registration = await navigator.serviceWorker.register(import.meta.env.BASE_URL + 'sw.js', {
    scope: import.meta.env.BASE_URL,
  });
  const ready = await navigator.serviceWorker.ready;
  const worker = ready.active || registration.active;
  if (!worker) throw new Error('The offline service worker is not active');
  return worker;
}

function sendOfflineRequest(worker: ServiceWorker, type: RequestType, urls: string[], onProgress?: (done: number, total: number) => void): Promise<OfflineResponse> {
  return new Promise((resolve, reject) => {
    const channel = new MessageChannel();
    channel.port1.onmessage = (event: MessageEvent<OfflineUpdate>) => {
      const response = event.data;
      if (response.type === 'progress') {
        onProgress?.(response.done, response.total);
        return;
      }
      channel.port1.close();
      if (response.type === 'error') reject(new Error(response.message));
      else resolve(response);
    };
    worker.postMessage({ type, urls }, [channel.port2]);
  });
}

export function useOfflineLesson(lesson: Lesson) {
  const [status, setStatus] = useState<OfflineStatus>('checking');
  const [message, setMessage] = useState('');
  const [done, setDone] = useState(0);
  const [operation,setOperation] = useState<OfflineAction|null>(null);
  const generation=useRef(0);
  const urls = downloadableAudio(lesson);
  const total = urls.length;

  useEffect(() => {
    let active = true;
    const id=++generation.current;
    setOperation(null);
    setDone(0);
    setMessage('');
    if (urls.length === 0) {
      setStatus('unsupported');
      return () => { active=false;generation.current++; };
    }
    setStatus('checking');
    activeWorker().then(worker => sendOfflineRequest(worker, 'STATUS', urls)).then(result => {
      if (active && id===generation.current) {
        setStatus(result.ready ? 'ready' : 'absent');setDone(result.done);
      }
    }).catch(error => {
      if (active && id===generation.current) {
        setStatus('unsupported');setMessage(error instanceof Error ? error.message : 'Offline unavailable');
      }
    });
    return () => { active = false;generation.current++; };
  }, [lesson.id, lesson.items]);

  const action = async () => {
    if (status !== 'ready' && status !== 'absent' && status !== 'error') return;
    const type=nextOfflineAction(status,operation);
    const id=generation.current;
    setOperation(type);
    setStatus('downloading');
    setMessage('');
    try {
      const worker = await activeWorker();
      const result = await sendOfflineRequest(worker, type, urls, count => {
        if(id===generation.current)setDone(count);
      });
      if(id!==generation.current)return; // Lesson changed while the request was pending.
      setDone(result.done);
      setStatus(result.ready ? 'ready' : 'absent');
      setOperation(null);
    } catch (error) {
      if(id!==generation.current)return;
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Offline cache operation failed');
    }
  };
  return { status, message, done, total, operation, action };
}
