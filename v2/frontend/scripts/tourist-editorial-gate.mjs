/**
 * B-03 draft-content identity gate. This packet is editorial planning only.
 * It must never be imported by the learner app or confer recording approval.
 */
import {readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const here=dirname(fileURLToPath(import.meta.url));
const repoRoot=resolve(here,'../../..');
const json=(path)=>JSON.parse(readFileSync(path,'utf8'));
const own=(value,key)=>Object.prototype.hasOwnProperty.call(value,key);
const checkKeys=(value,keys,label)=>{
  if(!value||typeof value!=='object'||Array.isArray(value)||
      Object.keys(value).sort().join('|')!==[...keys].sort().join('|'))
    throw new Error('Unexpected '+label+' fields');
};
const requireText=(value,label)=>{
  if(typeof value!=='string'||!value.trim())throw new Error('Missing '+label);
};

export function validateTouristEditorialPacket(packet,sources,protectedIds,touristManifest){
  checkKeys(packet,['schemaVersion','reviewStatus','published','scope','workItems'],'packet');
  if(packet.schemaVersion!==1||packet.reviewStatus!=='editorial_draft_not_for_runtime'||
      packet.published!==false||JSON.stringify(packet.scope)!=='["T02","T03"]'||
      !Array.isArray(packet.workItems)||packet.workItems.length!==2)
    throw new Error('B-03 draft packet cannot be published or re-scoped');
  // B-03 protects the original T01–T03 editorial baseline even when more
  // source-only tourist units are appended. Do not freeze the entire catalogue
  // at three and accidentally block legitimate T04–T06 source extensions.
  if(!touristManifest||touristManifest.schemaVersion!==1||
      touristManifest.editorialStatus!=='source_refs_only_native_review_pending'||
      !Array.isArray(touristManifest.units)||touristManifest.units.length<3||
      touristManifest.units.slice(0,3).some((unit,index)=>
        unit.id!==['T01','T02','T03'][index]||
        unit.journey!==1||unit.position!=='beginning'||unit.order!==index+1))
    throw new Error('Tourist pilot baseline changed');

  const seen=new Set();
  let anchorCount=0;
  packet.workItems.forEach((work,index)=>{
    checkKeys(work,['unitId','gap','reviewStatus','sourceAnchors','requiredOutputs'],'work item');
    const expectedId=['T02','T03'][index];
    if(work.unitId!==expectedId||work.reviewStatus!=='pending_native_polish_and_audio_review')
      throw new Error('Unapproved '+expectedId+' status or order');
    requireText(work.gap,'editorial gap');
    if(!Array.isArray(work.requiredOutputs)||work.requiredOutputs.length<4||
        work.requiredOutputs.some(x=>typeof x!=='string'||x.trim().length<30))
      throw new Error('Missing reviewer deliverables for '+expectedId);
    if(!Array.isArray(work.sourceAnchors)||work.sourceAnchors.length!==3)
      throw new Error('Unexpected anchor inventory for '+expectedId);
    const unit=touristManifest.units.find(x=>x.id===expectedId);
    if(!unit)throw new Error('Unit missing from live pilot: '+expectedId);
    for(const anchor of work.sourceAnchors){
      checkKeys(anchor,['itemId','polish','english','expectedUse'],'anchor');
      requireText(anchor.itemId,'original item ID');
      requireText(anchor.polish,'original Polish');
      requireText(anchor.english,'original English');
      if(seen.has(anchor.itemId))throw new Error('Duplicate source anchor');
      seen.add(anchor.itemId);
      const separator=anchor.itemId.lastIndexOf(':');
      const lessonId=anchor.itemId.slice(0,separator);
      const itemIndex=Number(anchor.itemId.slice(separator+1));
      if(separator<1||!/^\d+$/.test(anchor.itemId.slice(separator+1))||
          !Number.isSafeInteger(itemIndex))throw new Error('Invalid source item ID');
      const source=sources[lessonId];
      const rows=source&&(Array.isArray(source.cards)?source.cards:source.passages);
      const row=rows?.[itemIndex];
      if(!row)throw new Error('Original source missing: '+anchor.itemId);
      if((row.phrase??row.polish)!==anchor.polish||
         (row.meaning??row.english)!==anchor.english)
        throw new Error('Source transcript drift: '+anchor.itemId);
      const use=protectedIds.has(anchor.itemId)?'protected_source_reference':'source_context';
      if(anchor.expectedUse!==use)throw new Error('Protected reference classification drift: '+anchor.itemId);
      anchorCount++;
    }
    if(expectedId==='T02'){
      if(!seen.has('Conversation_1:25')||
          unit.steps.some(s=>s.mode==='speak'&&s.itemIds.includes('Conversation_1:25')))
        throw new Error('T02 incomplete source must stay out of Speak unit');
    }else if(unit.steps.some(s=>s.mode==='read')){
      throw new Error('T03 has no approved contextual reading step');
    }
  });
  return {workItems:2,sourceAnchors:anchorCount,approvedItems:0,livePilotUnchanged:true};
}

export function checkTouristEditorialPacket(){
  const content=resolve(repoRoot,'v2/content');
  const packet=json(resolve(content,'tourist-editorial-review-v1.json'));
  const units=json(resolve(content,'tourist-units-v1.json'));
  const blockers=json(resolve(content,'additional-speak-reference-blockers.json'));
  const protectedIds=new Set(['Conversation_1:24','Conversation_1:25',
    ...blockers.sourceBlockers.map(x=>x.itemId)]);
  const sources={};
  for(const work of packet.workItems)for(const anchor of work.sourceAnchors){
    const lessonId=anchor.itemId.slice(0,anchor.itemId.lastIndexOf(':'));
    // Every reference is an original checked-in source; never synthesize targets.
    if(!own(sources,lessonId))
      sources[lessonId]=json(resolve(repoRoot,'docs/sets',lessonId+'.json'));
  }
  return validateTouristEditorialPacket(packet,sources,protectedIds,units);
}

if(process.argv[1] && import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  const report=checkTouristEditorialPacket();
  process.stdout.write('B-03 editorial draft/source identity PASS: '+JSON.stringify(report)+'\n');
}
