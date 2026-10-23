// Consistent, lightweight in-app navigation artwork. No icon font or emoji rendering.
export type UIIconName='home'|'library'|'practice'|'expedition'|'profile'|'reading'|'sounds';
export default function UIIcon({name,size=22}:{name:UIIconName;size?:number}){
  const mark={
    home:<><path d="m3.5 10 8.5-7 8.5 7"/><path d="M5.5 9.5V20h13V9.5M10 20v-6h4v6"/></>,
    library:<><rect x="3.5" y="4" width="7" height="7" rx="1.5"/><rect x="13.5" y="4" width="7" height="7" rx="1.5"/><rect x="3.5" y="14" width="7" height="6" rx="1.5"/><rect x="13.5" y="14" width="7" height="6" rx="1.5"/></>,
    practice:<><path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5A8.5 8.5 0 0 0 12 3.5Z"/><path d="m8 12 2.6 2.6 5.5-5.5"/></>,
    expedition:<><path d="m3 6 6-2 6 2 6-2v14l-6 2-6-2-6 2Z"/><path d="M9 4v14m6-12v14"/><circle cx="12" cy="10" r="1.2" fill="currentColor" stroke="none"/></>,
    profile:<><circle cx="12" cy="8" r="3.5"/><path d="M4.8 20a7.2 7.2 0 0 1 14.4 0"/></>,
    reading:<><path d="M12 6c-2.5-1.7-5.7-2-9-1v13c3.4-1 6.5-.6 9 1 2.5-1.6 5.6-2 9-1V5c-3.3-1-6.5-.7-9 1Z"/><path d="M12 6v13"/></>,
    sounds:<><path d="M4 10v4h4l5 4V6l-5 4H4Z"/><path d="M16 9a4 4 0 0 1 0 6M18 6a8 8 0 0 1 0 12"/></>,
  }[name];
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true" focusable="false">{mark}</svg>;
}
