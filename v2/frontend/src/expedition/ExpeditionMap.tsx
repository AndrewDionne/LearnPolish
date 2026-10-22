import {useState} from 'react';
import regions from './regions.json';
import type {FamilySummary} from '../family/api';
import {chooseRegion, nextRegionCost, regionTotal, unlockedRegions} from './expedition';
import type {ExpeditionState} from './expedition';

type Props={state:ExpeditionState;onChange:(value:ExpeditionState)=>void;shared?:FamilySummary|null};

export default function ExpeditionMap({state,onChange,shared}:Props){
  const [view,setView]=useState<'mine'|'family'>('family');
  const usingFamily=!!shared&&view==='family';
  const memberRegion=shared?.regions.find(x=>x.region===state.selectedRegion);
  const unlocked=usingFamily
    ? shared.regions.filter(x=>x.unlocked).map(x=>x.region)
    : unlockedRegions(state);
  const goal=usingFamily
    ? memberRegion?.target??Math.round(300*Math.pow(1+.22*(shared?.regions.length??0),1.35)/10)*10
    : state.regionGoals[state.selectedRegion]??nextRegionCost(state);
  const earned=usingFamily ? memberRegion?.earned??0 : regionTotal(state,state.selectedRegion);
  const active=regions.find(x=>x.id===state.selectedRegion)!;
  const select=(id:string)=>onChange(chooseRegion(state,id));
  return <section className="expedition-panel" aria-label="Open Poland expedition map">
    <div className="expedition-header">
      <div><span className="eyebrow">{usingFamily?'FAMILY POLAND MAP':'YOUR POLAND EXPEDITION'}</span>
        <h2>Explore Poland, together.</h2>
        <p>Every region is available from the start. Choose where your next completed lessons contribute XP.</p>
        {shared&&<div className="expedition-view-toggle" role="group" aria-label="Map progress view">
          <button type="button" aria-pressed={!usingFamily} onClick={()=>setView('mine')}>My Map</button>
          <button type="button" aria-pressed={usingFamily} onClick={()=>setView('family')}>Family Map</button>
        </div>}</div>
      <div className="expedition-stat"><strong>{unlocked.length} / 16</strong><span>Regions unlocked</span></div>
    </div>
    <div className="expedition-layout">
      <div className="poland-map" role="group" aria-label="Choose a Polish region from the map">
        <svg viewBox="0 0 585 555" role="group" aria-label="Clickable outline map of Poland showing sixteen regions" preserveAspectRatio="xMidYMid meet">
          {regions.map(region=><path key={region.id}
            d={region.path}
            className={'poland-region '+(unlocked.includes(region.id)?'unlocked ':'')+(region.id===state.selectedRegion?'chosen':'')}
            onClick={()=>select(region.id)}
            onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(region.id);}}}
            tabIndex={0} role="button" aria-label={region.name}
            aria-pressed={region.id===state.selectedRegion}>
            <title>{region.name}</title>
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
          <small>{usingFamily ? (memberRegion?'Family region target is fixed.':'Family target will freeze when the first team XP is contributed.')
              : (state.regionGoals[active.id]?'Personal region target fixed on first XP.':'Personal target will freeze on first XP.')}</small>
        </div>
        <label className="expedition-label" htmlFor="destination-select">Explore another region</label>
        <select id="destination-select" value={state.selectedRegion} onChange={e=>select(e.target.value)}>
          {regions.map(region=><option key={region.id} value={region.id}>{region.name}{unlocked.includes(region.id)?' ✓':''}</option>)}
        </select>
        <p className="expedition-local-note">{usingFamily
          ? 'Family map uses verified server ledger totals. Each learner can select a different region. New eligible practice is shared only after opting in.'
          : 'Your personal XP and map are saved locally on this device. Family results stay separate.'}</p>
      </div>
    </div>
  </section>;
}
