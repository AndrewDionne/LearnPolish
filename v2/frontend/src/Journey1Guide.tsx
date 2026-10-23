import {useState} from 'react';
import type {Journey1GuideStep} from './journey1-guide';

/** A quiet source-backed guide, not another proficiency or stage label.
 * Only actual existing source lesson and tourist-unit launch actions are shown. */
export default function Journey1Guide({steps,onLesson,onUnit}:{
  steps:Journey1GuideStep[];
  onLesson:(lessonId:string)=>void;
  onUnit:(unitId:string)=>void;
}){
  const [expanded,setExpanded]=useState(false);
  if(!steps.length)return null;
  const visible=expanded?steps:steps.slice(0,4);
  return <section className="foundation-guide" aria-label="Guided Polish foundations">
    <div className="foundation-guide-top">
      <h3>Start with the essentials</h3>
      <button type="button" className="foundation-guide-expand"
        onClick={()=>setExpanded(x=>!x)}>
        {expanded?'Show less':'See all 20 steps'} →
      </button>
    </div>
    <div className="foundation-guide-list">
      {visible.map((step,index)=><button type="button" key={step.id}
        className="foundation-guide-step"
        onClick={()=>step.type==='foundation'?onLesson(step.lessonId):onUnit(step.unitId)}>
        <span className="foundation-guide-number" aria-hidden="true">
          {String(index+1).padStart(2,'0')}
        </span>
        <span className="foundation-guide-title">{step.title}</span>
        <span className="foundation-guide-arrow" aria-hidden="true">→</span>
      </button>)}
    </div>
  </section>;
}
