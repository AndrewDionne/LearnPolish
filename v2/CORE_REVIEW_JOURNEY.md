# A-04 — Optional core review, separate personal practice

**Status:** implementation tranche, subject to final-head four-lane GitHub CI. Based on verified B-03 main at `e176d305415aead590c8f0ad3fd1fe1a9adb6d38`.

## Learner behavior

- Home's existing **Ready to review** action uses an exact total of scheduled due items, with the distinction between **On your path** and **other lessons**. If core items are due, a single click launches the next core due review; otherwise it goes to Practice.
- Practice groups *actual currently scheduled Learn reviews* in three plainly titled sections: **On your path** (the 20 source-mapped course lessons), **Your lessons** (personal/imported lessons), and **Explore more** (supplementary/diagnostic built-ins). Sections with no personal/extra reviews stay hidden. Each source lesson can still be reviewed individually.
- **Review N expressions** on the course section launches a short *in-memory* queue, fixed at activation, of due core source lessons in canonical journey order; each lesson uses its exact pre-existing item IDs in the established Learn review path. After the first lesson's due items, the completion screen offers **Continue scheduled review** for the next source lesson. The last stop returns to Practice. There is no account-level assignment, cross-lesson audio mix, forced sequence, new mastery claim or course unlock.
- A missed item remains immediately due according to the unchanged saved scheduler, but does not loop again *within the same run*. Skipping/navigating away ends the optional review run, leaving every existing date unchanged. Individual noncore personal/optional review remains independent.
- Review opens with `updateCourseCursor=false`, protecting the user's chosen **Continue course** Home target. A new optional review never changes source canonical journey ordering. Normal intentional Library or course selection continues to update course position.
- Course unit exercises and Numbers 1–20 1–10 / 11–20 voluntary groups are unaffected: review is still a Learn due-item subset and never a new built-in lesson. No new profile item, backup schema, local storage key, review scheduling formula, point multiplier or family XP path.

## Integrity / evidence

Pure `src/core-review.ts` partitions valid due source lessons using existing `dueItems` and `journeyPlacement`; it snapshots only selected due source item IDs for each run. Unit tests cover canonical journey order, source/personal isolation, empty/future schedules, real missed-item retry state, stable snapshot and no writes. Desktop/mobile E2E seeds known due dates including a core greeting, core numbers, a personal card and an optional geography card, then checks one-tap Home review, cross-lesson continuation, no missed-item loop, untouched stored course cursor, personal/optional due separation and 320px touch/overflow.

The following are **not** inferred: comprehension proficiency, speech-accent improvement, pronunciation scores, verified native Polish accent or group competitive performance. Existing 14 `practice_only` speech references, source audio, offline, family consent/privacy, self-rated progress and all recording/provider gates remain unchanged. Physical Safari/microphone/native/acoustic testing and hosted rollout remain deferred.

## Certification

Run `npm run check` and `npm run test:e2e` within `v2/frontend`, and require all four GitHub Actions lanes at the final PR head: frontend browser/offline/a11y; connected family; private backend; benchmark. Only after PASS should this development tranche be merged.

**Next meaningful work:** human editor/audio review [issue #126](https://github.com/AndrewDionne/LearnPolish/issues/126) for complete T02 name response and T03 natural price/quantity/payment + contextual Read; then source-approved T04/T05 modules. Course/unit completion evidence (A04 finding) remains distinct from this scheduled review slice and must never manufacture an acoustic mastery grade.
