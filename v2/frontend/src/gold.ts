/** Reward effort, not arbitrary percentages or unvalidated pronunciation grades.
 * Local ledger is an encouragement mechanic, not tamper-proof currency.
 */
export type RewardMode = 'learn' | 'read' | 'listen' | 'speak';
export type GoldEvent = { id: string; itemId: string; mode: RewardMode; at: string; gold: 10 };
export type GoalMode = 'path' | 'self';
export type AvatarId = 'hero' | 'chonky' | 'tall' | 'junior';
export const AVATARS: {id:AvatarId; label:string}[] = [{id:'hero',label:'Pierogi Hero'},{id:'chonky',label:'Pierogi Chonky'},{id:'tall',label:'Pierogi Tall'},{id:'junior',label:'Pierogi Junior'}];
export type GoldState = { schemaVersion: 1; goalMode: GoalMode; selfGoal: number; events: GoldEvent[]; avatar?: AvatarId };
export const GOLD_STORAGE_KEY = 'ptp-v2-gold';
export const DEFAULT_GOLD: GoldState = { schemaVersion:1, goalMode:'path', selfGoal:500, events:[] };
export const GOLD_PER_ITEM = 10;
const MODES = new Set<RewardMode>(['learn','read','listen','speak']);

export function calendarDay(at: string): string {
  const d = new Date(at);
  if (!Number.isFinite(d.getTime())) throw new Error('Invalid award date');
  // Respect learner local calendar days, not browser-independent UTC midnight.
  return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
}
export function parseGold(raw: string | null): GoldState {
  if (!raw) return {...DEFAULT_GOLD,events:[]};
  try {
    const a: unknown = JSON.parse(raw);
    if (!a || typeof a !== 'object' || Array.isArray(a)) return {...DEFAULT_GOLD,events:[]};
    const value = a as Partial<GoldState>;
    if (value.schemaVersion !== 1 || !['path','self'].includes(value.goalMode || '') ||
        !Number.isSafeInteger(value.selfGoal) || Number(value.selfGoal)<50 || Number(value.selfGoal)>5000 ||
        !Array.isArray(value.events) || value.events.length>20000) return {...DEFAULT_GOLD,events:[]};
    const keys = new Set<string>();
    const valid: GoldEvent[]=[];
    for (const event of value.events) {
      if (!event || typeof event !== 'object' ||
          typeof event.itemId !== 'string' || !/^[\w:.-]{1,180}$/.test(event.itemId) ||
          !MODES.has(event.mode) || typeof event.at !== 'string' || !Number.isFinite(Date.parse(event.at)) ||
          event.gold !== GOLD_PER_ITEM ||
          typeof event.id !== 'string' ||
          !/\d{4}-\d{2}-\d{2}$/.test(event.id) ||
          event.id !== event.mode + ':' + event.itemId + ':' + event.id.slice(-10) ||
          keys.has(event.id)) continue;
      keys.add(event.id);
      valid.push(event);
    }
    return {schemaVersion:1,goalMode:value.goalMode!,selfGoal:value.selfGoal!,events:valid,
      ...(AVATARS.some(avatar => avatar.id === value.avatar) ? {avatar:value.avatar} : {})};
  } catch {return {...DEFAULT_GOLD,events:[]};}
}

/** Once per item, mode and local calendar day, even if the learner replays a session. */
export function awardGold(state: GoldState, itemId: string, mode: RewardMode, at: string): GoldState {
  if (!/^[\w:.-]{1,180}$/.test(itemId) || !MODES.has(mode)) return state;
  const id=mode + ':' + itemId + ':' + calendarDay(at);
  if (state.events.some(e => e.id === id)) return state;
  if (state.events.length >= 20000) return state;
  return {...state, events:[...state.events,{id,itemId,mode,at,gold:GOLD_PER_ITEM}]};
}

function mondayStart(now: Date): number {
  const d=new Date(now.getFullYear(),now.getMonth(),now.getDate());
  d.setDate(d.getDate()-((d.getDay()+6)%7));
  return d.getTime();
}
export function goldSummary(state: GoldState, now: string) {
  const n=new Date(now);
  const start=mondayStart(n);
  const goal=state.goalMode==='path'?500:state.selfGoal;
  const weekly=state.events.filter(e=> {
    const t=Date.parse(e.at);
    return t>=start && t<start+7*86400000;
  }).reduce((sum,e)=>sum+e.gold,0);
  const total=state.events.reduce((sum,e)=>sum+e.gold,0);
  const dates=new Set(state.events.map(e=>e.id.slice(-10)));
  const today=new Date(n.getFullYear(),n.getMonth(),n.getDate());
  const cursor=new Date(today);
  if (!dates.has([cursor.getFullYear(),String(cursor.getMonth()+1).padStart(2,'0'),String(cursor.getDate()).padStart(2,'0')].join('-'))) cursor.setDate(cursor.getDate()-1);
  let streak=0;
  while (dates.has([cursor.getFullYear(),String(cursor.getMonth()+1).padStart(2,'0'),String(cursor.getDate()).padStart(2,'0')].join('-'))) {
    streak++;cursor.setDate(cursor.getDate()-1);
  }
  return {total, weekly, goal, streak, reachedGoal:weekly>=goal, remaining:Math.max(0,goal-weekly)};
}
export function setGoal(state: GoldState, mode: GoalMode, selfGoal: number): GoldState {
  if (!Number.isSafeInteger(selfGoal) || selfGoal<50 || selfGoal>5000 || selfGoal%10) return state;
  return {...state,goalMode:mode,selfGoal};
}

export function selectAvatar(state:GoldState, avatar:AvatarId):GoldState {
  return AVATARS.some(choice=>choice.id===avatar) ? {...state,avatar} : state;
}
