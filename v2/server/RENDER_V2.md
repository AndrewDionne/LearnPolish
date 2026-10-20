# Path to Polish — Render-only V2 hosting handover

## Decision and status

GitHub is the durable **source**, and should be made private after the new Render V2 service is verified. Render is the intended **sole host**. At the time of this change, Render already contains TWO **legacy/free** web services for this repository: `Path to Polish` (`path-to-polish.onrender.com`, Frankfurt) and `flashcards` (Ohio). Neither hosts the actual V2 family API. Do NOT mistake those for the new unified service or silently replace them.

This tranche implements the deployable, single-process V2 React + Flask image and isolated readiness tests. **It does not create a paid Render service, provision secrets, initialize a production family database, or make the repository private.** The existing GitHub Pages URL may still serve V2 until a verified Render cutover.

## Why one Render web service?

The former static Pages frontend could load while a different Render backend slept. This produces a misleading first screen. Here, the same Flask/Gunicorn service serves **both** the built React frontend and the `/api/v2/family/*` endpoints from one HTTPS origin. Startup requires built catalog, private persistent SQLite path, expected HTTPS origin and email delivery when `PTP_RENDER_REQUIRE_EMAIL=1`. The service health check is `GET /health/ready`: 200 only when the database tables and catalog are readable. GET `/` and asset responses are **503** if storage is unavailable, without exposing a half-ready UI. Production browser build uses `VITE_FAMILY_API_URL=same-origin`, not a second waking API host.

Production V2 PWA navigations fetch the live response first. If Render returns 503 during startup, the service worker does not substitute a stale cached UI. Genuine network disconnection can still use the PWA's previously installed offline shell. Offline practice remains available by design, but it cannot promise online family sync without a connection.

**Cold starts:** a free Render web service still sleeps after 15 minutes of inactivity and can take about a minute to wake; Render itself displays a loading page while spinning up. Unified hosting prevents the two-service mismatch, not the wait itself. A paid always-on **Starter** service eliminates free-tier idle spin-down. **Data safety:** Render free service storage is ephemeral and cannot hold this SQLite account data; the Blueprint therefore describes a **paid Starter service + persistent 1 GB disk**. This is a billing change and must be explicitly approved before the Blueprint is applied. There is no reliable free permanent database currently provisioned in this workspace.

## Implementation and checks

- `Dockerfile.v2` builds the V2 React app using the existing legacy JSON/audio **as data inputs only**, then copies only `v2/frontend/dist` and `v2/server` into the runtime image.
- `v2/server/render_app.py` composes existing validated family Flask routes with the static React build; `render_wsgi.py` is the Gunicorn entry point.
- `render.yaml` defines **optional** paid Render creation with one Frankfurt web service, attached private persistent disk, readiness health check and SMTP secrets as `sync:false` (never put actual credentials in Git). No Render instance is created simply by committing this YAML unless the user explicitly links a Blueprint.
- `PTP_PUBLIC_ORIGIN` must match the service's real HTTPS origin. Update this before going live if Render allocates a different hostname or you use a custom domain; otherwise same-origin browser POSTs fail closed.
- `PTP_FAMILY_DB` must live under the attached Render disk (`/var/data/family/family.sqlite` in the example). Database and directory must remain owner-private, no symlinks. SQLite storage and backup/restore are not interchangeable with Render Postgres.
- SMTP verification and recovery credentials must work before sign-up is enabled; `PTP_RENDER_REQUIRE_EMAIL=1` deliberately refuses startup without configured SMTP. This check verifies configuration, not deliverability; actual sending must also be tested. Provider assessment is **OFF** by default (`PTP_SPEECH_ENABLED=0`); no audio uploads or Azure/Groq calls during CI or hosting setup.

For local checks (not a real deployment):
```bash
cd v2/frontend && npm run check
cd ../..
python -m unittest discover -s v2/server -p 'test_*.py' -v
```
The Render host tests use a disposable private SQLite database and synthetic frontend files; no provider calls or real family data.

## Controlled cutover steps

1. Review the paid Starter+disk cost and privately arrange a dependable off-site backup/restore approach, email verification delivery and production security/privacy review. Family accounts for minors require a verified guardian and consent model **before enablement**.
2. In the Render dashboard, deploy this repo's **single V2** `render.yaml` Blueprint (or equivalent Docker web service + disk). Confirm Render has GitHub App access to `AndrewDionne/LearnPolish` **after it becomes private**; reconnect the repository if necessary.
3. Configure real SMTP secrets and exact `PTP_PUBLIC_ORIGIN` on Render, never in GitHub. Confirm the Render service's build, `/health/ready`, actual `/`, static assets, family health/API sign-in workflow and phone/browser audio & offline behavior. Check backend data survives restart/redeploy and test restore drill before family use. Never test registration with minors.
4. **Only after new Render V2 is healthy**, disable/archive the old `Path to Polish` and `flashcards` Render services, turn off the GitHub Pages deploy workflow/site, and change GitHub repo visibility via **Settings → General → Danger Zone → Change repository visibility → Private**. GitHub connector currently does not expose the visibility mutation. Ensure Render still has access to the now-private GitHub repo and new commits can deploy.
5. Check Render URL on actual Mac/iPhone after changing visibility and repeat a deploy; do not delete V1 lesson/audio inputs while V2's content generator still uses them.

Do not represent a saved private GitHub repository or a configured Blueprint as successful Render hosting until actual live health/route checks confirm it. The backend is still experimental and has not passed guardian enrollment, incident response, and operational backup certification.
