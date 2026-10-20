# Path to Polish V2 — Render FREE only

## Owner constraint: no paid services

**Render Free only.** The owner rejected the paid Starter+disk proposal on 2026-10-20. The authoritative [`render.yaml`](../../render.yaml) is now `plan: free`, with **no disk, database, SMTP, Azure, or other paid add-ons**. Source remains in `AndrewDionne/LearnPolish`; GitHub privacy and GitHub Pages retirement happen only after verified Render hosting.

Render Free is subject to its published monthly allowances. Its web-service filesystem is **ephemeral** and free web services sleep after 15 minutes of inactivity. The initial wake can take about one minute; **Render shows its loading page while it starts**. The browser cannot skip that cold start, but there is no longer a separate sleeping API to wake AFTER the V2 frontend loads. Check latest official [Render Free limitations](https://render.com/docs/free) before setup; if your workspace has a payment method, excess bandwidth/build minutes **may still incur charges**. A free plan is not an unconditional zero-bill guarantee. Configure account spending/usage controls or avoid deployment if the current billing configuration could charge overages.

## Free deployment scope: honest capability, safe storage

One V2 Docker image includes the built React/TypeScript V2 learner PWA, trusted imported lesson/audio assets, a Flask same-origin file server and `GET /health/ready` from **one Render process**. The server validates the bundled lesson manifest and shell before binding. The home page and assets return 503 if a previously ready host loses required local assets; the browser PWA fetches online navigations before using a cached offline shell. When the service is asleep, users see Render's loading page, then the complete offline-first learner UI.

**Free persistent family storage is not available on this Render service.** Render erases files (including SQLite) on redeploy, restart and sleep, and free web services cannot attach disks. Consequently `PTP_RENDER_FAMILY_MODE=disabled` is the safe default and **the free frontend is built with `VITE_FAMILY_API_URL` empty**. It DOES NOT activate registration, emailed verification, permanent server XP/family memberships, cross-device sync, or Azure speech inference. The old V2 family backend remains source code / local CI implementation only; it is neither silently simulated nor exposed to free users. Keep the existing personal/local PWA learning history and optional downloaded offline packs on each user's browser. Browser storage is device-local and can be erased by browser controls.

**Full V2 family online capabilities will need a separate durable free database solution and production privacy/guardian/SMTP review.** This has NOT been implemented. Do not try to work around persistence by writing user accounts to Render's ephemeral filesystem or committing them to GitHub. Do not enable unverified minors or upload real speech to external providers.

## Deploy / verify without paying for compute plans

- Repository deployment contract: [`render.yaml`](../../render.yaml): `type: web`, `plan: free`, Frankfurt, `Dockerfile.v2`, no disk.
- Existing `Path to Polish` (Frankfurt, `path-to-polish.onrender.com`) and `flashcards` (Ohio) Render services are legacy/free V1. **Neither is the unified V2 host.** Prefer repurposing the existing Frankfurt service when possible, so you don't add to the workspace's shared free resource consumption. The available connected Render tools cannot change that service's runtime/build commands in place, so use Render's dashboard for an in-place Docker migration, or explicitly replace it with a free Blueprint after reviewing current usage and billing settings. Do not automatically create an additional service without checking free hours / billing.
- After deploying, verify `/health/ready` reports `{"ready":true,"family_available":false}`, the root displays V2, bundled audio plays, and disconnected practice works; confirm no `/api/v2/family/*` request can create an account. Confirm the first cold browser visit does not display V2 as ready before Render starts, and inspect logs for errors.
- Only after physical verification, disable the old Pages workflow and Pages site. Then change GitHub visibility manually in **Settings → General → Danger Zone → Change repository visibility → Private**, after verifying the Render GitHub App's private repository access at [Render's Git provider guide](https://render.com/docs/git-provider). If private repo access fails, restore Render repository permissions before any further deploy.
- CI tests are synthetic and do not prove a Docker image is actually deployed, or certify family accounts and children. Preserve V1 lesson/audio inputs because the V2 build still imports `docs/sets/` and `docs/static/`.

## Local source checks

```bash
cd v2/frontend && npm run check
cd ../..
python -m unittest discover -s v2/server -p 'test_*.py' -v
```

No special paid services, API keys, private learner WAV, or external inference needed.
