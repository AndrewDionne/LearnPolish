import {describe,expect,test} from 'vitest';
import {claimCompletion} from './completion-guard';

describe('per-view completion idempotency',()=>{
  test('only the first activation may record a visible answer',()=>{
    const state={step:null as string|null};
    expect(claimCompletion(state,'lesson|learn|0|0|item1')).toBe(true);
    expect(claimCompletion(state,'lesson|learn|0|0|item1')).toBe(false);
    expect(claimCompletion(state,'lesson|learn|0|0|item1')).toBe(false);
  });
  test('navigating to another item, mode, or session permits new practice',()=>{
    const state={step:null as string|null};
    expect(claimCompletion(state,'lesson|learn|0|0|item1')).toBe(true);
    expect(claimCompletion(state,'lesson|learn|0|1|item2')).toBe(true);
    expect(claimCompletion(state,'lesson|read|0|0|item1')).toBe(true);
    state.step=null; // React navigation effect after leaving/reopening a step
    expect(claimCompletion(state,'lesson|learn|0|0|item1')).toBe(true);
  });
});
