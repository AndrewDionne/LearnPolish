import { useEffect, useRef, useState } from 'react';

type Playback = { playing: string | null; play: (relativePath: string) => Promise<void>; stop: () => void };

export function useLessonAudio(): Playback {
  const player = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);

  const stop = () => {
    if (player.current) {
      player.current.pause();
      player.current.currentTime = 0;
      player.current.src = '';
      player.current = null;
    }
    setPlaying(null);
  };

  const play = async (relativePath: string) => {
    stop();
    const audio = new Audio(import.meta.env.BASE_URL + relativePath);
    player.current = audio;
    setPlaying(relativePath);
    const finish = () => {
      if (player.current === audio) {
        player.current = null;
        setPlaying(null);
      }
    };
    audio.addEventListener('ended', finish, { once: true });
    audio.addEventListener('error', finish, { once: true });
    try { await audio.play(); } catch {
      finish();
      throw new Error('Audio could not play. Check your connection and try again.');
    }
  };

  useEffect(() => () => {
    if (player.current) {
      player.current.pause();
      player.current.removeAttribute('src');
      player.current.load();
      player.current = null;
    }
  }, []);

  return { playing, play, stop };
}
