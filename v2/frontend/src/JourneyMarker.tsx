import type {JourneyPlacement} from './core-journey';

/** Deliberately decorative: titles and actions already communicate the lesson.
 * No tooltip, aria label, keyboard target, spoken tier, or nine-level legend.
 */
export default function JourneyMarker({placement}:{placement:JourneyPlacement}){
  return <span className={'journey-marker journey-'+placement.journey} aria-hidden="true">
    <svg viewBox="0 0 24 24" width="18" height="18" focusable="false" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {placement.position==='beginning'
        ? <circle cx="12" cy="12" r="8"/>
        : placement.position==='middle'
          ? <><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/></>
          : <><circle cx="12" cy="12" r="8"/><path d="m8 12 2.5 2.5L16 9"/></>}
    </svg>
  </span>;
}
