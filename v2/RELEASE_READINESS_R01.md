# R-01 — Free Render deployment and offline artifact release preflight

**Status:** Synthetic and repository-backed verification only. **No cutover, no environment changes, no real-account activation, no external API usage, no live microphone test.**

## Product boundary

Path to Polish V2 is a self-directed learning/practice application, **not a grammar tutor**. [Owner scope correction](../chat%20ai%20workflow.md) supersedes the abandoned C-16D item-by-item coaching expansion and issue #156 (closed, not planned). The completed feature-development tranche through [PR #159](https://github.com/AndrewDionne/LearnPolish/pull/159) has 4/4 CI passes. R-01 is a production-readiness *test improvement*, not new teaching content.

## Verified live Render staging metadata (read-only, 2026-10-24)

Connected Render service `srv-dbbik2uq1p3s73codovg` / `path-to-polish-v2` uses `plan: free`, Frankfurt, Docker `Dockerfile.v2`, branch `main`; last inspected deploy `dep-dbefrdtg1s2s739cfqug` was marked **live**, based on Git commit `09b4940916ffa03af89bc6ee77d71de8944b65a5`. These are service/deploy **control-plane** facts, **not** evidence that a cold browser/MP3/offline workflow has passed live.

**Actual service configuration drift:** the Render service reports `autoDeploy: yes`, `autoDeployTrigger: commit`, and `serviceDetails.healthCheckPath: ""`; `render.yaml` declares `autoDeployTrigger: checksPass` and `healthCheckPath: /health/ready`. The Render deploy history confirms pushes of documentation-only commits triggered fresh builds. **Changing `render.yaml` is not enough to prove the already-created service has those settings.** The connected Render controls expose service inspection but not an authorized service-settings update operation. Do not assume its desired deploy gating/health checks are active. This drift is an operator verification/fix item, *not* silently corrected by this PR.

**Required Render dashboard reconciliation before production cutover**: inspect service Settings → Build & Deploy for the deploy trigger and ensure deployment after CI/required checks, not unguarded every-commit rebuilding. Inspect Settings → Health Checks and configure `/health/ready` to match the checked-in Blueprint. Do not turn on a persistent account backend without secure Neon runtime login, verified HTTPS mail, appropriate child/guardian privacy, tested export/erasure/backup and explicit owner approval. Keep Render Free/no disk; do not pay for any services. Do not delete old hosting or change GitHub repo visibility before successful manual checks.

## Automated read-only built-artifact test

Run from `v2/frontend`:

```bash
npm run check
# or, after a production build:
npm run test:release-artifact
```

`scripts/release-asset-preflight.mjs` audits the actual **compiled `dist`**, never `docs/` as if it were the deploy:

- Complete `index.html` with React root and Vite-built JavaScript/CSS entrypoint(s), no leftover unbuilt `/src/main.tsx`.
- Every referenced JS/CSS file exists as a nonempty ordinary local file (not a symlink or escaped path).
- Generated `sw.js` has a valid, unique precache list containing index, prepared lesson catalog and **every** referenced JS/CSS entrypoint. All precached files exist and are nonempty.
- `generated/lessons.json` is valid schema V1, retains **26** unique source/curated lessons with valid nonempty text and unique item IDs, and references the expected large original recording corpus (at least 400 unique bundled MP3s).
- **Every** referenced original complete MP3 in the actual prepared catalog exists at the intended `generated/audio/<lesson>/<index>.mp3` path and is nonempty; malformed, missing, external or traversal audio URLs fail the build. No external network or paid speech request, keys, account data or live database are touched.
- Prints only an artifact count/status receipt, explicitly **false** for physical Safari, speech accuracy and family-account release signoff. Fixture mutation tests reject missing JS/CSS/SW/catalog/audio, malicious paths, missing English and duplicate lesson/item IDs.

The test now runs at the end of `npm run check` after `npm run build` and offline service-worker checks, under GitHub's frontend lane. Four exact-head CI lanes still required for merges. This guarantees **the compiled artifact contains its own referenced resources at build time**; it does **not** prove that a live host has served them to an external browser, that native reference audio is accurate, or that offline/recording behavior passes real Safari.

## Separate live / manual cutover gate — NOT completed by this PR

1. With Render Free staging configured appropriately, manually check `https://path-to-polish-v2.onrender.com/health/ready` yields HTTP 200 and `ready:true,family_available:false`. Observe any real cold-start delay rather than fabricating one.
2. Confirm real `/`, bundled JS/CSS, at least one original greeting MP3, original Numbers, mobile Library/Listen, local progress, and offline pack after a disconnected revisit. On cold start and refresh, service should not display the wrong V1 UI.
3. Confirm `/api/v2/family/health` and signup **fail closed with 503** while hosted accounts are disabled, and the public bundle does not expose a database/mail/speech secret.
4. Test real iPhone Safari microphone permission and full utterance reference playback; physical pronunciation scoring remains **not validated** and must not be marketed as calibrated.
5. Confirm free usage/billing and secure identity/privacy/guardian/retention gates **before** activating any online family accounts; do not turn on external paid API usage without owner authorization.
6. Only after explicit go-live acceptance decide when to retire old Pages/V1 hosts or make source repo private. A successful build, `live` deployment status or four CI checks alone is not public-release certification.

**Next after this R-01:** genuine manual Render browser cold-start/mobile/audio/physical run and explicit settings reconciliation. Do not add new curriculum/tutor features.
