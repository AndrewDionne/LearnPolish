/** Suppress duplicate activations of the same rendered lesson step.
 * The caller resets the step at navigation boundaries, so intentionally
 * repeating a card in a new session is never prohibited.
 */
export type CompletionGuard={step:string|null};

export function claimCompletion(guard:CompletionGuard,step:string):boolean{
  if(!step || guard.step===step)return false;
  guard.step=step;
  return true;
}
