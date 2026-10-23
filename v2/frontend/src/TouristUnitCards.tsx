import type {TouristUnit} from './tourist-units';

const modeText=(mode:'listen'|'speak'|'read')=>mode==='listen'?'Listen':mode==='speak'?'Speak':'Read';

/** Source-linked actions: no nine-tier explanation and no inference of mastery. */
export default function TouristUnitCards({units,onStart}:{
  units:TouristUnit[];
  onStart:(unitId:string,stepIndex:number)=>void;
}){
  if(!units.length)return null;
  return <div className="tourist-unit-grid" aria-label="Conversation practice">
    {units.map(unit=><section className="tourist-unit-card" key={unit.id}>
      <strong>{unit.title}</strong>
      <div className="tourist-unit-actions">
        {unit.steps.map((step,index)=><button type="button"
          key={step.mode} onClick={()=>onStart(unit.id,index)}
          aria-label={unit.title+': '+modeText(step.mode)}>{modeText(step.mode)}</button>)}
      </div>
    </section>)}
  </div>;
}
