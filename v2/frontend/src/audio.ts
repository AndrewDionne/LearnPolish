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
  playExcerpt: (relativePath:string,startMs:number,endMs:number) => Promise<void>;
  stop: () => void;
};

export function useLessonAudio(): Playback {
  const player = useRef<HTMLAudioElement | null>(null);
  const excerpt = useRef<{controller:AbortController;context:AudioContext|null;source:AudioBufferSourceNode|null}|null>(null);
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
    const clip=excerpt.current;
    excerpt.current=null;
    if(clip){
      clip.controller.abort();
      try{clip.source?.stop();}catch{/* already stopped */}
      if(clip.context)void clip.context.close().catch(()=>{});
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


  /** Sample-accurate syllable excerpts of the SAME recorded whole Polish word.
   * Never infer offsets: the caller gets these only from reviewed source data.
   * WebAudio uses decoded original MP3; HTMLAudio timeupdate is too imprecise
   * for short consonants and syllables. No new request to a speech provider. */
  const playExcerpt=async(relativePath:string,startMs:number,endMs:number)=>{
    stop();
    setError('');
    if(!/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(relativePath)||
      !Number.isSafeInteger(startMs)||!Number.isSafeInteger(endMs)||
      startMs<0||endMs<=startMs||endMs-startMs<45||endMs>30000){
      setError('This syllable excerpt has no trusted recording boundary.');
      return;
    }
    const ticket=token.current;
    const clip:{controller:AbortController;context:AudioContext|null;source:AudioBufferSourceNode|null}={
      controller:new AbortController(),context:null,source:null,
    };
    excerpt.current=clip;
    try{
      const response=await fetch(import.meta.env.BASE_URL+relativePath,{
        signal:clip.controller.signal,credentials:'same-origin'});
      if(!response.ok)throw Error('Audio recording unavailable');
      const body=await response.arrayBuffer();
      if(ticket!==token.current||excerpt.current!==clip)return;
      const context=new AudioContext();
      clip.context=context;
      const decoded=await context.decodeAudioData(body);
      if(ticket!==token.current||excerpt.current!==clip)return;
      if(endMs>Math.round(decoded.duration*1000)+30)
        throw Error('The excerpt is outside this recording');
      const source=context.createBufferSource();
      source.buffer=decoded;
      source.playbackRate.value=rate;
      source.connect(context.destination);
      clip.source=source;
      source.onended=()=>{
        if(ticket!==token.current||excerpt.current!==clip)return;
        excerpt.current=null;
        setPlaying(null);
        void context.close().catch(()=>{});
      };
      if(context.state==='suspended')await context.resume();
      if(ticket!==token.current||excerpt.current!==clip)return;
      source.start(0,startMs/1000,(endMs-startMs)/1000);
      setPlaying(relativePath);
    }catch{
      if(ticket!==token.current||excerpt.current!==clip)return;
      excerpt.current=null;
      if(clip.context)void clip.context.close().catch(()=>{});
      setPlaying(null);
      if(!clip.controller.signal.aborted)
        setError('Could not play this syllable excerpt. Try the full recording.');
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
    const clip=excerpt.current;
    excerpt.current=null;
    if(clip){
      clip.controller.abort();
      try{clip.source?.stop();}catch{/* already ended */}
      if(clip.context)void clip.context.close().catch(()=>{});
    }
  }, []);

  return { playing, rate, setRate, error, play, playExcerpt, stop };
}
