## 2026-10-14 — Natural Conversation & Voice interruption reliability

- PR #36 fixes a visible interruption bug: stopped desktop Cloud chat no longer leaves `Dashboard` in THINKING or shows the expected AbortError as a failure. The native `interrupt` action remains forwarded; network and timeout failures still notify.
- New Node interruption/state tests: **7 passed** (plain AbortError, browser DOMException, network error, timeout error, unknown error). Frontend `npm run build` passed; `npm run test:earth` **6 passed**; `npm run test:bundle` **1 passed**. Existing Python voice runtime/state/VAD tests: **20 passed**. `git diff --check` and Scene workflow YAML parsing passed.
- GitHub Actions for Scene `verify` and responsive UI passed on the final PR head before the review-ready transition.
- Real device microphone/speech and Gemini/Qwen quality/latency are **NOT_RUN**. No Render deployment occurred; Render health was HTTP 200 at production commit `6ef3f5d207fc9430cbbd552988935995529e87f5`.

## 2026-10-14 — Cognitive intent router v2, local verification

- Production base was fetched and verified as `b6b563d0521a874c46bd0cbe2d1a1ab5e4d8efc0`; PR #30 SHA `9c7817f` is its ancestor. The work is isolated on `feat/golge-cognitive-router-v2-20261014`; prior branch/worktree was clean and left intact.
- New test-first intent suite: `intent_scenarios.json`, SHA256 `e640562e2011e9189471182f570511b5e9181c7e553e59914170db23cb8c8ef4`, 100 cases with 10 balanced categories and 50 Turkish/50 English. `python evals/conversation/intent_eval.py`: **100/100** deterministic route + context/tool label matches. Production b6b563d's old dialogue-act classifier matched **32/100** on these new labels. Repeated in-process route benchmark p50/p95: old **0.003164/0.004637 ms**, new **0.038924/0.080290 ms**; **0 extra model calls**. This is not real model answer quality or model response latency.
- Cloud Python discovery: **345 passed, 60 skipped** for unavailable PostgreSQL/provider/device prerequisites. Backend FastBrain/ModelRouter/Cloud-delivery regressions: **56 passed + 4 subtests**; local-cloud bridge contracts **6 passed**; Earth backend **5 passed**. Frontend `npm ci`, TypeScript/Vite build, and Earth suite **6/6** passed. Existing Vite advisory remains for the 620.10 kB GLTF loader chunk; no frontend source changed. Mobile chat transport **8/8** and panel routing **4/4** passed.
- `python evals/conversation/run.py --validate`: real-answer suite structurally valid at 100 (50 TR/50 EN); provider quality remains **NOT_RUN**. No `GEMINI_API_KEY` is configured and `127.0.0.1:11434` is unreachable. First-token latency, total model latency, actual Qwen selection/inference, actual Gemini answers and physical iPhone behavior are **NOT_RUN**. No mock was scored as a model.
- Public Render health returned HTTP 200 and exact production commit `b6b563d0521a874c46bd0cbe2d1a1ab5e4d8efc0`. Draft [PR #32](https://github.com/fatmakahraman304-hash/ULTRON/pull/32) is open with functional code head `74c932ae5002e9dae4285ffdc5552972ca50514c` and is not merged. Exact-head Actions: Cloud Queue PostgreSQL Integration #38548733163, ULTRON Scene Build Check #38548733148, and ULTRON Local Qwen Listening Analysis #38548733003 **SUCCESS**. No Render deployment was triggered.

## 2026-10-14 — Desktop intent-to-agent dispatch, local verification

- Regression first failed because an explicit “Run the tests” request on the default/general path reached Cloud chat and the API returned no agent result. `merged_api.invoke` now uses the shared `classify_intent`; computer tasks bypass read-only chat and go to the existing local agent with `approved=False`. It returns the actual state/message, distinguishes approval pending, and leaves partial/no-intent results incomplete. Ordinary question remains on Cloud chat.
- HTTP contract covers computer-action dispatch, chat preservation, ignoring a client `approved:true` flag, and an unsupported action not being reported completed. Approval-gate state test covers real server agent `message`. Focused tests **7 passed**; full backend: **1,026 passed, 3 skipped, 6 subtests passed**; `py_compile` and `git diff --check` passed.
- These tests use fake Cloud/agent contracts; no actual Windows command, browser task, Gemini or Ollama inference ran. Physical Windows/iPhone behavior and provider latency remain **NOT_RUN**. Updated code head `e0729e0fe673e94ba9d5112e0d8eb96583ab5ec0` passed Cloud/PostgreSQL #38547400002, Scene #38547399990, and Local Qwen Listening #38547399984. No Render deployment was triggered.

## 2026-10-14 — Search-result evidence honesty regression

- Two new tests failed before the fix: search-result domains were counted as corroborating a claim without source-page evidence, and `evil-arxiv.org` inherited `arxiv.org`'s high reliability score. The discovery engine now labels its output `search_results_only`, returns zero claim confidence, does not infer corroboration/contradiction, and exposes source reliability separately. The capability registry now marks research as an adapter until page retrieval and claim matching exist.
- A previous full-suite run exposed a brittle process-list test that relied on the pytest runner itself being named `python`. It now starts a known Python child process and checks that exact PID. Focused research/process suites: **28 passed**. Full backend suite at `74c932ae5002e9dae4285ffdc5552972ca50514c`: **1,029 passed, 3 skipped, 6 subtests passed**.
- External search/page retrieval was not run. Real Gemini/Qwen quality, device execution and provider latency remain **NOT_RUN**. Exact-head Actions for code head `74c932ae5002e9dae4285ffdc5552972ca50514c` all passed: Cloud/PostgreSQL #38548733163, Scene #38548733148, Local Qwen Listening #38548733003. No Render deployment occurred.

## 2026-10-14 — Conversation policy context-budget regression

- New regressions first failed on the old behavior: a long optional configured prompt hid persona/read-only rules under a 4,500-character budget; a 64-character cap returned a policy fragment; and the local Qwen request did not receive the shared system prompt. The bounded composer now keeps runtime policy intact and local Qwen uses the same configured prompt as Gemini.
- Focused style/context/local-bridge/continuity: **67 passed, 86 subtests passed**. Full `python -m pytest ultron/cloud_service -q`: **275 passed, 60 skipped** (disposable PostgreSQL/integration prerequisites unavailable), 13 warnings. PR #30 one-hour listening JS tests: **22/22**; browser listening tests: **7/7**. `python evals/conversation/run.py --validate`: **100 scenarios valid (50 Turkish, 50 English)**; no Gemini/Qwen inference or quality score was produced. `git diff --check` passed.
- Runtime code SHA `db1fd50b63b1abd1097e0ec5082e833b2e81f15e` is on draft [PR #31](https://github.com/fatmakahraman304-hash/ULTRON/pull/31); current doc head at verification was `971673e1c55b16a4f0389610e8cb7c16b7c61f27`. Exact-head Cloud/PostgreSQL `38541558443`, Local Qwen Listening `38541558445`, and Scene `38541558508` all **SUCCESS**. An earlier Cloud runner could not pull PostgreSQL due to ECR's data limit; rerunning only the failed job passed, without changing the tests. No Render deployment was triggered by this isolated change.
- In authorized My Workspace, the actual GÖLGE service deploy `dep-db7jjdm7bikc73d3h5og` is **LIVE** at PR #30 merge SHA `9c7817f6196850b5e245cd77daba438d519b380b`; public `/health` returned `{"ok":true,...}` with the same SHA. Physical iPhone microphone, Windows Qwen, Gemini inference, model quality and latency remain **NOT_RUN**.

## 2026-10-14 — First-run setup keyboard and persistence regression

- Added an offscreen Qt test for first-boot ordering: the setup child appears before the main window while another input exists underneath. Before the fix, focus remained in that underlying input; after the fix, the setup key field receives focus and accepts typed text. Setup UI and persistence regressions: **2 passed**; `python -m py_compile ui.py` and `git diff --check` passed.
- Root integration tests with `PYTHONPATH=ultron/backend`: **25 passed, 3 failed** in this Linux workspace. Failures are missing `sounddevice`, one unavailable optional health component, and platform-specific singleton-lock behavior. These are outside the setup code. The owner previously reported `INSTALL.bat` completed on Windows; this change has not yet been tested on that laptop.
- The persistence regression confirms existing local model preferences survive first-run setup and saved setup is recognized on the next startup. The Gemini key remains in the existing ignored local config; tests and logs do not print it. Render is unaffected by this desktop-only change.
- GitHub Scene Build Check [#38469167141](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38469167141) passed on exact SHA `1dda1d4f5833a3e52564711c29aa10f7274e1741`. Public Render `/health` returned HTTP 200 at independent Cloud SHA `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c`; no Render deploy was triggered by the native desktop change.

## 2026-10-14 — Windows installation completed

- Owner reran `INSTALL.bat` at handoff HEAD `4648d70` on Windows 11 (Python 3.12.14, Node 24.19.0, npm 11.17.0). The frontend compiled, all install stages including `pytest tests` and `integration.doctor --quick` returned successfully, and the installer printed **`Kurulum tamamlandi.`** The pasted terminal did not show the pytest case count. Ollama's four configured models were already present; the install did not need to download them.
- The first attempt had **27 passed, 1 failed** because the test asserted the retired `ULTRON Hologram` title. Reproduced and corrected the test to assert the current `GÖLGE Hologram` title; focused local regression **1 passed**. No runtime application code changed.
- Local Linux full-suite result was **25 passed, 3 failed** due to missing `sounddevice`, one unavailable health component, and a Linux lock-behavior discrepancy. This is separate from the successful owner Windows run.
- Fixed npm's high-severity transitive `source-map-js` 1.2.1 advisory (GHSA-68fv-2mgg-jv7q) by locking 1.2.2. Clean `npm ci`, `npm audit` (**0 vulnerabilities**), and Vite build pass. The >500 kB chunk message is a nonfatal bundler warning.
- GitHub Scene Build [#38467187863](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38467187863) and Frontend Build [#38467187789](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38467187789) both **SUCCESS** on fix code SHA `4d9b8a7`. Render is a separate cloud service and remains LIVE at `1ad5f28`; this client-only fix did not deploy there.
- Still not run on the physical laptop: launching `START.bat`, real chat/voice/vision and scene acceptance, Gemini inference/fallback behavior, or provider-quality scoring.

## 2026-10-13 — Windows laptop source handoff package

- Confirmed functional code SHA `13b3147eb01a0cdcd1352b5bbf136fda7ab1d56c` before handoff; owner cloned handoff commit `3a6f489`. The later install-feedback fix is commit `4d9b8a7`.
- Built a ZIP with `git archive`; validated required installer/bootstrap/frontend/backend files, 833 archive members, and exclusion of `.git`, `node_modules`, and `.venv`. The archive is source only; it does not include runtime packages, model weights, user settings, or API credentials.
- At package-generation time, Windows installation was not available from this Linux workspace. Owner subsequently installed the source successfully on the physical laptop; see the Windows installation result above. Real Qwen/Gemini inference and latency/quality evaluation remain **NOT RUN**.

## 2026-10-13 — Desktop model, agent, vision and Cloud error privacy

- Test-first regressions reproduced raw provider and user-image text exposure through model health, local chat/image HTTP responses, desktop agent final errors, CloudClient status, and vision debug logging. Public/provider boundaries now expose only stable categories or generic Turkish messages; HTTP 404 and transient provider failures retain distinct classifications.
- Focused suites: **41 passed, 4 subtests passed**. Scene's new model/agent/vision/API privacy step: **22 passed**. It exercises real aiohttp chat/image handlers plus synthetic chat, vision and log failures with fake credentials/user text.
- Full backend suite from repository root: **1,025 passed, 3 skipped, 6 subtests passed in 40.44s**. Python compilation passed. `git -c core.whitespace=cr-at-eol diff --check` passed because the existing vision file uses CRLF line endings.
- Code commits `b327c3de1b8bf4269ddbfb0ea2d2b0715bbf5c16` and `675ea678ec41bd7b88fac645f218a9d1493dcb3f` both passed exact-SHA Scene and Cloud/PostgreSQL Actions: [38460977820](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38460977820), [38460977851](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38460977851), [38462071665](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38462071665), [38462071649](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38462071649).
- My Workspace Render remains LIVE at Cloud SHA `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c`; public `/health` returned HTTP 200 at that exact SHA and error logs were empty. No real Gemini/Qwen calls, device acceptance, or Windows installation were run; this is not a 100/100 conversation score.

## 2026-10-13 — Provider exception privacy

- Reproduced raw exception exposure through a fake vision-provider failure. The handler previously wrote the provider's entire exception string to the event detail. A shared classifier now emits only `provider_request_failed` or `provider_temporarily_unavailable`; transient error detection and the chat 503 response remain intact. The desktop-task watcher also stopped forwarding raw status-fetch exception text.
- `test_provider_error_privacy.py`: **3/3 passed**. The live HTTP vision test verifies a fake API-key-like value and private prompt do not appear in either the response or event record. Static regression contracts cover chat, PDF, camera, Live voice and the task watcher. Full Cloud Python discovery: **323 passed, 60 skipped**; Python compilation and `git diff --check` passed; Cloud workflow YAML parsed.
- App SHA `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c`: Scene Build [#38457949652](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38457949652) and WORLD smoke [#38457949491](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38457949491) succeeded. Workflow SHA `e83b0d5929d1fee256a5165754b66b16b6844766`: Cloud Queue/PostgreSQL [#38458215679](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38458215679) succeeded, including the new privacy regression step.
- Render deploy `dep-db78mn5bedkc738a0fu0` is **LIVE** at the app SHA; `/health` returned HTTP 200 with the exact commit. Actual Gemini failures were not induced; no real model-quality claim is made.

## 2026-10-13 — Frozen bilingual scenario validation

- Test-first regression changed one English case label to `fr`; the previous validator incorrectly accepted the dataset. The validator now rejects languages outside `tr`/`en` and requires five Turkish and five English cases in each of ten categories.
- `python -m unittest ultron.cloud_service.test_conversation_eval -v`: **11/11 passed**. `python evals/conversation/run.py --validate`: **100 scenarios, 10 categories, 50 TR + 50 EN; model quality NOT evaluated**. Full Cloud Python discovery: **320 passed, 60 skipped** for environment-dependent prerequisites. Changed Python files compile; `git diff --check` passed.
- Exact SHA `5677dca638909d23d96aab2dedab2597dbd196c1`: Cloud Queue/PostgreSQL [#38456643001](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38456643001) and Scene Build [#38456642956](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38456642956) both **SUCCESS**. Render deploy `dep-db78i45bedkc7389oi50` is **LIVE** at this SHA; public `/health` returned HTTP 200 with the exact commit.
- The suite's language distribution is now actually enforced. Real Gemini/Qwen transcripts and independent reviews were not run, so no conversational quality score is claimed.

## 2026-10-13 — Typed Live turns enter consent and history

- Test-first integration regression initially reproduced the defect: typed websocket text reached Gemini but did not enter `in_parts`, so explicit `save_memory` consent was invisible and the turn was absent from saved history. The fix adds bounded text to the current turn before provider dispatch; inputs over 16,000 characters return `text_too_long` without being forwarded. The test invokes the real nested browser-to-Gemini, tool guard, and Gemini-to-browser handlers with fake socket/provider/database boundaries.
- Focused `test_live_voice_policy.py`: **8/8 passed**. Full Cloud Python discovery: **319 passed, 60 skipped** for unavailable external prerequisites. Cloud Node/browser suite: **153/153 passed**. `py_compile` and `git diff --check` passed.
- Exact SHA `f932b184eda215585a01d8d5d933b9f682611de1`: GitHub Cloud Queue/PostgreSQL [#38455888395](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38455888395), Scene Build [#38455888286](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38455888286), and WORLD read-only smoke [#38455888333](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38455888333) all **SUCCESS**.
- Render deploy `dep-db78feajnfac73d01fo0` is **LIVE** at the exact SHA; `https://ultron-yubh.onrender.com/health` returned HTTP 200 and reported the same commit. This test uses synthetic Live/database objects; actual Gemini inference, mobile websocket use, and phone microphone behavior remain **NOT_RUN**. The 100-case dataset is scenario coverage, not a model quality score; no 100/100 claim is made.

## 2026-10-13 — Natural Turkish live-voice consent variants

- Test-first regression cases reproduced four false negatives: “Aklında bulunsun…”, “Bunu aklında bulundur…”, “Bunu hafızana yaz…”, and “Bunu notlarına ekle…”. They are now accepted as explicit current-turn requests. “Bunu aklında bulundurma”, “Bunu hafızana yazma”, and “Bunu aklında tutmalı mıyım?” remain non-consent. The complete focused live-voice policy suite passes **7/7**.
- All Cloud Python tests: **318 passed, 60 skipped** for unavailable integration keys/devices/database prerequisites. Conversation dataset validates **100 scenarios: 50 Turkish + 50 English**; this validates data only and does not evaluate model quality.
- Exact SHA `86ad3922f2ae04fe630c0ea08a4d53275a6f32f2`: Scene Build [#38452607673](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38452607673) and Cloud Queue/PostgreSQL [#38452607354](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38452607354) both **SUCCESS**. Render deploy `dep-db783rnavr4c73euva8g` is **LIVE** at the same SHA; `/health` returned HTTP 200 and reported the exact deployed commit.
- A synthetic long-history check at the configured 2,600-character Qwen history limit retained the requested old topic, correction, answer ending, and latest turn. No context budget was changed because this workspace has no Qwen tokenizer/model to measure token occupancy. Real model output and phone transcription remain **NOT_RUN**.

## 2026-10-13 — Live voice consent and capability grounding

- Test-first: new tests initially failed for absent consent policy, no server write guard, credential acceptance, invalid categories, and transcript ordering; corrected behavior passes **7/7** focused tests. They execute the actual nested `save_memory` handler with fake database and Live tool objects: a personal disclosure causes zero writes, an explicit current-turn request writes, credentials cause zero writes, and unsupported categories map to schema-safe FACT.
- All Cloud service Python tests: **318 passed, 60 skipped** for environment-dependent PostgreSQL/key/device integrations; no failures. Conversation persona 13/13, turns 7/7, contextual recall 15/15, response quality 6/6, frozen eval infrastructure 10/10, style 13/13, and development-routing 6/6 also passed in focused runs. App imports from the Render service root; Cloud workflow YAML parses.
- Removed unsupported desktop feature claims from the Live system instruction and constrained delegation to actual task/status/result tools. Instruction text shrank 6,789 → 1,913 characters (72%). This is a prompt-size change, not a measured response-latency gain.
- Exact code SHA `166ae52e4f47421329e60d1d5c474d47e8ef2a9b`: Scene Build [#38449688028](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38449688028) and Cloud Queue/PostgreSQL [#38449688070](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38449688070) both **SUCCESS**. CI initially caught two static tests still checking the old `app.py` prompt location; those tests now inspect the extracted policy module. Render deploy `dep-db77pougekts73dhtjpg` is **LIVE** at this exact SHA; public `/health` returned HTTP 200 and the error-log query returned no entries.
- Real provider evaluation did not run: **0/20** pilot transcripts were captured because this workspace has no Gemini key or reachable local Qwen. This is NOT_RUN, not a model failure or success. Real Gemini Live and phone/laptop behavior remain unverified.

## 2026-10-13 — Deferred 3D startup validation

- `ultron/frontend`: production TypeScript/Vite build passed; `test:bundle` passed 1/1; Earth JS passed 6/6; combined frontend Node tests passed 10/10. Scene-intent and data-only design validators passed.
- Browser validation with real Chromium/SwiftShader passed: scene interaction suite 9/9; new shell-first test 1/1 held the production WebGL dependency, verified chat input remains interactive before it resolves, then verified the actual `.center-stage canvas` loaded with no browser errors.
- Production entry changed from 294.21 kB raw / 84.34 kB gzip to 105.07 kB / 30.92 kB gzip. GLTF/WebGL remains available in a deferred 620.10 kB raw / 158.73 kB gzip chunk. Vite's >500 kB advisory persists, but this chunk is no longer in the initial static entry graph.
- Exact commit `a4f31c66bfb31c1d733ea5ab9d475bf4a8af9f24`: Frontend Build Check [#38445096269](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38445096269) and Scene Build Check [#38445096168](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38445096168) both **SUCCESS**, including the actual WebGL and deferred-stage Chromium checks. Render service root is `ultron/cloud_service/`; the frontend-only commit did not trigger a backend deploy. Public `/health` returned HTTP 200 at backend SHA `c805e1e8fab2d5ca4bd4c8b48ff8d7e3bf7fff9f`. Real Gemini/Qwen answer quality remains unmeasured.

## 2026-10-13 — Whole-system audit at release c805e1e

- Exact commit `c805e1e8fab2d5ca4bd4c8b48ff8d7e3bf7fff9f`: GitHub Cloud Queue/PostgreSQL run [#38440168681](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38440168681) and Scene Build run [#38440168682](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38440168682) both **SUCCESS**. The Cloud run includes real disposable PostgreSQL fencing/privacy cases and Chromium mobile-chat cases with explicitly synthetic providers; these do not measure model intelligence.
- Expanded Python matrix `PYTHONPATH=ultron/backend:ultron/cloud_service python -m pytest -q ultron/backend/tests scripts/tests`: **1,074 passed, 9 skipped, 6 subtests passed**. Skips were for the unavailable user Picovoice key, physical Windows/audio/screen device, disposable PostgreSQL, and one deterministic parser path not recognized in this runtime; no test failure.
- Local reruns: Cloud Python **311 run, 60 skipped** because this workspace lacks integration prerequisites; Cloud Node **153/153**; backend Python **58/58** with `PYTHONPATH=ultron/backend`; scripts Python **62 run, 6 skipped** for optional/environment-dependent cases. Actual headless Qt dock tests **5/5** passed after installing PyQt6 only into this Linux execution workspace. Targeted Python syntax, Cloud delivery guard **17/17**, scene grammar and scene-design validation passed. Real Chromium/SwiftShader 3D scene browser suite **9/9**, mobile composition browser test **1/1**, and scene asset/design API contracts **9/9** also passed.
- Frontend `npm ci`, production TypeScript/Vite build, and Earth JS tests **6/6** passed from `ultron/frontend`. Vite printed a non-failing advisory for `intents-DQRPHuqq.js` at **821.74 kB raw / 222.42 kB gzip**. The initial dashboard statically imports this Three.js chunk for its default WebGL GÖLGE orb; the separate Hologram Lab remains lazy-loaded. A real public-source smoke fetched Poly Haven ArmChair_01 (CC0, **154,988 bytes**) and verified import, move, remove, and undo in actual WebGL. Evaluation dataset validation confirmed **100 scenarios: 50 Turkish + 50 English**; no inference or quality grade was run.
- Render workspace My Workspace: deploy `dep-db76oo6q1p3s73f48g6g` **LIVE** at exact SHA `c805e1e8fab2d5ca4bd4c8b48ff8d7e3bf7fff9f`; build and deploy events succeeded. Public `/health` returned HTTP 200/`ok`. `/static/auto-brain.js`, `chat-transport.js`, `scene-control.js`, `scene-intents.js`, and `sw.js` all returned HTTP 200 and matched checked-in bytes exactly.
- Limits: the workspace has no `GEMINI_API_KEY` and no reachable Ollama at `127.0.0.1:11434`; Render’s `gemini: true` health field indicates configuration only, not a successful inference. Real Gemini/Qwen responses, independent evaluation, physical phone/laptop voice or camera behavior, and Windows installation are **NOT VERIFIED**. No 100/100 result or error-free-everywhere guarantee is claimed.

## 2026-10-13 — Diacritic-tolerant Turkish

- Before fix, “Saka yapma, ciddi konus” was classified as balanced and “Konuyu degistirelim, mimarlik konusalim” failed topic-switch detection. After adding `text_normalization.py`, 44 targeted persona, recall, continuity and recap tests passed.
- Full Cloud Python: 310 tests run, 60 environment-dependent skips, zero failures. Cloud browser suite: 153/153; changed Python modules compile. These deterministic checks do not evaluate live model answers. Gemini key and local Ollama are unavailable in this workspace; real provider quality remains unmeasured. Initial exact-SHA Scene `38439674528` and Cloud Queue PostgreSQL `38439674364` exposed a package import failure: Render imports service files from its root directory, while the desktop imports them as `ultron.cloud_service.*`. The shared helper now uses package-relative imports in package mode and local imports in service mode. The new package-import test, full Cloud Python suite, 153 browser tests, desktop local-brain suite (6), local bridge suite (8), and desktop lease/isolation suite (17) pass after the fix. Fixed commit `c805e1e8fab2d5ca4bd4c8b48ff8d7e3bf7fff9f` passed Scene `38440168682` and Cloud Queue/PostgreSQL `38440168681`; all jobs succeeded, including the repaired paired-Qwen package-import test and 17 desktop lease/isolation tests. Render deployment is LIVE at this exact SHA and `/health` confirms it.

## 2026-10-13 — Qwen readiness probe recovery

- Added a regression proving a failed readiness HTTP request selects Gemini before local queue submission. Existing local-first selection and strict `desktop_offline` fallback tests remain unchanged.
- Cloud Python: 306 tests run, 58 skipped (environment-dependent PostgreSQL/integration prerequisites), no failures. Cloud Node: 153/153 pass. Focused mobile-routing, auto-brain and voice tests: 18/18 pass. Frontend `npm ci`, production build and Earth tests: build pass, Earth 6/6 pass. Vite reports the existing large-chunk advisory.
- Gemini API key and local Ollama are unavailable in this workspace; real Gemini/Qwen conversation evaluation was not run. No model score or live phone-to-laptop success is claimed. Exact-SHA Actions succeeded for commit `52b776a62ec5d236ba8ee4b20e0f9cd02ee235b5`: Scene Build `38438751167`, Cloud Queue PostgreSQL `38438751172`; every job and step succeeded. Render deployment `dep-db76jq0jo6nc738ii4n0` is **LIVE** at this exact SHA, and `/health` returns HTTP 200 with that commit. The runs include real disposable PostgreSQL, private image persistence, mobile Chromium, WebGL and Qwen routing contracts.

## 2026-10-13 — Approval-gated self-development and draft PR

Publisher, CodeGen and rollback targeted tests: 22 passed. Cloud development intent/release contracts: 6 passed. Mobile intent/router contracts: 8 passed; minimal UI and PWA cache contract passed with shell v69. Python compilation passed. Full backend suite: 1,012 passed, 3 skipped for unavailable deterministic parser, owner-provided Picovoice key and physical Windows/microphone/screen; six subtests passed. The frontend production build and Earth suite passed (6/6). GitHub CLI write access was not invoked in this workspace, and physical laptop PR creation has not yet been exercised; deployment/CI follows push.

## 2026-10-13 — Personal briefing suggestions

`test_personal_briefing.py`: 5/5 pass, including plan-backed and saved-goal suggestions with no actions/reminders. Personal panel JS suggestion contract: 4 cases pass (source validation and one-item cap). Local planner and memory tests: 7 pass. Frontend production build passes (Vite reports its existing large-chunk advisory); backend py_compile and Earth config: 5/5 pass. Real device voice and Gemini/Qwen output quality remain untested.

## 2026-10-13 — Correction-aware recall regression

Before fix: new correction test failed because old C180 answer survived but the owner correction did not. After fix: contextual recall 14/14, conversation turns 7/7, reference return 5/5, thread recap 7/7, Earth backend 5/5. `npm ci`, frontend build, Earth frontend tests and required Python compilation passed. These are deterministic code tests, not real Gemini/Qwen response evaluations. Release `202e4f98de3020b77ff4ef2460fa7696e765774c`: Actions Cloud/PostgreSQL `38389301592` and Scene `38389301598` both SUCCESS; full logs inspected, including 6 queue browser and 9 WebGL scenarios. Render `dep-db71706q1p3s73erimfg` LIVE; public health returns this exact commit. Frozen evaluation dataset validates 100 scenarios (50 TR / 50 EN), without inference. No new 100/100 or JARVIS percentage claimed.

## 2026-10-13 — Verified public-model release

- Functional code `bca7e945b689f38bd1c6a6a4cbfac8e997e50b62` is pushed. Cloud/PostgreSQL #38387946739, Frontend #38387946743 and WORLD smoke #38387946860 passed. Scene #38387946750 initially failed because the new HTTP asset test ran before aiohttp installation; no runtime failure was implicated.
- Workflow correction `72f5e91c947efc7df824d166e0641bcc85c450ec` moves that test after dependency installation. Exact-SHA Scene #38388140843 and Cloud/PostgreSQL #38388141206 **SUCCESS**; complete logs read, including five asset contracts, two desktop routing cases, nine actual WebGL cases, scene queue privacy/idempotency and six Qwen synthetic-provider browser cases. No test removed or weakened to conceal the failure.
- Render deployment `dep-db711em7bikc73fnlip0` **LIVE at functional bca7e94**, finished 2026-10-13T11:07:39Z. `/health` HTTP200/ok and scene-control.js, scene-intents.js, sw.js HTTP200 and byte-for-byte match. Shell v66. Later workflow/docs-only commits do not change the deployed runtime. Authenticated production provider/asset sessions were not exercised here.
- Real public-source smoke previously downloaded and displayed Poly Haven ArmChair_01 (CC0, 154,988-byte geometry-only GLB), with movement/removal/undo verified and screenshot inspected. This validates real public asset retrieval; real Gemini/Qwen creative output quality and physical devices remain unverified. Disposable local test database removed. No Windows installation.

## 2026-10-13 — Live-source model search and import

- “İnternetten sandalye modeli bul getir” now searches the dynamic Poly Haven CC0 catalogue (521 public models observed), selects the highest matching result and loads its actual geometry. Common Turkish object terms and English names/tags are supported; the asset ID list is not hardcoded. Unknown queries preserve the scene and report no match. Basic shapes remain instant; “bir masa modeli oluştur” remains the separate conceptual generation path.
- **Real public-source smoke passed:** fetched `ArmChair_01`, converted its declared buffers to an embedded geometry-only GLB (**154,988 bytes**), displayed it in actual Chromium WebGL, moved it, removed it and restored it. Screenshot inspected. Source: https://polyhaven.com/a/ArmChair_01 ; CC0, author Kirill Sannikov. This is real downloaded geometry, not a synthetic provider output. Source/license/author are shown and retained in exported part descriptions. Textures are intentionally omitted for the existing hologram material and modest GPU budget.
- Authenticated same-origin search/download routes share Cloud/desktop implementation. Only fixed HTTPS Poly Haven API/download hosts and model paths; redirects rejected, declared buffers only, 30MB total, max16 buffers, deadline and two-download concurrency cap. External textures/extensions removed before GLB import; existing 200-part/750k-triangle/nonfinite-geometry checks stay. No arbitrary URL fetcher, filesystem deletion, generated code, weight download or extra main-screen panel.
- Preserved remote listening improvements and GÖLGE rebrand through `f53f3e4`. Upstream Cloud CI #38381976427 had stale ULTRON identity assertions; full local tests also exposed an old development-ticket label assertion. Updated those display expectations to the actual GÖLGE behavior while retaining protocol/legacy compatibility tests; PWA shell/cache tests synchronized at v66.
- Local **263/263 Python tests**, including real disposable PostgreSQL with no skips; **147/147 JS**, **9/9 WebGL UI tests**, **6/6 Qwen queue/browser tests**, two desktop routing tests, parser/schema/project validation, npm ci/build, Earth 6 JS/5 Python and py_compile pass. Explicit public-source smoke additionally passes. Gemini/Qwen creative geometry quality and physical Windows/iPhone still NOT VERIFIED; no universal model availability/engineering-accuracy claim. Windows installation deferred. Exact new CI/Render results pending push.

## 2026-10-13 — Shapes and free-form conceptual scene synthesis

- Added direct “daire”, “kare”, “üçgen”, “silindir”, “koni” and “halka” geometry. “Bir masa modeli oluştur” or, inside the scene, “sandalye oluştur” now requests a data-only assembly rather than rejecting every object outside the built-in demo list. Generated assemblies reuse movement, rotation, part selection, removal, reset and project persistence.
- New bounded geometry schema: up to 24 parts, eight primitive kinds, validated dimensions/positions/rotations; provider instruction requests 1–8 meaningful parts for small-model budgets. No generated code, tool call or URL is executed. Invalid output preserves the current scene; closing the workspace prevents late replacement. Generated models are explicitly labelled conceptual, never engineering CAD or downloaded assets.
- Mobile prioritizes actually ready local Qwen, via owner-scoped idempotent scene queue using the existing fenced no-tools worker and shared three-task capacity; only confirmed pre-submission offline rejection allows Cloud fallback. Desktop uses installed Qwen first, configured Cloud otherwise. Scene prompts/results do not enter chat conversations, learning or personal memory. New authenticated Cloud endpoint uses the existing Gemini configuration, no new provider/account/model downloads.
- **Limits:** actual Gemini/Qwen geometry quality and physical Windows/iPhone not tested here. Internet asset search/download is NOT implemented: explicit web-search requests receive an honest explanation. A licensed asset source/download integration remains necessary for that part of the user's request. No claim that every arbitrary object can be reconstructed accurately. Windows installation remains deferred.
- Local checks: **251/251 Cloud Python** with actual disposable PostgreSQL and zero skips (includes three new queue ownership/idempotency/capacity cases); **134/134 JS**, **8/8 Chromium WebGL scene cases**, **6/6 Qwen queue/browser cases with synthetic providers**, two desktop routing tests, schema/parser validation, 18 project checks, npm ci/build, Earth 6 JS/5 Python, py_compile and workflow YAML all pass. Provider outputs in generation tests are synthetic; no actual creativity score measured. PWA shell v63. New CI/Render evidence pending push.

## 2026-10-13 — Verified reset release

- Runtime commit `60403db496d9021668afa15d68763b48df5cbd7a`: Scene #38353845104, Cloud/PostgreSQL #38353845427 and Frontend #38353845172 **SUCCESS**. Read full Scene/Cloud logs; five actual WebGL cases and six synthetic-provider Qwen Chromium/queue cases pass.
- Repaired inherited listening workflow YAML (unquoted colon in step title at line 101); its initial run #38353843296 failed before jobs could start. Fix `52ebff6831dcf2388ed1a196f073e9c7b7276db0` quotes the title and enables manual verification. Exact fix SHA: Scene #38353910646, Cloud #38353913024 and Local Qwen Listening #38353907640 **SUCCESS**, logs read. Listening includes 17 queue/worker tests, five real disposable PostgreSQL privacy cases, three synthetic-mic browser cases and five actual WebGL cases. No failed check remains for this verified code/workflow SHA.
- Render deployment `dep-db6sf9vavr4c73bpbgq0` is **LIVE** at runtime `60403db`, finished 2026-10-13T05:55:46Z. Public health HTTP200/ok; scene-control.js, scene-intents.js and sw.js HTTP200 and byte-for-byte match, PWA shell v62. Later workflow/document-only commits do not change the deployed runtime.
- Physical Windows/iPhone, microphones and actual Qwen/Gemini generation remain unverified. No Windows installation or model download. Conceptual models/owner GLB only; no fabricated 100/100 model-quality result.

## 2026-10-13 — Undoable scene reset and project orientation

- Reproduced a real WebGL regression: reset retained edited rotations, scale and removed parts, including after project reload. Store initial part orientation separately from current view; reset now restores position, orientation, unit scale and visibility, stops active gestures, and remains undoable/redoable. New exports preserve baseline orientation; old project files remain accepted and use their stored part orientation as their baseline (the older exporter did not retain pre-edit orientation).
- Added mobile/desktop “sahneyi sıfırla” / “modeli sıfırla” commands, scoped to an active scene; no file/system actions. Existing scene library and owner GLB limits unchanged. Preserved remote listening additions through `cc2ab74` by fast-forward; PWA shell v62 and Qwen stale-cache test synchronized.
- Local verification: regression failed before fix (rotations); **5/5 actual Chromium WebGL cases passed** after fix, including project reload/reset/undo/redo and mobile reset. Frontend npm ci/build, scene grammar, 18 project checks, Earth 6 JS/5 Python, py_compile passed. These are UI/code tests, not Gemini/Qwen model-quality or physical device evidence.
- CI and Render for this new patch pending push at this checkpoint. Windows installation remains deferred.

## 2026-10-12 — Verified 3D release

- Functional SHA `51e5f52a6fb205e1b805f895f2289287f3cc6e73` is pushed to `feat/ultron-cloud-shared-memory`. The remote Qwen commits through `a03d122` (bounded confirmed-length retry and thought-channel sanitization) were preserved by rebasing the unpushed scene commit, then retested.
- Exact-SHA **SUCCESS**: [Scene + actual WebGL #38305686409](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38305686409), [Cloud/PostgreSQL + Qwen browser #38305686424](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38305686424), [Frontend Build #38305686410](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38305686410). Logs read; generated bundle reproducibility check passed.
- Render `dep-db6kb76q1p3s73akvt70` is **LIVE at that exact functional SHA**, finished `2026-10-12T20:41:02Z`. Production `/`, `/static/scene-intents.js`, `/static/scene-control.js`, `/static/sw.js` all HTTP200 and byte-for-byte match to this commit; health HTTP200/ok. JS cache is no-store, PWA shell v57. Later documentation-only commits do not change this deployed runtime.
- Final merged local tests: **220/220 Cloud Python** including 45 disposable PostgreSQL cases, **93/93 JavaScript**, **6/6 Qwen Chromium/queue**, **4/4 real WebGL Chromium scene tests**, 18 project validation checks and scene grammar suite; 17 client/lease, six local runtime, frontend build, Earth 6 JS/5 Python also passed. No outstanding test failure.
- The engine is a conceptual 21-part procedural model; a brand-specific engineering model must be supplied as GLB. No general text-to-any-3D generator is claimed. Windows install remains deferred. WebGL was tested with Chromium/SwiftShader, not physical iPhone Safari, Windows Qt, real microphones or RTX GPU. Qwen/Gemini browser test providers remain synthetic; physical phone-to-real-Qwen inference still awaits the single device smoke check.

## 2026-10-12 — Command-controlled 3D scene (user-requested follow-up)

- The mobile hologram placeholder is replaced by an actual local WebGL scene, reusing the desktop `HologramScene`. The ~618KB renderer loads only after an explicit scene request; ordinary chat loads only the small intent parser. No external model-generation API, automatic asset download, new main-screen panels or permissions were added.
- “Bir motorun 3D modelini göster” creates a **conceptual** 21-part four-cylinder engine (block, crankshaft, cylinders, pistons, connecting rods, intake and flywheel), not a manufacturer CAD replica. Built-in arm/reactor/cube/sphere and owner-chosen embedded GLB models are supported. Unknown requested models receive a truthful library/upload explanation.
- Turkish UI commands rotate with degrees/axis, move with direction/distance, move aside, scale, select named parts, remove the selected part or complete model, undo and redo. “Onu” means the selected part, or the complete model if no part is selected. “Onu kaldır” asks lift-versus-remove; “onu taşı” asks direction. File/system deletion cannot be dispatched by this parser. Negated, quoted and explanatory requests remain ordinary chat.
- Mobile typed/local-mic text and completed Live input transcripts use the same dispatcher; partial Live transcripts never mutate the scene. Desktop typed requests open the existing Hologram Lab; its command field/native transcript event controls actual meshes. Physical microphones, Windows Qt and iPhone Safari are not tested here.
- Removed parts are undoable. Rotations/scales/removal flags persist in validated project files, with backward compatibility for existing files. Uploaded GLB limits remain 30MB/200 static parts/750,000 triangles; external references and non-finite geometry are rejected before replacing the current model. Scene moves/rotation/scale are local UI operations only.
- Validated: four actual Chromium/SwiftShader tests (mobile manipulations and selection, desktop events/project export-import, real GLB + external-reference rejection, close-during-lazy-load); 18 saved-project checks; Turkish grammar contracts; **215 Cloud Python including 45 PostgreSQL cases, 93 JS and six Qwen queue/browser scenarios** all pass. npm ci/build, Earth 6 JS/5 Python, py_compile, workflow YAML and diff checks pass. Screenshots inspected; camera framing adjusted so moved models remain visible.
- Added CI verifies deterministic generated browser bundles and actual mobile/desktop WebGL. PWA cache is v57. Code/CI/Render evidence will be appended after push. Windows installation remains deferred; existing approval/privacy/device-task controls are unchanged.

## 2026-10-11 — Verified release evidence, Qwen connection repair

- Functional commit: `72ffb35744465626718df83010e73ad36d20c0c7` pushed to `feat/ultron-cloud-shared-memory`; no `main` update.
- Exact-SHA CI **SUCCESS**: [Scene/Frontend #38132619456](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38132619456), [Cloud/PostgreSQL + Chromium #38132619449](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38132619449), [public WORLD smoke #38132619430](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38132619430). Workflow logs fetched/read, including six real-browser scenarios with explicit synthetic providers.
- Render `srv-db20lmei0phs73crgujg`, authorized My Workspace: deployment `dep-db5mdrp5efls73apm39g` **LIVE**, exact functional commit above, finished `2026-10-11T10:38:34Z`. `/health` HTTP200/ok; `/`, `/static/auto-brain.js`, `/static/chat-transport.js`, `/static/sw.js` HTTP200 and byte-for-byte match to the commit. JS responses carry `Cache-Control: no-store, max-age=0`; shell is v56.
- Local final results: 215 Cloud Python tests (includes 45 PostgreSQL cases, zero skips), 93 JS, 17 client/lease, six local runtime contracts, six Chromium scenarios, frontend build and Earth 6 JS/5 Python all passed. No remaining test failure. Before fixes, routing and duplicate-submit regressions failed as expected; refactor-sensitive source checks were updated to the new locations without removing owner/fencing checks.
- This evidence verifies code, synthetic HTTP/queue/model-boundary behavior and deployed assets. It does **not** verify physical iPhone → Render → Windows → real Qwen, real Gemini inference, real model latency/quality, or the historical Windows socket/Live1008 incident cause. Desktop installation/download intentionally not performed. Required next step remains the single physical smoke check described below.
- This documentation-only follow-up preserves the exact tested runtime; its own CI/Render state will be checked separately and reported in the final response.

## 2026-10-11 — Qwen mobile connection repair (baseline `ad2b07f`)

- Reproduced defects: forced typed-chat presence refresh was skipped during Live/microphone activity; HTTP/body reads had no deadline; lost accepted POST responses had no request idempotency; concurrent sends/history refresh could race. Desktop Qwen still used the default executor despite isolated Cloud I/O.
- Implemented fresh forced routing, bounded transport (6s presence, 15s local submit × at most 3 with SAME UUID/body, 8s poll, 150s local total budget), early send lock, server message-ID reconciliation/order and retained optimistic messages. No Gemini fallback after acceptance or ambiguous network failure; only explicit pre-creation offline rejection permits it.
- Owner-scoped PostgreSQL submission deduplication, identical same-attempt local completion replay, bounded completion transport retry without repeating inference, isolated Qwen executor, late reply recovery via history and before next-turn context. Device side-effect retries, fencing and Approval Gate unchanged.
- JavaScript assets now no-store, service worker v56 bypasses HTTP cache on update/fetch. Current server baseline matched GitHub; stale cache on the actual iPhone was NOT established as the incident cause.
- Verified locally: **215/215 Cloud Python tests with PostgreSQL (45 actual DB cases, no skips); 93/93 JS; 17/17 Cloud client/lease tests; 6/6 local runtime contracts; 6/6 Chromium HTTP/PostgreSQL/desktop-handler scenarios; frontend npm ci/build, 6/6 Earth JS and 5/5 Earth Python; py_compile and diff check.** Chromium providers are synthetic, not live Qwen/Gemini.
- Browser cases: Live flags + double submit + next-turn context; lost POST and completion responses (one inference); offline fallback; 22s inference across lease window + poll disconnect; old v55 cache replacement; page closure with delayed reply recovery. Actual task result metadata checked `completed`, `local-ollama`, `qwen3:4b` **under a fake Ollama HTTP server**.
- CI and Render verification for the new commit: pending push at this checkpoint; append exact evidence after verification. No Windows install, model swap/download, production chat readout or secret logging.
- Physical iPhone → Render → Windows Qwen and real Gemini inference remain **NOT VERIFIED**; no credentials/VPN/hardware access in this environment. Historical WinError10054/10060 and Live1008 were not reproduced on the user's devices. A closed-default-executor failure was reproduced synthetically and the new independent Qwen executor passed.

## 2026-10-11 — Transaction-safe local chat queue and Qwen-only answer origin

- Functional commits `2e2eedd45dee6aa9577f6f512e026ae2fa008af8` and `5f0f709c7d97fa7f2b66bdcbdaff83987f0f8b50` in `feat/ultron-cloud-shared-memory`.
- **Real PostgreSQL:** Atomically serialize local-chat submissions using owner-specific transaction advisory lock. One queued/delivered message per owner/conversation; global owner cap 3 now checked inside the same lock. Both simultaneously submitted same-thread messages cannot be queued; tests verify one 202, one 429 and one persisted owner user message. After first Qwen response is marked completed and fetched/persisted, the same conversation accepts a follow-up with prior answer in scoped history. Separate conversations can still use remaining queue slots.
- **Provider identity:** `local_reply_validation.py` now rejects `local-ollama` without a verified Qwen family model label, even when a legacy desktop omits provider. LLaVA/Llama/blank model labels rejected; correct namespaced Qwen and `local-no-image` with empty model retained. Matching helper shared with actual local model selection and evaluation.
- Verified code exact SHA `5f0f709c7d97fa7f2b66bdcbdaff83987f0f8b50`: [Cloud Queue PostgreSQL Integration 38122601917](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122601917) **SUCCESS**; [ULTRON Scene Build Check 38122601915](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122601915) **SUCCESS**. Previous exact SHA `2e2eedd`: [Cloud 38122481638](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122481638) and [Scene 38122481653](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122481653) also **SUCCESS**.
- Still to address: reply completed but not yet saved may not count as pending in queue. Live Gemini/Qwen 20/100-case human-reviewed benchmark, model latency, current Render deployed commit, physical iPhone/Windows voice are **NOT VERIFIED**. No `main` or Windows changes; no measured intelligence gain claimed.

## 2026-10-11 — Ollama token-limit completeness and correct source attribution

- Final functional code SHA `78a9a9de314888f1c7adea4ca6613575603bac34`; [Cloud Queue PostgreSQL Integration #38119041641](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38119041641) **SUCCESS**, [ULTRON Scene Build Check #38119041637](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38119041637) **SUCCESS**.
- `local_chat` now rejects Ollama `done_reason=length` even if `done=true`, rather than silently displaying a token-cut response as complete. Unit tests verify this plus normal `stop` response and previously accepted compatibility cases; original code `66ad747` passed both CI #38118862678 and #38118862643.
- `local_reply_validation.py` strictly accepts a nonempty text `assistant_reply`, known provider and string model label; no-image notices are stored with `desktop-local-no-image` device provenance, while actual Qwen remains `desktop-local-ollama`. Unexpected provider and JSON/list reply payloads are rejected. Once-only transaction lock and owner checks remain. First implementation `b2248db` had red frontend CI due to optional `aiohttp` missing in lightweight test; extracted the pure helper in `78a9a9d` so both workflows are green. No automated retries, model downloads or permission changes.
- Caveat: CI runs mock/local contract and disposable PostgreSQL tests, not actual user Windows GPU Qwen generation or Gemini inference. Authentic 20/100-case conversation quality, Render LIVE SHA, laptop/iPhone voice latency remain unverified; no claim of improved percent or 100/100 score.

## 2026-10-10 — Consistent Qwen continuation instructions and strict response validation

- Functional code at `303b18df36cf1428da234228fe4f8fd2e07a21da`, previous feature `14727eda`, updated static integration test `4b1ec463`. CI: [Cloud Queue/PostgreSQL 38082521495](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38082521495) **SUCCESS** and [Scene/Frontend 38082521796](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38082521796) **SUCCESS**; previous patch Cloud #38082401537 and Scene #38082401280 also success. Earlier initial change CI failed on obsolete static variable-name contract; that test was corrected, then both workflows passed. Do not hide or misreport the initial red CI.
- Mock Ollama tests: bare Turkish/English continuation inherits previous explicit detail/brief mode in model instruction *and* bounded generation maximum. It uses fixed style hint only (no raw untrusted conversation content promoted to system) and skips hint if the full trusted system prompt would otherwise be truncated. Mock response validation rejects malformed message content, non-string content, blank output, `done=false` partial output and mismatch between returned Ollama model label and requested Qwen. Valid output continues with one no-tools Ollama request.
- These are provider-free code-contract results, NOT real Gemini/Qwen model intelligence or measured latency. 20/100 model quality scenarios have not been run; no JARVIS percentage raised. No Render workspace selected for live deployment verification, and Windows/iPhone hardware and final Windows update unchanged.

## 2026-10-10 — Bare continuation model choice + reply length inheritance

- Functional code at `14f2fe11d9bace632e6dafc78572e00b43918875` on branch `feat/ultron-cloud-shared-memory`, initial patch `a83e8cac974804e34df774feb95ffedcfb630819`. Latest exact-SHA [Cloud Queue/PostgreSQL run 38081941536](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081941536) **SUCCESS** and [ULTRON Scene Build Check run 38081941541](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081941541) **SUCCESS**. Initial patch [Cloud #38081817720](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081817720) and [Scene #38081817699](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081817699) also **SUCCESS**.
- Deterministic mock Ollama contract tests cover `Python kod yaz` followed by `Devam et` selecting installed coding Qwen, `Python öğreniyorum` followed by `Continue` selecting conversational Qwen, repeated bare continuations, no-code constraints, new unrelated user topics, and ignored assistant/system spoofed messages. Follow-up `Devam et` following an explicit detailed or brief previous request preserves bounded 360+/<=160 token max respectively; new unrelated requests revert to default. Current prompt only is never silently rewritten.
- Remaining: genuine provider latency/accuracy/fluency testing, human review of 20/100 scenarios, latest Render live SHA and real Windows/iPhone inference are **NOT VERIFIED**. Mock/test success must never be represented as 100% conversational intelligence. No Windows installation or main-branch changes performed.

## 2026-10-10 — Real installed Qwen only + tech-chat versus coding routing

- Latest functional code SHA: `22edb909a93f7a4c4d6d4579994cf5bd12a83a75` (initial identity/readiness code `6c474f66d85a50302569642cdd4e988a1d707d22`). [Cloud Queue PostgreSQL Integration #38081094332](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081094332) **SUCCESS**; [ULTRON Scene Build Check #38081094309](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081094309) **SUCCESS**.
- Offline contract tests added: local chat is NOT ready if only `llava:7b` is installed, and actual inference rejects that inventory rather than making visual-model calls for regular text. Mixed `llava:7b` + `qwen2.5-coder:7b` correctly selects installed Qwen; evaluation `is_qwen_model` uses the same helper as production. Plain language learning prompts (`Python öğreniyorum...`, `React öğrenmek...`) and negated code requests select chat routing, while explicit code generation/debug selects coding model, confirmed by one mocked Ollama payload per case in TR/EN.
- Previous code CI at `6c474f6`: [Cloud #38080922802](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080922802) and [Scene #38080922875](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080922875) **SUCCESS**.
- Does NOT establish a measured model intelligence gain or real laptop GPU latency improvement. The real Gemini and local Qwen 20/100 case human-reviewed evaluations, exact Render deployment SHA and physical Windows/iPhone inference remain **NOT VERIFIED**. `main` and Windows left unchanged.

## 2026-10-10 — Prevent invented image contents in text-only Ollama chat

- Functional commits: `3547fcb6948a78c919c1f87c6569d158aab48ed5` (text-only local visual request no longer invokes vision Ollama; desktop reports the no-image provider instead of a fabricated Ollama result); `c8be0b96f172649a2846e2a860717c56487b5d18` (Turkish/English grounded replies); and `599d8aa709cb1288d95fc3313cc24ab7c4577707` (explicit *how-to* tutorial questions still invoke installed text Qwen instead of vision LLaVA or no-image error).
- Offline mock tests: direct Turkish `Bu fotoğrafı analiz et` and `Şu ekran görüntüsünü oku`, English `Analyze this screenshot` and `What is in this picture?` produce a truthful missing-image notice, empty model label, distinct provider and zero Ollama API/inventory calls. Tutorial prompts in both languages use one Qwen text inference in mocked local model inventory, even if LLaVA is also installed. Ordinary `Mercedes C180 bakımı?` still reaches Qwen.
- GitHub final code SHA `599d8aa709cb1288d95fc3313cc24ab7c4577707`: [Cloud Queue PostgreSQL Integration run #38080586438](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080586438) **SUCCESS**, [ULTRON Scene Build Check #38080586446](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080586446) **SUCCESS**. Previous code `c8be0b9` Cloud #38080465402 and Scene #38080465619 also SUCCESS.
- Not verified: actual image input to mobile local chat (**NOT IMPLEMENTED** by this change), real Gemini/Qwen 20/100 conversation benchmark, model inference latency and correct image perception, latest Render LIVE commit, physical Windows/iPhone device routing. No Windows update or model download occurred.

## 2026-10-10 — Shared Qwen reply-length policy + accurate response-quality flag

- Functional code `a7134b0f6479649434c737077b22ee08f6733434` and `ac1e9556851c9943804b838275b2e7b0ec14a2b3` on `feat/ultron-cloud-shared-memory`.
- Extracted one pure shared TR/EN negation-aware reply-length classifier into `reply_policy.py`; Cloud persona and local Ollama use the same decision. Explicit brief max generation 96–160, normal at least 240, explicit detail at least 360, unchanged ceiling 420 and local max context 4096. The final affirmative instruction wins. Unit/mocked loopback tests show `Detaylı anlatma, kısa cevap ver` does not waste detailed generation budget, while `Kısa cevap istemiyorum, detaylı anlat` uses detail. This does not measure actual laptop speed.
- Presentation quality flags now honor the same classifier; negated `kısa cevap istemiyorum` no longer falsely marks a long requested answer as too long. Existing finalization still does not truncate requested text. Regression tests added.
- Exact code CI completed SUCCESS: [Cloud Queue PostgreSQL Integration #38080025754](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080025754), [ULTRON Scene Build Check #38080025720](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080025720). Earlier first change [Cloud 38079929332](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079929332) and [Scene 38079929341](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079929341) SUCCESS.
- Live Qwen/Gemini model quality and inference latency, Render latest LIVE SHA, physical Windows/iPhone operation remain unverified. No Windows update or model download; no 100/100 claim.

## 2026-10-10 — Historical correction and future reminder distinction

- Latest functional code `800a54d07e0159cec063c67f7555a94abe2ced48` (historic Q&A-correction commit `dc97a58`). GitHub [Cloud Queue PostgreSQL Integration 38079636700](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079636700) **SUCCESS** and [ULTRON Scene Build Check 38079636678](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079636678) **SUCCESS**.
- New unit+real PostgreSQL regression: retrieve oldest matched `Mercedes C180 2009` question, its assistant answer, and immediately following owner `Hayır, 2010'u kastettim` without the topic repeated, across 115 subsequent messages. Tenant and thread secrets omitted, before-current filter applied and context/turn bounds preserved.
- Real PostgreSQL and deterministic tests for distinction between future reminders (`yarın saat 9'da hatırlat`) and named historical recall. Future reminders use recent scoped context rather than topic matching; no actual reminder insertion is claimed.
- Cloud/Frontend CI verifies code routing, not live Gemini/Qwen reasoning, factual correctness, latency, Render exact deployed SHA or physical device voice. 100-case quality score NOT MEASURED; Windows unchanged.

## 2026-10-10 — Gemini/Qwen latest instruction + topic switching verification

- Functional code `ec566816ef4eeaa162b579f05f86bb0828ff4237`; parent `a08b3afadaed0f17ec67bfdbab6a3ebe5375b8bf` also passed both CI workflows.
- Tests added: overlong current input retains both opening and end-of-message correction under 3k Qwen and 16k Gemini wire caps; local mock Ollama receives late correction. Explicit topic switching in Turkish/English selects bounded recent same-thread history only and common persona adds TOPIC SWITCH hint. Real disposable PostgreSQL test inserts old Mercedes history, newer mimarlık history, and different owner/thread secrets: no old-topic keyword revival or tenant leakage.
- Cloud Queue PostgreSQL Integration [38078914038](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078914038): **SUCCESS**. Scene/Frontend [38078914033](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078914033): **SUCCESS**.
- Actual real-model correctness/style/logic evaluation remains NOT MEASURED. Production Render SHA and physical iPhone/Windows not verified. No Windows change.

## 2026-10-10 — Current prompt head+tail retention, not history alone

- Functional SHA `a08b3afadaed0f17ec67bfdbab6a3ebe5375b8bf` — Cloud Queue PostgreSQL Integration [38078688366](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688366) SUCCESS; ULTRON Scene Build Check [38078688244](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688244) SUCCESS.
- The old production Qwen and Gemini wire formatting discarded the last part of long **current** messages via `[:3000]` and `[:16000]`, respectively; Qwen's `local_chat` pre-truncated even earlier. Both now retain the latest user correction with a bounded head/end excerpt, within unchanged prompt lengths. Tests exercise both wire formatters and local Ollama mocked outgoing payload.
- Real Gemini/Qwen quality scores, Render exact deployed SHA, Windows and iPhone microphone/inference verification: NOT MEASURED/NOT VERIFIED. No Windows installation or model download performed.

## 2026-10-10 — Negated reply-style instructions and colloquial followups

- Functional code `0f0f9936d3407d63e91218adb5b5e7645b63971f` following `3d07bf4`.
- Tests now cover `Şaka yapma` / `No jokes` without conflicting playful directions, `Kısa cevap istemiyorum, detaylı anlat`, `Detaylı anlatma, kısa cevap ver`, latest affirmative reply-length priority, casual `Yok, onu demedim`/ `Aslında` corrections and `Onu/Buna/Şunu` followups.
- Cloud/PostgreSQL [run 38077714651](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38077714651) SUCCESS. Scene/Frontend [run 38077714632](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38077714632) `verify` job SUCCESS; workflow final state pending in last check.
- **Still NOT RUN:** Real Gemini or Qwen speech/conversation benchmark, independently reviewed 100-case score, exact Render LIVE SHA, physical Windows/mobile. Infrastructure CI successes do not prove JARVIS-level intelligence, and no actual percent improvement can be claimed.

## 2026-10-10 — Pilot availability / non-Qwen mislabelling guard

- Functional SHA `ceef1f499ccb5690de3bdcd8289873a5d6f8c52f` (initial feature `bf9ddc28b112266228a606e4c2fd817a7625f558`). Cloud/PostgreSQL CI [38076948096](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38076948096) **SUCCESS**; Scene/Frontend [38076948157](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38076948157) **SUCCESS**.
- New unit tests check that pilot includes 2 per category/1 Turkish and 1 English, never modifies frozen SHA256, and that Qwen-family labels are recognized while Llava/Llama/QwQ/other models are rejected as Qwen. A no-network CLI pilot test with missing Gemini key verifies actual `not_run` status and null model score rather than fake 20/20 success.
- Pilot requests can produce real model transcripts only on a host with configured authorized API key or installed reachable local Qwen; **none were actually available/tested here**. CI passing does not measure quality, inference latency or true production deployment. Exact Render LIVE SHA, Windows/iPhone device behavior unverified; final Windows update postponed.

## 2026-10-10 — Oldest historical Q&A survival under dense matches

- Code SHA `f73d43358715358dc21b48f4b34c510307627f3f`. [Cloud Queue PostgreSQL Integration run 38073658327](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073658327): **SUCCESS**. [ULTRON Scene Build Check run 38073658416](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073658416): **SUCCESS**.
- Regression: Named-topic search no longer samples only the latest 24 historical matching rows. It checks oldest and newest 16 matching rows in separately scoped SQL, takes bounded best lexical candidates with paired adjacent Q&A, and retains up to existing model context limits. Added test with 42 old keyword repetitions and 105 recent turns on disposable PostgreSQL; other users' and conversations' messages are not included. Normal pronoun followups do not invoke deep retrieval.
- This CI confirms code/regression behavior, not real Gemini/Qwen reasoning quality. 100-case conversation score, Render LIVE SHA and real mobile/Windows voice inference **NOT VERIFIED**; Windows update intentionally untouched.

## 2026-10-10 — Evaluation integrity + actual Gemini model identity

- Functional code SHA `043a5386e510bc81a1bc163d9887cef8f75a4071`. GitHub [Cloud Queue PostgreSQL Integration #38073193493](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193493) **SUCCESS**; [Scene Build Check #38073193481](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193481) **SUCCESS**; [ULTRON WORLD Live Read-only Smoke #38073193495](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193495) **SUCCESS**.
- Added evaluation tests: altered/transplanted transcript hash invalidates review, generated human-review templates keep five criteria null, missing latency statistics stay null, nearest-rank p95/median are deterministic. Same production `_gemini_reply` wrapper is compiled with no-network fake model generation for primary and fallback paths; default production callers still receive a string.
- All scores remain unmeasured until 100 actual captured responses and independent reviews per provider. Hash linkage is content integrity, not provider authenticity or proof of factual correctness.
- CI does not establish a LIVE Render commit or physical-device voice/inference functionality. No Windows update, model download, or private credential usage performed in this continuation.

## 2026-10-10 — Long historical answer final-correction coverage

- **Functional SHA:** `4a196658820aa38f747cb6cd1e74a12714c59eaf`.
- GitHub Cloud Queue PostgreSQL Integration [38072623731](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38072623731): **SUCCESS** (including a new long-history + tenant isolation regression).
- GitHub ULTRON Scene Build Check [38072623801](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38072623801): **SUCCESS** (synthetic question/answer ending preservation and unchanged frontend build).
- Historical matched messages no longer lose a trailing conclusion merely because the old exchange was long; the code selects the start and end within the prior character quota. Includes tests of model-visible prior question, final answer, recent dialogue, total token-related character budget, and absence of other owner/thread content.
- The earlier `064a9f6` release fixed incidental-recent-mention suppression of old Q&A; these tests add protection for the final statements within that evidence.
- The 100-scenario real Gemini/Qwen assessment and Render live commit for this newer code remain **NOT VERIFIED**. No model quality score, no claimed production/hardware validation and no Windows download/install.

## 2026-10-10 — Named historical recall and late-correction quality regressions

- Functional HEAD: `1e5e11002a471d041023e5c8efd95047b733442b`; prior context commit `d9d1f9ac33d75fd558671a2f3fafc7ab376dd5af`.
- **Exact-HEAD Cloud Queue PostgreSQL Integration** [38071243972](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071243972): **SUCCESS** (persona policy and real disposable PostgreSQL checks).
- **Exact-HEAD ULTRON Scene Build Check** [38071243961](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071243961): **SUCCESS** (regressions, browser contracts and frontend build).
- Prior commit likewise passed Cloud #38071107141 and Scene #38071107135. New regression cases test a named first-topic exchange beyond 80 messages with real PostgreSQL owner/thread isolation, deterministic deep retrieval, short technical/acronym topics, beginning+ending preservation in long prior user statements, and read-only persona evidence discipline.
- **NOT_RUN:** Actual Gemini and Ollama/Qwen transcript grading; owner hardware inference/latency, mobile microphone/voice, Windows update. No conversation-quality score. Render exact deployment for this code has not been confirmed.

## 2026-10-10 — Continued natural conversation: true midpoint in long recaps

- Functional SHA: `066b7b982a19c97297a2d74ee4cf68a4a9c4d336`.
- GitHub Actions Cloud Queue PostgreSQL Integration [38070614904](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614904): **SUCCESS**, including new 120+ message real PostgreSQL recap/multitenant regression.
- GitHub Actions Scene Build Check [38070614899](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614899): **SUCCESS**.
- New deterministic `test_thread_recap.py` case verifies true beginning, true midpoint, recent end, role/character bounds and identical authenticated-thread query predicates. New `test_conversation_turns_postgres.py` case verifies content from the true middle after >80 turns and excludes another conversation and another owner. Existing Cloud and frontend CI remain green.
- **Limit:** This is deterministic infrastructure verification, not proof of naturalness or model accuracy. Real Gemini and Qwen evaluation still NOT MEASURED; no 100/100 score. New Render deploy commit / device tests were not independently checked.

# ULTRON — Gerçek Test Kayıtları

## 2026-10-09
**Başlangıç HEAD:** `0638b116c30d221f4167a4df35381a5697237668`.  
**Son kod/CI referansı:** `afe9f5b6855fc4742e384a4d298b71ee6c6feb18`.

### GitHub Actions: PASS
- Workflow: `ULTRON Scene Build Check`
- Run: `37893780863`
- GitHub commit: `a010726149f7a1352933a2e45af51f9b1a985662`
- Görülen başarılı adımlar:
  - Python 3.12 değişen kaynakların `py_compile` kontrolü.
  - `test_earth_watch_config.py` saf backend state regresyonları.
  - `test_ultron_dev_resume.py` read-only devam raporu regresyonları.
  - `python scripts/ultron_dev_resume.py --json`.
  - `npm ci`, `tsc --noEmit`, Vite üretim derlemesi.
  - `npm run test:earth`: geospatial, input wrapping, equinox/solstice ve UTC güneş testleri.
- Önceki kod HEAD `7f89ba130485536fa6e655ef942a782a39b44632`: `ULTRON Scene Build Check` PASS.

### Çalıştırılmamış / dış ortam bağımlı
- Windows 11 cihazında `START.bat` ve gerçek masaüstü UI etkileşim smoke testi: **NOT RUN**.
- RTX 2050 üzerinde FPS/VRAM benchmark: **NOT RUN**.
- Gerçek mikrofon, hoparlör, wake-word ve Gemini Live/Cloud uçtan uca: **NOT RUN**.
- Gerçek ISS API erişimi: **NOT RUN** (hata durumunda UI fallback kodlandı).
- Tüm Python pytest suite: **NOT RUN**.
- Render deployment SHA doğrulaması: **NOT CHECKED**.
- Testler derleme ve saf mantık sözleşmesini doğrular; gerçek cihazdaki başarının yerine geçmez.

## Sonraki turda
Yeni testler/CI sonuçları için run ID ve tam commit SHA yaz. Olmayan testi PASS gösterme.

### Cloud task queue regresyonu — PASS
- Workflow: `ULTRON Scene Build Check`, run `37894840971`.
- Kod HEAD: `34b80e43abe023e58a8f65c87688aa104d6d55e7`.
- `python -m unittest discover -s ultron/cloud_service -p 'test_device_queue_contract.py' -v`: **6 tests PASS** (`Ran 6 tests in 0.135s, OK`).
- Senaryolar: parallel claim, direction guard, late duplicate completion, inactive command statuses, retry limit, SQL atomic status checks.
- Aynı run: Python syntax, Earth backend, resume tests, Node/npm install, TypeScript/Vite build, Earth math test: PASS.
- Hatalı test harness ilk aşamalar: `37894708692` (source path) ve `37894774521` (fake aiohttp exception constructor) FAILED; düzeltildi.
- **Kapsam sınırı:** AST-extracted gerçek handler fonksiyonları fake DB ile çalıştırıldı; gerçek PostgreSQL advisory lock semantiği, Render deploy, telefon-laptop runtime ve Windows smoke **NOT RUN**.


### 2026-10-09 — Cloud attempt fencing: verified PASS
- **Final code SHA:** `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`.
- **Scene Build Check:** `37897505788` — **PASS**.
  - Python syntax/py_compile: Cloud app, laptop `mark_app.py`, `cloud_client.py`, Earth/backend.
  - `test_earth_watch_config.py`: **5 PASS**.
  - `test_device_queue_contract.py`: **14 PASS**.
  - `test_ultron_dev_resume.py`: **3 PASS**.
  - Frontend TypeScript/Vite production build: **PASS**.
  - Earth geographic regression: **6 PASS**.
- **Cloud Queue PostgreSQL Integration:** `37897505793` — **PASS**, **4 tests** on disposable PostgreSQL 16 service.
  - Parallel claim single-agent lane; retry/reclaim increments fencing generation.
  - Old worker cannot complete a new delivery; current worker can.
  - Old worker cannot renew lease or write progress/checkpoint.
  - Legacy one-shot wake completion remains accepted.
- **Fixed failures honestly recorded:** early integration CI `37897241297` failed due to SQL `$3` type ambiguity plus raw JSONB response; `37897368506` failed due to test-side JSONB string parsing. Both corrected before final PASS.
- **Limitations:** Real Render production deployment/phone/Windows/RTX microphone/Gemini Live end-to-end **NOT RUN**. Disposable real PostgreSQL is not a production deployment test. Cloud callback fencing does not prove exactly-once local tool side effects.


### 2026-10-09 — Desktop Cloud ownership loss + stale worker guard: VERIFIED CI PASS
- **Kod commit:** `d96638e1ecaad7d0b800e20fb22580ade555e777`.
- **Workflow:** `ULTRON Scene Build Check`, run `37914696238` — **SUCCESS**.
- Python `py_compile` (backend/Cloud/client/mark_app): **PASS**.
- `test_earth_watch_config.py`: **5 PASS**.
- `test_cloud_delivery_guard.py`: **10 PASS** (6 RemoteLeaseGuard davranışı + 4 CloudClient HTTP sınıflaması).
- `test_device_queue_contract.py`: **14 PASS**.
- `test_ultron_dev_resume.py`: **3 PASS**.
- `npm run build`: **PASS** (Vite 3.28s); `npm run test:earth`: CI step **PASS**.
- **NOT RUN:** gerçek Windows üzerinde `START.bat`, Gemini Live sesli agent ve telefon görev uçtan uca testi; Render deploy SHA ve kullanıcı hesabı; gerçek enjekte edilmiş ağ kopmasıyla side-effect kontrolü.
- **Gerçek kapsam:** Cloud HTTP status handling ve lease monitor unit/regression testleri; `mark_app.py` import/syntax ve CI bağlantısı. Gerçek harici tool side-effect exactly-once **kanıtlanmadı**.


### 2026-10-09 — Durable desktop dispatch fence (CI SUCCESS)
- Yeni `cloud_dispatch_journal.py` ve `test_cloud_dispatch_journal.py`, `mark_app.py` entegrasyonu ve Scene CI adımı eklendi.
- `ULTRON Scene Build Check` run `37915768918` **SUCCESS** @ kod SHA `afe9f5b6855fc4742e384a4d298b71ee6c6feb18`; GitHub Actions job `verify` SUCCESS. Gerçek Windows/Cloud/Gemini Live E2E **NOT RUN**.
- Doğrulanması gereken: ilk claim, yeniden claim, restart, corrupt DB fail-close, concurrency, plaintext gizliliği, pre-dispatch wiring ve Approval Gate etkilenmemesi.

- **CI logları:** 11 durable dispatch journal testi PASS (first/duplicate/restart/changed-payload/different command/scope, no plaintext, invalid/corrupt fail-closed, concurrent reserve, pre-dispatch wiring). Diğer saf Python test grupları: 10 lease, 14 Cloud contract, 5 Earth backend, 3 resume = toplam 43 PASS. Python compile ve frontend TypeScript/Vite production build PASS; Earth math test step PASS.
- **Bilinen sınır:** `RemoteDispatchJournal` aynı yerel sqlite'ı paylaşan masaüstü komutları için at-most-once Gemini dispatch sağlar. Tool-level exactly-once, Cloud-prod deploy/Windows/telefon gerçek cihaz doğrulaması değildir; crash sonucu belirsiz görevleri manuel kontrol gerektirir.


### 2026-10-09 — Native iPhone Siri task / iOS Bridge (CI PENDING)
- Native XcodeGen/iOS Simulator/unsigned device derleme sonucu henüz doğrulanmadı; gerçek iPhone Siri, kilit ekranı, Cloud-login, Kestirmeler ve Windows laptop uçtan uca **NOT RUN**.


### Native iPhone v0.3 — CI PASS (2026-10-09)
- Kod commit: `0b4751a5d7c5f6ceb4642af4eb413f6fb0ca16b9`.
- Native iOS Build: [GitHub Actions 37917812910](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37917812910), **SUCCESS**.
- Yeni Siri/Shortcuts native sözleşme testleri: **5 PASS** (authenticated desktop queue, explicit user tap/allowlist, handled WS events, bounded Siri HTTP/status route, Keychain storage).
- XcodeGen: **PASS**; iOS Simulator compile: **BUILD SUCCEEDED**; unsigned iPhone compile: **BUILD SUCCEEDED**; unsigned IPA 178K ve Xcode project zip artifacts: **upload PASS**.
- Önceki hata açık kaydı: iOS 18 deployment'da kullanılamayan `IntentModes` (iOS 26+) compile ERROR; `openAppWhenRun = false` iOS18-uyumlu yöntemle düzeltildi ve PASS alındı.
- Bu statik kontrat testleri runtime Siri, locked-screen/Apple Shortcuts ve gerçek cihaz onaylarının doğru çalıştığını kanıtlamaz; gerçek iPhone/Windows/Render/prod deployment **NOT RUN**. İmzasız IPA cihaza doğrudan kurulamaz.


### 2026-10-09 — TestFlight workflow (implementation only, NOT PUBLISHED)
- `.github/workflows/ios-testflight.yml`: opt-in manual-only protected environment; Apple certificate import, provisioning profile download, signed iPhone archive/export, TestFlight upload; ULTRON SVG source to AppIcon render.
- `ios/ULTRONMobile/tests/test_testflight_release_contract.py`: 4 static checks; `Native iOS Build` CI result pending.
- Apple Developer membership, certificates, App Store Connect app record/API key, TestFlight publication/invitation, real device install: **NOT RUN**.


### 2026-10-09 — TestFlight hazırlığı native CI doğrulandı
- TestFlight yayın hattı `.github/workflows/ios-testflight.yml` **yalnız elle** ve **sadece main** dalından çalışır; protected `testflight` environment ve Apple signing secrets/variables şarttır. Apple'a yükleme bu ortamda **NOT RUN**.
- Kod SHA `076e9962959c7ce091dec440d2ec1a54673f4d10` için [Native iOS Build run 37919528795](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37919528795): **SUCCESS**. Native iOS regresyon/sözleşme testleri, Simulator build, unsigned iPhone build, unsigned IPA ve Xcode projesi artifacts başarılı. Bu *imzalı TestFlight IPA* veya gerçek cihaz doğrulaması değildir.
- Apple Developer Program üyelik, App Store Connect app record, distribution certificate .p12, provisioning profile ve p8 App Store API key henüz sağlanmadı; gerçek TestFlight upload, processing, invitation veya kablosuz kurulum yapılmadı.

## 2026-10-09 — Ücretsiz iPhone PWA komut onayı ve canlı görev göstergesi (CI PASS)
- iPhone ana ekrana eklenen ücretsiz Cloud PWA geliştirildi; ücretli TestFlight gerektirmez. `static/mobile-action-guard.js`: yalnız `ULTRON Bridge` ve `set_focus`, `set_volume`, `set_brightness`, `bluetooth`, `wifi`, `compose_message` allowlist'i; URL/JSON manipülasyonu, keyfi shortcut isimleri ve bilinmeyen eylemler engelleniyor.
- `static/index.html`: Cloud Live'dan gelen `ios_action`/`ios_shortcut` komutları artık otomatik URL açmak yerine iPhone üzerinde `KESTİRMELERİ AÇ / VAZGEÇ` onay ekranını bekler. İkinci komut önceki onayı sessizce değiştirmez. `UZAKTAN` sekmesinde Cloud queue'daki aktif laptop görev badge'i ve kuyruk/çalışıyor/başarısız özetleri var.
- `static/sw.js`: offline shell `ultron-shell-v37`, guard script precache ve HTTP error response caching engeli. Mikrofon/Gemini Live, laptop Approval Gate ve Cloud queue koruması değiştirilmedi.
- Test dosyası `ultron/cloud_service/test_mobile_action_guard.cjs`: 8 gerçek Node test (komut parse/allowlist, unsafe bypass, onay bileşeni, inline JS sözdizimi, badge), `.github/workflows/scene-check.yml` adımlarına eklendi.
- **Gerçek CI:** Kod SHA `dd839dd5bdf1ee5ff93ad066d57eacc26d380917`; Scene build [37922721093](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37922721093) **SUCCESS** (8 PWA Node PASS, diğer backend/Cloud regresyonları, TS/Vite build ve Earth tests); gerçek PostgreSQL [37922721027](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37922721027) **SUCCESS**.
- **Henüz doğrulanmadı:** Render üretim SHA ve otomatik deploy, iPhone Safari ana ekran PWA UI testi, kilit ekranı/bildirim arka plan davranışı. Browser PWA iOS sandbox'ı aşmaz, kapalı uygulamada 7/24 mikrofon veya APNs push vaat edilmez. Yeni özellikler Render'ın bu branch'i deploy etmesiyle görünür.

## 2026-10-09 — CORE küçük animasyon + ULTRON WORLD (kod ve canlı kaynaklar doğrulandı)
- CORE içi animasyon: kuş / yörünge / nabız presetleri, React/CSS boyuta duyarlı panel, oynat/duraklat/kapat; animation_show backend + stage tool + Türkçe metin komutları. Rastgele Python/Pygame çıktısı henüz otomatik gömülmüyor.
- Yerel frontend ve masaüstü backend CORE animasyon aşaması: SHA cfacb7355b87af174182b37b635152bd2c204729, frontend build 37925291261 SUCCESS, Scene build 37925291379 SUCCESS.
- WORLD: iPhone ana ekran PWA DÜNYA sekmesi ve Windows CenterStage içi world_map modu; Leaflet OSM sokak haritası (zoom 19 ve atıf), Three.js WebGL küre, adres/koordinat arama, favoris, izinli geolocation.
- Gerçek REST sağlayıcıları: Open-Meteo / MET Norway (Render IP Open-Meteo 429 olduğunda resmî MET Norway tahmin yedeği), adsb.lol / adsb.fi v3 (ADS-B uçak konumu), USGS depremler, Open-Meteo Air Quality, Photon OSM geocoding. Kısa süreli bounded cache, sabit upstream URL, açık kaynak atfı, 502 durumunda sahte veri üretmeme.
- Uydu, Street View, trafik, yağış radarı, rüzgâr, gemiler işaretli harici servis bağlantılarıdır; ULTRON içinde native entegre canlı veri katmanı gibi sunulmaz. 3D her evin detaylı fotogrametrik modeli değildir.
- SHA 5c0b8781f0303ae8351dc772d9df3dbcee57f6f9: Scene build 37927499485 SUCCESS, PostgreSQL 37927499348 SUCCESS, public production WORLD live smoke 37927499312 SUCCESS. 5/5 gerçek API kategorisi JSON kaynak doğrulama PASS (hava MET Norway, uçak adsb.lol, AQI Open-Meteo, deprem USGS, Photon adres). Sağlayıcı erişimi değişebilir.
- Render autoDeploy yes, feat/ultron-cloud-shared-memory dalı. Son live SHA ayrıca Render panelinden doğrulanmalı. Windows bilgisayarda git pull/START.bat gerekir.
- NOT RUN: gerçek iPhone Safari WORLD 2D/3D görsel ve harici harita tile/CDN testi; Windows Qt içinde CORE animasyon fiziksel testi; keyfi Pygame animasyonu gömme, harici trafik/uydu/gemi native katmanları.

### ULTRON WORLD sesli ve yazılı telefon komutları — 2026-10-09
- PWA index.html worldVoiceIntent: kullanıcı tarafından konuşulan/yazılan Dünya, 2D/3D, Gazimağusa, Lefkoşa, Kıbrıs, İstanbul, uçaklar/deprem/hava durumu görüntüle komutlarını DÜNYA sekmesine iletir. Harita iframe'i yalnız aynı origin ve kendi parent kaynağının postMessage komutlarını; tip, koordinat, mod ve katman allowlist guard'ını geçirse işler. Lazy-load sırasında en fazla dört komut bekletilir. Sesli sohbet motoru/Gemini reply Cloud oturumuyla devam eder.
- Cache PWA v40. Sesli komut güvenliği ve WORLD sözleşme testleri Scene Build Check 37928165355 SUCCESS; Cloud PostgreSQL 37928165548 SUCCESS. Kod SHA b473a4bfd28835aefae0472fb07a15442e7e383f. Önceki 37928109729 Scene FAIL sebebi test regex'i; düzeltme sonrası PASS. Üretim WORLD real-provider smoke 37928109603 SUCCESS (bu smoke bir önceki sesli komut kodunun commit'inde tetiklendi; sesli komut cihaz testi değildir).
- NOT RUN: fiziksel iPhone Safari PWA sesli komut → iframe görsel etkileşim, WebGL/CDN texture, Windows Qt CORE. Render AutoDeploy canlı HEAD ayrıca doğrulanmalı.

## 2026-10-09 — Original MARK-LV native video engine restored INSIDE ULTRON CORE
- Investigation of actual original MARK files actions/video_player.py and ui.py: the player was a QMediaPlayer with a QGraphicsVideoItem mounted in the avatar/camera/video stack. It supports local files, HTTP direct media, optional yt-dlp YouTube resolution with separate synchronized audio/video, initially muted sound, stop/mute. The merged integration/web_panel.py had MOVED _video_cont to a separate QDialog (user's pop-out regression).
- New integration/video_dock.py MarkVideoDock reparents the SAME original _video_cont into the actual QWebEngineView. It positions the native QWidget according to .reactor-panel .center-stage DOM bounds, scaled by viewport, clamped so as not to cover surrounding telemetry/chat. Rechecks while open and calls Qt _fit_video on size changes. No new QMediaPlayer engine or video_dialog is created.
- integration/web_panel.py NativeBridge.videoRequest forwards explicit typed video commands to actions.video_player, and MARK native voice tools continue using old video_player directly. React Dashboard.tsx adds deterministic typed media routing irrespective of chosen model; CORE adds MARK VIDEO native-only button. Unknown or source-less voice 'video oynat' asks Qt native file picker (instead of generating a fabricated animation). Preset CORE bird/orbit/pulse animations remain separate.
- ui.py now retains native/QGraphicsVideoItem support after reparenting, QMediaPlayer pause/resume signal & button, correct sound output selection for mic protection, auto-closes the dock after EndOfMedia/decoder failure rather than leaving a black box. Opening a different clip cancels stale asynchronous YouTube requests.
- Headless GUI smoke scripts/tests/test_mark_video_dock_qt.py explicitly instantiated real PyQt6 QMediaPlayer, QGraphicsVideoItem, QAudioOutput, and verified QWidget signals/placement/resizing; 5 tests PASS with QT_QPA_PLATFORM=offscreen and Ubuntu EGL/PulseAudio dependencies. Pure geometry/plugin/contract tests scripts/tests/test_mark_video_dock.py 12 PASS.
- Exact tested code SHA 54a2f2408c54385fc53bc69f7cf944a7a22b1637, GitHub Actions Scene Build Check https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931870709 SUCCESS. Prior frontend build https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931231558 SUCCESS (no frontend changes since).
- Honest NOT RUN: real Windows GPU/QtWebEngine+QGraphicsVideoItem rendered video frame screenshot, real MP4 decoder and split audio through Windows speakers, live YouTube (yt-dlp/network), complete desktop voice Gemini route. The CI Qt smoke verifies Qt object creation and QWidget behavior, not actual codec playback on a Windows PC.
- This is a Windows-native MARK feature in a GitHub branch; Render is the Cloud Python host and does not execute or install a Windows Qt video widget. Laptop must git pull and START.bat; user might need INSTALL.bat once if dependencies are not present.


## 2026-10-09 — ULTRON Fast Brain ücretsiz yerel modül (CI PASS)
- ultron/backend/app/core/fast_brain.py: FAST/GENERAL/CODING/VISION sınıflaması. Sadece gerçekten kurulu Ollama modelleri seçilir; ücretsiz Qwen3.5:4b varsa günlük sohbet, yoksa qwen3:4b. qwen3:8b daha kapsamlı sorulara, qwen2.5-coder:7b kod isteklerine, llava:7b görsele. Model otomatik indirilmez.
- ultron/backend/app/core/model_router.py: önce model çalıştırıp ikinci aşamada ekstra paralel 2-model race + judge çağıran gecikme kaldırıldı (Fast Brain interaktif yolunda). Manuel local evaluation korunuyor. Orijinal Approval Gate ve izin/araç akışı korunur; tek model yanıtı veya yalnız hata üzerine fallback.
- ultron/backend/app/core/brain.py: Qwen3/3.5 için think:false, kısa yanıt num_predict, sınırlı bağlam ve 10m sıcak model ayarı. Basit selamlaşmalarda ağır araç şeması atlanır; gerçek görevlerde araç erişimi korunur.
- ultron/backend/config/settings.json: fast_brain etkin ve tercih listeleri; mevcut kurulu modellerle ücretsiz çalışır. scripts/ultron_fast_brain_doctor.py yerel /api/tags ve opsiyonel gerçek yanıt zamanı --benchmark; kılavuz ultron/FAST_BRAIN_README_TR.md.
- Gerçek GitHub CI: code SHA 2d0eb712347cf98e100ea89b05c51751bc7c75d1, run https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37940137389 SUCCESS; 15 test_fast_brain.py PASS, Python compile, TypeScript/Vite ve mevcut regresyonlar PASS.
- Fiziksel Lenovo/Ollama/GPU hızı ve mikrofon gecikmesi NOT RUN. MARK Gemini Live & iPhone Cloud Live hiç değiştirilmedi; bu modül provider ücretsiz plan/sınırlarını otomatik değiştirmez. Model qwen3.5:4b indirme kullanıcı tercihi olup birkaç GB disk/indirme ve cihazda olası CPU offload gerektirir.


## 2026-10-09 — Hybrid Free-First Brain (Qwen primary, Gemini optional)
- iPhone web PWA chat defaults to YEREL QWEN ÜCRETSİZ; separate GEMINI İSTEĞE BAĞLI selector. POST /api/local-chat, GET /api/local-chat/{id} polls real completion. Offline laptop responds 409 rather than silently using Gemini. Gemini Live microphone remains a separately disclosed opt-in service.
- Cloud local_brain_bridge.py: authenticated web-only and owner-scoped chat queue with limited concurrent jobs, context from shared Cloud memory, exactly-once PostgreSQL assistant persistence via local_chat_requests. Render never runs Ollama nor exposes a user-supplied Ollama URL.
- Windows MARK bridge: integration/local_cloud_brain.py chooses only installed Qwen/llava models via FastBrainPolicy, Ollama fixed localhost 127.0.0.1:11434, no Gemini and no desktop tool execution in read-only chat mode; mark_app.py handles mode=local_brain agent_task using lease renewal and checked completion.
- Native iOS CloudSession.askULTRON Siri defaults to local laptop Ollama; ContentView Siri metin beyni selection can explicitly choose Gemini; bounded task polls, no silent Gemini fallback. Continuous native voice is still Gemini Live, not free offline local audio.
- GitHub code SHA 98b5902ab5cc793aa3d16c4a3ac55f993bc15ceb: Scene Build Check 37942388982 SUCCESS, Real Cloud Queue PostgreSQL Integration 37942388970 SUCCESS. iOS code SHA ed82517cf03264d29e04bc5b2fcc414382ba91ac: Native iOS Build 37942797049 SUCCESS (simulator and unsigned iPhone; static contracts). Render 98b5902a deployed live. No real iPhone/Windows visual/audio or local Ollama hardware round-trip benchmarks.
- Windows requires user git pull and START.bat restart; Ollama must run with an installed model. Laptop offline -> free phone chat unavailable. Paid/limited Gemini deliberately remains optional. Camera, PDF, and Live audio paths still use Gemini. Existing approval and desktop automation unchanged.

## 2026-10-09 • ULTRON Hybrid Brain — local Qwen primary, Gemini optional
- Existing owner-authenticated iPhone Cloud /api/local-chat → paired Windows Ollama/Qwen remains free default text chat. Phone/Render do not themselves host Qwen; Windows laptop and Ollama must be online.
- Added ultron/cloud_service/static/local-voice.js: explicit tap-to-talk in Turkish via browser SpeechRecognition (when available), free Windows Qwen via the existing queue, and browser speechSynthesis for Turkish response. No browser Gemini fallback or automatic background microphone.
- PWA static/index.html: Qwen mic button now calls local recognition; Gemini Live mic starts only after explicit Gemini mode selection plus mic tap. App boot/pageshow/visibility will not silently initiate Gemini anymore. Service worker v43.
- Browser speech recognition may be unsupported in iOS Home Screen PWA and may use the browser vendor's network service. This is not guaranteed fully offline STT, no native iOS Siri entitlement, and does not establish guaranteed speech latency.
- Original Windows Fast Brain via installed Ollama models already exists; Windows MARK live-voice engine still Gemini separately and was NOT switched automatically to local Whisper/Piper.
- Code SHA f33bc81f9bdfdb4d5644c7beeaa7c061f8e63cbf: Scene Build Check #37989333207 SUCCESS, PostgreSQL #37989333208 SUCCESS and Render this code SHA observed live. Physical iPhone Safari microphone and Windows actual GPU latency NOT RUN. Further documentation: ultron/HYBRID_BRAIN_TR.md.

## 2026-10-10 — Shared persona tests introduced
- ultron/cloud_service/test_conversation_persona.py: 8 offline tests covering serious vs playful cue, ULTRON identity, non-human-emotion honesty, read-only prompts, memory bounds and mode wiring.
- .github/workflows/cloud-queue-postgres.yml: added independent persona-policy job to run on every Cloud source change. CI completion still must be verified.
- Prior Cloud CI run 37992292068: failed in Initialize containers, skipped all Python tests. No outcome attributed to the ULTRON code.
- Windows, physical iPhone, local Ollama, live Gemini and new Render deployment tests: NOT RUN.

## 2026-10-10 — Actual passing CI proof
- Code commit 2e424e9c6da7eb2efecff50b8737f18532e36a67: Scene Build Check #37992487672 SUCCESS.
- Workflow fix commit 015ed652a03fd67caaf1118ff6707cc55e3b6f30: Cloud Queue PostgreSQL Integration #37992572797 SUCCESS.
- Persona-policy: 8/8 Python unittest PASS; postgres-fencing job ran the 8 persona tests and real PostgreSQL delivery fencing, local-brain and ChatGPT development request integrations successfully.
- Older CI failures from 37992371192: Docker Hub anonymous pull rate-limit, plus an earlier tone test mismatch for the Turkish inflection 'param'; both corrected and independently verified above.
- No actual laptop Windows voice, physical phone/3D, personal memory interaction or live Render deploy validation was executed.

## 2026-10-10 — Windows assistant persona refinement / verified
- Desktop Agent persona_guard.py now uses respectful ULTRON guidance rather than mocking the owner; no longer penalizes ordinary replies for lacking 'Boss'. agent.py no longer forces 'Boss' after reframing and removes the harsh rewrite cue.
- Added ultron/backend/tests/test_persona_warmth.py: 4 stdlib tests covering kind anchor, ordinary direct response, genuine apology and desktop postprocessor.
- GitHub Actions Cloud Queue PostgreSQL Integration #37992833637 on SHA 433617f77b669fbe30526705faccbe6532ccd545 SUCCESS: persona-policy (Cloud 8 + Windows 4 tests), real PostgreSQL queue/memory/development-request integrations all passed.
- ULTRON Scene Build Check #37992774370 SUCCESS at Windows agent postprocessor SHA 93f921f266a37bf01f565b9c8c32880854f3f372.
- No Windows local checkout, microphone/audio, physical phone or current Render deploy verified.


## 2026-10-10 — PWA owner panels test provenance
- Previous Cloud Queue PostgreSQL Integration run #37995893863 SUCCESS, including four offline personal briefing tests. Scene check run #37996651819 SUCCESS for mobile HTML integration commit f11fa3105215b24407e29835bd305d303422bb21.
- New UI six Node regression tests and explicit scene CI step added. Cache version bumped from v43 to v44. Scene runs #37996726191 and #37996824797 failed at an older voice-test assertion (hardcoded cache version, then incorrectly escaped regex); the fixed test was committed at c1c641f67cf7a8627609b02df2996072a88489d6 and requires fresh CI verification.
- Real physical iOS interaction, screenshot proof, latest Render deployment, and Windows installation have not been tested within this development run.


## 2026-10-10 — Manual plans test record
- Python unit contracts cover ISO dates/times, input bounds, NUL, source labeling, briefing, prompt privacy and route ownership.
- Disposable PostgreSQL tests cover create/list/done/undo/delete, cross-owner 404 denial, browser-only write, cross-site block and invalid payloads.
- Node UI tests cover explicit actions only, safe textContent, confirmation-gated deletion, completion, form validation and PWA asset reference.
- Intermediate Cloud PostgreSQL run 37998043718 success, run 37998144238 success. Intermediate scene check 37998033939 success after async handler correction.
- Final GitHub Actions and latest Render release must be confirmed after the last code commit. No physical iPhone or Windows desktop tests were executed in this session.


## 2026-10-10 — Owner plan edit contracts (CI pending final SHA)
- Python offline route and validation assertions now include owner-scoped PUT route.
- Disposable PostgreSQL test covers edit, reschedule, notes persistence, retained id, rejection of cross-owner writes and malformed dates, no notification sent.
- Node tests cover opt-in editing, cancel without writes, failure preserving draft, and existing completion/deletion. GitHub CI outcome and Render deployment must be checked after commit, no local device claim.

- Original edit-API integration run 37998999457 caught missing PUT inside Fetch-Metadata/JSON write guard (cross-site PUT incorrectly reached DB). Fix adds PUT to both checks, with regression assertion; rerun real PostgreSQL tenant/security CI before calling complete.


## 2026-10-10 — iCalendar export regression evidence
- CI Cloud Queue PostgreSQL Integration run 38034057983 SUCCESS includes offline ICS date/time DST tests and disposable PostgreSQL authenticated owner-only export, timezone and no-private-notes assertions; .ics file never contains private note and has no VALARM.
- CI ULTRON Scene Build Check run 38034046409 SUCCESS at SHA 74162f6 includes Node tests for explicit click/URL allowlist and existing UI regressions, TypeScript/Vite build and scene suite.
- Render ULTRON service srv-db20lmei0phs73crgujg verified live on code SHA 74162f6 at 2026-10-10 07:21Z.
- Latest workflow-only SHA fb77617 also passed Cloud CI 38034057983; subsequent documentation changes do not affect functional code. Physical iPhone Safari PWA download, Apple Calendar import and actual Windows device were not executed.

## 2026-10-10 — Reviewed learning automated test gates
- Offline test_approved_learning.py covers category/key/value bounds, null byte rejection, browser consent and absence of pending proposals in model memory context.
- Disposable PostgreSQL test_approved_learning_postgres.py covers proposal not saved until approval, owner isolation (cross-account 404), rejection no memory, existing memory conflict without overwrite, repeated approval failure, browser-only same-site JSON requirements and explicit deletion.
- Node test_learning_review_ui.cjs covers no automatic fetch/write, separate propose+approve click, rejection, confirmation-gated deletion, safe textContent, PWA/HTML wiring and existing-memory delete approval contract.
- GitHub workflow cloud-queue-postgres.yml runs both Python contracts (offline and real PostgreSQL), scene-check.yml runs UI tests. Earlier commit 7a65bcbee Cloud run 38036171181 failed a *test string whitespace assumption* for existing owner-memory SQL; corrected at 02be84c8. Its cloud CI run 38036212147 SUCCESS; Scene Build Check 38036212168 SUCCESS. The new memory deletion UI commit has its own CI pending and must be checked before claiming latest HEAD is tested.
- Real iPhone microphone, learning panel interactions, Windows installation, model behaviours and hardware remain NOT RUN here.

## 2026-10-10 — Auto learning regression plan (check latest CI)
- test_auto_learning.py: only explicit owner-written statements, deterministic keys, sensitive/URL/email/multiline exclusion, per-user SQL and Gemini/Qwen integration contract.
- test_auto_learning_postgres.py: default off, authenticated owner-toggle PUT, same-origin JSON requirement, rejection of device/cross-site calls, owner-scoped learning, idempotent saves, on/off and existing-key non-overwrite with a disposable Postgres.
- test_auto_learning_ui.cjs: initial no-network, opt-in confirmation, cancel and toggle-off, mobile UI wiring. GitHub workflow steps added.
- Scope disclaimer: These tests do NOT prove limitless general intelligence, model training or free infinite persistent storage. Real iPhone and Windows device behavior not tested. Check exact CI and Render before claiming a working release.


## 2026-10-10 — Minimal UI verification plan
- Added mobile Node test_panel_intents.cjs: natural command cases, negative ordinary questions, DOM and PWA shell registration, syntax of inline index.html JS.
- Added desktop Node v24 type stripping tests/ panelIntent.test.mjs: language commands, negative ordinary chat, React HologramLab/voice-first CSS wiring. Scene CI new test step.
- Updated legacy test_world_contract.cjs to assert WORLD's new indirect dispatcher route rather than outdated direct direct transcript call.
- Scene run 38051154409 failed old direct WORLD assertion; run 38051359430 succeeded after updating. Subsequent new test run 38051416468 caught parse "kaç" as substring "aç"; fixed by whole-word verb regex in mobile and desktop. Latest CI must show passed on updated SHA.
- Frontend Build Check 38051547171 SUCCESS on intent whole-word fix branch; Render code release and physical devices must be confirmed separately.


## 2026-10-10 — Auto brain routing CI evidence
- unit test_auto_brain.cjs: online desktop -> local; offline, stale/absent, "true" string, phone-only -> Gemini; fallback only exact 409 desktop_offline, never rate limited/failure/network ambiguity; no visible Qwen/Gemini picker; inline UI script syntax, only click starts mic.
- Updated offline test_local_brain_bridge.py to assert device-presence selection, automatic 409-before-queue fallback and safe preservation of local-only data bridge; updated test_local_voice.cjs to match no selector, tap-triggered local/cloud mode and revised unsupported speech warning.
- On code SHA 7cfb708000c5274e2d968b3e731d17a0cf2af8db: Cloud Queue PostgreSQL Integration 38053172917 SUCCESS; Scene Build Check 38053172923 SUCCESS. Render live for that SHA confirmed (dep-db53733bc2fs738bq5j0).
- Additional cleanup commit bd9aec003af2436f912116e2bd09ebdba6984f83 tripped old unsupported-voice test text regex (old test expected "deste.*yok"; source now says "desteklemiyor"). Fixed test at 09fe6974de0ebf53c00c51506b7bb50eba07ce6f. Latest CI and Render must be checked before calling final correction verified.
- Physical iPhone Safari, real Windows worker/Ollama availability, Gemini provider quota/network and Live mic permissions not tested here.


## 2026-10-10 — True multi-turn conversation test/CI contracts
- Offline test_conversation_turns.py tests chronological turn ordering, latest bounded history, system role injection rejection, conversation_id and user_id WHERE filtering, ID-before-current exclusion, persona naturalness prompt text and full Gemini/Qwen/mark_app integration contracts.
- Disposable PostgreSQL test_conversation_turns_postgres.py proves only current owner/thread's earlier chat is fetched; current prompt and other threads/users excluded (no fabricated external data).
- Qwen offline fake-Ollama test_local_dialogue_runtime.py checks actual outgoing Ollama user/assistant role messages and bounded temperature/top_p/num_predict/repeat_penalty without model download or tool access.
- Cloud Queue PostgreSQL Integration from workflow now executes all three tests; Scene Build Check runs full frontend/build integrity. CI success verifies code contracts, NOT real LLM naturalness on user devices.
- Render status/code SHA must be checked after docs update. No claims of real voice-latency improvement or model retraining; no new external model accounts connected.


## 2026-10-10 — Conversation style validation
- New test_conversation_style.py exercises 16 follow-up/new-topic/correction cases, 13 brief/detailed/casual cases, prior-turn authenticity, serious tone overrides, malformed untrusted history records and Cloud/local integration contract.
- Additional baseline contracts: test_conversation_turns.py and real Postgres test_conversation_turns_postgres.py remain enabled. GitHub Cloud Queue PostgreSQL Integration #38055784729 persona-policy successfully completed at code SHA 321d5105fcd7576fad489fd2c3705fe30a0e66ee; full PostgreSQL and Render final verification required before describing the whole release as green/live.
- The deterministic tests prove wiring and boundaries, NOT the live models' JARVIS-level intelligence or latency. Real Windows device is unchanged as requested.


## 2026-10-10 — Long conversation topic recall regression evidence
- Offline Python test_contextual_recall.py verifies older named-topic recall, recent-dialogue priority, no random old-topic recall on "Peki?" or "Devam et", max 80 SQL lookback, model character/turn caps and malformed/system-role rejection.
- Existing Python test_conversation_turns.py now checks the new Cloud and local contextual helper instead of the old direct load_thread_turns call.
- Disposable PostgreSQL test_conversation_turns_postgres.py also verifies 24+ intervening turns, old Mercedes C180 recall only for correct user and conversation, no leaks from other conversations/users, and exclusion of the current message.
- GitHub Cloud Queue PostgreSQL Integration run 38057407803 SUCCESS. Scene Build Check run 38057407812 SUCCESS on code SHA 8c25b3db4186d7e62bac465b6bbe8693af55a298. Render deployed same code SHA LIVE as dep-db546815efls73a9o7cg. Earlier intermediate code run 38057311007 failure was an outdated test asserting the old function name; corrected in the passing code commit.
- No real Gemini/OpenAI live naturalness benchmark or physical iPhone/Windows acceptance has been executed in this session. Only CI contracts and Render deployment are verified.


## 2026-10-10 — Recap verification
- Python unit test_thread_recap.py covers explicit Turkish/English same-conversation recap commands, excludes ordinary "kitabı özetle", head/mid/recent selection, model role separation, text/token/SQL lookback limits, malformed record filtering, and no phantom history.
- Disposable PostgreSQL integration test_conversation_turns_postgres.py extended: 28-turn chat, recap sees start/mid/end while excluding current request and other user/conversation secrets; owner-scoped query enforced.
- Cloud Queue PostgreSQL Integration 38061079383 SUCCESS at ef474b66ad9009871aa4dae7126223ee363ebe6c (test CI includes explicit recap step), and prior 38061059249 SUCCESS at 8ffd9983cc1fc077745f3c5ed257b9f224553b8f.
- ULTRON Scene Build Check 38061059184 SUCCESS at 8ffd9983cc1fc077745f3c5ed257b9f224553b8f.
- Render code release at da9f6e76049953e88ae91b17104018bb9bdc6613 confirmed LIVE; subsequent commits differ only in tests/workflow. Exact Render promotion for subsequent test-only commit is optional and should not be confused with a new code release.
- No physical iPhone, Windows Ollama/Qwen, live Gemini conversational benchmark or real voice interaction was performed here.


## 2026-10-10 — Conversation notes test results
- test_conversation_notes.py: preview bounded, common secret-looking excerpts omitted, field validation and rejection of NUL/control chars, absence of implicit model-memory integration.
- test_conversation_notes_postgres.py: disposable database complete draft/read/save/update/delete lifecycle, no draft or editing without explicit write, cross-user/cross-thread access isolation, CSRF JSON/session restrictions, no writes into memories.
- test_conversation_notes_ui.cjs: no API on mount, natural typed/voice requests, review and explicit save, XSS-safe textContent, editing and confirmation-gated deletion, hidden-panel PWA wiring and inline JavaScript syntax.
- Initial Scene CI runs #38061640815, #38061738567 and #38061793040 failed due to a stale test_auto_brain.cjs exact 'ultron-shell-v50' assertion after PWA cache v51. Changed assertion to accept future cache version numbers at code SHA a1afc4befbdfbd84fc52e3b0511aebdba675bed8.
- Final GitHub Cloud Queue PostgreSQL Integration #38061837383 SUCCESS and ULTRON Scene Build Check #38061837381 SUCCESS at the same SHA. Render deploy dep-db555toae00c739bvqn0 for the same SHA LIVE. Earlier failed intermediate CI runs are superseded; no real provider or physical iPhone/Windows acceptance tests were executed.


## 2026-10-10 — Live natural audio test results
- Node test_live_playback.cjs exercises queued three-chunk response: turn_complete must wait until all three finish; duplicates and stale onended following cancel ignored; a new turn retains its own pending counter; empty responses do not leave a talking/microphone lock.
- Static PWA contracts assert actual playback helper and service worker v52 wiring, WebAudio source onended accounting, queued-drain turn_complete with no stopPlayback, and immediate cancellation for bargeBlocks>=2 or Gemini server interrupted.
- Intermediate GitHub ULTRON Scene Build Check #38065262849 failed on 'playback.create is not a function' due to shadowed CommonJS module binding. Corrected UMD wrapper in code SHA b431b82314c4b27fee7c1cf7b2d96e5b27a51acf.
- GitHub Cloud Queue PostgreSQL Integration #38065354266 SUCCESS; ULTRON Scene Build Check #38065354265 SUCCESS; Render automatic deploy dep-db55ubl9mjac73899sl0 LIVE at the same code SHA.
- This does NOT establish real iOS microphone/audio interruption latency or guarantee network-based Gemini provider availability; hands-on physical iPhone test remains necessary. No local Windows installation attempted.


## 2026-10-10 — Speaker policy regression evidence
- Added Node test_speaker_policy.cjs: desktop speaker online+speaking+voice_active+not muted, no string/false trust; phone Gemini Live or local Qwen mic priority, no remote-result secondary phone TTS, cancelling old audio and clearing remoteResultSpeaking, immediate mic-tap takeover, stale out-of-order heartbeat checks, PWA v53 asset+inline script validation.
- CI workflow .github/workflows/scene-check.yml executes node --check speaker-policy.js and node --test test_speaker_policy.cjs in addition to previous Live playback tests.
- Commit 6e35a098378ba1fc03f622f73636070ddbd26bad: GitHub Cloud Queue PostgreSQL Integration #38066016781 SUCCESS and ULTRON Scene Build Check #38066016772 SUCCESS.
- Commit 4952ea5a6a44c041aebf5d87e21ce2184ad3e48d: latest Cloud Queue PostgreSQL Integration #38066114015 SUCCESS and ULTRON Scene Build Check #38066114014 SUCCESS. Render code at prior 8eb876077ab7951758892cee05b32d6e4f63b597 LIVE as of verification; Render promotion of test-only 4952ea5a6 still in progress then. Check final live SHA before claiming deployment.
- CI does not exercise real iPhone/Windows speaker, physical acoustic feedback or Chrome/Safari AudioContext timing. User intentionally deferred Windows update and no local desktop files were altered.


## 2026-10-10 — Phone local Qwen stale TTS protection
- test_voice_turn_guard.cjs: generation tokens reject stale async completions, idempotent invalidation across repeated mic taps, invalid/fabricated tokens, and no late voice replies while backgrounded, muted or after typing new chat. Static PWA asserts text result is still added, sound gated by token and visibility.
- Original intermediate Scene run #38066796046 failed after function signature changed to send(true,voiceToken); old test_local_voice.cjs expected send(true) exactly. Updated assertion in commit 70991ff6610e2cac631a2c1ec91d856588aa0cab.
- Exact commit 70991ff6610e2cac631a2c1ec91d856588aa0cab: GitHub Cloud Queue PostgreSQL Integration run #38066919827 SUCCESS, ULTRON Scene Build Check run #38066919837 SUCCESS. Render deployment dep-db5697jhu5js73djph4g was still update_in_progress on last check, not marked live until verified.
- No physical iPhone microphone / SpeechSynthesis playback, actual Qwen inference, headset echo or desktop hardware tests were run. Windows package not downloaded or installed.


## 2026-10-10 — Personal context & Qwen reasoner test evidence
- Offline Python test_personal_context_focus.py: long irrelevant memory vs old Mercedes C180 project, Turkish reply preference preservation, event priority and chronological inclusion, empty/cap checks, malformed line flattening, app+local bridge wiring, deep installed-Qwen8B route and fast Qwen4B default.
- Disposable PostgreSQL test_personal_context_focus_postgres.py: real memorized project + preference and unfinished dated plan per owner; no foreign owner's private memory/plans or private note leakage; strict scope and bounded output.
- Original CI intermediate commits 76b7fe17, 4d5eb6ad, 0119eb83, d25056d4, 7684956e failed persona-policy because pre-existing tests assumed all SQL remained physically in app.py's _memory_context. These tests were corrected to examine personal_context_focus.py while preserving the real query and note-omission assertions; intermediate Postgres tests passed.
- Final Cloud Queue PostgreSQL Integration #38068020642 SUCCESS (persona-policy + postgres-fencing) and ULTRON Scene Build Check #38068020631 SUCCESS for code a6ce694ff35423f93a386140c7e1938a374ad162.
- Render autoDeploy dep-db56gpmoq3os73c5cicg for a6ce694f was still update_in_progress at latest inspection. Earlier test-only deploy dep-db56gcn40ujc73c6ctag at 7684956ec0 was LIVE. Confirm final live SHA before claiming latest release live.
- CI tests do not measure real model reasoning ability, GPU/offload latency, Turkish speech understanding or subjective naturalness. User laptop installation remains intentionally deferred.


## 2026-10-10 — Conversational intelligence regression cycle 1
- Explicit first-topic return now retrieves the actual opening of the same owner/thread, including conversations beyond the 80-message recall window. Named recall includes adjacent question/answer evidence; very small context/turn budgets no longer overflow. Three new regressions first FAILED on the old code, then PASSED after fixes.
- Shared lightweight response quality checks remove only adjacent identical long prose paragraphs, preserve code/verbatim text, and flag excessive length without another model call. This is not semantic truth verification.
- Added versioned `evals/conversation`: 100 distinct scenarios (50 TR/50 EN), ten categories, scenario-specific acceptance plus five review dimensions. Real production provider adapters, transcript/latency capture, independent review and honest missing-run handling.
- Local verification: conversation tests 30 PASS / 6 PostgreSQL tests SKIPPED (no local disposable DB), response-quality 3 PASS, local runtime 3 PASS, reference-return 3 PASS, contextual recall 5 PASS, recap 6 PASS, local brain 5 PASS; backend Earth 5 PASS; Python compile PASS; npm ci/build PASS and Earth JS 6 PASS. PostgreSQL extension awaits real CI.
- Real model attempts: Gemini unavailable (no configured GEMINI_API_KEY in this environment); local Qwen unavailable (no reachable local Ollama). Each report has 100 NOT_RUN, zero captured transcripts, null quality score. **100/100 model quality NOT established.** No production personal chat accessed; no Windows install/model download.
- Prior functional Render SHA a6ce694ff35423f93a386140c7e1938a374ad162 verified LIVE (dep-db56gpmoq3os73c5cicg). This cycle's CI and Render pending commit/push.


## 2026-10-10 — Conversational intelligence cycle 2: real readiness and bounded memory
- Local-first routing now requires a fresh desktop heartbeat AND boolean local_chat_ready from a 1.5-second live loopback Ollama tags/model probe. Dedicated readiness executor preserves Cloud heartbeat independence from voice executors. Browser and server both reject missing/false/string readiness. Pre-queue 409 fallback remains the only safe retry route; accepted/ambiguous requests are never replayed.
- Older Windows builds do not advertise readiness and therefore safely use Gemini until the single final Windows update. No Windows install or model download performed. A readiness probe proves reachable service/installed model, not future inference or VRAM success.
- Auto-learning rejects common unlabelled API/private-key/JWT formats; canonical normalization deduplicates whitespace/case/final punctuation. No deletion or rewrite of existing owner memory. Explicit unambiguous reply-language/length conflicts use the newest saved preference in model context; scoped, negated, ambiguous and other factual conflicts are not automatically resolved. Owner CRUD/approval remains intact.
- Indexed PostgreSQL full-text retrieval combines 100 recent entries, 20 standing preferences and 40 lexical matches (at most 160 records) within unchanged prompt caps. Actual integration test retrieves an old C180 memory beyond 130 newer records while excluding another owner's matching keyword. This is bounded lexical retrieval, not universal semantic recall.
- Removed desktop queue payload logging to avoid exposing prompt/history/memory text. No changes to Approval Gate, device task permissions or UI controls; PWA cache v55 refreshes automatic routing.
- Evaluation scoring additionally checks exact suite hash, unique known scenario IDs, category and full matching transcripts before accepting reviews. Missing/error/unreviewed cases cannot establish 100/100.
- Actual local validation: ALL Cloud Python tests **152 PASS**, including **28 real disposable PostgreSQL tests**; mobile Node **86 PASS**; local-brain tests **6 PASS**; py_compile PASS. Frontend TypeScript/Vite and Earth 6 tests passed in cycle 1; no frontend TypeScript changed afterward.
- Cycle 1 SHA 27abf3c4fb53ecd0ce4bb70d89ca59146b56e289: GitHub Cloud/PostgreSQL 38069553694 SUCCESS, Scene 38069553682 SUCCESS, Render dep-db56rfou01pc73echpjg LIVE. Cycle 2 exact CI/Render awaits commit/push.
- Real model quality remains UNMEASURED: no configured Gemini credential or reachable Qwen/Ollama here. Common-secret filters and style heuristics are deliberately limited; no perfect privacy classification, semantic truth oracle, latency or 100/100 model quality claim.


## 2026-10-10 — Final bounded-evidence regression
- Long recalled assistant answers could still evict their corresponding question within the older-evidence character budget. A new regression FAILED before the fix; each selected role now reserves a bounded share, preserving both question and answer. Reference-return tests 4 PASS and actual conversation PostgreSQL tests 4 PASS.
- Final full local Cloud run: **153 PASS**, no skips, including 28 disposable PostgreSQL tests. `evals/conversation/LATEST_RESULTS.md` separately records all 100 TR/EN scenarios as NOT_RUN for both live providers and no quality score.
- Cycle 2 SHA 06acb933f9568c7548ec0d62631fcdb6f65a1811 verified: Cloud PostgreSQL run 38069902423 SUCCESS, Scene run 38069902369 SUCCESS; Render dep-db56tv7avr4c73eqm5lg LIVE. Final bounded-evidence commit CI/Render is checked after push.
- Continuation document now exposes current priorities under the resume script's supported `Next tasks` heading. No Windows changes, downloads or installations.


## 2026-10-10 — Legacy multimodal history isolation
- Audit found `_recent_context` blended other same-owner conversations when called without a thread (image/PDF paths). It now returns no prior history without a conversation_id and delegates explicit threads to bounded role-filtered load_thread_turns. User memory remains separately owner-scoped.
- Two actual-helper regression tests FAILED before the fix and now PASS. Full local Cloud suite **155 PASS**, including the same 28 real PostgreSQL tests, no skips.
- Prior bounded-evidence code 25b8ee9a3495e4b82e8f1a7e98cfda95a37f6a3a: Cloud CI 38070026514 SUCCESS, Scene CI 38070026493 SUCCESS; Render dep-db56unf40ujc73c6t1p0 update_in_progress at inspection. Current isolation commit's CI/Render must be verified after push.
- Real Gemini/Qwen quality, physical devices and Windows installation remain NOT RUN. No 100/100 conversational result claimed.


## Final verification — 2026-10-10 conversational intelligence
- Functional code SHA: `78930a44f40835917337b3d7f494435a500cd94e`.
- [Cloud Queue PostgreSQL Integration 38070103017](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070103017): **SUCCESS**, exact SHA; persona/evaluation/memory/readiness/legacy-history regressions and real PostgreSQL passed. Logs inspected.
- [ULTRON Scene Build Check 38070103005](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070103005): **SUCCESS**, exact SHA; Python checks, browser tests and frontend build passed. Logs inspected.
- Local final tests: 155 Cloud Python including 28 disposable PostgreSQL, 86 Node, 6 local-brain, 5 Earth backend and 6 Earth math PASS; frontend TypeScript/Vite PASS. Health endpoint HTTP 200.
- Live Gemini/Qwen quality remains **NOT MEASURED**, 100 scenarios per provider NOT_RUN, no quality score. See `evals/conversation/LATEST_RESULTS.md`. Missing Gemini credentials and local Ollama prevented actual inference.
- Completed changes: bounded paired/first-topic recall; no cross-conversation multimodal context; shared low-cost presentation checking; real local service readiness; indexed scoped memory recall; conservative preference conflict/deduplication/common-secret controls; 100-scenario independent-review harness.
- Limits: semantic factual verification and arbitrary memory contradictions are not solved by these rules. No hardware latency/quantization benchmark, phone voice acceptance or Windows installation performed. Old Windows worker falls back to Gemini until final authorized update advertises readiness.
- Render **LIVE** verified at the exact functional SHA `78930a44f40835917337b3d7f494435a500cd94e`, deployment `dep-db56v7vmphoc739fq12g`, finished 2026-10-10 17:03:37 UTC. Later documentation-only commits do not represent additional tested code.


Release verification for owner-grounded suggestions: runtime code `de228a8` is included in merge commit `a0352a517c7d7221177229563cfce60ff49ec768`. Cloud/PostgreSQL Actions `38427591507` and Scene/UI Actions `38427591557` both **SUCCESS**; full logs read, including the new briefing privacy/grounding test and Chromium UI checks. Render `dep-db75df2jnfac73eluhag` **LIVE** and `/health` reports the exact `a0352a5` SHA. The frontend production build and local planner/memory tests passed. Physical laptop/phone operation and real Gemini/Qwen answer-quality scoring remain pending.


Release verification: merge commit `bd09410034d369093b87430e61737cd6e9fbff1e` contains the self-development routing and PR flow. Cloud/PostgreSQL Actions `38430065807`, Scene/UI `38430065886`, and WORLD smoke `38430065957` all **SUCCESS**; workflow logs inspected. Render deployment `dep-db75lruq1p3s73f2eorg` is **LIVE** and `/health` confirms exact SHA `bd09410`. This verifies the Cloud routing and repository checks. The Windows app has not been installed, and GÖLGE's own laptop `gh auth status`, actual branch push, and draft PR have not been tested.
## 2026-10-13 — Image create/edit and uploaded-image context

- `python -m unittest test_image_generation test_conversation_turns test_recent_context_isolation test_response_quality -v` from `ultron/cloud_service`: **19 passed**. Covers authentication, actual image payload contract, edit source bytes reaching provider, same-thread visual follow-up, conversation turn isolation and response policy.
- `node test_image_generation_ui.cjs`: **1 passed**; checks Turkish/English creation intents, image edit follow-up and non-image chat routing. Inline UI script syntax check passed.
- Full Cloud Python discovery: **303 passed, 58 skipped**; skips include tests requiring external services/provider credentials or dedicated PostgreSQL setup. Frontend `npm run build`: passed (existing large-chunk warning).
- `python -m py_compile app.py test_image_generation.py`: passed.
- Inline chat script `node --check`: passed; `node test_mobile_chat_flow.cjs`: **7 passed**.
- Gemini image-generation provider call, production credentials/model availability, Render deployment, and physical iPhone behavior: **not run**. No actual generated image or live-provider success is claimed.
## 2026-10-13 — Image output download and payload bounds

- Full Cloud Python discovery: **304 passed, 58 skipped** (previous 303 plus the Gemini response payload test).
- `node test_image_generation_ui.cjs`: **1 passed**, including save action and temporary URL cleanup; mobile chat routing: **7 passed**.
- Python compilation and `git diff --check`: passed. Gemini provider call and real-device save behavior remain NOT RUN.

## 2026-10-13 — GÖLGE code-change approval routing

- `PYTHONPATH=ultron/backend python -m unittest discover -s ultron/backend/tests -p 'test_github_pr_publisher.py' -v`: approval-routing tests **2 passed**. Includes standalone commands, Turkish normalization, ambiguous multiple proposals, exact IDs, rejection, wrong IDs, and conversational false positives.
- `python -m py_compile ultron/backend/bridge.py ultron/backend/github_pr_publisher.py`: passed. CI now runs the self-development publisher suite and compiles both files.
- GitHub execution from the owner’s Windows laptop and a real draft PR are not yet tested.

## 2026-10-13 — Image ownership/failure isolation and GÖLGE path boundary

- Full `python -m unittest discover -s . -p 'test_*.py' -v` from `ultron/cloud_service`: **306 passed, 58 skipped**. New image tests prove provider failure creates no conversation/messages and a foreign owner's conversation is rejected before calling Gemini. Existing upload/edit, thread-continuity, supported MIME and image output limit checks passed.
- Desktop: `PYTHONPATH=ultron/backend python -m pytest -q ultron/backend/tests/test_codegen_pipeline.py ultron/backend/tests/test_github_pr_publisher.py`: **11 passed**; unittest approval router: **2 passed**; `test_codegen_path_boundary.py`: **1 passed**. The new traversal-prefix regression failed before the `Path.parents` fix and now passes.
- `py_compile` for cloud app and desktop codegen/bridge/publisher passed. `node test_image_generation_ui.cjs`, full inline chat script syntax check, and `node test_mobile_chat_flow.cjs`: **1, 7 passed** respectively.
- Live Gemini image generation, production account/model availability and physical phone/laptop behavior: **not tested**.

- First Cloud CI attempt for `54f91bb` exposed a test-job dependency omission (`ModuleNotFoundError: asyncpg`). After adding `asyncpg` and `google-genai`, corrected Cloud run [38437032742](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38437032742) passed, including disposable PostgreSQL and Chromium job steps. Scene [38436800737](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38436800737) and WORLD smoke [38436800759](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38436800759) passed for code SHA `54f91bbb5e061c2eb79a5ae53daca653fc55bdef`. Render `dep-db76d1bm8hqs73fe8spg` is LIVE and `/health` confirms `54f91bb`. No actual Gemini generation was performed.

## 2026-10-13 — Reviewable code proposal limits

- `PYTHONPATH=ultron/backend python -m unittest discover -s ultron/backend/tests -p 'test_codegen_path_boundary.py' -v`: **4 passed**. Covers sibling path prefixes, security-core paths, normalized duplicate paths, 13-file proposals, per-file overflow and total payload overflow. Each new case failed before the validation fix.
- `PYTHONPATH=ultron/backend python -m pytest -q ultron/backend/tests/test_codegen_pipeline.py ultron/backend/tests/test_github_pr_publisher.py`: **11 passed**. Explicit approval-router unittest: **2 passed**. `py_compile` for codegen/bridge/publisher and `git diff --check`: passed.
- No generated patch was applied and no laptop GitHub credentials/device state were touched.

- Exact code SHA `4112b3ca99c850c8e286dc087002a968788c5cd7`: Scene Action [38437781712](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38437781712) **SUCCESS**; compile, approval router, proposal boundary, frontend, WebGL, mobile and identity checks passed. Render remains LIVE at Cloud SHA `54f91bb`; self-development limits are desktop-only.

## 2026-10-14 — Memory and Verified Research V3 local verification

Code commit: `d95b64640381ae4a519024f767560892e20270a4`. Baseline: production commit `0b2315a77d657361821ae728814ba3506a79b309`, clean worktree; `feat/golge-memory-research-v3-20261014` created from that exact commit. Initial selected regression baseline was **46 passed**. Baseline deterministic timings: 98-record personal-context selection p50/p95 **0.3708/0.5109 ms**; search-only fake discovery p50/p95 **0.0121/0.0149 ms**.

After changes:
- Full backend pytest: **1,141 passed, 3 skipped, 6 subtests passed**.
- Full Cloud pytest with disposable PostgreSQL 16: **354 passed, 7 skipped, 13 warnings, 320 subtests passed**.
- Continuity regression first failed at 500 follow-ups on the old 320-message scan; after widening only the explicit continuation path to at most 1,200 same-thread messages (six 200-row pages), continuation, contextual recall, reference return and PostgreSQL history tests: **51 passed, 16 subtests passed**. The 500-turn check preserves the original goal, latest correction and newest status under the same output cap. All new memory tests—including two concurrent corrections, owner isolation, idempotence, explicit history, and delete purge—ran against the disposable DB. Seven skips are the existing listening tests that require a separate dedicated test database.
- Focused Cloud research/memory/live-tool suite: **31 passed**, plus three PostgreSQL cases skipped in the no-DB focused invocation; those PostgreSQL tests passed in the full DB-backed run.
- Focused research/evaluation suite: **135 passed**. The annotated evaluation has 100 distinct cases (50 Turkish/50 English; 20 each memory retrieval, historical recall, secret guard, SSRF policy, and evidence matching) plus an aggregate validation check: **101 passed**.
- `py_compile` for changed Python modules: passed. Full suite includes SSRF fixtures, redirects/downgrade, private-address rejection, payload limits, HTML sanitization, actual page-read citations, untrusted source prompt, no search on normal chat, and one existing model call per Cloud/desktop response.
- CPU-only deterministic fixture timing after change: memory selection p50/p95 **0.7471/0.9088 ms** for 98 records; fake search plus three fake page reads p50/p95 **0.0683/0.1036 ms**. These exclude external network and model time and are not end-to-end response latency.
- Gemini/Qwen answer quality, actual public web reads, Windows/iPhone behavior, and real response/first-token latency: **NOT_RUN**. No credential values or user conversation data were used.

The separate disposable PostgreSQL container was used only for tests and stopped after verification.

Exact-head hosted verification for workflow commit `698190a94ac8f8a471cc91dc481cac59d0f71ea5`: Cloud/PostgreSQL [#38555225630](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225630) **SUCCESS**, Scene [#38555225647](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225647) **SUCCESS**, Local Qwen Listening [#38555225690](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225690) **SUCCESS**. Hosted V3 steps: 500-continuation suite **8 passed**; deterministic research/evaluation **112 passed**; real PostgreSQL memory versioning suite **8 passed**. Draft [PR #33](https://github.com/fatmakahraman304-hash/ULTRON/pull/33), unmerged.
Render deploy `dep-db7lkuavcj2c73e8hb70` remains LIVE at SHA `0b2315a77d657361821ae728814ba3506a79b309`; public `/health` returned HTTP 200 and the same commit. No deployment or merge was performed.
