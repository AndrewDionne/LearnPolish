import regions from './regions.json';
import {chooseRegion, nextRegionCost, regionTotal, unlockedRegions} from './expedition';
import type {ExpeditionState} from './expedition';

type Props={state:ExpeditionState;onChange:(value:ExpeditionState)=>void};

export default function ExpeditionMap({state,onChange}:Props){
  const unlocked=unlockedRegions(state);
  const goal=state.regionGoals[state.selectedRegion]??nextRegionCost(state);
  const earned=regionTotal(state,state.selectedRegion);
  const active=regions.find(x=>x.id===state.selectedRegion)!;
  const select=(id:string)=>onChange(chooseRegion(state,id));
  return <section className="expedition-panel" aria-label="Open Poland expedition map">
    <div className="expedition-header">
      <div><span className="eyebrow">YOUR POLAND EXPEDITION</span>
        <h2>Explore Poland, together.</h2>
        <p>Every region is available from the start. Choose where your next completed lessons contribute XP.</p></div>
      <div className="expedition-stat"><strong>{unlocked.length} / 16</strong><span>Regions unlocked</span></div>
    </div>
    <div className="expedition-layout">
      <div className="poland-map" role="group" aria-label="Choose a Polish region from the map">
        <svg viewBox="0 0 585 555" role="img" aria-label="Clickable outline map of Poland showing sixteen regions" preserveAspectRatio="xMidYMid meet">
          {regions.map(region=><path key={region.id}
            d={region.path}
            className={'poland-region '+(unlocked.includes(region.id)?'unlocked ':'')+(region.id===state.selectedRegion?'chosen':'')}
            onClick={()=>select(region.id)}
            onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(region.id);}}}
            tabIndex={0} role="button" aria-label={region.name}
            aria-pressed={region.id===state.selectedRegion}>
            <title>{region.name}: {unlocked.includes(region.id)?'unlocked':(region.id===state.selectedRegion?'currently selected':'available to explore')}</title>
          </path>)}
        </svg>
        <div className="expedition-legend"><span><i className="legend-open"/>Unlocked</span><span><i className="legend-selected"/>Selected</span><span><i className="legend-locked"/>Available</span></div>
      </div>
      <div className="expedition-detail" aria-live="polite">
        <span className="eyebrow">SELECTED DESTINATION</span>
        <h3>{active.name}</h3>
        <p>{unlocked.includes(active.id)?'Region unlocked! Explore another destination to keep opening the map.':
          'Your completed learning activities now contribute toward opening this region.'}</p>
        <div className="expedition-progress">
          <div><strong>{Math.min(earned,goal)} / {goal} XP</strong><span>{Math.min(100,Math.round(100*earned/goal))}%</span></div>
          <div className="xp-track" role="progressbar" aria-label={active.name+' unlock progress'}
            aria-valuemin={0} aria-valuemax={goal} aria-valuenow={Math.min(earned,goal)}>
            <span style={{width:Math.min(100,100*earned/goal)+'%'}}/></div>
          <small>{state.regionGoals[active.id]?'Region target fixed when first XP was contributed':'Target is fixed once you contribute the first XP'}</small>
        </div>
        <label className="expedition-label" htmlFor="destination-select">Explore another region</label>
        <select id="destination-select" value={state.selectedRegion} onChange={e=>select(e.target.value)}>
          {regions.map(region=><option key={region.id} value={region.id}>{region.name}{unlocked.includes(region.id)?' ✓':''}</option>)}
        </select>
        <p className="expedition-local-note">Single-learner preview. Family membership, shared XP and leaderboards need secure accounts and sync; progress here is local to this browser.</p>
      </div>
    </div>
  </section>;
}
