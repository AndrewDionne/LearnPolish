import {test} from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {buildUnifiedFirstUseAudit,renderUnifiedFirstUseMarkdown,
        auditCurrentUnifiedAssets} from "./audit-unified-first-use.mjs";

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../../..");
const generated=path.join(repo,"v3/ios/Resources/generated");
const read=n=>JSON.parse(fs.readFileSync(path.join(generated,n),"utf8"));
const fixture=()=>({
  catalog:read("lessons.json"),guided:read("guided-foundations.json"),
  core:read("core-journey.json"),unified:read("unified-journey.json")
});
const audit=(x)=>buildUnifiedFirstUseAudit(x.catalog,x.guided,x.core,x.unified);
test("single authored Journey 1 includes each of 16 guided and 19 original core sources",()=>{
  const a=auditCurrentUnifiedAssets(repo);
  assert.equal(a.totals.chapters,8);
  assert.equal(a.totals.activities,35);
  assert.equal(a.totals.sourceRows,381);
  assert.equal(a.totals.uniqueSourceIDs,313);
  assert.equal(a.totals.encounteredForms,344);
  assert.equal(a.totals.nonSoundMeaningExposures,328);
  assert.equal(a.groups.filter(g=>g.kind==="guided").length,16);
  assert.equal(a.groups.filter(g=>g.kind==="sounds").length,5);
  assert.ok(a.rows.every(r=>r.audio.startsWith("generated/audio/")));
  assert.ok(a.rows.every(r=>r.status==="pending_human_lexical_and_grammar_review"));
});
test("sound exposure does not falsely count as lexical teaching",()=>{
  const a=auditCurrentUnifiedAssets(repo);
  assert.ok(a.rows.some(r=>r.isSound&&r.firstForms.length>0));
  assert.ok(a.rows.filter(r=>r.isSound).every(r=>r.lexicalForms.length===0));
  const seen=new Set(),lexical=new Set();
  for(const row of a.rows) {
    for(const form of row.firstForms)assert.ok(!seen.has(form)&&seen.add(form));
    for(const form of row.lexicalForms)assert.ok(!lexical.has(form)&&lexical.add(form));
  }
  assert.equal(seen.size,344);
  assert.equal(lexical.size,328);
});
test("no vocabulary option uses a later source card in first introduction",()=>{
  const a=auditCurrentUnifiedAssets(repo);
  assert.deepEqual(a.risks,[]);
  assert.equal(a.totals.potentialEarlyOptionCards,0);
  const {catalog}=fixture();
  const lesson=catalog.lessons.find(x=>x.id==="numbers_1-20");
  const target=lesson.items[4];
  const seen=new Set([target.english]);
  const earlier=lesson.items.slice(0,4).filter(x=>{
    if(seen.has(x.english))return false;
    seen.add(x.english);return true;
  });
  assert.ok(earlier.length>=2);
  assert.equal(lesson.items[1].id,"numbers_1-20:1");
});
test("source text, English, MP3, and unified route tampering fail closed",()=>{
  const x=fixture();
  const clone=structuredClone;
  const id=x.guided.steps[0].items[0].id;
  for(const name of ["polish","english","audio"]) {
    const changed=clone(x);
    changed.catalog.lessons.flatMap(l=>l.items).find(i=>i.id===id)[name]="corrupted";
    assert.throws(()=>audit(changed),/mismatch/);
  }
  const moved=clone(x);
  moved.unified.chapters[0].activities[0]="l:unapproved-source";
  assert.throws(()=>audit(moved),/Unified path source identity drift/);
  const repeated=clone(x);
  repeated.unified.chapters[0].activities[1]=repeated.unified.chapters[0].activities[0];
  assert.throws(()=>audit(repeated),/Unified path source identity drift/);
});
test("checked-in full report is a source-derived pending-review projection",()=>{
  const report=renderUnifiedFirstUseMarkdown(auditCurrentUnifiedAssets(repo));
  assert.equal(fs.readFileSync(path.join(repo,"v3/JOURNEY1_UNIFIED_FIRST_USE.md"),"utf8"),report);
  assert.ok(!report.includes("| Approved |"));
  assert.match(report,/313 unique original source-item IDs/);
  assert.match(report,/No future-card options detected/);
});
