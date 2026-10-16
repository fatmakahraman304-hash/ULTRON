## 2026-10-16 — Güncel kapsam ve devam

## 2026-10-15 — Current merge queue and Memory V4 status

- PR #34 now contains PR #35 and is synchronized with production through `c66b5dae`; its latest implementation adds bounded 1–365 day recall and bilingual connector-word filtering. Exact-head Actions for `fece4ef` are pending.
- The older “Next tasks — Memory and Verified Research V3” section below is historical. Episodic Memory V4 and Evidence V4 implementation are present in PR #34; remaining limits are semantic retrieval/verification, PDF support, live providers, and physical device testing.
- Next: wait for all PR #34 checks; merge only if they pass. Then verify Render's production SHA and continue with PR #36's synchronized interruption flow. PR #40 scheduler remains blocked on its upstream rollout and independent credentials/cost review.

1. PR #44'te üç eski özelliğin kaldırılmasını incele: GÖLGE intro render, Dünya hologramı, enerji hologramı. Ana CORE ve ayrı harita kullanıcı talimatıyla kalır.
2. Yeni kaldırma commit'inin GitHub Actions kontrollerini tamamla; başarısız job varsa düzelt. Test: `python -m unittest discover -s scripts/tests -p 'test_removed_stage_presets.py' -v`, frontend build, `python scripts/tests/test_frontend_stage_loading.py`.
3. Üretime merge veya Render deploy için ayrıca açık onay gerekir; bu görev yayın yetkisi vermez.
4. Fiziksel Windows/iPhone ve gerçek Qwen/Gemini/mikrofon/TTS testleri hâlâ yapılmadı. Önceki raporların bu sınırlarını koru.

Aşağıdaki eski görevler tarihsel kayıttır; kaldırılan üç preset yeniden eklenmemelidir.

## PR #44 — CORE/Dünya son doğrulama ve fiziksel kabul

1. docs/GOLGE_EARTH_V7.md ve docs/ui-v7/ gerçek ekran/kayıtlarını incele. Etiketli sentetik ses testi mikrofon/TTS başarısı değildir; yeni sohbet ekranlarında gerçek sahne cevapları ve model UNAVAILABLE sonucu vardır.
2. Yetkili Windows laptopta mevcut bridge/Ollama/Qwen ve Cloud eşleşmesini doğrula. Bu yürütücüde VPN/model kimliği yok; internete Ollama açma veya model indirme. Native PCM/TTS RMS, kesme ve ses transkriptinden Dünya/CORE komutlarını ölç.
3. RTX'te gerçek FPS/VRAM, gizli sekme, düşük kalite ve 20+ geçiş; iPhone'da gerçek klavye/mic/PWA/uzun dinleme. SwiftShader kayıt ölçümü p50 178,2 ms/p95 198,0 ms; bu ortamda 60 FPS yok. Fiziksel donanım NOT RUN.
4. Uydu/terrain ancak gerçek veri lisansı ve güvenli kaynak ile etkinleşebilir. Varsayılan uydu BLOCKED; MAP gerçek OSM sokak haritasıdır. Ücretli sağlayıcı otomatik açılmaz.
5. PR #44 taslak kalsın; mevcut diğer PR bağımlılıklarına dokunma. Kullanıcının ayrı açık onayı olmadan production merge veya Render deploy yapma.

## PR #44 — Tasarım incelemesi ve gerçek cihaz/model engelleri

1. `docs/GOLGE_V5_VISUAL_REVIEW.md` ve `docs/ui-v5/` altındaki yeni gerçek uygulama kayıtlarını incele. Dolu sohbet örnekleri görünür SENTETİK SOHBET etiketi taşır; tasarım kabulünü teknik test sonucundan çıkarma.
2. Yetkili Windows laptopta mevcut Ollama/Qwen kurulumunu ve Qt köprüsünü doğrula. Bu yürütücüde laptop/VPN veya hazır model yok; ağırlık indirme veya internete Ollama açma.
3. Mevcut Cloud cihaz eşleşmesi ve kullanılabilir model yetkisi sağlanırsa aynı gerçek sohbet kabulünü tekrar çalıştır. API anahtarlarını arayüze/loglara koyma; UNAVAILABLE sonucunu başarı sayma.
4. Fiziksel iPhone Safari'de sabit fotoğraf, gerçek klavye, uzun sohbet, dosya/mikrofon ve PWA yeniden bağlantısını; Windows'ta gerçek RMS/TTS senkronunu ve RTX yeniden boyutlandırmayı ölç. Headless CPU-kompozitörü kaydı cihaz testi değildir.
5. PR #44 taslak kalsın. Kullanıcının açık üretim onayı olmadan production merge veya Render deploy yapma. Diğer açık PR bağımlılıklarına dokunma.

## Next tasks — GÖLGE V5 interface release verification

