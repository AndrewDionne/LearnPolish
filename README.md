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

**Data integrity:** Render Free has no durable local storage. The free build provides the offline-first personal V2 learning experience, but **does not falsely offer server-side family accounts, sync or Azure inference**. Those remain disabled until a genuinely durable, zero-paid-cost storage solution and production safeguards are available. Render Free's shared usage limits/possible overages also require checking account billing settings; a free plan does not guarantee a zero invoice.

## Previous GitHub Pages publishing

The GitHub Pages previously hosted **V2**, built from `v2/frontend/dist/`. After all four [V2 CI](.github/workflows/v2-ci.yml) lanes pass on `main`, [Deploy V2 to GitHub Pages](.github/workflows/deploy-v2-pages.yml) builds and publishes that static artifact. The old `docs/` tree is **not** the publishing target. V2 source belongs on `main`; the deploy artifact is generated and is not committed to `docs/`.

**One-time GitHub setting required if Pages was previously configured for `main /docs`:** in the repository choose **Settings → Pages → Build and deployment → Source → GitHub Actions**. Until this setting is changed and a deployment succeeds, the old V1 site may still appear at the public URL. Do not mistake merged V2 code for a completed public release.

The public static app does not automatically provide private family sign-in/sync or Azure pronunciation assessment. Those rely on a separately deployed and secured V2 API and stay disabled in the default public build. No Speech key is used in browser artifacts.

## V1 reference

V1 code and original lesson material remain in Git history and under `app/`, `docs/`, and older scripts **for reference only**. Currently V2's [content preparation](v2/frontend/scripts/prepare-content.mjs) still reads `docs/sets/` and `docs/static/` at build time for imported lesson JSON and trusted MP3s, so **do not delete those files** yet. The migration is one-way and does not imply the V1 UI is supported.

Decisions, delivery and test evidence are tracked in [`chat ai workflow.md`](chat%20ai%20workflow.md) and [`V2_REBUILD_PLAN.md`](V2_REBUILD_PLAN.md). Private recordings, provider results, and API credentials must remain local and Git-ignored.
