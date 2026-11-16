import {test} from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {polishWrittenForms,buildGuidedFirstUseInventory,
        renderGuidedFirstUseMarkdown,auditCurrentGeneratedAssets}
  from "./audit-guided-lexicon.mjs";

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../../..");
const base=path.join(repo,"v3/ios/Resources/generated");
const read=name=>JSON.parse(fs.readFileSync(path.join(base,name),"utf8"));

test("Polish written forms normalize NFC, distinguish inflections and exclude punctuation",()=>{
  assert.deepEqual(polishWrittenForms("ŁÓDŹ, Łódź! Żółć… nie?"),["łódź","żółć","nie"]);
  assert.deepEqual(polishWrittenForms("bilet, bilety; BILET"),["bilet","bilety"]);
  assert.throws(()=>polishWrittenForms(" ... 123!"),/No written/);
});
test("all real source occurrences and original recording IDs are auditable",()=>{
  const a=auditCurrentGeneratedAssets(repo);
  assert.deepEqual(a.totals,{steps:16,sourceRows:68,distinctWrittenForms:74});
  assert.equal(new Set(a.entries.map(x=>x.sourceId)).size,55);
  assert.equal(a.steps.filter(s=>s.stepId.startsWith("grammar:")).length,7);
  assert.ok(a.entries.every(x=>x.editorialStatus==="pending_human_lexical_and_grammar_review"));
  assert.equal(a.entries[0].sourceId,"Conversation_1:14");
  assert.deepEqual(a.entries[0].firstSeenForms,["tak"]);
  assert.ok(a.entries.every(x=>x.english?.length>0 && x.audio.startsWith("generated/audio/")));
});
test("repeated original phrases are not counted as newly introduced word forms",()=>{
  const a=auditCurrentGeneratedAssets(repo);const seen=new Set();
  for (const entry of a.entries) {
    for (const form of entry.firstSeenForms) {
      assert.ok(!seen.has(form));seen.add(form);
    }
    assert.ok(entry.repeatedForms.every(x=>seen.has(x.form)));
  }
  assert.equal(seen.size,74);
});
test("modified original text, translation, audio and editorial status fail closed",()=>{
  const guide=read("guided-foundations.json"),catalog=read("lessons.json");
  const copy=value=>structuredClone(value);const itemId=guide.steps[0].items[0].id;
  for(const field of ["polish","english","audio"]) {
    const altered=copy(catalog);
    altered.lessons.flatMap(l=>l.items).find(x=>x.id===itemId)[field]="altered";
    assert.throws(()=>buildGuidedFirstUseInventory(guide,altered),/source mismatch/);
  }
  const edited=copy(guide);edited.lessonReviewStatus="approved";
  assert.throws(()=>buildGuidedFirstUseInventory(edited,catalog),/Unsupported/);
});
test("checked-in report is an exact source projection with no approved claims",()=>{
  const current=renderGuidedFirstUseMarkdown(auditCurrentGeneratedAssets(repo));
  assert.equal(fs.readFileSync(path.join(repo,"v3/JOURNEY1_FIRST_USE.md"),"utf8"),current);
  assert.ok(!current.includes("| Approved |"));
});
