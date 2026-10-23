import {describe,expect,test} from 'vitest';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import JourneyMarker from './JourneyMarker';
import type {Journey,JourneyPosition} from './core-journey';

describe('A-01 decorative 3 × 3 lesson signals',()=>{
  test('all nine combinations have shape plus colour class but no accessible narration',()=>{
    const shapes:JourneyPosition[]=['beginning','middle','end'];
    for(const journey of [1,2,3] as Journey[])for(const position of shapes){
      const html=renderToStaticMarkup(createElement(JourneyMarker,{
        placement:{lessonId:'sample',journey,position,order:1}
      }));
      expect(html).toContain('journey-'+journey);
      expect(html).toContain('aria-hidden="true"');
      expect(html).toContain('focusable="false"');
      expect(html).not.toMatch(/title=|aria-label=|role="tooltip"|tabindex|<title>/i);
      expect(html).not.toMatch(/journey\s*[123]|beginning|middle|end|tier/i);
      expect(html.match(/<circle /g)?.length).toBe(position==='middle'?2:1);
      expect(html.includes('<path ')).toBe(position==='end');
    }
  });
});
