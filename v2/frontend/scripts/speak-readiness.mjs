/** Read-only, deterministic audit of the ACTUAL generated V2 lesson catalog.
 *
 * Usage from repo root:
 *   cd v2/frontend && npm run content && npm run audit:speak
 *
 * Never enables AI inference or calls providers. It distinguishes
 * - a Speak tab from one that does not exist on reading lessons;
 * - draft text groupings from genuinely reviewed pronunciation;
 * - reference text that the current backend proxy cannot compare;
 * - unfinished sample utterances (ellipsis).
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const catalog=path.resolve(here,'../public/generated/lessons.json');
const BACKEND_STRIPPABLE=/[\s.,!?;:()\-’'„”“"…]/gu;
const BACKEND_LETTERS=/^[a-ząćęłńóśźż]+$/u;
const PLACEHOLDER=/…|\.{3,}/u;

export function inspectSpeakCatalog(manifest){
  if(!manifest || manifest.schemaVersion!==1 || !Array.isArray(manifest.lessons)){
    throw new Error('Missing built V2 learning catalog');
  }
  const modules=[];
  let items=0,spokenItems=0,readingItems=0,audio=0;
  let drafts=0,editorial=0,authored=0,unsupported=0,unfinished=0;
  for(const lesson of manifest.lessons){
    if(!lesson || typeof lesson.id!=='string' || !['vocabulary','sounds','reading'].includes(lesson.kind) ||
       !Array.isArray(lesson.items)||!lesson.items.length){
      throw new Error('Unexpected learning module in Speak audit');
    }
    const entry={id:lesson.id,title:lesson.title,kind:lesson.kind,
      speakAvailable:lesson.kind!=='reading',
      items:lesson.items.length,withAudio:0,
      authored:0,editorial:0,autoDraft:0,legacyEnglishCues:0,
      blockedReferences:[],unfinishedReferences:[]};
    for(const item of lesson.items){
      if(typeof item.polish!=='string')throw new Error('Missing Polish target in '+lesson.id);
      const source=item.polish.trim();
      const parts=item.pronunciationSegments;
      if(!parts || !Array.isArray(parts.segments) ||
         parts.segments.join('')!==item.polish){
        throw new Error('Missing exact-match source grouping in '+lesson.id);
      }
      if(item.audio){entry.withAudio++;audio++;}
      if(item.pronunciationGuide || item.pronunciation)entry.legacyEnglishCues++;
      if(parts.method==='authored-v1'){entry.authored++;authored++;}
      else if(parts.method==='editorial-draft-v1'){entry.editorial++;editorial++;}
      else if(parts.method==='draft-orthographic-v1'){entry.autoDraft++;drafts++;}
      else throw new Error('Unexpected group provenance in '+lesson.id);
      const normalized=source.toLowerCase().replace(BACKEND_STRIPPABLE,'');
      if(!BACKEND_LETTERS.test(normalized)){
        entry.blockedReferences.push({itemId:item.id,polish:item.polish});
        unsupported++;
      }
      if(PLACEHOLDER.test(source)){
        entry.unfinishedReferences.push({itemId:item.id,polish:item.polish});
        unfinished++;
      }
    }
    items+=entry.items;
    if(entry.speakAvailable)spokenItems+=entry.items;else readingItems+=entry.items;
    modules.push(entry);
  }
  return {schemaVersion:1,
    summary:{modules:modules.length,speakModules:modules.filter(m=>m.speakAvailable).length,
      readingModules:modules.filter(m=>!m.speakAvailable).length,
      items,spokenItems,readingItems,withAudio:audio,authored,
      editorial,autoDraft:drafts,blockedReferences:unsupported,
      unfinishedReferences:unfinished,
      publicDualProviderEnabled:false},
    modules};
}

export function printAuditMarkdown(result){
  const head='| Learning module | Mode | Items | Audio | Authored | Editorial draft | Auto draft | Blocked references | Unfinished targets |';
  const sep='|---|---|---:|---:|---:|---:|---:|---:|---:|';
  const rows=result.modules.map(m=>[m.title,m.speakAvailable?'Speak':'Read only',m.items,m.withAudio,
    m.authored,m.editorial,m.autoDraft,m.blockedReferences.length,m.unfinishedReferences.length]
    .map(x=>String(x).replaceAll('|','/')).join(' | '));
  return [head,sep,...rows.map(r=>'| '+r+' |')].join('\n');
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const arg=process.argv[2];
  if(arg && arg!=='--markdown' && arg!=='--json')throw new Error('Use --markdown or --json');
  const report=inspectSpeakCatalog(JSON.parse(fs.readFileSync(catalog,'utf8')));
  process.stdout.write(arg==='--markdown'
    ? printAuditMarkdown(report)+'\n'
    : JSON.stringify(report,null,2)+'\n');
}
