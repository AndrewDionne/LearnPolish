/**
 * Approved UX-05B geometric P: the same viewBox, silhouette and terminal
 * geometry as the canonical square icon in v2/brand-review/geometric-p/.
 * The icon is decorative beside the existing, accessible wordmark.
 */
export default function BrandMark({size=52}:{size?:number}){
  return <svg className="brand-mark" width={size} height={size}
    viewBox="0 0 256 256" fill="none" aria-hidden="true" focusable="false">
    <rect width="256" height="256" rx="51" fill="#143E55"/>
    <path fill="#FFFFFF" fillRule="evenodd"
      d="M55 35 H129 C178 35 218 62 218 100 C218 146 179 164 127 164 H88 V197 H185 V221 H55 V164 H35 V139 H55 Z M88 62 V139 H124 C165 139 185 128 185 101 C185 75 166 62 124 62 Z"/>
    <circle cx="209" cy="209" r="12" fill="#72D5BB"/>
  </svg>;
}
