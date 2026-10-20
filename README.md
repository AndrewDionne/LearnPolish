# Path to Polish

**Path to Polish V2 is the canonical application.** Its source is in [`v2/frontend/`](v2/frontend/), on the existing GitHub `main` branch. There is no separate V2 branch or repository to merge.

## Local development (macOS/Linux)

Install Node.js 22 or newer, then from the repository root:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
./dev.sh
```

Open **http://127.0.0.1:5186/**. Override the app-specific development port with `PTP_DEV_PORT=5187 ./dev.sh` if needed. `./dev.sh` uses the canonical V2 React/Vite app, not Flask V1.

For a production-like V2 PWA/offline preview run `./prod_like.sh`, then open **http://127.0.0.1:4186/**. For local build and test validation, run `./publish.sh`; that command does not push commits or deploy a site.

## Hosting migration: Render-only target

The owner requires **Render Free only**. The [Render V2 runbook](v2/server/RENDER_V2.md) and [`render.yaml`](render.yaml) define **one free Docker web service, no disk and no paid add-ons**. The host starts before delivering the V2 UI, preventing the former Pages-frontend/separate-Render-backend wake-up mismatch. Render Free can still take time to wake from idle; it provides its own loading page. Existing GitHub Pages and legacy Render services remain unchanged until free V2 hosting is verified.

**Data integrity:** Render Free has no durable local storage. The existing Frankfurt Neon `Path_to_Polish_DB` now has the additive `ptp_v2` schema (14 V2 tables, no V1 account migration). The default free Render build still keeps family accounts disabled until the narrowly privileged Neon runtime login and HTTPS email verification are configured and physically tested. **SMTP cannot work from Render Free** because Render blocks ports 25/465/587, so the account code now supports an optional server-side Resend HTTPS API. No paid services are authorized. Monitor shared Render free-hour, bandwidth and build quotas; a free plan does not guarantee zero overage invoices.

## Previous GitHub Pages publishing

The GitHub Pages previously hosted **V2**, built from `v2/frontend/dist/`. After all four [V2 CI](.github/workflows/v2-ci.yml) lanes pass on `main`, [Deploy V2 to GitHub Pages](.github/workflows/deploy-v2-pages.yml) builds and publishes that static artifact. The old `docs/` tree is **not** the publishing target. V2 source belongs on `main`; the deploy artifact is generated and is not committed to `docs/`.

**One-time GitHub setting required if Pages was previously configured for `main /docs`:** in the repository choose **Settings → Pages → Build and deployment → Source → GitHub Actions**. Until this setting is changed and a deployment succeeds, the old V1 site may still appear at the public URL. Do not mistake merged V2 code for a completed public release.

The public static app does not automatically provide private family sign-in/sync or Azure pronunciation assessment. Those rely on a separately deployed and secured V2 API and stay disabled in the default public build. No Speech key is used in browser artifacts.

## V1 is reference-only; V2 accounts start fresh

**No V1 personal data is being migrated.** New Neon V2 accounts, groups, sessions, earned XP and progress begin from zero in the isolated `ptp_v2` schema. Existing legacy `public` tables are not a compatibility target, and no V1 passwords, scores or memberships are copied. Live-data deletion is a separate irreversible action, not part of the schema migration.

V1's **lesson source material is different from V1 account history**: the canonical [V2 content builder](v2/frontend/scripts/prepare-content.mjs) still reads `docs/sets/` JSON and `docs/static/` MP3 assets for active V2 lessons. Before deleting those old directories, move their required lessons and recordings to V2-owned paths and test the V2 content/audio build. Old V1 runtime/UI is not supported.

Decisions, delivery and test evidence are tracked in [`chat ai workflow.md`](chat%20ai%20workflow.md) and [`V2_REBUILD_PLAN.md`](V2_REBUILD_PLAN.md). Private recordings, provider results, and API credentials must remain local and Git-ignored.
