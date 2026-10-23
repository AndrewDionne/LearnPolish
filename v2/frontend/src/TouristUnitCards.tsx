import type {TouristUnit} from './tourist-units';
import {resumeTouristUnit,unitActivityCounts} from './tourist-activity';
import type {TouristActivities} from './tourist-activity';

const modeText=(mode:'listen'|'speak'|'read')=>mode==='listen'?'Listen':mode==='speak'?'Speak':'Read';

/** Show factual mode-level attempt evidence, never mastery or nine-tier labels.
 * Explicit Listen/Speak/Read actions always start fresh; Resume is opt-in.
 */
export default function TouristUnitCards({units,activity,onStart}:{
  units:TouristUnit[];
  activity:TouristActivities;
  onStart:(unitId:string,stepIndex:number,resumeItemId?:string)=>void;
}){
  if(!units.length)return null;
  return <div className="tourist-unit-grid" role="group" aria-label="Conversation practice">
    {units.map(unit=>{
      const counts=unitActivityCounts(activity,unit);
      const resume=resumeTouristUnit(activity,unit);
      return <section className="tourist-unit-card" key={unit.id}>
        <strong>{unit.title}</strong>
        {activity.units[unit.id] && <small className="tourist-unit-activity">{counts.tried} / {counts.total} tried</small>}
        <div className="tourist-unit-actions">
          {unit.steps.map((step,index)=><button type="button"
            key={step.mode} onClick={()=>onStart(unit.id,index)}
            aria-label={unit.title+': '+modeText(step.mode)}>{modeText(step.mode)}</button>)}
        </div>
        {resume && <button type="button" className="tourist-unit-resume"
          onClick={()=>onStart(unit.id,resume.stepIndex,unit.steps[resume.stepIndex].itemIds[resume.itemIndex])}
          aria-label={'Resume '+unit.title}>Resume →</button>}
      </section>;
    })}
  </div>;
}
