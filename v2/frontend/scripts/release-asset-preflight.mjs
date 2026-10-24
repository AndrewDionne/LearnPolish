import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';

/** Read-only, offline artifact verification. Never contacts Render, providers,
 * Neon, family servers or browsers, and never reads private environment keys. */
const home=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BAD=message=>{throw new Error('V2 artifact preflight: '+message)};
const isRecord=v=>!!v&&typeof v==='object'&&!Array.isArray(v);

function localAsset(base,relative){
 if(typeof relative!=='string'||!relative||
    relative.startsWith('/')||relative.includes('\\')||
    relative.includes('?')||relative.includes('#')||
    relative.split('/').some(x=>!x||x==='.'||x==='..'))BAD('invalid local asset path');
 const root=path.resolve(base),filename=path.resolve(root,relative);
 if(!filename.startsWith(root+path.sep))BAD('asset escapes dist');
 try{
  const stat=fs.lstatSync(filename);
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size===0)BAD('asset missing, empty or symlinked: '+relative);
 }catch(e){
  if(e?.message?.startsWith('V2 artifact preflight:'))throw e;
  BAD('asset missing, empty or symlinked: '+relative);
 }
 return filename;
}
function entrypointAssets(html){
 // Vite rewrites its source /src/main.tsx to a fingerprinted /assets/*.js.
 // The release must not accidentally serve the unbuilt development HTML.
 const tags=[...html.matchAll(/<(?:script|link)\b[^>]*>/gi)].map(x=>x[0]);
 const get=(tag,key)=>tag.match(new RegExp('\\b'+key+'\\s*=\\s*(["\\x27])([^"\\x27]*)\\1','i'))?.[2]??'';
 const refs=[];
 for(const tag of tags){
  const isScript=/^<script\b/i.test(tag);
  const isSheet=/^<link\b/i.test(tag)&&get(tag,'rel').split(/\s+/).includes('stylesheet');
  if(!isScript&&!isSheet)continue;
  const url=get(tag,isScript?'src':'href');
  // Google Fonts remain external and are not part of our built asset contract.
  if(!url||/^https:\/\//.test(url))continue;
  const relative=url.replace(/^\.?\//,'');
  if(!/^assets\/[^?#]+\.(?:js|css)$/.test(relative))BAD('unexpected local built entrypoint: '+url);
  refs.push({path:relative,script:isScript});
 }
 if(!refs.some(x=>x.script)||html.includes('/src/main.tsx'))BAD('built JavaScript entrypoint absent');
 return refs;
}
export function auditProductionArtifact(dist=path.join(home,'dist'),{canonical=true}={}){
 const root=path.resolve(dist);
 const html=fs.readFileSync(localAsset(root,'index.html'),'utf8');
 if(!html.includes('id="root"'))BAD('React root absent');
 const entrypoints=entrypointAssets(html);
 for(const item of entrypoints)localAsset(root,item.path);

 const sw=fs.readFileSync(localAsset(root,'sw.js'),'utf8');
 const match=sw.match(/const PRECACHE = (\[[^\n;]+\]);/);
 if(!match)BAD('generated offline shell list absent');
 let precache;
 try{precache=JSON.parse(match[1]);}catch{BAD('offline shell list is not JSON');}
 if(!Array.isArray(precache)||new Set(precache).size!==precache.length||
    !precache.includes('index.html')||!precache.includes('generated/lessons.json')||
    !precache.includes('./'))BAD('offline precache incomplete or duplicated');
 for(const resource of precache){
  if(resource==='./')continue;
  localAsset(root,resource);
 }
 for(const entry of entrypoints)if(!precache.includes(entry.path))
  BAD('entrypoint omitted from offline shell: '+entry.path);

 let catalog;
 try{catalog=JSON.parse(fs.readFileSync(localAsset(root,'generated/lessons.json'),'utf8'));}
 catch(e){if(e?.message?.startsWith('V2 artifact preflight:'))throw e;BAD('lesson catalog invalid JSON');}
 if(!isRecord(catalog)||catalog.schemaVersion!==1||!Array.isArray(catalog.lessons))
  BAD('invalid canonical lesson catalog');
 const lessonIds=new Set(),itemIds=new Set(),audio=new Set();
 for(const lesson of catalog.lessons){
  if(!isRecord(lesson)||typeof lesson.id!=='string'||!lesson.id||
     lessonIds.has(lesson.id)||!Array.isArray(lesson.items)||!lesson.items.length)
    BAD('missing, duplicate or empty lesson');
  lessonIds.add(lesson.id);
  for(const item of lesson.items){
   if(!isRecord(item)||typeof item.id!=='string'||itemIds.has(item.id)||
     !item.id||typeof item.polish!=='string'||!item.polish.trim()||
     typeof item.english!=='string'||!item.english.trim())BAD('invalid or duplicate catalog item');
   itemIds.add(item.id);
   if(item.audio!==undefined){
    if(typeof item.audio!=='string'||
       !/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(item.audio))
      BAD('untrusted bundled audio reference');
    audio.add(item.audio);
   }
  }
 }
 for(const p of audio)localAsset(root,p);
 if(canonical&&(lessonIds.size!==26||audio.size<400))
  BAD('canonical lesson or full recording inventory unexpectedly reduced');
 return Object.freeze({
  artifact:'path-to-polish-v2',status:'local_artifact_verified_not_live_or_physical',
  lessonCount:lessonIds.size,itemCount:itemIds.size,distinctAudioFiles:audio.size,
  entrypointCount:entrypoints.length,precacheCount:precache.length,
  familyAccountSignoff:false,physicalSafariSignoff:false,pronunciationAccuracySignoff:false
 });
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const index=process.argv.indexOf('--dist');
 if(index>=0&&(!process.argv[index+1]||index+2!==process.argv.length))BAD('expected --dist <directory>');
 console.log(JSON.stringify(auditProductionArtifact(index<0?undefined:process.argv[index+1])));
}
