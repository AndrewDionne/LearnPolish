/**
 * Path to Polish identity: a lowercase p and a restrained two-stop learning route.
 * The route replaces the old typographic dot. Shared geometry with public/brand-mark.svg.
 * Pure vector: no icon font, emoji, or network dependency.
 */
export default function BrandMark({size=52}:{size?:number}){
  return <svg className="brand-mark" width={size} height={size} viewBox="0 0 64 64"
    fill="none" aria-hidden="true" focusable="false">
    <g stroke="currentColor" strokeWidth="7.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 16v38"/>
      <path d="M17 20C23 11 36 11 42 17c7 7 6 17-1 22-7 5-19 3-24-5"/>
    </g>
    <path d="M40 52c5-7 8 1 13-8 1.7-3.1 3.5-3.1 5-3.5"
      stroke="var(--brand-route, #7fddc5)" strokeWidth="3.2" strokeLinecap="round"/>
    <circle cx="40" cy="52" r="2.7" fill="var(--brand-route, #7fddc5)"/>
    <circle cx="58" cy="40.5" r="2.7" fill="var(--brand-route, #7fddc5)"/>
  </svg>;
}
