#!/usr/bin/env node
// Original-source-only first-use audit; pending independent linguistic review.
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {polishWrittenForms} from "./audit-guided-lexicon.mjs";

export function buildUnifiedFirstUseAudit(catalog, guided, core, unified) {
  if(catalog?.schemaVersion!==1 || !Array.isArray(catalog.lessons) ||
     guided?.schemaVersion!==1 || guided.steps?.length!==16 ||
     core?.schemaVersion!==1 || core.placements?.length!==21 ||
     unified?.schemaVersion!==1 || unified.chapters?.length!==8 ||
     unified.editorialStatus!=="source-mapped_unified_navigation_not_independently_linguistic_reviewed")
    throw Error("Incomplete unified source inventory");
  const lessons=new Map(catalog.lessons.map(x=>[x.id,x]));
  const guidedSteps=new Map(guided.steps.map(x=>[x.id,x]));
  const coreIDs=new Set(core.placements.filter(x=>x.journey===1).map(x=>x.lessonId));
  const keys=unified.chapters.flatMap(x=>x.activities);
  const expected=new Set([...coreIDs].map(x=>"l:"+x).concat(
    [...guidedSteps.keys()].map(x=>"g:"+x)));
  if(lessons.size!==catalog.lessons.length || guidedSteps.size!==16 ||
     coreIDs.size!==19 || keys.length!==35 || new Set(keys).size!==35 ||
     keys.some(x=>!expected.has(x))) throw Error("Unified path source identity drift");
  const original=new Map(catalog.lessons.flatMap(l=>l.items.map(i=>[i.id,i])));
  if(original.size!==catalog.lessons.reduce((n,x)=>n+x.items.length,0))
    throw Error("Duplicate original item IDs");
  const encountered=new Map(), nonSound=new Map(), sourceUsed=new Set();
  const rows=[],groups=[],risks=[];
  let activityOrder=0,chapterOrder=0;
  for(const chapter of unified.chapters) {
    chapterOrder++;
    if(!chapter.id || !chapter.title || !chapter.description ||
       !chapter.activities?.length) throw Error("Empty authored chapter");
    for(const key of chapter.activities) {
      activityOrder++;
      const guide=key.startsWith("g:");
      const id=key.slice(2);
      const lesson=guide?null:lessons.get(id);
      const step=guide?guidedSteps.get(id):null;
      if((guide&&!step)||(!guide&&(!lesson||!coreIDs.has(id))))
        throw Error("Missing original Journey 1 activity: "+key);
      const sourceItems=guide?step.items:lesson.items;
      const sound=!guide&&lesson.kind==="sounds";
      let firstForms=0,meaningForms=0,reuses=0;
      for(const item of sourceItems) {
        const recorded=original.get(item.id);
        if(!recorded || recorded.polish!==item.polish ||
           recorded.english!==item.english || recorded.audio!==item.audio ||
           typeof item.audio!=="string" ||
           !item.audio.startsWith("generated/audio/"))
          throw Error("Source Polish/English/recording mismatch: "+item.id);
        const first=[],lexical=[],prior=[];
        for(const form of polishWrittenForms(item.polish)) {
          if(!encountered.has(form)) {encountered.set(form,item.id);first.push(form);}
          else prior.push(form);
          // Sound exemplars are orthographic/acoustic exposure, NOT a proof
          // that their meaning, case, or full word has been taught.
          if(!sound&&!nonSound.has(form)) {nonSound.set(form,item.id);lexical.push(form);}
        }
        firstForms+=first.length;
        meaningForms+=lexical.length;
        if(sourceUsed.has(item.id))reuses++;
        sourceUsed.add(item.id);
        rows.push({chapterOrder,chapterTitle:chapter.title,activityOrder,
          activityId:key,sourceId:item.id,polish:item.polish,english:item.english,
          audio:item.audio,isSound:sound,firstForms:first,lexicalForms:lexical,
          priorForms:prior,status:"pending_human_lexical_and_grammar_review"});
      }
      groups.push({chapterOrder,chapterTitle:chapter.title,activityOrder,
        activityId:key,kind:guide?"guided":lesson.kind,sourceRows:sourceItems.length,
        newEncounteredForms:firstForms,newNonSoundForms:meaningForms,
        reusedOriginalIDs:reuses});
      // Existing provisional exercise plan uses index 1,4,7 ... for Learn.
      // NativePracticeRules.choices may source distractors from later cards.
      if(!guide&&lesson.kind==="vocabulary") {
        for(let idx=1;idx<lesson.items.length;idx+=3) {
          const target=lesson.items[idx];
          const used=new Set([target.english]);
          // Match exact NativeExercisePlan.choices: *earlier* authored items
          // only. This prevents showing the answer to a future word as a
          // quiz distractor during the introductory pass.
          const earlier=lesson.items.slice(0,idx).filter(i=>{
            if(used.has(i.english))return false;
            used.add(i.english);return true;
          });
          if(earlier.length<2)continue;
          const offset=idx%earlier.length;
          const choices=earlier.slice(offset)
            .concat(earlier.slice(0,offset)).slice(0,2);
          const prematurelyOffered=choices.filter(opt=>{
            const position=lesson.items.findIndex(i=>i.id===opt.id);
            return position>=idx;
          }).map(x=>x.id);
          if(prematurelyOffered.length)
            risks.push({activityId:key,sourceId:target.id,
              laterOptionIDs:prematurelyOffered});
        }
      }
    }
  }
  return {schemaVersion:1,editorialStatus:"all_rows_pending_human_review",
    totals:{chapters:8,activities:groups.length,sourceRows:rows.length,
      uniqueSourceIDs:sourceUsed.size,encounteredForms:encountered.size,
      nonSoundMeaningExposures:nonSound.size,potentialEarlyOptionCards:risks.length},
    groups,rows,risks};
}

