import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe,expect,it} from 'vitest';

// Review-only SVG assets live outside the shipped frontend.
const review=(name:string)=>readFileSync(
  fileURLToPath(new URL('../../brand-review/geometric-p/'+name,import.meta.url)),'utf8');

describe('UX-05B editable geometric brand candidates',()=>{
  it('keeps the primary wordmark immediately beside the P bowl',()=>{
    const svg=review('path-to-polish-signature.svg');
    const wordX=Number(svg.match(/<text x="(\d+)"/)?.[1]);
    const bodyMaxX=507*.63+15;
    expect(wordX-bodyMaxX).toBeGreaterThan(10);
    expect(wordX-bodyMaxX).toBeLessThan(25);
    expect(svg).toContain('>Path to Polish</text>');
    expect(svg).toContain('H2140 V560'); // The P and long baseline stay connected.
    expect(svg).toContain('<circle cx="1403" cy="312" r="19" fill="#56CFAE"/>');
  });

  it('balances all four square-icon optical margins to 35/256',()=>{
    const svg=review('path-to-polish-square.svg');
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

  it('exposes real review SVGs at both sizes without changing runtime branding',()=>{
    const html=review('index.html');
    expect(html).toContain('src="./path-to-polish-signature.svg"');
    expect(html).toContain('src="./path-to-polish-square.svg"');
    for(const size of [16,24,32,48,72]){
      expect(html).toContain('width="'+size+'" height="'+size+'"');
    }
    expect(html).toMatch(/not yet deployed/i);
  });
});
