import assert from 'node:assert/strict';
import { test } from 'node:test';
import { shellResources } from './build-offline.mjs';

test('precache excludes lesson MP3s but includes main bundle and manifest', () => {
  const resources = shellResources();
  assert.ok(resources.includes('./'));
  assert.ok(resources.includes('generated/lessons.json'));
  assert.ok(resources.some(item => item.endsWith('.js')));
  assert.ok(!resources.some(item => item.endsWith('.mp3')));
  assert.ok(resources.includes('avatars/hero-neutral.svg'));
  assert.ok(resources.includes('avatars/chonky-win.svg'));
});

import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

// Exercise the real service-worker message handler without touching the network
// or a physical browser. A quota error is injected specifically during promotion
// from the temporary staging cache into persistent lesson audio.
test('offline worker rolls back half-committed lesson downloads and can retry',async()=>{
  const source=readFileSync(new URL('./sw-template.js',import.meta.url),'utf8')
    .replace('/*__APP_CACHE_VERSION__*/',JSON.stringify('test'))
    .replace('/*__PRECACHE_RESOURCES__*/','[]');
  const listeners=new Map();
  const stores=new Map();
  let failPromotion=true;
  const existing={tag:'previous-good-audio'};
  function open(name){
    if(!stores.has(name))stores.set(name,new Map());
    const files=stores.get(name);
    return {
      match:async key=>files.get(key),
      put:async(key,value)=>{
        if(name==='ptp-v2-lesson-audio-v1'&&key.endsWith('/1.mp3')&&failPromotion){
          failPromotion=false;throw new Error('QuotaExceededError');
        }
        files.set(key,value);
      },
      delete:async key=>files.delete(key),
    };
  }
  const scope='https://example.test/app/';
  const urls=['generated/audio/sample/0.mp3','generated/audio/sample/1.mp3'];
  const absolute=urls.map(u=>new URL(u,scope).href);
  stores.set('ptp-v2-lesson-audio-v1',new Map([[absolute[0],existing]]));
  const sw={
    registration:{scope},addEventListener:(name,fn)=>listeners.set(name,fn),
  };
  runInNewContext(source,{
    self:sw,caches:{open:async name=>open(name),delete:async name=>stores.delete(name)},
    fetch:async url=>({ok:true,headers:{get:()=> 'audio/mpeg'},tag:'new-'+url}),
    URL,Map,Set,Math,Date,Error,
  });
  async function request(type){
    const messages=[];
    let work;
    listeners.get('message')({
      data:{type,urls},ports:[{postMessage:message=>messages.push(message)}],
      waitUntil:promise=>{work=promise;},
    });
    await work;
    return messages;
  }
  const attempt=await request('DOWNLOAD');
  assert.equal(attempt.at(-1).type,'error');
  assert.equal((await open('ptp-v2-lesson-audio-v1').match(absolute[0])).tag,existing.tag);
  assert.equal(await open('ptp-v2-lesson-audio-v1').match(absolute[1]),undefined);
  assert.equal((await request('STATUS')).at(-1).ready,false);
  assert.equal((await request('STATUS')).at(-1).done,1);
  const retry=await request('DOWNLOAD');
  assert.deepEqual(JSON.parse(JSON.stringify(retry.at(-1))),{type:'done',ready:true,done:2,total:2});
  assert.equal((await request('STATUS')).at(-1).ready,true);
  assert.equal([...stores.keys()].some(name=>name.startsWith('ptp-v2-temporary-')),false);
});
