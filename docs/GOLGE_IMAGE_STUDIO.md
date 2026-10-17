# GÖLGE Image Studio — review build, 2026-10-17

Text-to-image for the existing Windows React cockpit and iPhone Cloud PWA.
Stacked on draft PR #59 (`b0b4dbf0481c5650aa64e7cd5c63254164213f71`).
No production merge, Render deployment, credential changes or paid API calls.

## Provider verification

Official sources checked 2026-10-17:
- [Image generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [Imagen migration](https://ai.google.dev/gemini-api/docs/imagen)
- [Pricing](https://ai.google.dev/gemini-api/docs/pricing)

Google's current pages mark Imagen as shut down and Gemini 2.5 Flash Image as
retired on October 2, 2026. The existing default was therefore unsuitable.
The implemented, explicitly allowlisted provider is `gemini-3.1-flash-image`,
using official `google-genai` `client.models.generate_content`, matching the
existing SDK integration. Google's latest recommended family member is Nano
Banana 2.1; this first bounded integration does not silently switch providers.
Another provider can implement the existing callable output contract; it must
have a separately reviewed capability/cost profile before being enabled.

Google lists 3.1 Flash Image at $0.50 / million input tokens, $3 / million text
and thinking output tokens, $60 / million image output tokens; approximately
$0.067 for a 1K image, excluding input/thinking. No free API tier is advertised.
Prices/access must be reconfirmed before enabling. No Search grounding tools
are enabled on image calls.

This release requests **1K** only, with **1:1, 9:16, 16:9** aspect ratios.
1K square is documented as 1024×1024; rectangular dimensions come from the
actual decoded output. It does not promise arbitrary pixels, 2K, 4K or upscaling.
Photo/cinematic/anime/3D/digital-art are prompt styles, not separate models.
Image editing is deliberately **unavailable** in this release. Photo upload,
owner-scoped retention and vision analysis remain on their existing paths.

## Enablement — NOT performed

Server environment (never frontend):

```dotenv
GOLGE_IMAGE_ENABLED=false
GOLGE_IMAGE_BUDGET_APPROVED=false
GOLGE_IMAGE_DAILY_LIMIT=0
GOLGE_IMAGE_DAILY_BUDGET_USD=0
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image
# GEMINI_API_KEY must already be provisioned securely; do not paste into Git.
```

All gates must pass, and each user request requires an explicit browser cost
confirmation. Merely asking to implement this feature does not approve spending.
An existing retired `GEMINI_IMAGE_MODEL` also fails closed.
Limits are global across users/workers: at most 20 calls/day, further restricted
by the configured daily count and floor(daily USD budget / 0.50). Every accepted
attempt reserves $0.50 including failures, cancellations and ambiguous outcomes.
This conservative reservation is not a measured bill. Requests have ≤4000 prompt
characters, 4096 output-token cap, 1K output and one SDK attempt; no automatic
retry or provider fallback. Billing changes still require operator review.
A verified provider-side budget should additionally be configured before use.

Windows needs the existing authenticated local session and paired Cloud bridge.
The Cloud service stores the image; a tokenless desktop image proxy refuses
access. No provider API key or paired-device token enters JavaScript.

## User path

- Type “Bana gerçekçi bir Ferrari fotoğrafı oluştur” or “Telefonum için dikey
  duvar kâğıdı oluştur” in the existing chat. Transcribed voice requests use
  the same intent handler; no new microphone stream or lease is opened.
- Disabled/unconfigured service gives a clear message and makes no provider call.
- When enabled, review the cost confirmation; refusal makes no provider call.
- Generation status appears in chat. ESC / stop suppresses the eventual output.
- Click the finished image to enlarge (Windows: zoom slider); use download/save
  or supported Web Share. iPhone full-size view uses the browser's image zoom.
- Qt download handling now allows only same-origin, numeric Image Studio asset
  routes with PNG/JPEG/WebP MIME and asks for a save location. Other arbitrary
  URLs remain rejected; existing hologram/video download handling is preserved.

Desktop history still uses the existing native owner-authenticated Cloud history
poller. Image messages now preserve image IDs and deduplicate polling arrivals.
The desktop's existing history is an aggregate owner view; it is not a new
thread-picker. New desktop images share a durable image conversation ID, stored
locally and visible in the Cloud history. Phone requests use the current Cloud
conversation ID. Both see the same private asset when viewing that conversation.

## Storage, cancellation and security

- Reuses `generated_images` and existing conversation/message tables. Additive
  `image_requests` ledger: owner + UUID, prompt fingerprint (not prompt text),
  conversation ID, status, reservation and final reference.
- PostgreSQL transaction/advisory lock fences quota and dispatch across workers.
  A duplicate UUID replays a persisted result or returns its existing state;
  altered prompt/options/thread with that UUID returns conflict.
- Worker death or transport timeout never triggers automatic redispatch. `running`
  after a lost worker means uncertain, not success. Operator reconciliation with
  Google billing is required; do not reset that row to retry.
- Early cancellation uses an owner-scoped tombstone; a cancellation from another
  owner cannot affect the request. At most 100 new ledger entries per owner/day
  through cancellation. A new turn is independent from a cancelled turn.
- Google server-side cancellation is **not verified**. Thread cancellation or
  closing the HTTP connection is not reported as stopping generation/refunding.
- Final image, user message, assistant success and ledger result commit together;
  cancelled late output is discarded. Saved completed output is not falsely
  described as cancelled. Expired/deleted output replays return 410, no new bill.
- Real Pillow decode, MIME match, frame count, 8 MiB and 20M pixel caps reject
  disguised/empty/truncated/SVG results; intermediate thought images are ignored.
- Only owner-authenticated private URLs serve images, with no-store/nosniff and
  safe generated download filenames. Redirects never forward desktop credentials.
- Cookie-authenticated writes require matching Origin plus Fetch Metadata;
  paired-device bearer requests retain the existing device boundary.
- The existing last-12 / 30-day image-byte policy remains; daily cleanup also
  expires generated bytes. Chat history shows unavailable assets explicitly.
- Ledger tombstones intentionally persist after bytes expire: pruning them would
  permit old request UUIDs to spend again. They contain no raw images/prompts or
  provider error logs. Account-erasure/lifetime archival policy is a future task.

## Verification and limits

Controlled provider fixtures are clearly synthetic PNGs, not generated AI art.
Real PostgreSQL tests exercise API writes, auth, cross-owner reads, browser
Origin, concurrent duplicate/cancel races, global quota, restart idempotency,
expired replay and persistence. Browser tests use actual Chromium and actual
built React/PWA, with a fake Cloud/provider and, for history, a fake Qt signal.
They do not substitute for physical Windows or iPhone acceptance.

Commands:
```bash
# Use ONLY a disposable local/CI PostgreSQL URL in both variables.
PYTHONPATH=ultron/cloud_service:. pytest -q ultron/cloud_service
PYTHONPATH=ultron/backend:. pytest -q ultron/backend/tests
cd ultron/frontend
npm ci
npm run build
node --experimental-strip-types --test tests/*.test.mjs
npm run test:earth
cd ../..
node --test ultron/cloud_service/test_*.cjs
PYTHONPATH=. python scripts/tests/test_image_download_policy.py
python scripts/tests/test_image_studio_browser.py
python scripts/tests/test_research_source_ui.py
```

Latest measured counts and CI status are recorded in `ULTRON_TEST_RESULTS.md`.
Live Google image generation: **BLOCKED** (no key, enablement or spending approval).
Windows hardware/Qt save dialog and microphone: **NOT RUN** (laptop unavailable).
iPhone Safari/PWA physical zoom/share/save and microphone: **NOT RUN**.
Live image quality, latency, billing and model safety-filter behavior: **BLOCKED**.
No need for the user to run laptop commands during this development stage.

Rollback: disable `GOLGE_IMAGE_ENABLED`; old code can coexist with the additive
ledger. Do not delete ledger rows or user images as rollback. Deploy only after
review and explicit approval, keeping PR #59 dependency order.

## Browser evidence (synthetic fixtures)

The solid cyan PNG is a deliberate test asset, not AI artwork. These screenshots
prove image delivery/layout only, not model quality, Windows GPU or iPhone Safari.

- [Desktop fixture](image-studio/image-studio-desktop-fixture.png)
- [Phone fixture](image-studio/image-studio-phone-fixture.png)
