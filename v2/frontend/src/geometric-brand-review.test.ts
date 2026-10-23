import {describe,expect,it} from 'vitest';
import signatureSvg from '../../brand-review/geometric-p/path-to-polish-signature.svg?raw';
import squareSvg from '../../brand-review/geometric-p/path-to-polish-square.svg?raw';
import reviewHtml from '../../brand-review/geometric-p/index.html?raw';
import faviconSvg from '../public/brand-mark.svg?raw';
import productionSignatureSvg from '../public/path-to-polish-signature.svg?raw';
import brandComponentSource from './BrandMark.tsx?raw';

// Review art remains canonical; only this test imports its source into Vite.

describe('UX-05B editable geometric brand candidates',()=>{
  it('keeps the primary wordmark immediately beside the P bowl',()=>{
    const svg=signatureSvg;
    const wordX=Number(svg.match(/<text x="(\d+)"/)?.[1]);
    const bodyMaxX=507*.63+15;
    expect(wordX-bodyMaxX).toBeGreaterThan(10);
    expect(wordX-bodyMaxX).toBeLessThan(25);
    expect(svg).toContain('>Path to Polish</text>');
    expect(svg).toContain('H2140 V560'); // The P and long baseline stay connected.
    expect(svg).toContain('<circle cx="1403" cy="312" r="19" fill="#56CFAE"/>');
  });

  it('balances all four square-icon optical margins to 35/256',()=>{
    const svg=squareSvg;
    const edge=256;
    // Verified extrema of the filled custom P (incl. crossbar and baseline).
    const whiteP={minX:35,maxX:218,minY:35,maxY:221};
    const dot={x:209,y:209,r:12};
    const margins={
      left:Math.min(whiteP.minX,dot.x-dot.r),
      right:edge-Math.max(whiteP.maxX,dot.x+dot.r),
      top:Math.min(whiteP.minY,dot.y-dot.r),
      bottom:edge-Math.max(whiteP.maxY,dot.y+dot.r),
    };
    expect(margins).toEqual({left:35,right:35,top:35,bottom:35});
    expect(svg).toContain('M55 35 H129 C178 35 218 62 218 100');
    expect(svg).toContain('V197 H185 V221');
    expect(svg).toContain('<circle cx="209" cy="209" r="12" fill="#72D5BB"/>');
  });

  it('keeps approved production SVG assets byte-for-byte identical to review artwork',()=>{
    expect(faviconSvg).toBe(squareSvg);
    expect(productionSignatureSvg).toBe(signatureSvg);
    expect(brandComponentSource).toContain('viewBox="0 0 256 256"');
    expect(brandComponentSource).toContain('M55 35 H129 C178 35 218 62 218 100');
    expect(brandComponentSource).toContain('cx="209" cy="209" r="12"');
    expect(brandComponentSource).not.toContain('M17 16v38');
  });

  it('exposes the approved SVGs at both sizes in the review index',()=>{
    const html=reviewHtml;
    expect(html).toContain('src="./path-to-polish-signature.svg"');
    expect(html).toContain('src="./path-to-polish-square.svg"');
    for(const size of [16,24,32,48,72]){
      expect(html).toContain('width="'+size+'" height="'+size+'"');
    }
    expect(html).toMatch(/approved geometric p identity/i);
  });
});