export function renderUnifiedFirstUseMarkdown(a) {
  if(a?.schemaVersion!==1||a.editorialStatus!=="all_rows_pending_human_review")
    throw Error("No claimed independent linguistic approval");
  const quote=String.fromCharCode(96);
  const c=v=>String(v).replace(/\|/g,"\\|").replace(/[\r\n]+/g," ");
  const cells=v=>v.length?v.map(x=>quote+c(x)+quote).join(", "):"—";
  const t=a.totals;
  const lines=[
    "# Journey 1 — unified source-first written-form audit",
    "",
    "**Generated from original V2 lesson IDs, Polish/English pairs and MP3 references; all independent human editorial sign-offs PENDING.**",
    "The comparison uses Unicode NFC / Polish case-folded written surface forms.",
    "It is NOT linguistic lemma matching, grammatical or phonetic certification.",
    "A word encountered in a sound-contrast example is NOT automatically counted",
    "as a word whose meaning was taught. New inflections are separate forms.",
    "",
    "**Inventory:** "+t.chapters+" chapters, "+t.activities+" activities, "+
      t.sourceRows+" original source occurrences, "+t.uniqueSourceIDs+
      " unique original source-item IDs, "+t.encounteredForms+
      " distinct encountered written forms, "+t.nonSoundMeaningExposures+
      " first non-sound meaning exposures, and "+t.potentialEarlyOptionCards+
      " matching cards with possible premature later-card answer options.",
    "These are review leads, not confirmed teaching failures or certifications.",
    "",
    "Regenerate using the audit-unified-first-use.mjs script after prepare-assets.",
    "CI compares this report byte-for-byte with the same V2-generated source",
    "and the single native unified Journey 1 manifest.",
    "",
    "## Activity-level coverage",
    "",
    "| # | Chapter | Activity | Type | Source rows | First encountered forms | First non-sound forms | Reused original source IDs |",
    "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |"];
  for(const g of a.groups) lines.push("| "+g.activityOrder+" | "+c(g.chapterTitle)+
    " | "+quote+c(g.activityId)+quote+" | "+g.kind+" | "+g.sourceRows+
    " | "+g.newEncounteredForms+" | "+g.newNonSoundForms+" | "+
    g.reusedOriginalIDs+" |");
  lines.push("","## Matching-option sequencing gate","",
    "The source-backed introductory Learn quiz may use only EARLIER original",
    "same-lesson English meanings. When fewer than two distinct earlier",
    "meanings are available, the item remains a Speak introduction.",
    "Potential later-card violations under this rule are listed below.",
    "This gate prevents future-card leakage; it does not prove mastery of",
    "an earlier item that a learner deliberately skipped.","");
  if(a.risks.length) {
    lines.push("| Activity | Quiz target | Later untranslated source option(s) |",
      "| --- | --- | --- |");
    for(const r of a.risks)lines.push("| "+quote+c(r.activityId)+quote+
      " | "+quote+c(r.sourceId)+quote+" | "+cells(r.laterOptionIDs)+" |");
  }else lines.push("No future-card options detected.");
  lines.push("","## Item-by-item original-source audit","");
  let chapterOrder=0;
  for(const g of a.groups) {
    if(g.chapterOrder!==chapterOrder) {
      chapterOrder=g.chapterOrder;
      lines.push("### Chapter "+chapterOrder+": "+c(g.chapterTitle),"");
    }
    lines.push("#### "+g.activityOrder+". "+quote+c(g.activityId)+quote,"",
      "| Source item ID | Original Polish | Original English | First encountered | First non-sound exposure | Prior encountered forms | Original MP3 | Human review |",
      "| --- | --- | --- | --- | --- | --- | --- | --- |");
    for(const r of a.rows.filter(x=>x.activityOrder===g.activityOrder)) {
      lines.push("| "+quote+c(r.sourceId)+quote+" | "+c(r.polish)+" | "+
        c(r.english)+" | "+cells(r.firstForms)+" | "+cells(r.lexicalForms)+
        " | "+cells(r.priorForms)+" | "+quote+c(r.audio)+quote+" | Pending |");
    }
    lines.push("");
  }
  lines.push("## Editorial work still required","",
    "1. Confirm all original Polish/English utterance pairs and inflected forms.",
    "2. Verify sound and syllable coverage; source spelling is not pronunciation proof.",
    "3. Prevent matching a phrase against meanings never taught before that question.",
    "4. Verify source dialogue comprehension prerequisites and human audio clarity.",
    "5. Design source-backed repetition, spaced retrieval, and mixed exercise progression.",
    "6. Verify physical recording, headset channels, and any consented acoustic score.",
    "",
    "No row is approved by running this audit.","");
  return lines.join("\n");
}

export function auditCurrentUnifiedAssets(repo) {
  const root=path.join(repo,"v3/ios/Resources/generated");
  const read=n=>JSON.parse(fs.readFileSync(path.join(root,n),"utf8"));
  return buildUnifiedFirstUseAudit(read("lessons.json"),
    read("guided-foundations.json"),read("core-journey.json"),
    read("unified-journey.json"));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const mode=process.argv[2]??"--check";
  if(!["--check","--print"].includes(mode))throw Error("Expected --check or --print");
  const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../../..");
  const report=renderUnifiedFirstUseMarkdown(auditCurrentUnifiedAssets(repo));
  if(mode==="--print")process.stdout.write(report);
  else {
    if(report!==fs.readFileSync(path.join(repo,"v3/JOURNEY1_UNIFIED_FIRST_USE.md"),"utf8"))
      throw Error("Unified Journey 1 first-use report source drift; do not certify.");
    console.log("PASS: source-verified full Journey 1 first-use report.");
  }
}
