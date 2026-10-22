import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

test('failed audio removal rolls back both cached responses; retry succeeds',async()=>{
  const source=readFileSync(new URL('./sw-template.js',import.meta.url),'utf8')
    .replace('/*__APP_CACHE_VERSION__*/',JSON.stringify('remove-test'))
    .replace('/*__PRECACHE_RESOURCES__*/','[]');
  const scope='https://offline.example/app/';
  const urls=['generated/audio/sample/0.mp3','generated/audio/sample/1.mp3'];
  const absolute=urls.map(u=>new URL(u,scope).href);
  const initial=[{label:'old-audio-0'},{label:'old-audio-1'}];
  const entries=new Map([[absolute[0],initial[0]],[absolute[1],initial[1]]]);
  let failSecond=true;
  const cache={
    match:async key=>entries.get(key),
    put:async(key,value)=>{entries.set(key,value);},
    delete:async key=>{
      if(key===absolute[1]&&failSecond){failSecond=false;throw new Error('QuotaExceededError');}
      return entries.delete(key);
    },
  };
  const listeners=new Map();
  runInNewContext(source,{
    self:{registration:{scope},addEventListener:(name,listener)=>listeners.set(name,listener)},
    caches:{open:async()=>cache},
    URL,Map,Set,Date,Math,Error,
  });

  async function send(type){
    let lifetime;
    const messages=[];
    listeners.get('message')({
      data:{type,urls},ports:[{postMessage:message=>messages.push(message)}],
      waitUntil:promise=>{lifetime=promise;},
    });
    await lifetime;
    return messages.at(-1);
  }
  assert.equal((await send('STATUS')).ready,true);
  assert.equal((await send('REMOVE')).type,'error');
  assert.equal(entries.get(absolute[0]),initial[0]);
  assert.equal(entries.get(absolute[1]),initial[1]);
  assert.equal((await send('STATUS')).ready,true);
  assert.deepEqual(JSON.parse(JSON.stringify(await send('REMOVE'))),
    {type:'done',ready:false,done:0,total:2});
  assert.equal(entries.size,0);
  assert.equal((await send('STATUS')).ready,false);
});
