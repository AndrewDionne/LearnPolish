#!/usr/bin/env node
// Source-only first-use audit. All linguistic and audio-review statuses remain PENDING.
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";

export function polishWrittenForms(text) {
  if (typeof text !== "string" || !text.trim()) throw new Error("Empty Polish source text");
  const matches = text.normalize("NFC").match(/\p{L}[\p{L}\p{M}]*/gu) ?? [];
  if (matches.length === 0) throw new Error("No written Polish word forms");
  return [...new Set(matches.map(word => word.toLocaleLowerCase("pl")))];
}
export function buildGuidedFirstUseInventory(guided, catalog) {
  if (guided?.schemaVersion !== 1 ||
      guided.sourceStatus !== "authoritative_dependency_inventory_requires_independent_full_lexical_review" ||
      guided.lessonReviewStatus !== "source_only_not_independently_native_certified" ||
      catalog?.schemaVersion !== 1 || !Array.isArray(catalog.lessons) ||
      guided.steps?.length !== 16) {
    throw new Error("Unsupported or incomplete source-first audit inventory");
  }
  const original = new Map(catalog.lessons.flatMap(lesson =>
    lesson.items.map(item => [item.id, item])));
  const seen = new Map(), entries = [], stepSummary = [];
  let lastOrder = 0;
  for (const step of guided.steps) {
    if (step.order !== lastOrder + 1 || !step.id || !Array.isArray(step.items) ||
        !step.items.length) throw new Error("Invalid authored step order");
    lastOrder = step.order;
    const before = entries.length;
    let firstUseCount = 0;
    for (const item of step.items) {
      const source = original.get(item.id);
      if (!source || source.polish !== item.polish ||
          source.english !== item.english || source.audio !== item.audio ||
          source.referenceReview === "practice_only" ||
          typeof item.audio !== "string" ||
          !item.audio.startsWith("generated/audio/")) {
        throw new Error("First-use source mismatch: " + item.id);
      }
      if (step.type === "grammar" &&
          (!item.focus || item.polish.split(item.focus).length !== 2)) {
        throw new Error("Invalid authored grammar cue at " + item.id);
      }
      const firstSeenForms = [], repeatedForms = [];
      for (const form of polishWrittenForms(item.polish)) {
        if (seen.has(form)) {
          repeatedForms.push({form, firstAt: seen.get(form)});
        } else {
          seen.set(form, item.id);
          firstSeenForms.push(form);
        }
      }
      firstUseCount += firstSeenForms.length;
      entries.push({
        stepOrder:step.order, stepId:step.id, sourceId:item.id,
        polish:item.polish, english:item.english, audio:item.audio,
        focus:item.focus ?? null, firstSeenForms, repeatedForms,
        editorialStatus:"pending_human_lexical_and_grammar_review"
      });
    }
    stepSummary.push({
      stepOrder:step.order, stepId:step.id, title:step.title,
      stage:step.stage, sourceRows:entries.length-before,
      firstSeenWrittenForms:firstUseCount
    });
  }
  if (entries.length !== 68 || stepSummary.filter(x => guided.steps[x.stepOrder-1].type==="grammar").length !== 7)
    throw new Error("Changed guided first-use source inventory");
  return {
    schemaVersion:1,sourceAuthority:"V2 original recorded Guided Foundations utterances",
    lexicalPolicy:"Unicode NFC case-insensitive written word forms, not lemmas, meanings, phonemes or teaching certification",
    editorialStatus:"all_rows_pending_independent_human_review",
    totals:{steps:stepSummary.length,sourceRows:entries.length,distinctWrittenForms:seen.size},
    steps:stepSummary, entries
  };
}
export function renderGuidedFirstUseMarkdown(audit) {
  if (audit?.schemaVersion !== 1 || audit.editorialStatus !==
      "all_rows_pending_independent_human_review") {
    throw new Error("Cannot render unqualified lexical audit");
  }
  const cell = value => String(value).replace(/\|/g,"\\|").replace(/[\r\n]+/g," ");
  const forms = list => list.length ? list.map(x => "`"+cell(x)+"`").join(", ") : "—";
  const lines = [
    "# Journey 1 — original-recording first-use inventory",
    "",
    "**Automatically derived from V2 source; all editorial sign-offs are pending.**",
    "This report lists each of 68 existing recorded-phrase references in the native",
    "Guided Foundations sequence. It identifies written forms by Unicode NFC,",
    "Polish-aware lowercase and exact surface spelling only. A first occurrence is",
    "**not** evidence that the word, meaning, grammatical case or pronunciation",
    "has been independently taught, explained or approved. Inflected forms are",
    "distinct; synonyms, lemmas, pronunciation and sentence semantics are **not** inferred.",
    "The complete original English meaning and MP3 reference are retained per row.",
    "",
    "Generated with `node v3/ios/scripts/audit-guided-lexicon.mjs --print` after",
    "`node v3/ios/scripts/prepare-assets.mjs`. CI compares this checked-in output",
    "byte-for-byte with the source-derived result. Human review must be recorded",
    "separately; never change a generated Pending label to Approved by hand.",
    "",
    "**Inventory:** "+audit.totals.steps+" groups; "+audit.totals.sourceRows+
    " original reference occurrences; "+audit.totals.distinctWrittenForms+
    " distinct written surface forms; 0 independently certified rows.",
    ""
  ];
  for (const step of audit.steps) {
    lines.push("## "+step.stepOrder+". "+cell(step.title)+" — "+cell(step.stage));
    lines.push("");
    lines.push(step.sourceRows+" original references; "+
      step.firstSeenWrittenForms+" first-seen written forms in this ordered group.");
    lines.push("");
    lines.push("| Source ID | Original Polish | Original English | First-seen forms | Earlier forms | Grammar focus | Audio file | Editorial |");
    lines.push("| --- | --- | --- | --- | --- | --- | --- | --- |");
    for (const entry of audit.entries.filter(x=>x.stepId===step.stepId)) {
      lines.push("| `"+cell(entry.sourceId)+"` | "+cell(entry.polish)+" | "+
        cell(entry.english)+" | "+forms(entry.firstSeenForms)+" | "+
        forms(entry.repeatedForms.map(x=>x.form))+" | "+
        (entry.focus ? "`"+cell(entry.focus)+"`" : "—")+" | `"+
        cell(entry.audio)+"` | Pending |");
    }
    lines.push("");
  }
  lines.push("## Human editorial checklist (not yet completed)");
  lines.push("");
  lines.push("1. Confirm the original Polish and English gloss are accurate in context.");
  lines.push("2. Check every first-seen surface form, including inflections and case endings;");
  lines.push("   determine which words/forms need an earlier explicit explanation.");
  lines.push("3. Confirm that a new phrase is explained *before* it is assessed;");
  lines.push("   whole-phrase audio does not certify independent comprehension.");
  lines.push("4. Check the source recording against the written Polish (speaker, timing, clarity).");
  lines.push("5. Cross-check sound/letter combinations and the core Journey 1 lessons;");
  lines.push("   those are **not** covered by this guided-only first-use report.");
  lines.push("");
  return lines.join("\n");
}

export function auditCurrentGeneratedAssets(repo) {
  const generated = path.join(repo,"v3/ios/Resources/generated");
  const guided = JSON.parse(fs.readFileSync(path.join(generated,"guided-foundations.json"),"utf8"));
  const catalog = JSON.parse(fs.readFileSync(path.join(generated,"lessons.json"),"utf8"));
  return buildGuidedFirstUseInventory(guided,catalog);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const mode = process.argv[2] ?? "--check";
  if (!["--check","--print"].includes(mode)) {
    throw new Error("Expected --check or --print");
  }
  const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../../..");
  const audit=auditCurrentGeneratedAssets(repo);
  const result=renderGuidedFirstUseMarkdown(audit);
  if (mode === "--print") {
    process.stdout.write(result);
  } else {
    const checkedIn=fs.readFileSync(path.join(repo,"v3/JOURNEY1_FIRST_USE.md"),"utf8");
    if (checkedIn !== result) {
      throw new Error("Journey 1 first-use inventory drift: inspect original V2 source and regenerate only after editorial review");
    }
    console.log("Verified source-locked Journey 1 first-use inventory:",audit.totals);
  }
}