1. Review draft [PR #44](https://github.com/fatmakahraman304-hash/ULTRON/pull/44); validated code/test commit `41c907056130536b6ec7abb482a4a02bf33e1437` passed exact-head Responsive, Scene, Cloud/PostgreSQL and Local Qwen Listening Actions. Do not merge or deploy without the user's release authorization.
2. On the Windows laptop, confirm the real native bridge reports CPU/RAM/GPU and audio amplitude, verify local Ollama/Qwen and Gemini fallback, test 3D CORE state transitions and view switching, and measure actual GPU frame time. Keep missing sensors visibly unavailable.
3. On physical iPhone Safari, verify authenticated chat history, fixed wallpaper while scrolling, keyboard/safe-area composer, image/file attach, mic permission, voice turn and network recovery. Background microphone behavior remains subject to iOS restrictions.
4. Validate one authenticated local/cloud chat exchange and same-owner phone/laptop history without changing stored user data. Confirm the control-center action tools continue through existing approval/audit flows.
5. Recheck Render `/health` and deployment SHA after network is available. No live deployment has been started; this desktop code branch is unmerged.
6. Investigate the existing OrbitControls 575.89 kB chunk warning using measured bundle evidence before changing chunk boundaries.

## Next tasks — cognitive router v2 follow-up

1. Review draft [PR #32](https://github.com/fatmakahraman304-hash/ULTRON/pull/32) on isolated branch `feat/golge-cognitive-router-v2-20261014`, functional code head `74c932ae5002e9dae4285ffdc5552972ca50514c`. Exact-head Actions all passed (#38548733163 Cloud/PostgreSQL, #38548733148 Scene, #38548733003 Local Qwen Listening). Keep it unmerged and undeployed until explicit owner approval; `feat/ultron-cloud-shared-memory` is Render-connected.
2. Research is now correctly exposed as search-result discovery only (`adapter`): no page contents are read, so claim confidence stays zero and there is no corroboration/contradiction assertion. Next research code slice: implement a bounded source reader with public-IP/redirect validation, evidence extraction, prompt-injection isolation and claim-to-excerpt checks; validate with a local HTTP fixture and adversarial URL cases before routing research intent to it. Keep Approval Gate, audit and owner/thread boundaries.
3. When a real Gemini credential or the paired laptop's Ollama service is available, run the frozen 100-case real-model suite with recorded model identities, transcripts and latencies, then obtain independent review. Keep quality, first-token and total response latency **NOT_RUN** until that evidence exists.
4. On the Windows laptop, verify actual task dispatch, approval UI, agent result visibility and Qwen/Gemini routing. Measure Qwen3:4B/Qwen3:8B/coder latency on the stated RTX 2050/24 GB hardware; do not download models or alter Windows during this branch task.
5. On physical iPhone Safari, preserve PR #30 checks: foreground mic, long listening, explicit “Cevap ver”, reconnect/resume. Background/locked-screen listening remains unsupported unless real device behavior proves otherwise.

## Archived next tasks — first-run setup verification

The first-run setup focus/persistence fix is on the owner’s Windows handoff path. The owner reported `INSTALL.bat` completed at `4648d70`; opening `START.bat`, checking first-run typing, and confirming the setup stays closed after persistence still require the physical laptop. Do not paste API keys into chat, logs or bug reports.

## Completed checkpoint — provider error privacy hardening

Code commit `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c` replaces raw provider errors in owner logs and live error responses with stable safe categories, preserving transient-error handling. Focused privacy tests 3/3 and full Cloud Python 323 passed / 60 skipped. Cloud/PostgreSQL #38458215679 ran the new privacy test; Scene #38457949652 and WORLD smoke #38457949491 passed. Render deploy `dep-db78mn5bedkc738a0fu0` is LIVE at the code SHA. Workflow commit `e83b0d5929d1fee256a5165754b66b16b6844766` adds the regression to GitHub CI.

## Completed checkpoint — frozen bilingual evaluation integrity

Commit `5677dca638909d23d96aab2dedab2597dbd196c1` closes a dataset-validator gap: only `tr` and `en` are accepted, and every category must contain five of each. Evaluation tests: 11/11; full Cloud Python: 320 passed, 60 skipped. Cloud/PostgreSQL #38456643001 and Scene #38456642956 succeeded. Render deploy `dep-db78i45bedkc7389oi50` is LIVE at the same SHA; `/health` returned HTTP 200 with the exact commit. This is dataset validation, not answer-quality scoring.

## Completed checkpoint — typed live turns preserve consent and history

Commit `f932b184eda215585a01d8d5d933b9f682611de1` ensures typed `/api/live` turns reach the current-turn memory consent guard and conversation history, with a 16,000-character input cap. Cloud Python: 319 passed, 60 skipped; browser tests: 153/153. Scene #38455888286, Cloud/PostgreSQL #38455888395 and WORLD smoke #38455888333 passed. Render deploy `dep-db78feajnfac73d01fo0` is LIVE at the same SHA; `/health` returned HTTP 200 and the exact commit.

## Next tasks — real model and device validation after privacy hardening

1. On the paired laptop, test local Qwen failures/recovery, Gemini fallback, agent chat errors, and image uploads; confirm only useful safe status reaches the user and no image text enters diagnostic logs.
2. Run the frozen 100-case Turkish/English conversation suite against real Gemini and local Qwen, retaining actual transcripts/model identity/latency and independent review. Keep unavailable providers/devices **NOT_RUN**; never infer 100/100 from CI.
3. Measure Qwen token occupancy and Turkish p50/p95 latency on the target laptop before changing interactive context or model defaults.
4. Keep Windows installation deferred until the final combined update and preserve the approval, privacy, and device-permission gates.

## Completed checkpoint — live voice consent release

The live-voice memory guard and grounded tool instructions are pushed at `166ae52e4f47421329e60d1d5c474d47e8ef2a9b`. Scene #38449688028 and Cloud/PostgreSQL #38449688070 passed; Render deploy `dep-db77pougekts73dhtjpg` is LIVE at the same SHA, and public `/health` returns HTTP 200.

## Next tasks — real model and device quality

1. On the phone, confirm an unprompted personal disclosure is not persisted, an explicit “bunu hatırla” is persisted, and password/API-key-like content is refused. Record the actual Gemini Live transcript and device/provider versions.
2. Verify paired-laptop delegation reports queued/completed/failed truthfully and preserves the existing approval before code edits; test on real devices instead of inferring behavior from mocks.
3. Run the frozen 100-scenario Turkish/English evaluation against real Gemini and reachable local Qwen, followed by independent review. This workspace has no Gemini key or Ollama endpoint, so model quality and 100/100 remain unverified.
4. Keep Windows installation deferred until the single consolidated update already requested. Preserve owner approval, privacy isolation, and explicit device permissions.

## Next tasks — real conversation quality and device verification

1. On the owner’s phone and paired Windows laptop, verify accented and unaccented Turkish style/topic commands, Qwen-first routing when Ollama is actually ready, Gemini fallback, voice turn cancellation, image upload/recovery, and 3D scene edits. Record device/model versions and actual failures; do not infer hardware operation from browser mocks.
2. Run the frozen 100-scenario evaluation against real Gemini and reachable Qwen, then obtain independent review. Keep provider transcripts, latency, and factual/style scores separate; missing credentials or unavailable devices must stay `not_run`, never pass.
3. Measure the Vite 821.74 kB raw / 222.42 kB gzip Three.js chunk on a cold dashboard. `Dashboard.tsx` statically loads `CenterStage`, whose default `GolgeOrb` uses WebGL; the separate Hologram Lab is lazy. Add a browser timing/resource contract before considering a deferred orb or CSS fallback, and preserve the initial visual behavior unless the measured gain justifies a change.
4. Keep Windows installation/model downloads deferred until the final consolidated owner update; preserve Approval Gate, privacy, and device permissions.

## Completed checkpoint — Turkish matching release

The diacritic-tolerant code and package-import correction are pushed and verified: Scene `38440168682` and Cloud Queue/PostgreSQL `38440168681` passed, Render is LIVE at `c805e1e`, and served files match the release. The remaining owner phone/laptop and real Gemini/Qwen evaluation steps are listed at the top of this file.

## Next tasks — verify latest Qwen routing recovery

1. `52b776a` is pushed; Scene Build `38438751167` and Cloud Queue PostgreSQL `38438751172` both passed, and Render is LIVE at the exact SHA. Continue with actual phone and desktop provider verification.
2. On the phone, test with laptop/Qwen available, unavailable, and with the presence endpoint temporarily unavailable; verify fallback reply provenance on the server without resending accepted local tasks.
3. Run actual Gemini + reachable local Qwen 100-case TR/EN conversation evaluation with independent review. This workspace has no Gemini key or Ollama endpoint, so deterministic tests cannot substitute.
4. Continue the context-budget audit for verbose recent replies and recalled old-topic evidence.

## Next tasks — activate GÖLGE self-development on the laptop

1. Verify Cloud/Scene Actions and Render for the current self-development release.
2. During the already requested one-time Windows update, install this repository version and ensure GitHub CLI is installed and `gh auth status` succeeds for `fatmakahraman304-hash/ULTRON`. Never paste a token into GÖLGE chat.
3. On the laptop, test a specific request such as “Gölgeye 3D sahne düzenleme özelliği ekle”: inspect diff, approve, verify local suite, draft PR, Actions, manual merge, then Render deployed SHA. Also verify dirty checkout and missing GitHub login stop before editing.
4. Keep PR merge and Render rollout owner-controlled; no automatic deployment is claimed before device verification.
5. Run the real Gemini/Qwen 100-scenario conversation evaluation and independent review when provider/device access is available.

## Next tasks — verify device and provider quality

1. Owner-grounded briefing suggestions are verified live at `a0352a5` (Cloud/PostgreSQL and Scene/UI Actions passed; Render SHA matched).
2. Run the frozen 100-case TR/EN evaluation with actual Gemini and reachable local Qwen, then independent human review. Dataset validation alone does not score model quality.
3. On Windows and phone, verify actual voice continuity, live laptop presence, approval-gated tools, memory correction/deletion, and cloud-to-device task completion. Do not install on Windows until the previously requested final consolidated update.
4. Continue context-budget audit for verbose recent replies and recalled old-topic evidence.

## Next tasks — conversation, memory and reasoning

1. Correction-aware recall release `202e4f9` is verified: both Actions workflows passed, Render LIVE and health SHA matched. Continue with the context-budget audit below.
2. Investigate whether provider-side context recapping drops selected old evidence under verbose recent turns; reproduce before changing.
3. Run the frozen 100-scenario conversation evaluation with real Gemini and reachable Qwen, then independent review. Provider-free tests are not model-quality scores.
4. Validate actual laptop/phone voice and task completion when devices are available; preserve Approval Gate. No Windows installation now.

## Next tasks — 2026-10-13 public model retrieval

1. Functional bca7e94 is Render LIVE. Fixed workflow 72f5e91 passed Scene #38388140843 and Cloud #38388141206; full logs read. Documentation-only final HEAD receives a manual Scene check. Preserve remote GÖLGE identity and protocol compatibility.
2. Public model search is now implemented via Poly Haven CC0. Sources: `scene_assets.py`, `spatial/assets.ts`; opt-in external smoke: `python scripts/tests/scene_public_asset_smoke.py`. Normal CI uses bounded offline fixtures. Source may be unavailable or lack the desired asset; keep explicit no-match/failure behavior. Expand Turkish search synonyms/semantic translation only with tests that reject unrelated matches.
3. Remaining: real provider recognizability/latency evaluation for free-form generation, plus deferred Windows/iPhone voice/geometry smoke. Synthetic Gemini/Qwen outputs in unit/browser suites do not establish model quality or 100/100 conversational score. No Windows installation done.
4. Browser checks: “daire”, “kare çiz”, “bir masa modeli oluştur”, “internetten sandalye modeli bul getir”, then move/rotate/remove/undo; source attribution should stay in saved projects. Test larger catalogue assets against 30MB/200-part/750k-triangle limits before increasing limits.

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

## Next tasks — 2026-10-13 free-form scene synthesis

1. Check exact new Scene/Cloud CI logs and Render LIVE commit after push; functional changes touch Cloud app, static bundles and desktop endpoint. Local full checks pass as recorded below.
2. Remaining user requirement: licensed online model search/download. No asset provider/download credentials or validated source is connected; do not claim internet retrieval. Select and integrate a source with licence metadata, bounded embedded GLB downloads and attribution; keep external references blocked.
3. Run real Qwen/Gemini creative geometry checks (chair, table, house, unusual assemblies, impossible request), validate recognizability, latency and failure wording. Synthetic pipeline tests are not evidence that all arbitrary models can be generated. Original 100-case conversation quality goal remains unmeasured.
4. Deferred final Windows/iPhone smoke: “daire”, “kare çiz”, “bir masa modeli oluştur”, “onu sağa taşı”, “onu yok et”, “geri al”; verify local availability routing and voice on actual hardware. No Windows installation/download performed.
5. Source: spatial/design.ts, spatial/intents.ts, HologramScene.ts, scene_design.py, scene_queue.py, scene_design_api.py. Rebuild generated bundles via node scripts/build_scene_browser.mjs after npm ci; run scene browser/schema tests and disposable PostgreSQL queue tests.

## 2026-10-13 — Shapes and free-form conceptual scene synthesis

- Added direct “daire”, “kare”, “üçgen”, “silindir”, “koni” and “halka” geometry. “Bir masa modeli oluştur” or, inside the scene, “sandalye oluştur” now requests a data-only assembly rather than rejecting every object outside the built-in demo list. Generated assemblies reuse movement, rotation, part selection, removal, reset and project persistence.
- New bounded geometry schema: up to 24 parts, eight primitive kinds, validated dimensions/positions/rotations; provider instruction requests 1–8 meaningful parts for small-model budgets. No generated code, tool call or URL is executed. Invalid output preserves the current scene; closing the workspace prevents late replacement. Generated models are explicitly labelled conceptual, never engineering CAD or downloaded assets.
- Mobile prioritizes actually ready local Qwen, via owner-scoped idempotent scene queue using the existing fenced no-tools worker and shared three-task capacity; only confirmed pre-submission offline rejection allows Cloud fallback. Desktop uses installed Qwen first, configured Cloud otherwise. Scene prompts/results do not enter chat conversations, learning or personal memory. New authenticated Cloud endpoint uses the existing Gemini configuration, no new provider/account/model downloads.
- **Limits:** actual Gemini/Qwen geometry quality and physical Windows/iPhone not tested here. Internet asset search/download is NOT implemented: explicit web-search requests receive an honest explanation. A licensed asset source/download integration remains necessary for that part of the user's request. No claim that every arbitrary object can be reconstructed accurately. Windows installation remains deferred.
- Local checks: **251/251 Cloud Python** with actual disposable PostgreSQL and zero skips (includes three new queue ownership/idempotency/capacity cases); **134/134 JS**, **8/8 Chromium WebGL scene cases**, **6/6 Qwen queue/browser cases with synthetic providers**, two desktop routing tests, schema/parser validation, 18 project checks, npm ci/build, Earth 6 JS/5 Python, py_compile and workflow YAML all pass. Provider outputs in generation tests are synthetic; no actual creativity score measured. PWA shell v63. New CI/Render evidence pending push.

## Next tasks — 2026-10-13 reset follow-up

1. Runtime 60403db is LIVE; Scene/Cloud/Frontend passed. Workflow repair 52ebff6 passed Scene #38353910646, Cloud #38353913024, Listening #38353907640; logs read. Final docs-only HEAD will receive a manual Scene check; preserve remote listening additions at cc2ab74.
2. Physical Windows/iPhone smoke remains deferred to final device update: create engine, move, rotate, select Piston 1, remove, undo, reset and undo reset. No real Qwen/Gemini quality score is available.
3. Baseline orientation now survives project exports. Older files retain only the orientation saved by the old exporter; original pre-edit orientation cannot be reconstructed. Test with `python scripts/tests/test_scene_browser.py` after frontend build and `node scripts/build_scene_browser.mjs`.
4. Next coherent scene improvement: named-part command coverage and rejection of ambiguous targets; ensure rejected out-of-bounds commands do not add undo history. Keep parser limited to explicit local scene edits.

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

## Next tasks — 2026-10-12 natural 3D controls

1. Functional code, all three CI workflows and exact Render LIVE SHA are verified above. Check the documentation-only final HEAD with manual Scene/Cloud workflow dispatch, then physical device verification is the remaining dependency. Sources: `ultron/frontend/src/spatial/`, `hologram/HologramScene.ts`, `HologramLab.tsx`, `dashboard/Dashboard.tsx`, mobile `static/index.html`; generated JS rebuilt by `node scripts/build_scene_browser.mjs` after frontend npm ci.
2. Remaining physical check, after the final Windows update: ask “Bir motorun 3D modelini göster”, then “onu sağa taşı”, “onu döndür”, “Piston 1 seç”, “onu yok et”, “geri al”. This creates a conceptual model; arbitrary manufacturer models require the owner's GLB file. No Windows install/download was performed here.
3. Qwen production runtime fix `72ffb35` was LIVE and both workflows at final Qwen documentation SHA `aff9ee4` passed: Cloud #38132832978, Scene #38132830817; logs read. New scene work re-ran all six Qwen browser/queue tests successfully. Real physical phone → Render → Windows Qwen and real Gemini inference are still not verified; no credentials/VPN available here. Keep that validation separate from WebGL tests.
4. Test scene updates with `node scripts/test_scene_intents.mjs`, `node scripts/test_hologram_project.mjs`, frontend build and `python scripts/tests/test_scene_browser.py` (Playwright Chromium + aiohttp). Run `scripts/tests/test_qwen_browser.py` only with a disposable `ULTRON_QUEUE_TEST_DATABASE_URL`. Do not turn synthetic provider replies into real-model quality claims.
5. Keep UI command scope explicit: no file deletion, tool/OS actions, automatic model downloads or default camera access. Ambiguous lift/remove requests need clarification. Future expansion beyond the bounded built-in library requires actual assets or measured generation integration, not invented success.

## 2026-10-11 — Verified release evidence, Qwen connection repair

- Functional commit: `72ffb35744465626718df83010e73ad36d20c0c7` pushed to `feat/ultron-cloud-shared-memory`; no `main` update.
- Exact-SHA CI **SUCCESS**: [Scene/Frontend #38132619456](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38132619456), [Cloud/PostgreSQL + Chromium #38132619449](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38132619449), [public WORLD smoke #38132619430](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38132619430). Workflow logs fetched/read, including six real-browser scenarios with explicit synthetic providers.
- Render `srv-db20lmei0phs73crgujg`, authorized My Workspace: deployment `dep-db5mdrp5efls73apm39g` **LIVE**, exact functional commit above, finished `2026-10-11T10:38:34Z`. `/health` HTTP200/ok; `/`, `/static/auto-brain.js`, `/static/chat-transport.js`, `/static/sw.js` HTTP200 and byte-for-byte match to the commit. JS responses carry `Cache-Control: no-store, max-age=0`; shell is v56.
- Local final results: 215 Cloud Python tests (includes 45 PostgreSQL cases, zero skips), 93 JS, 17 client/lease, six local runtime contracts, six Chromium scenarios, frontend build and Earth 6 JS/5 Python all passed. No remaining test failure. Before fixes, routing and duplicate-submit regressions failed as expected; refactor-sensitive source checks were updated to the new locations without removing owner/fencing checks.
- This evidence verifies code, synthetic HTTP/queue/model-boundary behavior and deployed assets. It does **not** verify physical iPhone → Render → Windows → real Qwen, real Gemini inference, real model latency/quality, or the historical Windows socket/Live1008 incident cause. Desktop installation/download intentionally not performed. Required next step remains the single physical smoke check described below.
- This documentation-only follow-up preserves the exact tested runtime; its own CI/Render state will be checked separately and reported in the final response.

## Archived next tasks — 2026-10-11 Qwen connection repair

1. Code push, both CI checks and Render LIVE are verified above. Check the documentation-only final HEAD with manual workflow dispatch; then physical verification is the remaining dependency. Browser CI is in `cloud-queue-postgres.yml`.
2. Physical validation remains required after the final desktop update (not installed here): with laptop ULTRON + Ollama running, reload the phone conversation and send “2009 C180 hakkında konuşalım”; verify the new command is completed with `result.provider=local-ollama` and Qwen model. Do not infer real inference from synthetic browser/DB tests. No real cloud/device credentials available here; don't request or log raw secrets/history.
3. If the physical issue persists, capture only new command ID, status, delivery_attempt, progress stage/timestamps, provider/model and presence readiness (omit contents/token). If no row is created inspect the phone's POST/presence HTTP status and loaded shell v56; if queued inspect claim worker, if executing inspect lease and Ollama availability. Live1008 is a separate voice-session error until evidence connects it.
4. Test entry points: `scripts/tests/test_qwen_browser.py` requires disposable `ULTRON_QUEUE_TEST_DATABASE_URL`, cloud requirements + playwright/Chromium. `node --test ultron/cloud_service/test_*.cjs`; Cloud unittest discovery with disposable DB; backend `test_cloud_delivery_guard.py`. Never run destructive synthetic DB setup against production.
5. No further feature/UI decoration or real-model quality score claims before physical Qwen verification. Long-term conversation quality benchmark remains a separate, unrun provider-dependent task.

# 2026-10-11 — Verify same-thread Qwen ordering and provider identity

- **Latest verified functional code SHA:** `5f0f709c7d97fa7f2b66bdcbdaff83987f0f8b50` following queue transaction change `2e2eedd45dee6aa9577f6f512e026ae2fa008af8`. Exact-SHA [Cloud/PostgreSQL #38122601917](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122601917) **SUCCESS** and [Scene/frontend #38122601915](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122601915) **SUCCESS**. Initial change [Cloud/PostgreSQL #38122481638](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122481638) and [Scene/frontend #38122481653](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38122481653) also **SUCCESS**.
- **Owner-scoped Qwen queue:** A transaction-scoped PostgreSQL advisory lock per owner now serializes submissions and atomically checks at most three outstanding local chats, and rejects a *new request in the same conversation* while an earlier command is queued/delivered. It does not stop separate conversations from using available slots or change permissions. Disposable PostgreSQL tests cover two simultaneous submissions (one 202, one 429), owner cap 3, different conversations, no duplicate user messages, and sequential continuation after the prior completed reply was read and saved.
- **Provenance:** Cloud now applies the exact shared Qwen model-family identity validator to its local-ollama completion payload, including legacy desktop messages without the provider field. Non-Qwen (e.g. LLaVA/Llama), blank, malformed, and non-model replies are rejected; explicit `local-no-image` without a model remains accepted with distinct origin. Provider-free tests pass, no new model installation or network calls.
- **Caveat:** Same-thread command gating currently protects *queued/delivered* requests; a completed reply not yet polled/saved by the mobile client may still produce a short ordering window, which should be addressed before the final release. Real Gemini and Ollama Qwen model quality/latency (20-case pilot, then frozen 100-case evaluation) NOT RUN here. Exact Render LIVE deployment SHA and physical Windows/iPhone voice not verified; informal conversational % remains unchanged. `main`, Windows, approvals, privacy boundaries remain untouched.

---

# Latest verified Qwen completion and cloud provenance hardening — 2026-10-11

- **Latest code SHA:** `78a9a9de314888f1c7adea4ca6613575603bac34`, following Ollama length-stop fix `66ad74773190c5e09bad2c043496656b410dbe4c`, provenance patch `b2248db540b8ac1ef1f51edf2971685ceef7f3de`. Exact new code [Cloud/PostgreSQL CI #38119041641](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38119041641) **SUCCESS** and [Scene/Frontend #38119041637](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38119041637) **SUCCESS**. Initial token-limit fix also passed [Cloud #38118862678](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38118862678), [Scene #38118862643](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38118862643).
- **Correctness:** A non-stream Ollama chat with `done=true` but `done_reason=length` is not treated as a complete success. A clean `done_reason=stop` succeeds, as do older valid model replies without an optional reason. This avoids recording truncated answers as complete; it does *not* automatically retry or increase GPU budget.
- **Cloud provenance:** Mobile/paired-laptop completion replies must be nonempty strings with a recognized local provider (`local-ollama` or `local-no-image`). Invalid JSON-shaped or unknown-provider results fail closed instead of being stringified and saved as assistant prose. On successful first-save, `messages.device_id` identifies `desktop-local-no-image` versus `desktop-local-ollama`; model labels remain bounded. Owner/conversation SQL fencing, once-only reply lock, legacy local-Ollama client compatibility and neutral UI provider name remain unchanged. New pure `local_reply_validation.py` is testable without heavy aiohttp SDK.
- **CI transparency:** First provenance commit `b2248db` Cloud succeeded, but Scene CI failed because the lightweight test imported an aiohttp-dependent handler directly. This was fixed by extracting a pure validator and updating its tests; the subsequent exact-code Cloud and Scene CI both succeeded. Do not hide initial red CI.
- **NEXT:** Real authorized 20-case Gemini/Qwen pilot, independent 100-case TR/EN reviews and measured p50/p95 latency. These provider calls and real-model score are **NOT MEASURED**. Latest Render LIVE deployed SHA and physical Windows/iPhone voice/Ollama inference are **NOT VERIFIED**. Remain on feature branch; no main modifications, no Windows changes, no privacy/approval weakening until final user-approved deployment.

---

# 2026-10-10 — Verified continuation style and Ollama reply integrity

- **Latest functional commit:** `303b18df36cf1428da234228fe4f8fd2e07a21da` after first change `14727edaa2b6ed53589bed6bc04da84d59003c67` and follow-up contract fix `4b1ec463704473f4c84a6850d97124fba40c28cb`. Latest exact-code workflows both **SUCCESS**: [Cloud/PostgreSQL #38082521495](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38082521495), [Scene/Frontend #38082521796](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38082521796). Previous code both passed: #38082401537 and #38082401280.
- **Shared natural dialogue:** Turkish/English `Devam et lütfen`, `Devam et böyle`, `Continue please` and similarly unambiguous bare continuations inherit requested answer length, both via bounded Qwen `num_predict` and a *derived fixed wording* system hint. Historical text remains only in user/assistant messages; no raw history is promoted to system instructions. A maximally sized original trusted system prompt is preserved intact by skipping the optional hint. Static pipeline contract updated to confirm real wire serializer connection instead of relying on prior variable name; unit/regression CI passed.
- **No false Ollama successes:** local text-only chat refuses malformed/non-string/empty content, incomplete (`done=false`) results and an actual Ollama model label conflicting with the selected Qwen. These failures do not become forged model replies; valid model responses still use one local inference call and no tools or paid fallback. Tests exercise valid, missing optional model label and invalid payloads.
- **Still pending:** authorized live Gemini/Qwen bilingual pilot and independent 100-case reviews, real device latency, latest Render deployment SHA, physical iPhone/Windows voice. Read-only Render inspection is blocked because no workspace has been user-selected; do not choose workspace without explicit confirmation or claim live deployment. `main` and Windows remain untouched, one-time final update deferred; do not alter approval/privacy gates.

---

# Latest verified Qwen explicit-continuation coherence — 2026-10-10

- **Functional code SHA:** `14f2fe11d9bace632e6dafc78572e00b43918875`, following `a83e8cac974804e34df774feb95ffedcfb630819`. Exact code CI **SUCCESS**: [Cloud/PostgreSQL #38081941536](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081941536), [Scene/Frontend #38081941541](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081941541). First code SHA also passed [Cloud #38081817720](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081817720) and [Scene #38081817699](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081817699).
- **Behavior:** In the text-only, read-only local Qwen mobile/Windows queue, tightly scoped bare follow-ups like `Devam et`, `Continue`, `Kaldığın yerden devam et` inherit the latest *substantive user turn's* CODING/FAST/GENERAL routing and latest explicit short/detailed reply-length preference. Up to the most recent ten already-authorized same-conversation turns are inspected, skipping assistant/system and repeated continuation turns; fresh unrelated requests or explicit `kod yazma` reset routing. No extra model requests, database search, background work, memory writes, new permission, untrusted role promotion, or model download. GPU/Ollama caps remain intact.
- **Tests:** Fake Ollama wire tests verify coding continuation, English continuation, multiple successive continuations, topic changes, previous no-code instruction, empty history, ignored spoofed system/assistant role, inherited brief/detailed token ceiling, and prevention of inherited style on a new task. These are deterministic tests of model routing; **NOT real model reasoning scores**.
- **NEXT:** Run real owner-authorized Gemini and Qwen 20-case bilingual pilot and independent reviews, then frozen 100-case quality and real device response times. No actual percentage improvement or JARVIS parity established by this CI. Production Render commit, physical Windows/iPhone are unverified; keep `main` untouched and final Windows update postponed as requested.

---

# Latest verified Qwen local-chat routing (2026-10-10)

- **Functional code:** `22edb909a93f7a4c4d6d4579994cf5bd12a83a75`, after `6c474f66d85a50302569642cdd4e988a1d707d22`. Exact-SHA CI **SUCCESS**: [Cloud Queue/PostgreSQL #38081094332](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081094332) and [ULTRON Scene/Frontend #38081094309](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38081094309). Earlier base routing code Cloud [#38080922802](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080922802) and Scene [#38080922875](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080922875) also SUCCESS.
- **Provider readiness/correctness:** The text-only paired-phone local chat now counts only installed Qwen family models as available, not LLaVA-only/other-family inventories. `local_chat_ready` checks Qwen candidates against the live loopback tags; `local_chat` filters Qwen candidates before applying configured FastBrain preferences and refuses any non-Qwen substitution. Benchmark and production identity detection use the exact same pure helper `ultron/cloud_service/model_identity.py`. Mock tests cover only-LLaVA and mixed Qwen+LLaVA installations, including actual selected model on the Ollama wire. No download, paid fallback, image-data proxy or desktop tool permissions added.
- **More natural technology dialogue:** A text-only local-chat classifier distinguishes learning/advice about Python/React from actual code generation/debugging. Explicit `kod yazma` and `don't write code` remain normal discussion; actual `Python kod yaz` and `debug` use a coding model when installed. This affects only the Qwen chat queue, not the desktop coding agent. Deterministic mock Ollama tests cover both Turkish and English and preserve read-only/no-tools behavior.
- **NEXT:** Run real user-authorized Gemini and reachable Windows Ollama/Qwen 20-case bilingual pilot, then independent transcript review and frozen 100-case quality/latency checks. These model tests **NOT RUN** in this session; no supported real 100/100 conversation score or percentage bump. Exact production Render SHA and physical iPhone/Windows voice/local inference **NOT VERIFIED**. Keep `main` untouched and postpone one-time Windows update until acceptance and user instruction.

---

# Current priority — honest image understanding in text-only local chat (2026-10-10)

1. **Latest functional code SHA:** `599d8aa709cb1288d95fc3313cc24ab7c4577707`, following `3547fcb6948a78c919c1f87c6569d158aab48ed5` and `c8be0b96f172649a2846e2a860717c56487b5d18`. Both GitHub exact-code workflows completed **SUCCESS**: [Cloud/PostgreSQL #38080586438](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080586438) and [Scene/Frontend #38080586446](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080586446). Previous code [Cloud #38080465402](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080465402) and [Scene #38080465619](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080465619) also SUCCESS.
2. **Verified behavior:** The paired iPhone/Windows local-brain queue transports **text only**, not image bytes. Direct Turkish/English requests to inspect a referenced photo/screenshot now receive a grounded response saying no image arrived, without an Ollama generation request or fake image details. The desktop task-completion report uses the actual provider label and does not claim Qwen inference occurred for that no-image case. Explicit explanatory requests about *how to analyze an image* are distinguished from inspect-this-image requests and routed to an installed text Qwen, not a blind LLaVA. New mock transport and intent tests verify no false visual claim and normal Qwen chat remains functional. English/Turkish response language is preserved for the explicit no-image path.
3. **NEXT:** Authorize and run the real provider 20-case bilingual pilot (Gemini and reachable local Qwen); evaluate real transcripts independently, then run frozen 100-case comparison and latency. **Actual model intelligence and natural-conversation quality NOT MEASURED.** Last deployed Render SHA unverified; Windows/iPhone voice and physical vision upload not tested. This fix does NOT add actual image upload to local queue. Continue on feature branch; do not change main, install on Windows, or relax approvals before final user-approved release.

---

# Latest verified local Qwen conversation token budgeting (2026-10-10)

1. **Functional SHAs:** `a7134b0f6479649434c737077b22ee08f6733434` (shared response-length classifier for Cloud persona + local Qwen) and `ac1e9556851c9943804b838275b2e7b0ec14a2b3` (shared classifier for presentation length flag). Exact code CI [Cloud/PostgreSQL 38080025754](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080025754) SUCCESS; [Scene/Frontend 38080025720](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38080025720) SUCCESS. Earlier code CI [38079929332](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079929332) Cloud SUCCESS, [38079929341](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079929341) Scene SUCCESS.
2. **Verified production behavior:** Local Qwen no longer uses keyword-only `detaylı` detection to pick a generous generation max for requests saying `Detaylı anlatma, kısa cevap ver`. A single pure `ultron/cloud_service/reply_policy.py` uses the latest affirmative, non-negated TR/EN length request for shared cloud style and local Ollama `num_predict` upper bounds. Explicit short: 96–160 tokens; normal: at least 240 (capped 420); detailed: at least 360 (capped 420). Existing Ollama 4096 context cap, model selection, explicit approvals, local/private routing and read-only constraints unchanged. Model quality not measured and lower upper bound is NOT a guarantee of speed.
3. **Honest quality flags:** `response_quality.assess_response` uses the same shared policy to avoid `possibly_too_long` false positives on negated short-response requests. No automatic truncation of user's expected answers, and no extra inference calls.
4. **Next:** Run authorized genuine Gemini and Qwen 20-case pilot and independent transcript reviews (and then full 100), measure owner hardware response latency. **NOT RUN** here: actual provider inference, real model naturalness, exact Render deployed SHA, Windows/iPhone voice. No unsupported increase in conversational/JARVIS percentages. Single final Windows update intentionally postponed; do not modify `main` or change safety permissions.

---

# Latest verified dialogue intelligence (2026-10-10)

1. **Code HEAD:** `800a54d07e0159cec063c67f7555a94abe2ced48` after `dc97a58cf327e4d9c77880d934b845aef5bed9c0`. At latest code SHA GitHub [Cloud Queue PostgreSQL Integration #38079636700](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079636700) SUCCESS and [ULTRON Scene Build Check #38079636678](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079636678) SUCCESS. Earlier correction code also passed both: Cloud #38079471594, Scene #38079471493.
2. **Verified behavior:** On explicit historical named-topic recall, the earliest matching same-conversation user question + assistant answer now also checks the *immediately following* owner message for an explicit user correction, even when the correction omits the old topic name. Only one extra adjacent older-row query is made, owner/conversation/before-ID scoped. Existing character budget retained; fifth historical context turn permitted when a correction shares history with later evidence. New deterministic + disposable PostgreSQL long-history tests protect the newer correction from losing to older Q&A.
3. **Reminders vs memory:** Turkish and English future reminders with clear date/time are treated as *scheduling requests*, not automatic long-history retrieval. Named old-thread recall prompts are still supported. The common persona explicitly forbids claiming a reminder was created without authorized tool confirmation; no reminder is actually scheduled by this code. DB/query isolation validated with real PostgreSQL.
4. **NEXT:** Authorized live Gemini and installed local Qwen 20-scenario pilot, followed by frozen 100-scenario human-reviewed test. Model naturalness/accuracy is STILL NOT MEASURED: do not claim 100/100 or increase inferred JARVIS percentages based only on CI. Latest Render deployed commit and physical Windows/iPhone voice/model calls are not verified; keep final one-time Windows update deferred and don't alter `main` without instruction.

---

# Current priority — latest verified natural conversation improvements (2026-10-10)

1. **Newest verified code:** `ec566816ef4eeaa162b579f05f86bb0828ff4237`, following `a08b3afadaed0f17ec67bfdbab6a3ebe5375b8bf`. Exact code CI: Cloud/PostgreSQL [38078914038](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078914038) SUCCESS; Scene/frontend [38078914033](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078914033) SUCCESS. Previous bounded current-message code likewise passed Cloud [38078688366](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688366) and Scene [38078688244](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688244).
2. **Natural conversation:** Gemini/Qwen now preserve *end-of-current-long-message* corrections within unchanged 16k/3k caps. Explicit topic switch phrasing in Turkish/English now bypasses old-topic keyword fetching and instructs the common persona to follow the new subject instead of reviving earlier tasks. Ordinary follow-ups, explicit recall, approval controls, owner boundaries and minimal UI remain intact.
3. **NEXT:** Run actual authorized Gemini and Ollama/Qwen 20-case pilot and 100-case frozen evaluation with independent human reviews of transcripts and p50/p95 latency. Actual intelligence level NOT MEASURED; do not claim 100/100 or arbitrarily raise the informal JARVIS comparison percentages based on CI. Physical Windows/iPhone inference and latest Render live SHA are unverified; defer Windows update until final acceptance.

---

# Current priority — preserve late instructions in long current prompts (2026-10-10)

1. **Verified code SHA:** `a08b3afadaed0f17ec67bfdbab6a3ebe5375b8bf`. Both workflows completed **SUCCESS** on that exact SHA: [Cloud Queue/PostgreSQL #38078688366](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688366), [ULTRON Scene/frontend #38078688244](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688244).
2. **Real production behavior improved:** Both direct Gemini and local Qwen current-user-message adapters previously truncated from the beginning only (16,000/3,000 characters), silently dropping final user corrections. They now preserve the opening and closing instructions with an explicit omission marker within unchanged caps. Qwen `local_chat` no longer strips the final tail before its Ollama wire call. Regression tests check both provider message lists and mocked local Ollama wire payloads, no GPU/cloud secrets needed.
3. **NEXT:** Real authorized Gemini/local Qwen 20-case pilot, independent transcript review, full frozen 100-scenario run per provider with measured latency. No 100/100 score or new intelligence percentage based solely on code tests. Exact latest Render deploy SHA and physical iPhone/Windows verification still unconfirmed; defer single final Windows update as requested. Preserve privacy, cloud/local fallback, approval gates and minimal UI.

---

# Current priority — natural Turkish/English conversation cues (2026-10-10)

- **Latest code SHA:** `0f0f9936d3407d63e91218adb5b5e7645b63971f` after `3d07bf4df776a23472d61c11a232e49922ca780c`. Negated requests now control tone and reply length: `Şaka yapma` is not treated as a request for a joke; `Kısa cevap istemiyorum, detaylı anlat` selects detailed output; the final affirmative instruction wins. Everyday correction and follow-up wording (`Yok, 2010 değil 2009`, `Aslında...`, `Onu/Buna/Şunu...`) is recognized in the shared Cloud+local conversation persona. No model calls, new memory writes, system permissions or UI controls were added.
- **Regression coverage:** Deterministic Turkish+English prompt-routing and explicitly negated tone tests. Cloud/PostgreSQL CI [38077714651](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38077714651) SUCCESS; Scene build job `verify` within [38077714632](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38077714632) SUCCESS (workflow completion status should be checked again before calling the workflow fully complete).
- **NEXT:** Actual model quality remains NOT MEASURED. Run authorized local Qwen and/or Gemini 20-case bilingual pilot (`evals/conversation/run.py --pilot`), independently review real transcripts, then full 100 cases per model and measure p50/p95; only then revise conversational quality estimates. Latest production Render commit and physical iPhone/Windows inference remain unverified. Windows one-time final update still intentionally deferred.

---

# Current priority — live conversational acceptance pilot (2026-10-10)

- **Latest verified code:** `ceef1f499ccb5690de3bdcd8289873a5d6f8c52f` (preceded by `bf9ddc28b112266228a606e4c2fd817a7625f558`). [Cloud/PostgreSQL CI #38076948096](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38076948096) and [Scene/Frontend CI #38076948157](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38076948157) both **SUCCESS**.
- **Added real-model pilot:** `python evals/conversation/run.py --provider gemini --pilot --output /tmp/gemini-pilot.json` (or `--provider qwen`) evaluates 20 balanced scenarios: one TR and one EN per ten existing categories. Remaining 80 are explicitly NOT_RUN; full 100 frozen scenarios remain unchanged. No fake inference or success rate is generated.
- **Provider attribution:** The Qwen evaluator refuses to label other Ollama-family models (e.g. Llava/Llama) as Qwen. Gemini model labels still identify the actual primary/fallback call. Regression tests cover bilingual selection, family recognition, and the no-Gemini-key end-to-end pilot report producing 0 captured and no score.
- **NEXT:** Run authorized real Gemini and reachable Qwen on actual respective hosts; inspect real pilot transcripts with independent reviewers, then run all 100 per provider and compare quality/latency. No access to owner's Windows Ollama or Gemini key from the GitHub-only CI session. Exact latest Render deployed SHA and physical phone/Windows tests remain unverified. Do not update JARVIS-style percentages without measured model data; Windows final update remains intentionally postponed.

---

# Current priority — validated long-topic recall (2026-10-10)

1. **Latest functional code SHA:** `f73d43358715358dc21b48f4b34c510307627f3f`. Exact-SHA GitHub Cloud Queue PostgreSQL Integration [38073658327](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073658327): **SUCCESS**; ULTRON Scene Build Check [38073658416](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073658416): **SUCCESS**.
2. **New verified behavior:** Explicit named-topic historical recall searches up to 16 oldest AND 16 newest candidates older than the recent 80 turns, instead of newest 24 only. It selects bounded best matches from both ends with owner+thread+before-current SQL filters and adjacent Q&A evidence. New deterministic and real PostgreSQL >24 keyword-match tests verify preservation of original discussion, recent context, tenant isolation and unchanged maximum prompt size. Ordinary followups do not trigger deeper SQL calls.
3. **Next priority:** Run authorized real Gemini and Qwen/Ollama 100-scenario assessments with actual model answers, latency and independent reviews. **100/100 NOT MEASURED.** No user secrets or private chat should be exported for the benchmark. Use the frozen suite and integrity-linked review records; do not score mocks.
4. **Unverified:** Production Render exact deployed SHA of this code, physical iPhone/Windows model/voice, and final once-only Windows update. Keep approval gate, existing model fallback, sparse phone+desktop UI and owner privacy isolation intact.

---

# Current priority — real conversational acceptance (2026-10-10)

1. **Verified code HEAD:** `043a5386e510bc81a1bc163d9887cef8f75a4071`. Cloud Queue PostgreSQL Integration [38073193493](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193493) **SUCCESS**; ULTRON Scene Build Check [38073193481](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193481) **SUCCESS**; ULTRON WORLD Live Read-only Smoke [38073193495](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193495) **SUCCESS**.
2. **New assessment integrity:** Independent review templates carry SHA256 of the exact completed transcript and contain no pre-filled passes. Changed transcript invalidates a prior review; scoring requires matching digest and the five manually reviewed dimensions. Runtime reports capture per-turn model labels, per-turn presentation flags and p50/p95 latency. Gemini evaluation uses the production fallback path but now receives the actual successful model name through `include_model=True`; normal production behavior returns text only.
3. **Still NOT MEASURED:** 100 real Gemini and 100 local Qwen scenarios, independent human transcript reviews, scored naturalness and real device latency. Do not manufacture 100/100 or update the estimated JARVIS completion percentage based on CI tests. When credentials and a reachable model are legitimately available, execute `python evals/conversation/run.py --provider gemini --output /tmp/gemini-eval.json` or Qwen equivalent, use `--review-template` for blank review slots, then score completed human reviews. No extraction of Render secrets or production user chats.
4. Verify Render deployed commit by exact SHA before claiming production LIVE. Final Windows update remains postponed until acceptance; iPhone/desktop physical inference and microphone tests also remain pending. Preserve the existing permission/privacy guard and minimal UI.

---

# Current priority — natural conversation acceptance (2026-10-10)

1. **Latest verified functional code:** `4a196658820aa38f747cb6cd1e74a12714c59eaf`. [Cloud/PostgreSQL CI 38072623731](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38072623731) and [Scene/Frontend CI 38072623801](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38072623801) both completed successfully at this exact SHA. This follows `064a9f6efbea16f5a71bb474f35e27300584d26c` (older Q&A retrieved even when topic is incidentally mentioned recently).
2. **What changed:** older matched question/answer excerpts in `select_contextual_turns` now use bounded opening+ending excerpt selection rather than taking only the first characters. This retains an explicit conclusion or correction at the end of a long previous message, within unchanged model context/turn limits. New deterministic and real 110+ message disposable PostgreSQL regression checks prove historical ending survives, recent dialogue remains, and no other tenant/thread data leaks.
3. **NEXT TASK:** Real Gemini and locally reachable Qwen 100-scenario transcripts with independent correctness/context/style/honesty/privacy reviews, model identity and latency measurement. A CI PASS is NOT a 100/100 conversational model score. Do not use or disclose production credentials to bypass authorization.
4. **Still pending:** Exact Render live deployment verification for this latest SHA, actual iPhone and Windows microphone/Ollama inference tests, and the deliberately postponed one-time final Windows update. Keep existing safety approvals, minimal UI and conservative online/offline routing.

---

# Current priority — verified conversation continuation (2026-10-10)

1. **Latest verified functional HEAD:** `1e5e11002a471d041023e5c8efd95047b733442b`, following `d9d1f9ac33d75fd558671a2f3fafc7ab376dd5af`. Both CI paths PASS at this exact HEAD: [Cloud/PostgreSQL 38071243972](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071243972) and [Scene/Frontend 38071243961](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071243961).
2. Conversation improvements in this continuation: older-than-80 **explicit named** same-thread recall with bounded SQL matching and adjacent Q&A evidence; important end-of-long-message corrections preserved in shortened history; relevant short topic names DAÜ/YDÜ/Qwen/KKTC recognized; persona guided to rely on actual prior evidence without inventing old dialogue. Ordinary chats retain bounded recent context; approval, privacy, no cross-tenant access, model routing and sparse interface remain unchanged.
3. **NEXT:** Run the versioned 50-TR + 50-EN Gemini and Qwen/Ollama scenarios where authorized providers genuinely exist, retain actual transcript/model/latency artifacts, independently review correctness/context/style/honesty/privacy; only then report a score. Do not call infrastructure tests a 100/100 conversational score. Compare real latency before model changes.
4. **Not yet verified:** live-model inference, production Render commit for these two new code commits, physical iPhone/Windows model/microphone tests. Windows installation deliberately deferred until final update; old Windows safely uses Gemini when Ollama readiness is unavailable. Do not disclose secrets or bypass permissions to make evaluation run.

---

# Current priority — conversation acceptance (2026-10-10)

- **Latest verified functional code:** `066b7b982a19c97297a2d74ee4cf68a4a9c4d336`. Long-thread recaps now sample the actual beginning, midpoint and end, even after 80+ prior turns, rather than sampling only the latest 80.
- **Verified CI:** Cloud Queue PostgreSQL Integration [38070614904](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614904) SUCCESS; ULTRON Scene Build Check [38070614899](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614899) SUCCESS. New offline synthetic-long-thread and disposable PostgreSQL 120+ history/tenant-boundary tests are covered.
- **Next:** Obtain authorized real Gemini and local Ollama/Qwen evaluations without extracting secrets or connecting production private conversations. Run frozen 100-scenario suite for each available provider and independent human review before any quality score. Measure latency and context losses before increasing prompt budgets.
- **Do not yet:** call natural conversation 100/100; deploy a Windows update; claim new Render deployment LIVE without exact SHA confirmation. Preserve sparse UI, Cloud approval gate, owner isolation, and conservative model fallback.

---

# Current priority — conversational intelligence (2026-10-10)

## Next tasks

1. Code commits `b327c3d` and `675ea67` are pushed; Scene and Cloud/PostgreSQL workflows passed at both exact SHAs. Render remains healthy at Cloud SHA `1ad5f28` because its root directory is `ultron/cloud_service/`.
2. On the paired laptop, verify Qwen fallback, model/vision error handling and real uploaded-image analysis; confirm diagnostics do not contain provider strings or image-derived text.
3. Run the frozen 100-case Turkish/English evaluation with actual Gemini and local Qwen, independent transcript review, and latency records. No live provider quality score exists yet; keep unavailable runs NOT_RUN.
4. Measure target-laptop Qwen token occupancy and latency before changing interactive context. Windows installation remains deferred; preserve approval/privacy/device permissions.

---
Historical task records below; the priorities above supersede older Windows-install or non-conversation tasks.

# ULTRON — Sonraki Kesin Görevler / Kesinti Devam Kaydı

**Repo:** `fatmakahraman304-hash/ULTRON`  
**Branch:** `feat/ultron-cloud-shared-memory`  
**Doğrulanmış kod HEAD:** `afe9f5b6855fc4742e384a4d298b71ee6c6feb18` (ardından yalnızca doküman commit'i gelebilir).  
**CI:** `ULTRON Scene Build Check` run `37915768918` — PASS.

## Hemen yapılacak
1. `git status` ve `python scripts/ultron_dev_resume.py` ile yeni oturumun durumunu oku.
2. Windows 11 cihazında son branch'i pull ederek `START.bat` çalıştır; Earth Watch kamera/zoom kaybı, drag seçimi, Türkiye/Kıbrıs focus ve UTC SUN düğmesini manuel test et. Başarı gözlemi olmadan PASS yazma.
3. İnternetsiz durumdayken Earth Watch fallback, ISS WAIT durumu, network request ve UI cleanup davranışını gözle.
4. **Cloud P1 devam:** `ultron/cloud_service/app.py` için gerçek PostgreSQL üzerinden eşzamanlı claim/ack/retry integration testi yaz ve CI'da opsiyonel servisle koş; `mark_app.py` worker yeniden teslim/retry davranışını incele. Attempt token/fencing (eski worker sonraki claim'i bitiremesin) eklemeden tam idempotence PASS yazma.
5. Yeni kod için `npm run build`, `npm run test:earth`, backend pure unittests ve uygun CI workflow'u çalıştır; 4 geliştirme belgesine gerçek sonuçları yaz.

## Test komutları
```bash
python -m unittest discover -s ultron/backend/tests -p 'test_earth_watch_config.py' -v
python -m unittest discover -s scripts/tests -p 'test_ultron_dev_resume.py' -v
python scripts/ultron_dev_resume.py
python -m unittest discover -s ultron/cloud_service -p 'test_device_queue_contract.py' -v
cd ultron/frontend
npm ci
npm run build
npm run test:earth
```

## Sonraki öncelikler
- Kullanım hakkı açık offline texture + gerçek GPU memory/texture cleanup testi.
- Audio owner, wake-word, Türkçe STT/TTS ve barge-in regresyonları.
- Ollama local/cloud provider düşüşü ve memory persistence testleri.
- Agent görev logları için bounded retry ve state/checkpoint mekanizması.

## Kesinti koşulları
GitHub erişimi, izin veya güvenlik engeli çıkarsa burada gerçek başarısız adımı belirt. Bir oturum kendiliğinden arka planda devam etmez; sonraki Codex oturumunda `AGENTS.md` ve bu dosya üzerinden başlanır.

## 2026-10-09 doğrulanan Cloud queue altyapısı
- SHA: `34b80e43abe023e58a8f65c87688aa104d6d55e7`; Actions `37894840971` PASS.
- Eşzamanlı claim advisory lock, inactive completion reddi, retry limit ve guard için 6 izolasyon testi.
- Sonraki agent kesin adım: live/ephemeral Postgres ile claim/fencing integration tests; Render deploy/telefon testini kullanıcı ortamında ayrı doğrula.


## 2026-10-09 — Cloud P1 delivery fencing tamamlanan aşama
- En güncel doğrulanmış **kod SHA**: `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`.
- Scene/Cloud contract build: `37897505788` **PASS** (14 Cloud contract testi).
- Disposable PostgreSQL integration: `37897505793` **PASS** (4 test).
- Bütün eski worker callback'leri (completion, lease/progress, checkpoint) yalnızca o claim'e ait `delivery_attempt` ile kabul edilir. Control command geriye uyumludur.

## Sonraki kesin görev
1. Render uygulamasında `/health` üzerinden **deploy.commit** doğrula; branch commit ile birebir eşleşmeden yeni protokolün canlıda çalıştığını iddia etme.
2. Son branch'i Windows 11'e `git pull --ff-only origin feat/ultron-cloud-shared-memory` ile al ve `START.bat` smoke testi yap.
3. Telefon → Cloud → desktop gerçek `agent_task` gönder; delivery attempt >0, lease 20 saniye korunuyor mu, sonuç telefona geliyor mu? Telefon/laptop araçları çalışmıyorsa gerçek hatayı kaydet.
4. Yerel irreversible eylemler için permission-aware idempotency journal tasarla ve test et: re-delivery, duplicate action ve approval gate güvenli kalmalı. DB fencing sadece Cloud callback'lerini sınırlar.
5. Cloud queue load/reconnection ve DLQ/expired cleanup stres senaryoları; gerçek microhone/Gemini Live ve RTX GPU canlı testleri ayrı sürdür.
6. Test/CI sonucunu ve dört devam dosyasını aynı SHA ile güncelle; sıradaki işi kodlamaya geç.

**Dağıtım uyumu:** Yeni Cloud sunucusu eski agent_task istemcisinden `delivery_attempt` gelmediğinde güvenli biçimde callback'i reddeder. Masaüstü branch'inin de güncellendiğini ve server migration tamamlandığını doğrula.


## 2026-10-09 — Güncel kesin sonraki iş (Döngü 7 sonrası)
- **Güncel doğrulanmış kod SHA:** `d96638e1ecaad7d0b800e20fb22580ade555e777`.
- **CI:** `ULTRON Scene Build Check` `37914696238` PASS (5 Earth, 10 masaüstü lease/client, 14 Cloud contract, 3 resume, frontend build).
1. Render `/health` üzerinden sunucunun deploy commit'ini kontrol et; Cloud migration ile desktop branch aynı protokol neslinde değilse canlı görev testi iddia etme.
2. Windows üzerinde yeni branch'i al, `START.bat` smoke testi, gerçek Gemini Live ve telefon görevini dene. `CloudDeliveryRejected` geçersiz claim'i kesiyor mu, normal 5s lease refresh çalışıyor mu? Kullanıcı cihazında gözlemlenmeden PASS kaydetme.
3. **En yüksek P1 kalan risk:** Onay mekanizmasını ihlal etmeyen ve yalnız izinli yerel eylemlerde çalışan durable action-level idempotency/checkpoint journal tasarla. Duplicate task sonrası aynı geri döndürülemez tool çağrısını tekrar çalıştırmama semantiği ve crash recovery testleri ekle. Cloud fencing'in already-executed tools'u geri alamadığını belirt.
4. Çoklu worker yeniden bağlanma ve deadline/lease stres testi; mümkünse disposable PostgreSQL 16 senaryosunu çoğalt. Memory/performance etkisini ölç.
5. `ULTRON_ROADMAP.md`, `ULTRON_PROGRESS.md`, `ULTRON_NEXT_TASKS.md` ve `ULTRON_TEST_RESULTS.md` dosyalarını her doğrulama sonrası eşleştir.


## Döngü 8 sonrası kesin adımlar (CI doğrulandı)
1. Kod `afe9f5b6855fc4742e384a4d298b71ee6c6feb18` GitHub Actions `37915768918` PASS: 11 yeni dispatch testinin yanında 10 lease, 14 Cloud contract, 5 Earth backend, 3 resume testi, TypeScript/Vite ve Earth math PASS. Yeni kod değişikliği yapılınca aynı kontrolleri tekrar çalıştır.
2. Gerçek Windows 11 üzerinde telefon → Cloud → desktop agent_task, yeniden deneme ve süreç kapanma/kurtarma senaryolarını gözle; canlı eylem ve onay testini PASS saymadan kaydet.
3. Komut-seviyesi fence'den sonra *per-tool* permission-aware journal: tool çağrı kimliği, onay öncesi/sonrası durum ve crash 'uncertain' kararı; reset/manual audit akışı tasarla. Tam exactly-once vaadi verme.
4. Render `/health` deploy.commit, Windows START.bat, Gemini Live, Earth Watch ve RTX GPU hâlâ cihaz testine bağımlı.

### Windows tekrarlama testi için güvenli kılavuz
- Testi geri alınabilir/yalnız okuma eylemiyle yap; gerçek belge silme, ödeme, kapatma veya sistem ayarı gibi işlemlerle duplicate/retry testi yapma.
- Tek bir `agent_task` komut ID'sinin Cloud tarafından ikinci attempt ile verilmesini kontrollü test ortamında doğrula. İkinci otomatik Gemini dispatch olmamalı; telefon manuel kontrol mesajı görmeli.
- `data/cloud_remote_dispatch.sqlite3` yerel, kalıcı ve `.gitignore` kapsamındadır. Dosyayı temizlemek önceki güvenlik kayıtlarını kaybettirir; otomatik temizleme önerilmez.
- Render, canlı Cloud deploy ve gerçek Windows/telefon/RTX/mikrofon smoke testleri **NOT RUN**.


## Native iPhone Siri (v0.3) doğrulama ve devam
1. `Native iOS Build` workflow'u exact HEAD için XcodeGen, Simulator ve unsigned device build çıktısına bak; FAIL varsa derleme hatasını gider.
2. Mac/Xcode'da imzalı iPhone kurulum; Cloud parolasını gir; Siri'den `ULTRON bilgisayara görev gönder` ile kuyruğa ID ekle; Windows masaüstü agent Cloud claim ve Approval Gate'i gözle.
3. ULTRON Bridge kestirmesini Kestirmeler'de elle hazırla. Kullanıcı **DEVAM ET** demeden `ios_action` sistem ayarları çalışmamalı. Ekran kilidi/suspend davranışı ve izin reddini ayrı test et.
4. Cloud görev durumunu sorgulama ve izinli APNs bildirimlerini geliştirmeye devam et; tam telefon sandbox erişimi vaat etme.


## 2026-10-09 — Native v0.3 doğrulama sonrası kesin devam
- Kod SHA `0b4751a5d7c5f6ceb4642af4eb413f6fb0ca16b9`; `Native iOS Build` run `37917812910` SUCCESS. 5 statik güvenlik testi, Simulator/unsigned iPhone build, unsigned IPA/Xcode artifact paketleme/upload PASS.
1. Mac/Xcode ve uygun Apple signing ile native iPhone'a yükle; Cloud password/Keychain oturumu aç, Siri Ask/Send/Status komutlarını gerçek kilit ekranı ve arka plan koşullarında test et, logla.
2. ULTRON Bridge kestirmesini Kestirmeler'de yapılandır, supported action izinlerini doğrula; telefon sistem ayarı kullanıcı DEVAM ET dokunuşu olmadan değişmemeli.
3. Gerçek telefon→Cloud→Windows ULTRON `agent_task` oluştur, Cloud ID, lease, masaüstü Approval Gate, durum sorgusu ve yeniden deneme korumasını gözle. Render `/health` deploy SHA'yı doğrulamadan production ready deme.
4. Sistem izniyle APNs görev sonucu bildirimleri, Shortcuts ek eylemleri ve kullanıcının açık izniyle iOS entegrasyonunu geliştirmeyi sürdür. Üçüncü taraf uygulamanın gizli ekran kontrolünü veya 7/24 mikrofonu vaat etme.


## TestFlight (kablosuz) — sonraki adımlar
1. Apple Developer Program aktif üyelik, tekil Bundle ID, App Store Connect app record, App Store API (Issuer+Key+p8), Apple Distribution private-key içeren p12 ve App Store provisioning profile sağlanmasını **kullanıcı kendi hesabından** yapmalı. Secret veya parola sohbet/repo/commit içinde paylaşılmamalı.
2. `.github/workflows/ios-testflight.yml` dosyasını inceleyip default `main` dalına PR/merge yap (UI Run workflow default branch gerektiriyor); GitHub `testflight` environment koruması, 5 vars + 3 secrets ayarla.
3. Kullanıcı workflow'u manuel başlatsın, signed archive/export ve TestFlight upload sonuçlarını CI loglarıyla doğrula. Yayın yaptık iddiasında bulunma; Apple beta processing, metadata, encryption questions, AppIcon ve TestFlight internal invitation ihtiyaçlarını kontrol et.
4. iPhone TestFlight daveti ile kablosuz kurulum, Cloud password, Siri App Intents, kilit ekranı, arka plan, desktop queue/Approval Gate uca kadar test et.


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
### Kesin sonraki mobil adımlar
1. Render dashboard üzerinden `ultron-yubh.onrender.com` servisinin canlı commit/branch durumunu kontrol et. **Sadece bu branch deploy edildiyse** `/static/mobile-action-guard.js` HTTP 200 ve yeni `index.html` UI'sını doğrula; değilse prod deploy politikası/branch'i kullanıcının kendi Render hesabında kontrollü güncelle.
2. Gerçek iPhone 14 Pro Max Safari PWA'da (ana ekran simgesinden) ULTRON Bridge kurulu iken Gemini Live'dan `set_brightness=35` iste; izin modalı çıkmalı, otomatik Shortcuts geçişi olmamalı, kullanıcı VAZGEÇ sonrası ayar değişmemeli. Sonra KEStİRMELERİ AÇ'a basıp iOS izin davranışını test et.
3. Arbitrary `ios_shortcut` adı veya kötü formatlı action geldiğinde PWA girişini reddetmeli; `UZAKTAN` sekmesinde queued/delivered sayılarını, görev sonrası badge sıfırlanmasını, offline/reconnect durumunu fiziksel cihazla kontrol et.
4. Apple'ın sistem kısıtları altında izinli PWA voice UX, foreground reconnect ve bildirim seçeneklerini geliştir. Masaüstü Approval Gate veya Cloud lease/idempotency korumasını aşma.

## 2026-10-09 — CORE küçük animasyon + ULTRON WORLD (kod ve canlı kaynaklar doğrulandı)
- CORE içi animasyon: kuş / yörünge / nabız presetleri, React/CSS boyuta duyarlı panel, oynat/duraklat/kapat; animation_show backend + stage tool + Türkçe metin komutları. Rastgele Python/Pygame çıktısı henüz otomatik gömülmüyor.
- Yerel frontend ve masaüstü backend CORE animasyon aşaması: SHA cfacb7355b87af174182b37b635152bd2c204729, frontend build 37925291261 SUCCESS, Scene build 37925291379 SUCCESS.
- WORLD: iPhone ana ekran PWA DÜNYA sekmesi ve Windows CenterStage içi world_map modu; Leaflet OSM sokak haritası (zoom 19 ve atıf), Three.js WebGL küre, adres/koordinat arama, favoris, izinli geolocation.
- Gerçek REST sağlayıcıları: Open-Meteo / MET Norway (Render IP Open-Meteo 429 olduğunda resmî MET Norway tahmin yedeği), adsb.lol / adsb.fi v3 (ADS-B uçak konumu), USGS depremler, Open-Meteo Air Quality, Photon OSM geocoding. Kısa süreli bounded cache, sabit upstream URL, açık kaynak atfı, 502 durumunda sahte veri üretmeme.
- Uydu, Street View, trafik, yağış radarı, rüzgâr, gemiler işaretli harici servis bağlantılarıdır; ULTRON içinde native entegre canlı veri katmanı gibi sunulmaz. 3D her evin detaylı fotogrametrik modeli değildir.
- SHA 5c0b8781f0303ae8351dc772d9df3dbcee57f6f9: Scene build 37927499485 SUCCESS, PostgreSQL 37927499348 SUCCESS, public production WORLD live smoke 37927499312 SUCCESS. 5/5 gerçek API kategorisi JSON kaynak doğrulama PASS (hava MET Norway, uçak adsb.lol, AQI Open-Meteo, deprem USGS, Photon adres). Sağlayıcı erişimi değişebilir.
- Render autoDeploy yes, feat/ultron-cloud-shared-memory dalı. Son live SHA ayrıca Render panelinden doğrulanmalı. Windows bilgisayarda git pull/START.bat gerekir.
- NOT RUN: gerçek iPhone Safari WORLD 2D/3D görsel ve harici harita tile/CDN testi; Windows Qt içinde CORE animasyon fiziksel testi; keyfi Pygame animasyonu gömme, harici trafik/uydu/gemi native katmanları.

### Sonraki WORLD ve CORE görevleri
1. Render live SHA kontrolü, iPhone Safari DÜNYA menüsü 2D/3D ve adres/POI/gerçek uçak/hava/deprem/AQI gerçek cihaz kullanıcı testi.
2. Windows güncel branch git pull + START.bat, sesli küçük kuş animasyonunu ULTRON CORE'da başlat; boyut/oynatma/kapama davranışını fiziksel test et. Yeni masaüstü sürümü Windows yereline otomatik yüklenmez.
3. Harici traffic/satellite/Street View/RainViewer/MET provider lisanslarına uyarak ve erişim anahtarı varsa ayrı sürümde gelişmiş bina 3D tiles; mevcut dış bağlantıları yerleşik native özellik PASS yazma.
4. Keyfi Pygame animasyonunu güvenli MIME/size sınırı ve izinli içerikle CORE'da oynatmaya dönüştüren sonraki modül; mevcut 3 hazır animasyonla karıştırma.
5. Sağlayıcı 429/502 için circuit breaker/backoff/normalization testleri, uygun harita CDN bağımlılığı ve gerçek iPhone WebGL testi.

### ULTRON WORLD sesli ve yazılı telefon komutları — 2026-10-09
- PWA index.html worldVoiceIntent: kullanıcı tarafından konuşulan/yazılan Dünya, 2D/3D, Gazimağusa, Lefkoşa, Kıbrıs, İstanbul, uçaklar/deprem/hava durumu görüntüle komutlarını DÜNYA sekmesine iletir. Harita iframe'i yalnız aynı origin ve kendi parent kaynağının postMessage komutlarını; tip, koordinat, mod ve katman allowlist guard'ını geçirse işler. Lazy-load sırasında en fazla dört komut bekletilir. Sesli sohbet motoru/Gemini reply Cloud oturumuyla devam eder.
- Cache PWA v40. Sesli komut güvenliği ve WORLD sözleşme testleri Scene Build Check 37928165355 SUCCESS; Cloud PostgreSQL 37928165548 SUCCESS. Kod SHA b473a4bfd28835aefae0472fb07a15442e7e383f. Önceki 37928109729 Scene FAIL sebebi test regex'i; düzeltme sonrası PASS. Üretim WORLD real-provider smoke 37928109603 SUCCESS (bu smoke bir önceki sesli komut kodunun commit'inde tetiklendi; sesli komut cihaz testi değildir).
- NOT RUN: fiziksel iPhone Safari PWA sesli komut → iframe görsel etkileşim, WebGL/CDN texture, Windows Qt CORE. Render AutoDeploy canlı HEAD ayrıca doğrulanmalı.

Somut sonraki doğrulama: iPhone Safari ULTRON → DÜNYA; sesle “Gazimağusa'yı haritada göster”, “3D Dünya'yı aç”, “yakındaki uçakları göster”; iframe yüklenene kadar komut kuyruğunu, OSM zoom/MapLibre yerine Leaflet içerik yüklendiğini, kaynak hatalarında gerçek durumu kontrol et. Windows desktop git pull/START.bat ve CORE preset animasyonun ayrı Bird Flap penceresi açmadan görünmesini test et.

## 2026-10-09 — Original MARK-LV native video engine restored INSIDE ULTRON CORE
- Investigation of actual original MARK files actions/video_player.py and ui.py: the player was a QMediaPlayer with a QGraphicsVideoItem mounted in the avatar/camera/video stack. It supports local files, HTTP direct media, optional yt-dlp YouTube resolution with separate synchronized audio/video, initially muted sound, stop/mute. The merged integration/web_panel.py had MOVED _video_cont to a separate QDialog (user's pop-out regression).
- New integration/video_dock.py MarkVideoDock reparents the SAME original _video_cont into the actual QWebEngineView. It positions the native QWidget according to .reactor-panel .center-stage DOM bounds, scaled by viewport, clamped so as not to cover surrounding telemetry/chat. Rechecks while open and calls Qt _fit_video on size changes. No new QMediaPlayer engine or video_dialog is created.
- integration/web_panel.py NativeBridge.videoRequest forwards explicit typed video commands to actions.video_player, and MARK native voice tools continue using old video_player directly. React Dashboard.tsx adds deterministic typed media routing irrespective of chosen model; CORE adds MARK VIDEO native-only button. Unknown or source-less voice 'video oynat' asks Qt native file picker (instead of generating a fabricated animation). Preset CORE bird/orbit/pulse animations remain separate.
- ui.py now retains native/QGraphicsVideoItem support after reparenting, QMediaPlayer pause/resume signal & button, correct sound output selection for mic protection, auto-closes the dock after EndOfMedia/decoder failure rather than leaving a black box. Opening a different clip cancels stale asynchronous YouTube requests.
- Headless GUI smoke scripts/tests/test_mark_video_dock_qt.py explicitly instantiated real PyQt6 QMediaPlayer, QGraphicsVideoItem, QAudioOutput, and verified QWidget signals/placement/resizing; 5 tests PASS with QT_QPA_PLATFORM=offscreen and Ubuntu EGL/PulseAudio dependencies. Pure geometry/plugin/contract tests scripts/tests/test_mark_video_dock.py 12 PASS.
- Exact tested code SHA 54a2f2408c54385fc53bc69f7cf944a7a22b1637, GitHub Actions Scene Build Check https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931870709 SUCCESS. Prior frontend build https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931231558 SUCCESS (no frontend changes since).
- Honest NOT RUN: real Windows GPU/QtWebEngine+QGraphicsVideoItem rendered video frame screenshot, real MP4 decoder and split audio through Windows speakers, live YouTube (yt-dlp/network), complete desktop voice Gemini route. The CI Qt smoke verifies Qt object creation and QWidget behavior, not actual codec playback on a Windows PC.
- This is a Windows-native MARK feature in a GitHub branch; Render is the Cloud Python host and does not execute or install a Windows Qt video widget. Laptop must git pull and START.bat; user might need INSTALL.bat once if dependencies are not present.

### MARK-LV native video: physical verification
1. On Windows laptop: git pull origin feat/ultron-cloud-shared-memory; START.bat. Say 'ULTRON, video oynat' (native voice) or type it / press MARK VIDEO. Native file picker should open; choose a REAL MP4/WebM clip. Assert picture and mute/play/pause/close appear INSIDE CORE, not a Windows video dialog. Confirm dashboard side rails remain interactive.
2. Resize the Windows ULTRON window, switch display scaling/DPI: native QGraphicsVideoItem should refit inside CenterStage with aspect ratio and should never cover the activity/file panels.
3. Test YouTube URL/description resolution with yt-dlp and separate audio; initially muted. Enable sound and check mic echo protection, pause/resume synchrony, close and end/error returns to CORE. CI tests do not assert these real Windows codec/network conditions.
4. Do not represent native Qt video dock as shipped via Render or as an iPhone-PWA playback feature. This path is for local Windows MARK-ULTRON instance. If device video window remains blank, collect runtime logs and codec availability for a targeted fix.


## 2026-10-09 — ULTRON Fast Brain ücretsiz yerel modül (CI PASS)
- ultron/backend/app/core/fast_brain.py: FAST/GENERAL/CODING/VISION sınıflaması. Sadece gerçekten kurulu Ollama modelleri seçilir; ücretsiz Qwen3.5:4b varsa günlük sohbet, yoksa qwen3:4b. qwen3:8b daha kapsamlı sorulara, qwen2.5-coder:7b kod isteklerine, llava:7b görsele. Model otomatik indirilmez.
- ultron/backend/app/core/model_router.py: önce model çalıştırıp ikinci aşamada ekstra paralel 2-model race + judge çağıran gecikme kaldırıldı (Fast Brain interaktif yolunda). Manuel local evaluation korunuyor. Orijinal Approval Gate ve izin/araç akışı korunur; tek model yanıtı veya yalnız hata üzerine fallback.
- ultron/backend/app/core/brain.py: Qwen3/3.5 için think:false, kısa yanıt num_predict, sınırlı bağlam ve 10m sıcak model ayarı. Basit selamlaşmalarda ağır araç şeması atlanır; gerçek görevlerde araç erişimi korunur.
- ultron/backend/config/settings.json: fast_brain etkin ve tercih listeleri; mevcut kurulu modellerle ücretsiz çalışır. scripts/ultron_fast_brain_doctor.py yerel /api/tags ve opsiyonel gerçek yanıt zamanı --benchmark; kılavuz ultron/FAST_BRAIN_README_TR.md.
- Gerçek GitHub CI: code SHA 2d0eb712347cf98e100ea89b05c51751bc7c75d1, run https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37940137389 SUCCESS; 15 test_fast_brain.py PASS, Python compile, TypeScript/Vite ve mevcut regresyonlar PASS.
- Fiziksel Lenovo/Ollama/GPU hızı ve mikrofon gecikmesi NOT RUN. MARK Gemini Live & iPhone Cloud Live hiç değiştirilmedi; bu modül provider ücretsiz plan/sınırlarını otomatik değiştirmez. Model qwen3.5:4b indirme kullanıcı tercihi olup birkaç GB disk/indirme ve cihazda olası CPU offload gerektirir.

### FAST BRAIN kesin sonraki Windows kontrolleri
1. Doğru Git dalında 'git status', 'git pull origin feat/ultron-cloud-shared-memory'; START.bat restart. Proje kökünden .venv/Scripts/python.exe scripts/ultron_fast_brain_doctor.py --benchmark ile gerçekten kurulu modellerin gecikmelerini ölç; kod testlerini gerçek laptop hız testi sayma.
2. İsteğe bağlı kullanıcı onayıyla 'ollama pull qwen3.5:4b', gerekirse resmî Ollama sürüm güncellemesi; benchmark before/after, RTX2050 4GB VRAM ve 24GB RAM taşma riskini değerlendir.
3. Offline local voice Whisper -> Fast Brain -> Piper ve mevcut Gemini Live sesli çağrılarını fiziksel Windows cihazında ayrı ayrı dene; Gemini ücret/limit durumu değişmedi. Approval Gate ve Cloud görev araçlarını regress etme.


## 2026-10-09 — Hybrid Free-First Brain (Qwen primary, Gemini optional)
- iPhone web PWA chat defaults to YEREL QWEN ÜCRETSİZ; separate GEMINI İSTEĞE BAĞLI selector. POST /api/local-chat, GET /api/local-chat/{id} polls real completion. Offline laptop responds 409 rather than silently using Gemini. Gemini Live microphone remains a separately disclosed opt-in service.
- Cloud local_brain_bridge.py: authenticated web-only and owner-scoped chat queue with limited concurrent jobs, context from shared Cloud memory, exactly-once PostgreSQL assistant persistence via local_chat_requests. Render never runs Ollama nor exposes a user-supplied Ollama URL.
- Windows MARK bridge: integration/local_cloud_brain.py chooses only installed Qwen/llava models via FastBrainPolicy, Ollama fixed localhost 127.0.0.1:11434, no Gemini and no desktop tool execution in read-only chat mode; mark_app.py handles mode=local_brain agent_task using lease renewal and checked completion.
- Native iOS CloudSession.askULTRON Siri defaults to local laptop Ollama; ContentView Siri metin beyni selection can explicitly choose Gemini; bounded task polls, no silent Gemini fallback. Continuous native voice is still Gemini Live, not free offline local audio.
- GitHub code SHA 98b5902ab5cc793aa3d16c4a3ac55f993bc15ceb: Scene Build Check 37942388982 SUCCESS, Real Cloud Queue PostgreSQL Integration 37942388970 SUCCESS. iOS code SHA ed82517cf03264d29e04bc5b2fcc414382ba91ac: Native iOS Build 37942797049 SUCCESS (simulator and unsigned iPhone; static contracts). Render 98b5902a deployed live. No real iPhone/Windows visual/audio or local Ollama hardware round-trip benchmarks.
- Windows requires user git pull and START.bat restart; Ollama must run with an installed model. Laptop offline -> free phone chat unavailable. Paid/limited Gemini deliberately remains optional. Camera, PDF, and Live audio paths still use Gemini. Existing approval and desktop automation unchanged.

### Next hardware verification: free-first hybrid
1. Windows laptop: verify clean branch and pull feat/ultron-cloud-shared-memory, restart START.bat. Check ollama list shows qwen3:4b; optional qwen3.5:4b requires separate voluntary download.
2. iPhone Safari ULTRON: choose YEREL QWEN, send Merhaba, test actual round trip. Disconnect laptop and confirm truthful offline error rather than Gemini fallback. Select Gemini manually to compare.
3. Native signed iOS Siri Ask ULTRON on-device test, inspect local/Gemini selection and App Intents lifetime. Continuous Gemini Live remains separate.
4. Windows local latency benchmark: python scripts/ultron_fast_brain_doctor.py --benchmark. Do not assert fixed ms speed from unit CI tests.

## 2026-10-09 • ULTRON Hybrid Brain — local Qwen primary, Gemini optional
- Existing owner-authenticated iPhone Cloud /api/local-chat → paired Windows Ollama/Qwen remains free default text chat. Phone/Render do not themselves host Qwen; Windows laptop and Ollama must be online.
- Added ultron/cloud_service/static/local-voice.js: explicit tap-to-talk in Turkish via browser SpeechRecognition (when available), free Windows Qwen via the existing queue, and browser speechSynthesis for Turkish response. No browser Gemini fallback or automatic background microphone.
- PWA static/index.html: Qwen mic button now calls local recognition; Gemini Live mic starts only after explicit Gemini mode selection plus mic tap. App boot/pageshow/visibility will not silently initiate Gemini anymore. Service worker v43.
- Browser speech recognition may be unsupported in iOS Home Screen PWA and may use the browser vendor's network service. This is not guaranteed fully offline STT, no native iOS Siri entitlement, and does not establish guaranteed speech latency.
- Original Windows Fast Brain via installed Ollama models already exists; Windows MARK live-voice engine still Gemini separately and was NOT switched automatically to local Whisper/Piper.
- Code SHA f33bc81f9bdfdb4d5644c7beeaa7c061f8e63cbf: Scene Build Check #37989333207 SUCCESS, PostgreSQL #37989333208 SUCCESS and Render this code SHA observed live. Physical iPhone Safari microphone and Windows actual GPU latency NOT RUN. Further documentation: ultron/HYBRID_BRAIN_TR.md.
### Hybrid Brain next physical tests
1. iPhone ULTRON: select YEREL QWEN, manually tap mic, grant browser mic permission if supported, verify transcript, Cloud/Windows local answer and Turkish TTS. Confirm no Gemini connection or automatic restart on opening page.
2. Manually select GEMINI, tap mic and confirm original Live native audio works. Return to Qwen; Gemini must never be an unapproved fallback.
3. Windows: run Ollama, paired ULTRON Cloud worker and scripts/ultron_fast_brain_doctor.py --benchmark; measure actual response. Existing MARK voice Gemini Live is a separate audio path.
4. If browser STT is unsupported or requires third-party processing, consider opt-in audio capture relayed securely to Windows Whisper with retention/size/security testing; do not claim done.

## 2026-10-10 — Next concrete ULTRON steps
1. Confirm new standalone persona-policy CI job on b982019a0afe61cb4d1a39740e3fb9eccb9b3c8c. If red, inspect job steps/log and fix.
2. Retry Cloud Postgres runner integration when service initialization recovers; do not call its failure a regression without logs.
3. Check Render /health deployed commit, then physical iPhone Gemini Live and local Qwen conversations using jokes, personal memory and an emergency statement.
4. On Windows pull feat/ultron-cloud-shared-memory, START.bat; check microphone/approval gates still work. This connector cannot write to C:.
5. Explore user-controlled tone/humour preferences, opt-in briefings and preference sync to desktop agent; never claim true consciousness.

## 2026-10-10 — Next after verified CI
- CI proof: https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37992572797 succeeded (persona + actual PostgreSQL). Scene Build Check #37992487672 also succeeded.
- Outstanding: check Render release SHA, owner iPhone free-Qwen/Gemini mode behaviour and device voice; sync local Windows branch and start with START.bat; do not call the remote-only GitHub changes locally installed.
- Improve user-configurable style, humour, life reminders and secure opt-in calendar integrations with tests. Maintain permissions and user override.

## 2026-10-10 — Post-persona CI follow-up
- Latest passing Cloud+desktop persona/real DB CI: https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37992833637
- Next: verify Render /health active deployed SHA and actual Live voice/local Qwen on user devices. Sync Windows folder from feat/ultron-cloud-shared-memory; only GitHub was modified here.
- Add opt-in personal briefing, calendar/email integrations, adjustable wit and preference memory with explicit consent; keep Approval Gate active.


## 2026-10-10 — Owner request: complete 10 JARVIS-gap categories (realistic plan)
Scope and boundary: feature requests are accepted as a roadmap, NOT a claim that all 10 are implemented. Never represent sentience, unlimited iOS entitlements, physical holograms, powered-off PC control, or universal physical device access as available.

1. **Emotion / humour:** shared conversation policy now includes user-requested serious mode and warm personal style. More adaptive style preferences must be saved only after explicit consent and verified end-to-end.
2. **Personal life memory:** cloud/local shared history is available. Opt-in daily briefing is guided by real saved memory; next build source-authorized Calendar/Email integrations, data minimization, edit/delete controls and device tests.
3. **Learning:** user-approved preferences, task outcomes and corrections only; no silent surveillance, account crawling or unapproved collection. Add reviewable learned-facts dashboard.
4. **Powered-off laptop:** Cloud can hold requests but Windows-specific work cannot execute until an authenticated Windows worker comes online. Consider only user-owned, separately powered always-on worker; never promise power-on/control without suitable hardware or Wake-on-LAN network configuration and testing.
5. **iPhone Siri:** installable PWA with explicit Shortcut Bridge approval; native Swift source exists. Full Siri/background access requires signed installed iOS app, entitlements and Apple constraints. TestFlight has not been published.
6. **Hologram:** 3D Scene Lab on monitor is implemented. Genuine free-air volumetric hologram requires external display hardware not present.
7. **Human-like continuous voice:** Whisper/Piper local and optional Gemini Live already exist; test real Windows devices, speech interruption, latency, voice quality and phone/browser capability gaps. No perfect latency or unrestricted always-on phone microphone promise.
8. **Self-updating:** development request queue, GitHub CI and safe desktop update preparation exist. Require explicit owner permission, verified commit, clean worktree, tests, rollback and restart before announcing installed success. Never self-approve.
9. **Daily life apps:** add OAuth least-privilege, per-action authorization, calendar/email adapters, provider-reported delivery receipts, opt-in briefings, and integration tests before claiming complete management.
10. **Physical device control:** use only authorized supported IoT/Home Assistant HTTP devices, require confirmation for changes and report disconnected/missing devices honestly.

**Implemented this pass:** shared persona now adds explicit opt-in grounded daily-brief rules, per-request disable-jokes instruction, and no implicit personal learning or cross-device access claims. Four offline tests added in test_conversation_persona.py (12 tests total). Check Cloud Queue PostgreSQL Integration CI for these commits; physical devices and Render deploy remain unverified.


## 2026-10-10 — After owner briefing UI
1. Verify scene-check CI at c1c641f67cf7a8627609b02df2996072a88489d6, especially personal panel Node tests and older local voice tests.
2. Inspect Render service srv-db20lmei0phs73crgujg until live deployment matches current branch. Render autoDeploy=yes: do not trigger duplicate deploy.
3. On user's iPhone log into PWA, open HAFIZA, explicitly tap ÖZETİ GÖSTER and DURUMU KONTROL ET. Verify owner-scoped memory, no extra permissions, errors and empty state.
4. Install latest branch on Windows only with clean worktree and user-controlled update, then run START.bat. Test actual desktop and optional Qwen voice.
5. Next functionality: consent-based calendar/email connections with strict read scopes and no speculative appointments, editable learning preferences, verified device support and safe releases.


## 2026-10-10 — Next steps for life assistant
1. Verify final Cloud Queue PostgreSQL Integration + Scene Build Check CI green and Render service deployment SHA matches branch HEAD.
2. Test manually on iPhone Safari: create, list, complete/undo, confirm-delete; reopen tab and check persisted changes.
3. Confirm daily briefing displays owner-created plans. Query Qwen and opt-in Gemini, ensuring no fabricated appointments or reminders.
4. Add owner-selected timezone, edit/reschedule and optional consent-based notification channel with actual delivery acknowledgement.
5. Integrate third-party Calendar/Email only with scoped OAuth and explicit account connection and protect tokens; distinguish external providers from ULTRON's plan notebook.
6. Continue remaining ten JARVIS gaps with physical-device and safe self-update verification.


## After ULTRON Life plan rescheduling
1. Verify Cloud Queue PostgreSQL Integration and Scene Build Check for commit adding PUT/edit UI. If red, inspect failed GitHub logs and fix before continuing.
2. Verify Render autoDeploy latest code SHA live without manually triggering an unnecessary deploy.
3. On real iPhone: HAFIZA > KİŞİSEL TAKVİM > PLANLARI GÖSTER > DÜZENLE; change date and time; KAYDET; refresh and verify persisted. Check cancel, failed save, done state and cross-user isolation.
4. Next opt-in capabilities: user-selected timezone, optional verified calendar .ics export or provider OAuth, repeat plans; do not promise phone push alerts until actual provider and permissions configured.


## Next ULTRON Life acceptance and follow-ups
1. On a logged-in iPhone, open HAFIZA > KİŞİSEL TAKVİM VE PLANLAR, select Türkiye or Kıbrıs timezone and tap .ICS TAKVİM DOSYASINI İNDİR. Import the downloaded file in Apple Calendar only with user consent; verify timed plan and all-day plan timestamps. iOS browser/PWA download support and real import have not been tested.
2. Verify no private notes or automatic alarms appear in downloaded .ics; verify export does not mark a plan complete or update Cloud records.
3. Confirm Render live commit corresponds to latest code/test SHA and CI Cloud PostgreSQL + Scene Build Check succeeded; inspect new failures before changing more code.
4. For real two-way calendar integration require explicit provider OAuth authorization, least-privilege scopes and token security. For alerts require deliberate user opt-in and verified delivery; no alerts exist now.
5. Consider per-owner saved timezone default with versioned preference and no implicit location tracking; continue actual phone/Windows Gemini/Qwen voice tests and safe updates.

## After approved learning review (current)
1. Check latest Cloud Queue PostgreSQL Integration and Scene Build Check on exact HEAD; if failing, inspect job step and fix first. Check Render live hash separately. No hardware test claim.
2. On real iPhone Safari: HAFIZA > İZİNLİ ÖĞRENME. Propose "PREFERENCE / İletişim tarzım / Kısa Türkçe yanıtları seviyorum", tap ÖNERİLERİ GÖSTER, then REDDET or ONAYLA. Confirm pending facts do not appear in ORTAK HAFIZA, approved facts do. Confirm HAFIZADAN SİL really clears the key. Reopen app and verify persistence.
3. Connect model to *strictly validated* user-selected tone without treating untrusted saved memory as executable system instructions; optional playful/serious mode and test no humour in serious situations.
4. Add an optional explicitly consented language-model suggestion extraction step for review inbox (never auto-approve); bound privacy, prompt injection, rate and data retention.
5. For remaining capabilities: Apple/Google OAuth with minimum scopes, true reminder delivery receipts, iPhone native entitlements/hardware, local voice latency, powered-off computer wake hardware, optional IoT device adapters and safe updates/rollbacks. Never invent real hologram hardware or human consciousness.

## Next after optional auto-learning
1. Inspect GitHub Cloud Queue PostgreSQL Integration + Scene Build Check on latest auto-learning HEAD, fix any failing test, verify Render live commit. Do not mark successful without evidence.
2. iPhone Safari HAFIZA > SOHBETTEN OTOMATİK ÖĞRENME: tap status, explicitly enable, switch to chat and type "Tercihim: Kısa Türkçe yanıt". Check ORTAK HAFIZA, then disable and verify new phrases no longer save. Delete saved item using HAFIZADAN SİL.
3. Confirm account A's opt-in and stored facts are not accessible by B. Confirm direct Gemini and free Qwen text accepted. Verify no background audio/camera/email/calendar collection.
4. For smarter extraction beyond direct statements: separate approval inbox for low-confidence AI-suggested memories with source excerpts and PII redaction, no silent automatic approval. Add preferences for retention/export and limits; no unlimited database promise.
5. Other JARVIS goals: least-privilege calendar/email OAuth, native iOS entitlements/device build, Wake-on-LAN hardware, real smart-home enrollment, measured local Whisper/Piper voice and safe desktop self-updating, external holo hardware.


## Next after command-first UI
1. Verify exact HEAD Cloud Queue PostgreSQL Integration, Frontend Build Check and ULTRON Scene Build Check including NEW minimal intent tests. On failure inspect logs and patch, don't handwave.
2. Verify Render live deployed commit SHA. Do not trigger redundant manual deploy (autoDeploy enabled).
3. Real iPhone Safari/PWA: ensure chat input+mic visible, bottom DÜNYA/HAFIZA/UZAKTAN/GELİŞTİR buttons not exposed by default, ⋯ menu expands and closes, typing or speaking "Dünyayı aç"/"Hologram Lab'i aç"/"Ana ekrana dön" changes view. Verify World real map/3D render and Safari browser permission restrictions.
4. Real Windows START.bat: ensure native audio still owned by existing system; CenterStage+chat+small mic appear, old menu/footer hidden, "Hologram Lab'i aç" opens actual HologramLab, "Dünyayı aç" opens Earth stage, "Hafızayı göster" opens ToolPanel, Escape closes modal, menu button provides fallback.
5. Mobile screen-preview hologram is NOT same as full Windows 3D lab. If user wants full parity, ship prebuilt interactive Three.js mobile lab with verified performance/permissions and then test on hardware.
6. Continue truthful capability gaps and avoid real background/PC powered-off or native iOS feature claims without hardware/provider access.


## Next user acceptance: automatic Qwen/Gemini without a manual selector
1. Confirm latest Cloud Queue PostgreSQL Integration and ULTRON Scene Build Check on exact code SHA, inspect failures and fix before calling done. Confirm latest Render deploy status and code SHA (not merely repository commit).
2. Real iPhone: sign in to https://ultron-yubh.onrender.com, refresh PWA/Safari cache. Ensure no large "ULTRON BEYİN", Qwen/Gemini select, rate limit explanation row. Chat composer with microphone, attachment and send must remain.
3. With Windows ULTRON + CloudRemote queue + Ollama running, verify desktop device heartbeat is ONLINE, send ordinary text and test local Qwen answer returns with shared conversation. Tap mic with browser permission and test local speech turn.
4. Shut Windows ULTRON down, wait >15s for heartbeat to expire, send text and check real Gemini reply; try tap-to-speak and Gemini Live only after user tap. On reconnect, send next text and check automatic local selection. Do not claim actual laptop hardware powered-down detection beyond heartbeat.
5. Simulate laptop going offline between presence check and local queue submit: a confirmed 409 desktop_offline must trigger Gemini once; 429 busy, network ambiguity, queued timeouts and permission errors must NOT silently duplicate/replay message.
6. Verify Cloud API key quota failures are reported truthfully; model limits are not removed by hiding labels. No fully unbounded free model claims.


## Next — ULTRON humanlike conversational experience acceptance
1. Verify Cloud Queue PostgreSQL Integration and ULTRON Scene Build Check for exact code SHA dddbb7338c0689aa20fc0d708abfd5433d6646c6; fix any failed tests. Confirm Render deploy of this SHA live, do not infer from commit.
2. iPhone Cloud Gemini test with one conversation id: "2009 Mercedes C180'e bakalım" → "Yakıt tüketimi nasıl?" → "Peki onunla 2016 E220d'yi karşılaştır." Verify multi-turn 'onun' resolution and no stale different-topic bleed; request independent new conversation to ensure isolation.
3. Laptop with Ollama Qwen and running CloudRemote: repeat multi-turn chat, check queued local_brain payload contains bounded ordered turns, no duplicated current user prompt, and actual local Qwen follow-up coherence.
4. On real iPhone Gemini Live voice: speak several follow-ups and verify session_id-scoped history and interruption, no microphone capture without tap and no unproven tool actions.
5. Manually evaluate naturalness for 20 diverse Turkish dialogues (greetings, follow-ups, ambiguity, serious situations, humour requested, corrections, long/short requests). Track latency and provider model names. Do not claim human-level conversation without hardware/provider evidence.
6. For deeper conversational memory consider user-approved summaries of older conversation threads with explicit retention limits, never automatic sensitive facts or cross-user history mixing. Keep minimal mobile/desktop UX.


## Next ULTRON natural conversation tasks before final Windows update
1. Verify all Cloud Queue PostgreSQL Integration jobs including test_conversation_style.py and full Scene Build Check pass for latest functional commit; verify Render latest functional SHA LIVE. If failed, inspect exact logs and fix before new changes.
2. Run real conversational acceptance dialogues on deployed mobile Gemini: "Merhaba" -> natural short chat; "Mercedes C180 2009" -> "Peki onun yakıtı?" -> "Kısa cevap ver" -> "Hayır, 2016 E220d'yi kastettim" -> "Adım adım karşılaştır". Check no invented earlier context when starting a new conversation.
3. Preserve safety of native device approval gates and Cloud text/voice session scoping. Retest phone mic handoff without claiming physical hardware was tested.
4. Later add optional user-controlled advanced conversation presets or explicit feedback scores, keeping the mobile UI uncluttered and avoiding automatic personal-sensitive learning.
5. Only AFTER iterative GitHub+Render development is complete, guide user through a single Windows update of latest clean branch with START.bat/DOCTOR and real local Qwen tests. Do NOT attempt a Windows download or claim local installation now.


## Next ULTRON JARVIS-like capabilities — develop first, install Windows last
1. On the deployed mobile Cloud account, run a real 30-turn conversation: discuss Mercedes C180, switch to design/English for 20 turns, then explicitly ask "Mercedes C180 hakkında ne konuşmuştuk?" and verify selected old context is reflected without inventing facts; then ask "Peki?" and ensure it follows the immediate topic rather than jumping back. Repeat in a brand-new conversation ID to verify topic isolation.
2. On a running Windows Ollama/Qwen desktop after the user eventually installs the finalized build, test the same long thread; confirm acceptable latency on RTX 2050 and adequate context caps (2600 characters).
3. Maintain automated CI and Render proof for every changeset; treat physical iPhone voice latency, iOS PWA, Windows START.bat, local STT/Piper, IoT, calendar/email OAuth, true hologram hardware and powered-off PC interactions as separate unverified goals.
4. Next candidate: opt-in per-conversation "summary of older dialogue" feature with explicit, editable review and deletion. Never auto-save sensitive personal information or let LLM-authored summaries become system instructions; prefer deterministic bounded sources and preserve all owner approval/security gates.
5. Update user only with actual verified code/test/deployment outcomes, not a promise of nonstop autonomous work beyond the scheduled hourly task. Laptop installation remains deferred until the user requests it.


## Next ULTRON steps after scoped whole-chat recap
1. Run real iPhone Cloud Gemini conversation: discuss a car, then 20 messages on architecture, then a recent voice topic. Ask "Bu sohbeti özetle" and verify the recap covers the early, middle and latest *known* portions without fabricating facts or claiming exhaustiveness. No UI changes needed: type or speak normally.
2. Test a brand-new empty chat: same command should explicitly say there is no prior thread. Ask "Kitabı özetle" and verify normal book summary task is NOT misrouted to whole-conversation recap.
3. On real iPhone/Windows when approved and available, test Gemini Live multi-turn and local Qwen with shorter context; verify correctness and latency. Do not trigger a Windows download or installation until owner explicitly requests the final package.
4. Consider next: user-requested editable, local-only conversation notes and a review-before-saving mechanism; no automatic sensitive learning or unapproved external cloud sync. Keep UI minimal and voice-first.
5. Recheck GitHub CI + Render on each code SHA; never treat CI unit tests as live subjective conversation quality proof. Physically powered-off control, Apple entitlements, external Calendar/Email OAuth, actual volumetric holograms and hardware tests remain separate.


## Next after owner-reviewed chat notes
1. On a real iPhone Safari/PWA sign in to deployed ULTRON, have a multi-turn conversation, type/speak "Sohbet notu hazırla", inspect HAFIZA draft title and excerpt. Verify it is NOT saved before tapping NOTU KAYDET. Edit content, save, reopen, edit and delete with confirmation.
2. Start another conversation and verify the first conversation's notes do not appear there; check an unrelated user cannot access previews/notes. Verify ordinary "Kitabı özetle" stays a chat request, not a note preview.
3. Test privacy limits with genuinely sensitive-looking user messages; deterministic common-secret filters are NOT a substitute for guaranteed PII classification, so owner must review all excerpts before saving.
4. For Windows Qwen/Cloud Gemini continue improving real conversational and voice response quality; on actual hardware measure Turkish latency and interruption after user authorizes final Windows update. No local laptop install/download until the owner explicitly requests final package.
5. Investigate chat notes export/import or semantic overview only on specific request and with permission; never promote notes to model system instructions or automatic permanent personal memory. Preserve clean command-first interface.


## Next user-requested ULTRON development after safer Live audio playback
1. Test on real iPhone Safari/PWA, with microphone permission after user tap: ask for a two-sentence response; verify its last word is fully audible, UI does not say 'listening' while final WebAudio buffers are still queued, and no second browser SpeechSynthesis voice runs over Gemini Live.
2. Speak during a long Gemini Live response and verify Gemini's server interrupt or local RMS gate immediately stops playback, does not resume old chunks and recognizes the new user turn. Then mute/stop/close browser mid-playback and ensure no audio leak.
3. Test laptop single-speaker leader switching: phone output stops when desktop leads; on reconnect it should not replay stale audio. Check session-scoped transcript and approval-gated device tools remain intact.
4. Evaluate voice echo cancellation/threshold under real room noise and headphones. Consider exposing a private calibration diagnostic only after real recordings/tests; don't hardcode risky mic thresholds or claim flawless full-duplex conversation.
5. Continue safer real user tasks, per-chat edit/review and privacy tests while keeping the clean on-command UI. Windows laptop update/download only once the user explicitly requests final handoff.


## Next: single-speaker ownership hardware acceptance
1. Verify GitHub HEAD Cloud Queue PostgreSQL Integration and Scene Build Check at 4952ea5a6a44c041aebf5d87e21ce2184ad3e48d, verify Render LIVE at same code SHA.
2. User-authorized actual hardware testing later: with Windows desktop genuinely online and audible, phone receives a remote laptop task result and does NOT read it simultaneously via iOS TTS; it still shows the result in chat.
3. During phone Gemini Live with desktop reporting speaking=true, phone retains voice priority in UI; listen for actual duplicate desktop audio and debug Windows-side owner heartbeat if needed. Current phone-side policy cannot mute Windows physical speakers by itself.
4. Phone local Qwen one-tap microphone should take immediate UI priority even if earlier desktop speaker was leading. After stopping local voice, desktop presence refresh can regain speaker role without old WebAudio chunk replay or stale callback interference.
5. Stress overlapping /api/device-presence responses: only newest request should update phone speaker; server and user permission constraints still apply.
6. Real iPhone Safari, Gemini Live permissions, Windows microphone/speaker, Ollama performance and task replay are not verified. Do not install/update user's Windows files until they explicitly request final combined package.


## Next after tap-to-interrupt guarded local voice
1. Check the latest Render deployment dep-db5697jhu5js73djph4g for status live at code 70991ff6610e2cac631a2c1ec91d856588aa0cab; do not infer from GitHub success alone. Verify both Cloud/Scene jobs green, fixed old test.
2. Real iPhone Safari PWA + paired active Windows Qwen (when owner approves the final Windows update): tap mic, speak a long question, tap mic again while response is queued, confirm the old answer appears as text but does NOT begin speaking. Starting a new mic must stop old browser TTS immediately.
3. Test toggling speaker mute, sending typed chat while voice in-flight, hiding PWA and reopening; ensure no late local voice audio and no microphone use when backgrounded. Check desktop one-speaker handoff unaffected.
4. Keep the present deliberate Cloud local_chat queue behavior: tapping mic off is an audio stop, NOT a request to delete or cancel a real worker task; do not duplicate prompts via uncertain Gemini fallback. If user requests task cancellation, design a separately authenticated explicit cancel with approval and idempotent result semantics.
5. For genuine JARVIS quality, perform real latency, Turkish transcript accuracy and interrupt/reconnect measurements on owner devices when available; don't claim full-duplex natural human speech from CI-only tests. Continue advancing real features without installing Windows until requested.


## Next steps — make natural conversation measurably stronger, BEFORE other ULTRON features
1. Confirm Render latest deploy for functional code a6ce694ff35423f93a386140c7e1938a374ad162 is LIVE and inspect any deploy failure. Cloud/PostgreSQL and Scene CI are successful at exact SHA; no Windows installation.
2. Run 30–50 actual phone Gemini dialogues scored on Turkish naturalness, context continuity, corrections, hallucination avoidance and response time. Ask multiple referent follow-ups, abrupt topic shifts, explicit old-topic recall, concise/detailed mode, and "Bu sohbeti özetle"; keep all ratings reproducible and anonymized.
3. When owner requests final Windows installation, test actual Qwen4B FAST vs Qwen8B complex request inference latency and real answer quality on RTX2050 4GB/24GB RAM; 8B likely CPU offload and must not degrade everyday latency. Consider transparent opt-in detailed reasoning if too slow, without showing provider picker in normal UI.
4. Strengthen automatic contradictions / correction prioritization within the SAME conversation without treating old assistant guesses as confirmed owner facts. All untrusted chat/memory remains data, never tool instructions or elevated system role. No new sensitive auto-learning.
5. Avoid claiming JARVIS-level 100% or raising numerical readiness without measured provider/hardware quality. Keep user-requested focus on conversation intelligence; no hologram or UI changes and no Windows local download until final delivery.


Current activation status: Cloud/Render release `bd09410` LIVE; Cloud/PostgreSQL, Scene/UI and WORLD Actions passed. Remaining device work: install at the authorized final Windows update, confirm laptop `gh auth status` for this repository, then create a real draft PR from GÖLGE, inspect Actions, manually merge, and verify Render deployed SHA. No GitHub credential was placed in Cloud or chat.
## Next — verify image creation with the configured provider

1. On Render, test upload → “fotoğrafta ne var?” → “daha iyi yap” and a new prompt such as “mavi bir daire oluştur”; verify same conversation IDs, actual inline image output, and provider error reporting. Gemini API credentials remain server-side.
2. If image output fails, inspect only the safe API error category and check Gemini account/model access; set `GEMINI_IMAGE_MODEL` in Render only to a model available to that account. Never request or paste the API key into chat.
3. Confirm image bytes remain transient in browser memory and are absent from messages/events; test ownership isolation and reattach behavior after reload.
4. Continue deferring Windows installation until the user's final combined update.
## Next — live image quality check

1. In Render UI, try one Turkish and one English image request, download the result on iPhone and laptop, then upload a photo and ask for an edit. Confirm the generated file opens and the original is not available after page reload.
2. Confirm Gemini account access to the configured image model in a real session; offline and fake-provider tests do not establish provider availability or image quality.
3. If editing a HEIC/HEIF photo is rejected by Gemini despite API acceptance, add a server-side safe image conversion path with explicit format and pixel limits; preserve the raw upload only in memory.

## Next — complete end-to-end GÖLGE code-change verification

1. After CI passes for the exact commit, confirm Render deploy health/SHA.
2. On the owner’s Windows laptop at the final combined update, check GÖLGE’s existing GitHub authentication, create an owner-approved draft PR, and verify that no merge/deploy occurs automatically.
3. Add an async bridge-level test for two pending patches if the codegen bridge can be instantiated without hardware; current tests cover the command resolver and publisher contract.
4. Continue provider-backed image generation/edit checks separately; live Gemini credentials/model availability and real phone/laptop image handling have not been established by offline tests.

## Next — real phone and laptop validation

1. On phone, try a new image prompt and edit an uploaded photo; confirm inline output and download/save. A 200 health endpoint does not prove Gemini image-model access.
2. At the already-requested final Windows update, test GÖLGE's approved code proposal against a dirty checkout, missing `gh` login, and outside-root patch; verify all stop safely, then create an owner-approved draft PR without automatic merge.
3. If the phone reports provider access failure, inspect only its safe error category and confirm the account's `GEMINI_IMAGE_MODEL` access without exposing API keys.
4. Do not install Windows or download local models before the requested combined final update.

## Next — verify bounded GÖLGE patch generation and Jarvis-like use

1. Proposal-limit code SHA `4112b3c` is pushed and Scene Action `38437781712` passed. Render remains LIVE at Cloud SHA `54f91bb`, containing the image ownership/failure fix; the new codegen limits are desktop-only.
2. On the owner laptop during the requested final combined update, ask GÖLGE to add a concrete feature; inspect the bounded diff and test plan, approve by ID, then confirm local tests and draft-only PR. Also verify oversized/protected proposals are rejected before approval.
3. Run real Turkish and English multimodal/voice dialogues and score the existing frozen 100-case suite using actual Gemini and installed Qwen transcripts; keep quality unscored until independent review.
4. Continue to defer Windows installation/model downloads until the owner requests the combined final update.

## Next tasks — Memory and Verified Research V3

1. Draft [PR #33](https://github.com/fatmakahraman304-hash/ULTRON/pull/33) remains unmerged; Cloud/PostgreSQL #38555225630, Scene #38555225647 and Local Qwen Listening #38555225690 passed at `698190a94ac8f8a471cc91dc481cac59d0f71ea5`. Continue only with the next memory/research scope below; do not merge or deploy without explicit release approval.
2. Add time-aware episodic/project recall using authenticated owner and current-thread data. Support “dün”, “bir hafta önce”, “son projeye dön” and user corrections with source/time metadata; never use unrelated history as fallback. Add 200–500-turn cross-thread and stale-decision regressions.
3. Extend research evaluation from excerpt overlap to typed claim extraction, contradiction checks, source-domain independence, and quote/claim provenance. Keep any model-based verifier optional and measure its extra latency; deterministic fixtures must not be reported as semantic verification.
4. Test real Gemini and Qwen only when providers are reachable and credentials are available; report model/version, first-token/total latency, and all 100 scenarios with NOT_RUN for missing cases. Do not install/download models or modify the owner’s Windows laptop in this branch task.
5. Add bounded PDF parsing only if a safe dependency and decompression/page limits are justified; retain HTML/text-only truthful behavior until then.
6. After owner approval, release separately; verify production commit, Render deploy SHA and health. Physical iPhone/Windows acceptance remains a separate NOT_RUN item.
## Next: finish Windows startup recovery

1. Review/pull the startup dependency-sync fix from PR once its CI passes.
2. On the laptop, run `cd /d "%USERPROFILE%\ULTRON-3a6f489\ultron\frontend" && npm ci`, return to the repository root, then run `START.bat` once as immediate recovery.
3. On the fixed startup path, run `git pull --ff-only origin feat/ultron-cloud-shared-memory` after confirming the local branch/worktree are clean, then run `START.bat`; verify the frontend build completes and `leaflet` resolves.
4. Continue the previously pending real Windows Ollama/microphone/TTS checks and physical iPhone Safari voice checks. Do not treat CI or Chromium emulation as device validation.
## Current task — recover Windows frontend dependencies (2026-10-15)

- PR #44 is already merged/deployed at `bab1b760fcb97164d42d76b0ca67909a0591538a`. The owner then reported `START.bat` TypeScript TS2307 for `leaflet` because its old `node_modules` was not refreshed after the lockfile changed.
- Current fix branch: `fix/windows-start-sync-frontend-deps` from production SHA `bab1b760`. Wait for Windows PowerShell syntax check and Scene Build CI, then merge only after those checks pass (prior blanket release authorization applies to this fix).
- Immediate laptop workaround: `cd /d "%USERPROFILE%\ULTRON-3a6f489\ultron\frontend"`, run `npm ci`, return to repo root, then `START.bat`.
- After the fix is merged, pull the production branch with a clean working tree and rerun `START.bat`; capture exact output. Then resume physical Windows Qwen/mic/TTS and iPhone Safari tests. Never call those device tests passed based on CI.
## Current task — Windows backend import startup failure (2026-10-15)

- Owner log root cause: `ModuleNotFoundError: No module named 'ultron'` from `merged_api.py` at backend startup. Reproduction: from `ultron/backend`, setting `PYTHONPATH` only to that same backend directory makes `from ultron.cloud_service.conversation_persona import classify_intent` fail.
- Fix branch: `fix/windows-backend-pythonpath`, based on production after PR #50. New subprocess regression fails before the fix and must pass after it; wait for Scene Build CI before merge.
- After merge, on the owner's PC run `git pull --ff-only origin feat/ultron-cloud-shared-memory` from a clean production branch and `START.bat`. Confirm it prints `ULTRON hazır` without degraded-mode warning. Then test a short local Qwen chat, microphone input and Piper playback.
- Do not interpret `[WinError 10054]` during a closed health-check connection or malformed-PDF fixture messages as the fatal startup cause; use the final `Traceback` when diagnosing.
- Follow-up log on the owner laptop: backend reports ready; desktop then exits at `mark_app.py:52` because `memory` resolved to a non-package module. PR #51 has been extended with import-order fix and Python safe-path subprocess regression. Re-run `START.bat` after merging/pulling the reviewed fix; check for `ULTRON hazır` and a still-running desktop before microphone/TTS testing.

## Outstanding PR merge sequence — 2026-10-16

- PR #51 merged as `c66b5dae03a007e3b7674e1f627aaf3569911b4c`. PR #35 was merged into its Memory V4 dependency branch as `7b9fb812c3f9144b0313ca5e479710adc517ca8c`; PR #37 was merged into its interruption dependency branch as `61f3e02f3eaf18dc39a0c3931d23778735f72c5f`.
- Next synchronize PR #34 and #36 with current production, preserving both sides' workflow/doc changes, run checks on exact heads, and only then merge them. PR #47 has content conflicts; PR #48 duplicates the production Windows fix. PR #49 has no Actions checks. Scheduler PR #40 requires its upstream V2 rollout and explicit cost/secrets review.
