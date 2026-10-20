import { useEffect, useRef, useState } from 'react';

/** Natural-range Polish listening: never offer 0.5× or faster than the reference. */
export const AUDIO_RATES = [0.75, 0.85, 1] as const;
export type AudioRate = typeof AUDIO_RATES[number];
type Playback = {
  playing: string | null;
  rate: AudioRate;
  setRate: (speed: AudioRate) => void;
  error: string;
  play: (relativePath: string) => Promise<void>;
  stop: () => void;
};

export function useLessonAudio(): Playback {
  const player = useRef<HTMLAudioElement | null>(null);
  const token = useRef(0);
  const [playing, setPlaying] = useState<string | null>(null);
  const [rate, setRateValue] = useState<AudioRate>(1);
  const [error, setError] = useState('');

  const stop = () => {
    token.current++;
    const old = player.current;
    player.current = null;
    if (old) {
      old.pause();
      old.removeAttribute('src');
      old.load();
    }
    setPlaying(null);
  };

  const setRate = (speed: AudioRate) => {
    setRateValue(speed);
    if (player.current) player.current.playbackRate = speed;
  };

  const play = async (relativePath: string) => {
    stop();
    setError('');
    // Media imported from other apps must never control which network URL we load.
    if (!/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(relativePath)) {
      setError('This recording is not a trusted lesson audio file.');
      return;
    }
    const ticket = token.current;
    const element = new Audio(import.meta.env.BASE_URL + relativePath);
    element.preload = 'auto';
    element.playbackRate = rate;
    player.current = element;
    const finish = () => {
      if (player.current !== element || token.current !== ticket) return;
      player.current = null;
      setPlaying(null);
    };
    element.addEventListener('ended', finish, { once: true });
    element.addEventListener('error', () => {
      if (player.current === element && token.current === ticket) {
        setError('Could not load this recording. Check your connection or try another item.');
        finish();
      }
    }, { once: true });
    try {
      await element.play();
      if (player.current === element && token.current === ticket) setPlaying(relativePath);
    } catch {
      if (player.current === element && token.current === ticket) {
        setError('Playback was blocked or unavailable. Tap Listen to retry.');
        finish();
      }
    }
  };

  useEffect(() => () => {
    token.current++;
    const old = player.current;
    player.current = null;
    if (old) {
      old.pause();
      old.removeAttribute('src');
      old.load();
    }
  }, []);

  return { playing, rate, setRate, error, play, stop };
}
