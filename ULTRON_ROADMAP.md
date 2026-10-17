## 2026-10-17 — Kaynaklı Google araştırması ve bounded model fallback (güncel)

Geliştirme dalı: `feat/golge-grounded-research-20261017`; başlangıç üretim `b486f13`, uygulama `a42b6bf`, PR #56 düzeltmelerini **yalnızca geliştirme dalına** alma `48a688a`. Üretim veya Render'a merge/deploy yok. Önceki kayıtlar tarihseldir. Ayrıntılar: [docs/GOLGE_GROUNDED_RESEARCH.md](docs/GOLGE_GROUNDED_RESEARCH.md).

Tamamlanan uygulama: mevcut araştırma hattında isteğe bağlı resmî Google grounding; gerçek metadata atfı, çapraz yüzey kaynak gösterimi, owner-bound atomik kayıt, sınırlı yedek model ve sorgu mahremiyeti. Yeni konuşma motoru/özel JARVIS kodu eklenmedi. Gündelik sohbet web açmıyor; programlama sohbeti ile gerçek kod işi ayrılıyor.

Sıradaki kabul: onaylı anahtar/model/kota ile gerçek araştırma ve Google widget kurallarının doğrulanması; gerçek Windows/iPhone ses/kaynak okuma; canlı kaynak çelişki değerlendirmesi. JARVIS'e karşı konuşma kalitesi veya gerçek Gemini/Qwen performans üstünlüğü henüz ölçülmedi. Native ses Google Search ve Gemini Live grounding bu sürümün doğrulanmış özellikleri değildir. Üretim yayın kapısı kapalı tutulur.

## 2026-10-16 — Kullanıcının seçtiği üç eski özelliğin kaldırılması (PR #44)

- GÖLGE intro render, hazır Dünya hologramı ve enerji hologramı; düğmeler, presetler, prosedürel çizim ve araç tanımlarından kaldırıldı.
- Kullanıcı kapsamı açıkça doğruladı: ana canlı CORE ve ayrı Dünya/harita sistemi korunur.
- Kaldırılan türler/şablonlar API'de reddedilir; içe aktarma ve eski snapshot normalizasyonu bunları yeniden etkinleştirmez. Kayıtlı kullanıcı proje dosyaları silinmez.
- Üretime merge/deploy yok; değişiklik mevcut taslak PR #44'te incelenecek.

## 2026-10-16 — CORE / Dünya çalışma alanı (PR #44)

- [x] Ortak normal/kontrol merkezi Dünya durumu, kaynak bağlı konum arama ve seçim, gerçek sokak haritası, GPU geçiş/temizlik, UTC terminatör, gerçek hava/uçuş gösterimi.
- [x] API auth/Origin ve lisanssız uydu sınırları; mevcut kişisel hafıza, agent, approval ve ses köprüsü korunur.
- [ ] Fiziksel RTX FPS/VRAM, Windows mic/TTS ve iPhone Safari; gerçek Qwen/Gemini modeli.
- [ ] İsteniyorsa lisanslı uydu/terrain; görsel kabul ve ayrı üretim onayı. Ayrıntı: docs/GOLGE_EARTH_V7.md.

## 2026-10-15 — PR #44 referans tasarım düzeltmesi

Önceki teknik geçiş tasarım kabulü sayılmadı. Aynı dalda masaüstü menü/CORE/sohbet oranları, yakın-komşulu ağ geometrisi, yıldız ışıkları, enerji halkaları ve projeksiyon tabanı yeniden işlendi. Kontrol merkezi gerçek ölçüm göstergeleri, cihaz listesi, yerel paketlenmiş Dünya dokuları, komutla odak ve sağ olay/kamera/araç sütunuyla düzenlendi. Geometrik mobil SVG kaldırıldı; fotoğraf görünümünde üretilmiş WebP sabit arka plan kullanılıyor. Mevcut runtime, izinli araçlar ve ses genliği köprüsü korunuyor.

Gerçek izole backend, oturum doğrulaması, Origin reddi, WebSocket ve Linux telemetrisi çalıştırıldı. Gerçek model isteği sağlayıcı bulunmadığı için UNAVAILABLE: bu ortamda Ollama veya Cloud cihaz/model yapılandırması yok. Dolu sohbet görselleri görünür şekilde sentetik demo etiketli. Fiziksel Windows/iPhone, gerçek mikrofon/TTS ve Qwen/Gemini çıkarımı NOT RUN; görsel kabul kullanıcı incelemesi bekliyor. PR #44 taslak kalır, merge/deploy yapılmaz. Ayrıntılar: `docs/GOLGE_V5_VISUAL_REVIEW.md`.

## 2026-10-15 — GÖLGE V5 responsive chat, live CORE and laptop control center

Started from production tip `6ef3f5d207fc9430cbbd552988935995529e87f5` on isolated branch `feat/golge-v5-interface-control-center-20261015`. Draft [PR #44](https://github.com/fatmakahraman304-hash/ULTRON/pull/44) is based directly on production. The validated code/test commit is `41c907056130536b6ec7abb482a4a02bf33e1437`; exact-head GitHub Actions pass for Responsive Interface, Scene Build, Cloud/PostgreSQL, and Local Qwen Listening. A stale browser assertion was corrected to measure the independent fixed SVG wallpaper instead of the intentionally cleared body background. The PR remains unmerged and no deployment was started. The interface has one shared React dashboard state with a desktop-only, lazy-loaded control-center view and a mobile-only chat layout; switching views preserves the mounted dashboard runtime, conversation and device bridge. Existing CenterStage and EarthWatch were reused. The control center displays only the telemetry/device/event data supplied by the existing runtime, and unknown sensors remain “Kullanılamıyor”; its tool, terminal and camera entries call existing permission-aware panels/bridges. It adds no shell endpoint or fake live camera/weather/flight feed.

The desktop idle CORE uses a deterministic, bounded Three.js Fibonacci-sphere network (1,400 points, sparse links, signal points, four rotating rings and projection beam). State and amplitude are wired to the existing desktop audio bridge. Chromium WebGL testing caught an undeclared `alert` shader uniform that source-level checks missed; it was fixed, and CI’s real-browser dashboard test now checks for shader compilation errors, a clean WebGL context, control-center/globe entry, and return to CORE. The page honors reduced motion, visibility/intersection pause, responsive pixel ratio and resource cleanup. This verifies Chromium/SwiftShader WebGL only; it is not a measured RTX 2050 frame-rate claim.

Mobile chat now omits the CORE and desktop control center, keeps a separate scrolling message area and composer, and uses a fixed illustrative night-lake SVG wallpaper (not a camera or a claimed photograph). The cloud PWA stylesheet and service worker cache were updated in parallel. Visible legacy product names in the dashboard/scene/accessibility copy were changed to GÖLGE while internal API names remain compatible. Browser checks covered 390×844, 1366×768 and 1920×1080; physical iPhone Safari and Windows are still untested. Real backend/model/audio behavior and Render deployment remain unverified; no merge or deploy was performed.

## 2026-10-14 — Cognitive intent router v2 on production base b6b563d

Added a single zero-model-call `IntentDecision` path in `conversation_persona.py` and connected it to both Cloud/local shared dialogue guidance and desktop `FastBrainPolicy` task selection. It distinguishes chat, continuation, correction, return-to-previous-topic, current-thread history recall, explicit owner-memory recall, research, computer/tool tasks and 3D scene commands. Research uses the existing reasoning-model preference list (only installed models); ordinary greetings remain on FAST. Tool-shaped requests retain read-only/approval boundaries, and prompts forbid claiming web research, device/file/test changes or scene edits without confirmed tool output. No second model call or new client-side action system was added.

Context retrieval now recognizes “Az önce ne demiştim?” as recent same-thread recall instead of searching old messages for the phrase itself. Explicit previous-topic return scans at most four 80-turn pages in the authenticated current thread, retains the owner topic anchor before the latest explicit topic switch plus recent dialogue, and samples beginning/middle/recent turns when no switch identifies a unique return target. Ambiguity remains a short clarification; cross-owner/cross-thread retrieval is not introduced. PR #30's continuation paging and PR #31's context-budget/system-policy work remain intact.

Deterministic evaluation: new frozen `intent_scenarios.json` has 100 cases, ten balanced categories, 50 Turkish and 50 English; route/context/tool labels pass **100/100**. Against production `b6b563d`, the prior dialogue-act classifier matched only **32/100** of these richer intent labels (it exposed only new/follow-up/correction). Repeated in-process route benchmark: p50 **0.003164 → 0.038924 ms**, p95 **0.004637 → 0.080290 ms**; routing adds **0 model calls**. These are lexical-router timings, not inference/response latency. Gemini and Ollama are unavailable here, so actual model quality, first-token latency, total latency and hardware routing remain **NOT_RUN**. Production health was read-only verified at exact commit `b6b563d0521a874c46bd0cbe2d1a1ab5e4d8efc0`; this branch has not been deployed. Draft [PR #32](https://github.com/fatmakahraman304-hash/ULTRON/pull/32), functional code head `74c932ae5002e9dae4285ffdc5552972ca50514c`, is open against production base `b6b563d`.

The desktop `/api/merged/invoke` path now applies that same intent decision before choosing Cloud chat: explicit computer tasks in normal/general/coding/fast modes use the existing local agent with server-side `approved=False`; ordinary questions remain on the existing Cloud/local chat path. The response carries the real agent state and user-facing result. Approval waits and unrecognized/incomplete operations are not marked completed. Dispatch contracts only were exercised; no Windows task or live provider was executed. The follow-up research correction no longer treats multiple result domains as verification: result discovery has answer confidence zero and capability status `adapter` until source pages are read. Full backend suite at code head `74c932ae5002e9dae4285ffdc5552972ca50514c`: **1,029 passed, 3 skipped, 6 subtests passed**. Exact-head Actions: Cloud/PostgreSQL #38548733163, Scene #38548733148, and Local Qwen Listening #38548733003 all **SUCCESS**.

## 2026-10-14 — Protect conversational policy inside small-model context budgets

The local Qwen prompt builder placed optional configured guidance before the runtime persona. When that guidance exceeded the 4,500-character budget, the old fallback returned a raw prefix, removing persona, context trust boundaries and read-only rules. The phone-to-Qwen path also omitted the shared `ULTRON_SYSTEM_PROMPT` that Gemini receives. Three new regressions reproduced these gaps before the fixes. Local Qwen now receives the shared configured prompt through the bounded composer; an oversized optional prompt is dropped as a whole, while persona/privacy/honesty/read-only instructions remain intact and remaining budget goes to bounded memory and recent context. If an unrealistically small budget cannot hold required policy, the complete policy wins and context is omitted. No extra model call, persistence or model-routing change was introduced.

Validation: focused conversation/context/continuation tests **67 passed + 86 subtests**; full Cloud Python **275 passed, 60 skipped** for disposable PostgreSQL/environment prerequisites; PR #30 long-listening recovery Node contracts **22/22**; listening browser contracts **7/7**; frozen evaluation validator confirms **100 cases, 50 TR + 50 EN**, but did not run either real model. Draft [PR #31](https://github.com/fatmakahraman304-hash/ULTRON/pull/31) is at head `971673e1c55b16a4f0389610e8cb7c16b7c61f27` (runtime code `db1fd50b63b1abd1097e0ec5082e833b2e81f15e`). Exact-head Cloud/PostgreSQL `38541558443`, Local Qwen Listening `38541558445`, and Scene `38541558508` Actions all **SUCCESS**. An earlier Cloud attempt hit the ECR data limit; only that failed job was retried and it passed without test changes. Production Render remains on PR #30 SHA `9c7817f6196850b5e245cd77daba438d519b380b`, deploy `dep-db7jjdm7bikc73d3h5og`; `/health` returned `ok` with that SHA. This new work has not been deployed. Real Gemini/Qwen quality, target laptop latency and physical iPhone remain unmeasured/NOT_RUN.

## 2026-10-14 — First-run setup keyboard focus and one-time persistence

At first boot the Qt setup overlay was created before the top-level window and did not take keyboard focus from the chat composer underneath. The setup field now focuses after the window becomes visible, accepts Enter to submit, and can explicitly show/hide the masked Gemini key. Saving setup merges into the ignored user config, preserving existing model settings; an existing valid setup continues straight to the app on later launches. Regression tests cover focus, text entry, and persisted settings. Scene Build Actions `38469167141` passed for code SHA `1dda1d4`; Render remains healthy at its separate Cloud SHA. Physical Windows confirmation remains pending.

## 2026-10-14 — Windows installation passed after smoke-test correction

The owner's Windows install initially hit a stale title expectation (`ULTRON Hologram` vs the current `GÖLGE Hologram`) after 27 other tests passed. The assertion now verifies the current UTF-8 title. Also updated vulnerable transitive `source-map-js` 1.2.1 to 1.2.2; fresh npm install, audit (zero vulnerabilities), build and both GitHub Actions pass. On 2026-10-14 the owner reran `INSTALL.bat` at handoff HEAD `4648d70`; it completed through `pytest tests`, `integration.doctor --quick`, and printed `Kurulum tamamlandi.` Actual desktop startup, local Qwen/Gemini inference and scene interactions remain to be tested.

## 2026-10-13 — Windows laptop handoff prepared

Prepared a source-only ZIP from the current `feat/ultron-cloud-shared-memory` branch for the owner's laptop. The coding workspace is Linux and has no paired Windows execution channel or mounted laptop, so this is a verified handoff package, not a claimed laptop installation. The package excludes Git history, local dependencies, generated caches, credentials, and model weights. Real Windows install, Ollama/Qwen readiness, Gemini fallback, and device acceptance remain the next validation step.

## 2026-10-13 — Keep desktop model and image failures private

The privacy boundary now covers the full desktop path: model-router health and local HTTP errors, the chat agent's final failure message, uploaded-image analysis, CloudClient health/fallback status, and local vision debug output. Errors are categorized without exposing provider strings; vision logs record response length instead of image-derived text. Code SHAs `b327c3d` and `675ea67` passed Scene and Cloud/PostgreSQL Actions. Render remains independently healthy at Cloud SHA `1ad5f28`; no live Gemini/Qwen quality test was run.

## 2026-10-13 — Safe local and cloud provider diagnostics

Desktop model health, local chat/vision API failures, CloudClient health, and cloud-fallback activity now expose stable error categories instead of raw provider exception text. Transient local provider failures return 503/502 with a short Turkish message; input validation retains its specific guidance. Synthetic boundary tests cover credential-like values plus prompt/image details. This hardens diagnostics without changing model routing, approval gates, memory or the Render service.

## 2026-10-13 — Redact provider exception text from logs and live error responses

Gemini exception strings could include request or credential details and were being written to owner events or returned by the Live websocket. Provider failures now persist only `provider_request_failed` or `provider_temporarily_unavailable`; desktop status polling returns a fixed user-safe message. Transient detection and the existing 503 behavior are preserved. A fake-secret vision request verified the actual endpoint stores and returns no exception details; static contracts cover chat, document, camera, Live and its task watcher. Focused tests 3/3; full Cloud Python 323 passed / 60 environment-dependent skips. Cloud/PostgreSQL #38458215679 ran the new regression successfully; Scene #38457949652 and WORLD smoke #38457949491 passed on code SHA `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c`. Render deploy `dep-db78mn5bedkc738a0fu0` is LIVE at that SHA; `/health` returned HTTP 200. This protects logs and error paths; it does not test real provider inference.

## 2026-10-13 — Enforce bilingual conversation-suite coverage

The frozen-evaluation validator claimed 50 Turkish and 50 English scenarios but checked only the Turkish count; an English case relabeled `fr` still passed. A regression reproduced that mismatch. Validation now allows only `tr`/`en` and requires exactly five of each in every category. The eval tests pass 11/11, full Cloud Python passes 320 / 60 environment-dependent skips, and `run.py --validate` confirms 100 cases across 10 categories with 50 TR + 50 EN. Exact-SHA Cloud/PostgreSQL #38456643001 and Scene #38456642956 passed for `5677dca638909d23d96aab2dedab2597dbd196c1`. Render deploy `dep-db78i45bedkc7389oi50` is LIVE at that SHA and `/health` returned HTTP 200 with the exact commit. This verifies suite structure only; real model quality remains unmeasured.

## 2026-10-13 — Keep typed Live turns in consent and conversation history

Fixed the `/api/live` typed-message path: the message is now added to the current turn before it is sent to Gemini, so explicit memory consent is available to the server-side `save_memory` guard and the full turn is persisted with the same conversation. Inputs over 16,000 characters are rejected with a bounded error. A test-first regression exercised the actual nested websocket, tool and history handlers; all 8 live-voice policy tests pass. Cloud Python: 319 passed / 60 environment-dependent skips; Cloud browser suite: 153/153. Exact-SHA Cloud/PostgreSQL #38455888395, Scene #38455888286 and WORLD smoke #38455888333 passed for `f932b184eda215585a01d8d5d933b9f682611de1`. Render deploy `dep-db78feajnfac73d01fo0` is LIVE at that SHA; public `/health` returns HTTP 200 and the exact commit. Synthetic integration verification does not prove real Gemini Live or physical-phone behavior.

## 2026-10-13 — Recognize natural Turkish voice-memory consent

Expanded the conservative live-voice save detector for direct Turkish requests such as “aklında bulunsun”, “bunu aklında bulundur”, “bunu hafızana yaz”, and “bunu notlarına ekle”. Negations and question forms remain non-consent. Test-first regressions reproduced four missed positive phrasings; focused tests pass, and the full Cloud suite is 318 passed / 60 environment-dependent skips. Exact-SHA Scene #38452607673 and Cloud/PostgreSQL #38452607354 passed for `86ad3922f2ae04fe630c0ea08a4d53275a6f32f2`. Render deploy `dep-db783rnavr4c73euva8g` is LIVE at that SHA; `/health` returns HTTP 200. This expands command recognition only; real Gemini transcription and device use remain untested.

## 2026-10-13 — Make live voice memory and tool use consent-grounded

The phone Live prompt previously directed GÖLGE to save a stable fact even when the owner had not asked, and described desktop functions that were not verified by a returned task. It now requires a clear current-turn remember/save command; the server independently refuses memory writes without that transcript consent and blocks credential-like values. The function schema matches the database's five allowed memory categories, and invalid model output safely maps to FACT. Laptop delegation reports queue/result state and preserves approval for code changes. The live instruction fell from 6,789 to 1,913 characters (72% shorter). Focused consent tests pass 7/7; the full Cloud Python suite passes 318 with 60 environment-dependent skips. Exact-SHA Scene #38449688028 and Cloud/PostgreSQL #38449688070 both passed for `166ae52e4f47421329e60d1d5c474d47e8ef2a9b`. Render deploy `dep-db77pougekts73dhtjpg` is LIVE at that SHA and public `/health` returns HTTP 200. Actual Gemini Live, phone behavior, and real model answer quality remain untested; no 100/100 score is claimed.

## 2026-10-13 — Keep the 3D stage off the chat startup path

The dashboard now paints its chat shell first and imports the same real WebGL center stage after a short 250 ms delay. The production main entry shrank from 294.21 kB / 84.34 kB gzip to 105.07 kB / 30.92 kB gzip; the 620.10 kB / 158.73 kB gzip GLTF/WebGL dependency is retained as a deferred chunk. The 3D orb remains present and loads. Bundle-graph validation, Earth tests, all 10 frontend Node tests, 9 actual scene-browser cases, and a Chromium test that blocks the renderer while interacting with chat then verifies the real canvas all pass. Commit `a4f31c66bfb31c1d733ea5ab9d475bf4a8af9f24` passed Frontend Build Check [#38445096269](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38445096269) and Scene Build Check [#38445096168](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38445096168). Render is configured with root `ultron/cloud_service/`, so this frontend-only commit did not deploy the backend; `/health` remains HTTP 200 at backend SHA `c805e1e8fab2d5ca4bd4c8b48ff8d7e3bf7fff9f`. The build still reports the deferred large-chunk advisory.

## 2026-10-13 — End-to-end release audit

Audited functional release `c805e1e8fab2d5ca4bd4c8b48ff8d7e3bf7fff9f` without treating code tests as model intelligence. Exact-SHA Scene Build `38440168682` and Cloud Queue/PostgreSQL `38440168681` succeeded. Render deployment `dep-db76oo6q1p3s73f48g6g` is LIVE at that SHA; `/health` returned HTTP 200 and the served chat routing, scene, and PWA JavaScript matched the checked-in files byte for byte. Local Cloud Python, Cloud JS, backend, scripts, frontend build, Earth, scene grammar, and frozen evaluation-dataset validation passed. Real Chromium/SwiftShader scene interaction was **9/9**, and a real Poly Haven CC0 ArmChair_01 download was imported, moved, removed and restored. Environment-dependent skips and provider/device limits are recorded in `ULTRON_TEST_RESULTS.md`. This is a release and regression audit, not proof of real Gemini/Qwen answer quality or a 100/100 score. The frontend build reports an 821.74 kB raw / 222.42 kB gzip chunk advisory. Inspection shows the initial dashboard's GÖLGE 3D orb uses Three.js on startup; the separate Hologram Lab is still lazy. Measure the initial-load cost before changing that visual tradeoff.

## 2026-10-13 — Diacritic-tolerant everyday Turkish controls

Conversation-style and context classifiers now compare a folded copy of Turkish text, so casual inputs such as “kisa cevap”, “saka yapma”, “konuyu degistirelim”, and “hayir” follow the same brevity, serious-tone, topic-switch and correction paths as correctly accented text. Original conversation text remains unchanged for storage and provider context. This is classification robustness, not a Turkish model-quality score. Actions exposed a package-import difference between Render’s service-root launch and desktop integrations; the helper now imports correctly in both modes, with a package-import regression. Exact fixed-code SHA `c805e1e8fab2d5ca4bd4c8b48ff8d7e3bf7fff9f` passed Scene `38440168682` and Cloud Queue/PostgreSQL `38440168681`; Render is LIVE at the same SHA.

## 2026-10-13 — Local-first routing survives presence-probe failure

When the phone cannot read desktop readiness, the current chat turn now chooses the normal Gemini route. The readiness check happens before any local task is submitted, so an unavailable presence endpoint cannot strand a typed message by aborting local-first routing. Positive, fresh desktop readiness still selects Qwen; only confirmed `desktop_offline` after the local preflight may fall back after a local submission attempt. No model selector or UI surface was added. Commit `52b776a` is on the feature branch, both exact-SHA Actions workflows passed, Render is LIVE at the same SHA, and `/health` confirms it.

## 2026-10-13 — GÖLGE self-development through reviewed GitHub PRs

Self-development requests from phone text/voice now route to the paired laptop instead of stopping at a ChatGPT handoff. On the laptop, Qwen prepares a bounded CodeGen patch and the existing approval gate must be accepted. The approved patch runs TypeScript, production build, all backend tests, syntax checks and current service checks. With a clean, current trusted checkout and an existing authenticated GitHub CLI session, GÖLGE creates an isolated `golge/dev/<id>` branch, commits only proposal files and opens a draft PR. It never pushes to the Render-tracked branch, merges a PR or deploys from the PR. Render remains connected to the base branch and deploys after an owner merges.

## 2026-10-13 — Owner-grounded optional next-step suggestions

The user-requested capabilities map to existing bounded systems for natural multi-turn context, validated local task planning, owner-scoped editable memory, device readiness, and a manual briefing. The briefing now surfaces at most one optional next step based on an owner-created plan or explicitly saved goal/project. The mobile memory screen renders the suggestion with textContent after the owner opens the briefing. No reminders, background monitoring, or device actions are created.

## 2026-10-13 — Correction-aware conversational recall

Conversation reliability is the priority following the user’s latest request. Named-topic retrieval now preserves an immediately following explicit user correction even when it omits the topic name. No extra inference, persistence, permissions or context budget added.

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

## Conversation cognition — correction order and reminder intent (2026-10-10)

- [x] Retrieve clear owner correction directly after an older topic question/answer, even when correction omits the topic name. Ordered context remains user/assistant/user and stays capped; real disposable PostgreSQL long-history and isolation checks successful.
- [x] Separate scheduled future reminders from historical chat recall, preserving `ne demiştik` and named historic conversation requests. Do not invent scheduling success.
- [x] Cloud/PostgreSQL #38079636700 and Scene/Frontend #38079636678 SUCCESS on exact code `800a54d07e0159cec063c67f7555a94abe2ced48`.
- [ ] Run actual Gemini + Qwen 20-case pilot followed by independently reviewed frozen 100-case dataset; no provider model-quality score exists yet.
- [ ] Verify Render deployed commit and actual Windows/iPhone voice and inference before one-time final Windows installation. Keep main branch and approval gates unchanged.

## Conversation intelligence — explicit new-topic priority (2026-10-10)

- [x] Keep final user corrections in *current* long Qwen and Gemini prompts under unchanged length caps; mock wire tests confirmed.
- [x] Detect only explicit Turkish/English requests to switch subjects, skip lexical retrieval from old chats in those cases, and instruct both cloud and local persona to address the new goal. Tested without model calls and with disposable PostgreSQL tenant/thread isolation.
- [x] Cloud/PostgreSQL #38078914038 and Scene/Frontend #38078914033 both PASS at `ec566816ef4eeaa162b579f05f86bb0828ff4237`.
- [ ] Authorized real Gemini and Qwen/Ollama 20-case pilot, then independent frozen 100-case evaluations, model identity and latency comparisons. JARVIS parity not verified.
- [ ] Verify exact new Render LIVE SHA and phone/Windows actual interaction; single final Windows update remains postponed.

## Conversation intelligence — final user correction under capped current message (2026-10-10)

- [x] Preserve final explicit constraints of a long **current** message across Gemini (16k) and local Qwen (3k) model wires, not just older history; keep original character caps.
- [x] Add deterministic history+direct provider-message regression and mocked local Ollama payload test.
- [x] Exact code `a08b3afadaed0f17ec67bfdbab6a3ebe5375b8bf` passed Cloud/PostgreSQL #38078688366 and Scene/Frontend #38078688244.
- [ ] Human-reviewed real Gemini and Qwen/Ollama pilot 20-case run and frozen 100-case acceptance with device latency; not yet run here.
- [ ] Verify Render deployment SHA and physical iPhone/Windows model/voice behavior before deferred final Windows update.

## Natural conversation measurement: real small pilot (2026-10-10)

- [x] Add provider-specific `--pilot` to test 20 existing balanced TR/EN scenarios without touching frozen acceptance criteria; 80 unselected remain NOT_RUN, not false failures or passes.
- [x] Reject non-Qwen model selection in Qwen-specific evaluation; no production Ollama fallback changes.
- [x] Safe no-key Gemini pilot regression confirms no fabricated transcript, no score, and explicit NOT_RUN reasons.
- [x] Cloud/PostgreSQL CI `38076948096` and Scene/Frontend CI `38076948157` passed on `ceef1f499ccb5690de3bdcd8289873a5d6f8c52f`.
- [ ] Run actual Gemini/Qwen pilot on authorized/reachable model providers, inspect independent reviews, then 100-case benchmark, latency and corrective iterations. Real quality remains NOT MEASURED.
- [ ] Verify exact Render release SHA and device voice/inference before final one-time Windows update.

## Natural conversation — persistent oldest/newest topic retrieval (2026-10-10)

- [x] Fix omission of the original named-topic Q&A when more than 24 older lexical matches exist.
- [x] Reserve oldest and newest historical evidence under bounded same-user/same-conversation SQL, and preserve adjacent Q&A plus recent turns.
- [x] New deterministic and disposable PostgreSQL tests, including >100 recent turns, 42 older repeated-topic mentions, isolation and size caps. GitHub Cloud CI #38073658327 and Scene CI #38073658416 PASS on `f73d43358715358dc21b48f4b34c510307627f3f`.
- [ ] Complete genuine Gemini and local Qwen 100-case live inference plus independent human scoring. Model quality remains NOT MEASURED.
- [ ] Verify exact Render deployment SHA and true iPhone/Windows end-to-end performance. Final Windows update deferred.

## Measured conversational intelligence (2026-10-10)

- [x] Keep the frozen 100-scenario TR/EN acceptance dataset unchanged and auditably versioned.
- [x] Prevent old human reviews from being reused for edited transcripts via SHA256 linkage; template starts without passes.
- [x] Record actual successful Gemini fallback/primary identity for each read-only evaluation turn while preserving the string-only Cloud production API.
- [x] Capture p50/p95 inference latency and per-turn flags for eventual real Gemini/Qwen comparison.
- [x] Exact-code GitHub Cloud, Scene and WORLD smoke checks passed at `043a5386e510bc81a1bc163d9887cef8f75a4071`.
- [ ] Run real available Gemini and Qwen providers with authorized credentials/local Ollama and independent reviews. **Model score is unmeasured**, not automatically 100/100.
- [ ] Verify Render exact deployed SHA, iPhone/Windows voice and single final Windows update after quality acceptance.

## Conversation quality — final historical statement retrieval (2026-10-10)

- [x] Recall original same-thread Q&A older than 80 messages, even with later incidental mentions of the topic (previous commit `064a9f6`).
- [x] Preserve the **final decision/correction** in long historical Q&A snippets within the existing fixed history cap. Synthetic regression and real disposable PostgreSQL long-thread isolation tests passed on code `4a196658820aa38f747cb6cd1e74a12714c59eaf`.
- [x] Existing Cloud/PostgreSQL CI `38072623731` and Scene/Frontend CI `38072623801` successful.
- [ ] Run authorized real Gemini and reachable Qwen/Ollama 100-scenario transcripts with independent reviews and latency measurements; model accuracy NOT MEASURED.
- [ ] Verify Render exact live commit and on-device iPhone/Windows inference and voice. Single Windows update intentionally deferred.

## Conversational milestone — named recall beyond recent context (2026-10-10)

- [x] Explicit old-topic recall past 80 messages, authenticated-thread lexical match with adjacent Q&A and bounded history prompt.
- [x] Preserve long message beginning + final correction under existing character budget.
- [x] Recognize short specific topic names such as DAÜ/YDÜ/KKTC/Qwen/Siri, plus long-message trailing topic mentions.
- [x] Add grounded named-recall conversation guidance; verify with synthetic tests, disposable PostgreSQL and existing Cloud/Scene CI (`1e5e11002a471d041023e5c8efd95047b733442b`, two SUCCESS workflows).
- [ ] Run real Gemini/Qwen 100-scenario/provider evaluation with independent reviews and latency evidence. Model quality 100/100 is unmeasured, not achieved or claimed.
- [ ] Verify Render exact deployed commit and physical phone/Windows behavior. Windows final update remains postponed.

## Conversational intelligence — long recap coverage (2026-10-10)

- [x] True first-topic return beyond 80 turns (previous release).
- [x] Scoped real-start / real-midpoint / recent recaps for 80+ turn chats, validated in both deterministic and disposable PostgreSQL integration tests (`066b7b982a19c97297a2d74ee4cf68a4a9c4d336`, Cloud 38070614904 and Scene 38070614899: SUCCESS).
- [ ] Real Gemini and reachable Qwen/Ollama 100-case transcript capture + independent human scoring.
- [ ] Latency/context-window measurement and actual phone/desktop microphone tests.
- [ ] Final single Windows update after conversational acceptance. No Windows changes made in this cycle.

# ULTRON — Teknik Yol Haritası

Bu belge `MARK-ULTRON-MERGED` kaynak ağacına dayanır. **Test edilmemiş özellik tamamlanmış sayılmaz.**

## Korunacak mevcut sistemler
- Python 3.12/aiohttp backend; React/TypeScript + Three.js UI; Ollama ve SQLite.
- Telefon Gemini Live → Cloud device queue → desktop agent → yerel tool → Cloud result → telefon.
- Scene Lab, Earth Watch, 3D video, GLB Asset Library, Mission Sequences, Trigger Engine, Snapshot Vault.
- Approval Gate, sandbox, izin denetimi ve audit logları.

## Doğrulanmış ilk geliştirme dalgası (2026-10-09)
- [x] P0 Earth Watch: Kamera orbit/zoom konumu ayar değişiminde korunuyor; sürükleme yanlışlıkla koordinat tıklaması olarak işlenmiyor.
- [x] P0 Geospatial tests: `earthMath.ts` ile koordinat round-trip, Greenwich, boylam wrapping, UTC subsolar nokta, ekinoks ve gündönümü testleri.
- [x] P1 Backend state validation: `earth_watch.py` persisted ayarları, bool string, finite sayılar, enlem/boylam, renk ve pinleri normalize ediyor.
- [x] P1 ISS safety: Geçerli yanıt gelmeden sahte ISS pini yok; timeout, non-overlapping poll ve cleanup var.
- [x] P1 UTC light: Yaklaşık NOAA tabanlı UTC Sun synchronisation, UI ve sesli araç kontrolü.
- [x] P1 Development continuity: `AGENTS.md`, dört kalıcı belge, `scripts/ultron_dev_resume.py` ve regresyon testleri.
- CI referansı: `a010726149f7a1352933a2e45af51f9b1a985662` — `ULTRON Scene Build Check` PASS, run `37893780863`.

## Sonraki öncelikler
| Öncelik | Alan | Kabul ölçütü |
| --- | --- | --- |
| P0 | Windows gerçek test | `START.bat`, üç Earth Watch mod kontrolü, zoom/orbit persistence, ISS çevrimdışı fallback, gerçek mikrofon ve 3D GPU akışı doğrulanır. |
| P1 | Earth offline kalite | İnternetsiz gerçekçi/kullanım hakkı açık texture varlığı; fallback geometrisi; GPU yaşam döngüsü ölçümü. |
| P1 | Cloud queue idempotence | **İlk koruma tamamlandı:** eşzamanlı claim'i PostgreSQL advisory transaction lock ile seri hale getirme; terminal olmayan görevlerde atomic completion/retry; 6 izolasyon/SQL sözleşme testi CI PASS (34b80e4). **Tamamlandı:** disposable PostgreSQL üzerinde delivery_attempt fencing; masaüstü lease guard. **Açık:** Render/telefon/Windows gerçek cihaz doğrulaması ve per-tool idempotency journal. |
| P1 | Güvenlik kontratı | Approval Gate, audit ve riskli tool işlemleri için güvenli regresyonlar. |
| P2 | Ses ve AI router | Wake-word, barge-in, STT/TTS hata dayanımı; yok model için fallback ve timeout testleri. |
| P2 | Scene Studio | Büyük sahne FPS/VRAM benchmark; GLB proje/export round-trip. |
| P3 | Agent sürekliliği | Alt görev state ve safe checkpoint; güvenli hata sonrası devam; sessiz background çalışma iddiası yok. |

## İş akışı
1. `AGENTS.md` ve dört devam belgesini oku.
2. `python scripts/ultron_dev_resume.py` ile HEAD/branch/kirlilik/sonraki iş durumunu gör.
3. Kod değişikliği, gerçek test, CI sonucu, açıklayıcı commit, dört belge güncellemesi.
4. Repo dışına yazma, secret ifşa etme, izinsiz destructive işlem ya da Approval Gate bypass yapma.
5. Bir oturum bitince `ULTRON_NEXT_TASKS.md` içinde tekrar üretilebilir kesin sonraki adımı bırak.

## 2026-10-09 — Cloud Queue P1 ara doğrulama
- `ultron/cloud_service/app.py`: aynı kullanıcı/hedef için claim transaction advisory lock; yalnızca `delivered` görevden completed/failed/retry state geçişi; duplicate veya late callback'e 409.
- `ultron/cloud_service/test_device_queue_contract.py`: handler fonksiyonlarını AST üzerinden gerçek kaynakta çalıştıran dependency-free simülasyon; 6 test geçti.
- `.github/workflows/scene-check.yml`: queue regresyonları zorunlu.
- **GitHub Actions PASS:** kod SHA `34b80e43abe023e58a8f65c87688aa104d6d55e7`, run `37894840971`; Python compile, frontend build ve diğer mevcut regresyonlar da geçti.
- **Sınır:** fake DB testi gerçek PostgreSQL lock/Cloud deployment sonucunu doğrulamaz; attempt ID olmadan eski worker'ın yeni claim döngüsüne yazması ayrıca ele alınmalı.


## 2026-10-09 — Cloud queue P1 delivery fencing (gerçek DB ile doğrulandı)
- [x] Cloud schema migration: `device_commands.delivery_attempt INTEGER NOT NULL DEFAULT 0`; her claim atomik olarak nesli artırır ve desktop'a döndürür.
- [x] Ajan görevleri tamamlanırken, lease yenilerken, progress gönderirken ve checkpoint yazarken `status='delivered'` **ve aynı delivery_attempt** şartı SQL'de uygulanır. Eski worker'a 409/404 verilir.
- [x] `ultron/backend/cloud_client.py` ve `mark_app.py` bu nesli Cloud çağrılarına taşır. Tek seferlik kontrol komutları geriye uyumludur.
- [x] Cloud kuyruk için 14 izole regresyon testi; gerçek PostgreSQL 16 üzerinde 4 ek entegrasyon testi. TypeScript/Vite ve diğer testler PASS.
- **Kod SHA:** `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`
- **CI:** Scene `37897505788` PASS; PostgreSQL `37897505793` PASS.
- **Açık:** Render deploy SHA; masaüstü/telefon gerçek cihaz testleri; canlı kullanıcı hesabı ve ağ kopması dayanım testi; istenirse çoklu worker/failover ve DLQ yük testi.
- **Önemli:** Veritabanı fencing, bir worker'ın daha önce gerçekleştirdiği yerel yan etkileri geri almaz. Tam exactly-once masaüstü eylemi için permission-aware idempotency journal ayrıca gereklidir.


## 2026-10-09 — CloudRemote desktop lease loss protection (PASS)
- [x] `cloud_client.py`: device command 404/409 yanıtlarını `CloudDeliveryRejected` ile HTTP ağ/geçici hatalardan ayırma.
- [x] `cloud_delivery.py`: lease'i 5 saniyede yenileme; Cloud reddederse hemen işaretleme; 8s HTTP timeout, yaklaşık 15s yenilenememe halinde konservatif durdurma. Kısa kopmada anında iptal etmez.
- [x] `mark_app.py`: Gemini görevi dispatch öncesi ve yürütme sırasında lease kaybını denetleme; stale attempt'a completion raporu vermeme; eskimiş turn'ü best-effort interrupt etme ve aynı laptop içindeki agent_task'ları serileştirme.
- [x] `test_cloud_delivery_guard.py` ve `scene-check.yml`: 10 test, gerçek CloudClient HTTP hata sınıflaması ve lease yarışları CI'da PASS.
- **CI/commit:** `d96638e1ecaad7d0b800e20fb22580ade555e777`, run `37914696238`, Python+Frontend PASS.
- **Önemli sınır:** Çalışmaya başlamış harici/geri alınamaz eylemlerin exactly-once veya otomatik geri alındığı kanıtlanmamıştır. Bu katman bir teslim öncesi ve devam denetimidir; tam per-tool idempotency journal halen açık.


## 2026-10-09 — Desktop durable dispatch fence (CI PASS)
- Cloud `agent_task` Gemini Live'a gönderilmeden önce `data/cloud_remote_dispatch.sqlite3` dosyasında `(Cloud URL, device, command_id)` için atomik kalıcı kayıt ayrılır. Yeniden claim/retry veya süreç yeniden başladıktan sonra aynı komut otomatik tekrar gönderilmez. DB açılamıyorsa fail-closed; telefon sonucuna inceleme gerektiren hata gönderilir.
- Görev metni, API anahtarı veya yanıtlar veritabanında saklanmaz; sadece scope/payload özetleri ve komut/attempt kimlikleri.
- Approval Gate, mic ownership ve diğer kontroller değiştirilmedi. `test_cloud_dispatch_journal.py` testleri CI'a eklendi.
- **Gerçek doğrulama:** kod commit `afe9f5b6855fc4742e384a4d298b71ee6c6feb18`; `ULTRON Scene Build Check` run `37915768918` **SUCCESS**. `test_cloud_dispatch_journal.py` 11 PASS, lease 10 PASS, Cloud contract 14 PASS, Earth 5 PASS, resume 3 PASS; frontend TypeScript/Vite build ve Earth math PASS.
- **Sınır:** Bu komut seviyesinde at-most-once *dispatch* korumasıdır, per-tool exactly-once değildir. Aynı komutun farklı masaüstüne yönlenmesi, tek turn içi tool tekrarları veya rezervasyondan önce yapılmış yerel işlemler için garanti vermez. Crash rezervasyon-sonrası dispatch-öncesi olsa bile inceleme gerekir.


## 2026-10-09 — iPhone Siri / Native Cloud görev köprüsü (CI BEKLENİYOR)
- Native iPhone 0.3: Siri App Intent arka planda tek HTTP isteği ile laptop `agent_task` kuyruğa ekler; web oturumu ve Keychain kullanılır, masaüstü Approval Gate korunur.
- Native ekranda yazılı laptop görev alanı eklendi. Cloud Live `ios_action` ve `ios_shortcut` olayları sadece kullanıcı onaylı `ULTRON Bridge` Kestirmesiyle çalıştırılabilir. Otomatik sistem ayarı değiştirme yok.
- Xcode derleme sonucu ve gerçek iPhone/Siri kilit ekranı, Cloud deploy ile Windows uçtan uca sonuçları henüz doğrulanmadı.


## 2026-10-09 — Native iPhone v0.3 son doğrulama
- **Kod SHA:** 0b4751a5d7c5f6ceb4642af4eb413f6fb0ca16b9; **CI:** Native iOS Build run `37917812910` **SUCCESS**. `test_siri_bridge_contract.py` **5 PASS** (kaynak/sözleşme testleri), XcodeGen proje üretimi, iOS Simulator build **PASS**, unsigned iPhone build **PASS**, unsigned IPA/Xcode project paketleme/upload **PASS**.
- Yeni native App Intents: `AskULTRONIntent` (Cloud sohbet), `SendULTRONDesktopTaskIntent` (desktop queue), `CheckULTRONDesktopTaskIntent` (görev durumu). Siri'den çalıştırılabilir kısa Cloud HTTP istekleri; canlı ses WebSocket bağımlılığı yok.
- Native `ContentView` laptop görev yazma/gönderme/durum sor ve `BackgroundVoiceController` ios_action, ios_shortcut, laptop_task event desteği.
- PhoneActionRouter'da izinli sistem komutları sadece `ULTRON Bridge` üzerinden ve kullanıcı `DEVAM ET` onayıyla yönlendirilir; otomatik foreground/background ayar değiştirme yok. Bekleyen hassas komutlar UserDefaults'tan cihaz Keychain'ine taşındı. Masaüstü Approval Gate ve durable queue koruması değiştirilmedi.
- **NOT RUN:** gerçek iPhone/Siri/telefon kilidi, Xcode signing/install, canlı Cloud/Render deploy, gerçek Mac/Windows laptop uçtan uca eylem, iOS sistem tarafından sonlandırma sonrası mikrofon/arka plan devamı. Kodun derlenmesi bu cihaz davranışlarını ispatlamaz.


## 2026-10-09 — USB'siz TestFlight hattı hazırlandı (release NOT RUN)
- `.github/workflows/ios-testflight.yml` yalnız `workflow_dispatch` ile manuel imzalı App Store archive/export ve Apple-Actions TestFlight upload hattını hazırlıyor; push/PR otomatik yayın YOK. `testflight` environment'da Apple Developer/App Store Connect API signing değişken ve sırları gerekiyor; fail-closed preflight eklendi.
- `ios/ULTRONMobile/TESTFLIGHT_KABLOSUZ_TR.md` Windows/iPhone cihaz-bazlı rehber. Mevcut ULTRON SVG'den App Store 1024x1024 icon build sırasında oluşturulacak. Apple Developer Program ve sertifika yoksa TestFlight yüklemesi yapılamaz. Workflow `main` default branch üzerinde bulunmadan GitHub UI'da manuel çalıştırma seçeneği açılmaz.
- `test_testflight_release_contract.py` 4 statik release guard testi eklendi. GitHub Native iOS Build doğrulaması bekleniyor; kod-signing/App Store upload gerçek hesabı olmadan NOT RUN.


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

## 2026-10-10 — Personal ULTRON conversation parity
- Implemented shared conversation_persona.py for local Qwen and Cloud Gemini (text/image/PDF/camera/Live), with adaptive light humour versus serious tone, consistent name and consent-aware claims.
- Memory and history injected as untrusted bounded context; phone Qwen is explicitly read-only and never claims saved memory or local actions.
- Follow-up: real phone/Windows speech quality, configurable owner address/humour, personal daily brief only with opt-in, proof of live Render deployment.

## 2026-10-10 — Windows assistant persona refinement / verified
- Desktop Agent persona_guard.py now uses respectful ULTRON guidance rather than mocking the owner; no longer penalizes ordinary replies for lacking 'Boss'. agent.py no longer forces 'Boss' after reframing and removes the harsh rewrite cue.
- Added ultron/backend/tests/test_persona_warmth.py: 4 stdlib tests covering kind anchor, ordinary direct response, genuine apology and desktop postprocessor.
- GitHub Actions Cloud Queue PostgreSQL Integration #37992833637 on SHA 433617f77b669fbe30526705faccbe6532ccd545 SUCCESS: persona-policy (Cloud 8 + Windows 4 tests), real PostgreSQL queue/memory/development-request integrations all passed.
- ULTRON Scene Build Check #37992774370 SUCCESS at Windows agent postprocessor SHA 93f921f266a37bf01f565b9c8c32880854f3f372.
- No Windows local checkout, microphone/audio, physical phone or current Render deploy verified.


## 2026-10-10 — Owner personal-briefing mobile interface
- iPhone HAFIZA tab now exposes opt-in button for /api/personal-briefing and separate opt-in button for /api/capability-readiness (ten realistic JARVIS gap statuses).
- New static/personal-panel.js uses textContent-only rendering, no background fetches, no automatic account access or memory edits. PWA v44 precaches the script.
- Six Node UI tests in test_personal_panel.cjs cover no automatic network fetch, output provenance, status labels, safe DOM, error recovery and HTML wiring; scene CI runs them.
- Priorities remain verified iPhone hardware UX, consent-based calendar/email provider linking, and voice testing without disabling approval gates.


## 2026-10-10 — Owner Manual Calendar (ULTRON Life v1)
- Implemented: signed-in owner-created dated plans in PostgreSQL with create/list/mark done/undo/delete and strict title, time/date and note validation, owner-scoped SQL.
- iPhone HAFIZA tab has the plan editor; on-demand daily brief shows open plans and saved memory. Local/cloud assistant context receives plan titles and date/time, not private notes.
- NOT complete: Apple/Google Calendar OAuth syncing, scheduled background notifications, timezone controls, rescheduling, repeating events, physical iOS proof. Manual plans are not third-party calendar integration.


## 2026-10-10 — ULTRON Life v1 plan editor
- Add authenticated owner-only PUT /api/owner-plans/{id} to edit title/date/time/notes atomically, preserving plan id and completion. Avoid any external calendar sync or fake notification claims. iPhone HAFIZA includes explicit EDIT / SAVE / CANCEL, with draft preserved after network errors.
- CI acceptance: real PostgreSQL cross-owner edit forbidden and persistent update; Node UI confirms no write until click, cancel discards unsaved draft and errors retain it. No physical iPhone or Windows test inferred.


## 2026-10-10 — Personal calendar file export (no OAuth required)
- Implemented explicit owner-requested iCalendar (.ics) export from ULTRON HAFIZA.
- Browser-session-protected GET /api/owner-plans/calendar.ics accepts only Europe/Istanbul, Asia/Nicosia or UTC, converts timed events to true UTC instants and emits all-day dates without invented hours. Rejects ambiguous/nonexistent DST times instead of silently changing schedules.
- The file contains only outstanding plan titles and dates/times (not notes), uses stable opaque event identifiers and RFC5545 escaping/UTF-8 folding, and has no VALARM or subscription/provider side effects.
- The user explicitly chooses timezone and taps .ICS TAKVİM DOSYASINI İNDİR. Import into Apple/Google calendar must be user-initiated; export is not provider OAuth, syncing, notifications, calendar import verification or an automatic reminder.


## 2026-10-10 — Ten JARVIS capabilities implementation truth table
1. Expressive conversation: ULTRON persona, safety-aware humour and owner preferences carried through explicit saved memory; real human feelings/consciousness do not exist.
2. Personal memory/life: owner-scoped Cloud saved memory, daily briefing, manual dated plans, editing, completion and .ics export; real Gmail/Calendar provider authorization remains absent.
3. Learning with consent (NEW): owner-supplied fact/preferences inbox, approve/reject/delete proposal; only approved inserts into memories and older key is not replaced without review. No silent surveillance or continuous model retraining.
4. Offline powered-off computer: Cloud task queue exists, but actually powered-off PC control requires a separately powered authenticated device and compatible Wake-on-LAN configuration; unavailable here.
5. iPhone Siri: native source and explicit Shortcut approval bridge exist; full iOS app installation, Apple entitlements and device tests required.
6. Hologram: 3D scene on a screen exists; volumetric free-air hologram requires display hardware.
7. Humanlike voice: Whisper/Piper Windows path and optional Gemini Live/Qwen browser paths exist; live phone/Windows hardware speed and audio quality not measured here.
8. Self-updating: repository development queue, GitHub CI, Render autoDeploy exist; owner approval, tested desktop installation and rollback are mandatory before claiming fully self-updated.
9. Calendar/email: manual plans and .ics export exist; email and calendar OAuth provider connections, permissions and delivery receipts absent.
10. Smart home: connector concepts/adapters only; actual user-owned devices, authenticated LAN/cloud adapters and explicit device-change approval required.
All ten are *workstream requirements*; not all are implemented or physically achievable through software alone.

## 2026-10-10 — Optional automatic personal learning (bounded, user-controlled)
- Distinguish ordinary owner-approved inbox from opt-in auto-learning of explicit *owner-written* chat statements. Per-user database setting DEFAULT OFF, explicit browser toggle and reversible disable.
- Eligible exact-prefix expressions: "Tercihim:", "Hedefim:", "Projem:" and simple English equivalents. Stores only preference/goal/project value as owner-scoped memories; no model retraining, hidden scraping or app/microphone surveillance.
- Sensitive-pattern, email, long-number, URL and multiline rejects; bounded single message length/value and duplicate-key hash. No arbitrary "infinite storage" promise; actual storage and server resources are finite.
- Both Gemini Cloud and free paired Windows Qwen text chats can learn accepted owner messages after enabled, without weakening Approval Gate. Non-owner messages, replies and tool results must not be sources.
- Actual model-side autonomous omniscient learning, OS control while PC is powered off, unrestricted iOS Siri, free-air hologram and unpaired smart-home physical control remain unsupported.


## 2026-10-10 — One clean ULTRON interface, reveal workspaces on demand
- User wants mobile and desktop to show minimal cockpit/chat/voice by default. No permanently visible DÜNYA/Hologram/Tools grids; controls should appear only after user speech/text request (e.g. "Dünyayı aç", "Hologram Lab'i aç", "Hafızamı göster", "Ana ekrana dön").
- Mobile Cloud PWA: bottom multi-tab strip visually hidden except when ⋯ menu is explicitly opened; natural-language text and Gemini Live transcript routing to existing WORLD/HAFIZA/UZAKTAN/GELİŞTİR and new mobile screen-only Hologram Lab preview. PWA service worker shell caches panel-intents.js (v49). Menu remains for accessibility/no microphone.
- Windows: simplified voice-first React Dashboard hides top nav, footbar, system rail, redundant cards, retains CenterStage/ULTRON chat, small mic and one Menu. Desktop HologramLab opens on demand via dynamic component, Earth opens via existing stage backend, tools available in dialog.
- Safety: panel commands change visual UI only (except authenticated preexisting stage modes). No microphone auto-start, approval bypass, file operations, continuous recording or operating-system tool execution introduced.
- Mobile hologram is an animated *screen preview*, not full Windows 3D editor or a volumetric free-air hologram. Real devices still require manual acceptance.


## 2026-10-10 — Invisible local-first brain, clean mobile composer
- Requested simplified Cloud PWA removes visible "ULTRON BEYİN" title, Qwen/Gemini picker, cloud-limit explanations and duplicate technical guidance. Only voice button, attachment, message composer and send remain; existing hidden on-demand workspace menu is preserved.
- Browser Cloud /api/device-presence yields per-owner Windows desktop heartbeat: online within existing 15s window -> choose local Qwen; otherwise -> Gemini Cloud. No stale localStorage selector override. The choice re-checks before every text send and when the user taps microphone; background presence update is only for routing and must not start microphones.
- Browser transient source failures route to Gemini. Once a local request has entered the queue, uncertain timeout/failure is NOT blindly replayed to Gemini, avoiding duplicate command/message and surprise billing. Explicit 409 desktop_offline rejection before insert is safe for cloud fallback.
- Existing owner auth, browser microphone permission, live audio owner, queue fencing and local dangerous-tool isolation unchanged. Real provider subscription/quotas still apply, whether or not provider UI is hidden. Real iPhone/laptop manual verification remains required.


## 2026-10-10 — ULTRON natural multi-turn dialogue instead of one-shot Gemini/Qwen
- Build a natural conversational assistant through a consistent ULTRON-only personality: adapt response length to user intent, answer casual messages naturally, avoid canned greetings/constant 'efendim', use context to follow short pronoun-based follow-ups, ask one clarification only when necessary, correct errors gracefully and avoid claiming human feelings.
- Replace generic all-account message list in ordinary cloud and local text chat with bounded typed user/model turns from the owner-and-conversation-scoped SQL. Exclude current prompt from retrieved history to prevent duplicated user turn, preserving latest relevant messages.
- Gemini Cloud uses real genai Content(role=user/model) history rather than a flat concatenated string; local paired Qwen/Ollama receives role-separated messages (system/user/assistant). Cloud voice history now scoped to its existing session id.
- Prevent caller-supplied conversation UUID from silently modifying another owner's thread: conversation insert/update returns an id only when current owner owns it; reject cross-owner UUID before saving messages or queuing tasks.
- Local Qwen sampling uses moderate warmth 0.55, top_p .9, repeat penalty 1.08, and bounded 240–420 output tokens; tool/approval paths unchanged. Not model retraining or a guarantee of human-level reasoning. True sound/latency quality requires Windows+iPhone provider testing.


## 2026-10-10 — Natural conversation coaching, no Windows install until final hand-off
- Keep a coherent ULTRON-only personality for both phone Gemini and installed laptop Qwen, without adding visible brain/model controls. Expand deterministic per-turn response coaching: explicit brief/detailed requests, corrections (e.g. "Hayır, yanlış anladın") and elliptical follow-ups (e.g. "Peki onun fiyatı?", "Devam et").
- For follow-ups, distinguish real owner-scoped, same-conversation prior user/assistant turns from placeholder system text. If no previous turn exists in the conversation, ask once what should be continued instead of falsely referencing unrelated chat.
- Don't persist natural reply-mode instructions to personal memory or autonomously retrain. Don't insert untrusted history as system roles; ignore malformed injected history values.
- Preserve the user's explicit preference: continue code/test/deploy via GitHub/Render; download/install the Windows update once after the chosen features are completed and verified. Cloud autoDeploy may still update the web app, but the user's Windows installation is not touched.


## 2026-10-10 — Long-thread ULTRON contextual recall, without laptop installation
- Support JARVIS-like follow-up questions about specific topics referenced earlier in the *same* conversation. Fetch at most 80 prior user/assistant rows only by current authenticated user_id and conversation_id; older recall requires explicit topic terms (e.g. Mercedes C180), never guesses a subject from "Peki?".
- Keep the newest conversation turns and reserve at most ~25% of the existing model context budget for relevant older excerpts. Preserve chronological order, role boundary and bounded Qwen 4GB context; skip malformed/system records. No new persistent personal memory, embedding service, hidden model API, background surveillance or automatic training.
- Integrate into Cloud Gemini and queued Windows Qwen user text chat. Existing owner-approved memory stays separate; no new native tool execution or Approval Gate relaxation. Cloud autoDeploy remains independent of the user's deferred one-time Windows download.


## 2026-10-10 — ULTRON on-demand whole-chat recap (no extra UI)
- When the owner explicitly says "Bu sohbeti özetle", "Konuştuklarımızı özetle", "Az önce ne konuştuk?" or "Summarize this conversation", select beginning, middle and recent turns from *only the currently authenticated user's currently active conversation*. This fixes recaps based only on recent 12–16 messages.
- Regular conversation continues using recent / explicit-topic recall; no cross-conversation auto-summary, hidden background job, new permanent memory, external model call, provider account, hardware permission, or visible toolbar/picker.
- Preserve role boundaries (user/assistant only), 80-message SQL lookback, 7200-character absolute cap, existing Gemini (up to 5200) and 4GB laptop Qwen (up to 2600) budgets.
- Persona explicitly cautions Gemini/Qwen that sampled excerpts may omit intervening messages, forbids invented earlier topics and claims about saved personal memory. Real device tests still outstanding. Windows installation deferred until the final release.


## 2026-10-10 — Owner-reviewed conversation notes, no extra cockpit buttons
- Allow "Sohbet notu hazırla" or "Notlarımı göster" through the same command-first mobile/voice UI. The tool lives inside HAFIZA only; main chat composer stays minimal.
- GET /api/conversation-notes/preview reads up to 80 user/assistant rows scoped to authenticated user_id AND conversation_id. It presents a deterministic excerpt draft (not an exhaustive LLM summary), omitting some obvious secret-looking lines. The owner must review for residual sensitive data.
- Explicit POST/PUT/DELETE to /api/conversation-notes create/edit/delete owner-only notes stored in the ULTRON Cloud PostgreSQL account and linked to the original conversation. These are NOT offline phone files, separate third-party sync, or automatically model-visible personal memories. Draft GET never writes.
- Default privacy: authenticated browser session, same-origin checks for mutations, no device-token access, bounded 30 notes/conversation and 3000 characters per note, user-scoped SQL and consent-gated deletion UI.


## 2026-10-10 — Natural phone Live audio final-drain and instant barge-in
- On iOS PWA Gemini Live, turn_complete means the server finished transcription/response generation; it must NOT cancel scheduled 24 kHz WebAudio chunks. Only user interruption, explicit stop, session disconnect or laptop-single-speaker takeover may cancel playback.
- Keep a small explicit-generation playback queue for WebAudio source completion. Old onended callbacks after an interruption cannot unlock a new conversation or report a false status. Update listening UI only after pending chunks drain.
- Preserve Live microphone ownership, no auto-microphone on load, safety approval gates, desktop/cloud model selection, PWA voice-first minimal UX and limited local Qwen compute. Test actual hardware later; CI is only a functional contract.


## 2026-10-10 — Single-speaker iPhone/Windows voice arbitration
- Mobile browser applies deterministic phone-first output arbitration: an explicit Gemini Live voice session or active one-tap local Qwen microphone owns the phone's speech turn; only a confirmed online, active, unmuted Windows desktop is otherwise allowed to lead output.
- Desktop presence responses carry a locally monotonic request sequence, so late responses cannot undo more recent decisions or cause phone TTS cut-out/flapping.
- While desktop has output priority, phone task-result TTS is suppressed to avoid overlapping audio; engaging desktop ownership cancels outstanding browser SpeechSynthesis and clears its microphone gate. Local user mic tap preempts desktop speaker UI state instantly, rather than waiting for next 5-second poll.
- No change to actual desktop audio driver/device state, no new permissions, no always-on microphone, no giant picker. True physical cross-device acoustic echo and real device-leader behavior still require the owner to test on Windows and iPhone.


## 2026-10-10 — Local Qwen phone mic: user-first audible interruption
- The user wants the same natural JARVIS conversation on both phone and laptop, without extra on-screen model selectors or interruption delays. For phone one-tap local Qwen STT, starting a new mic capture MUST immediately cancel current iOS SpeechSynthesis so the phone doesn't transcribe its own outgoing reply as input.
- A previously dispatched local-chat task is NOT canceled/replayed just by stopping a voice turn. Its result stays in the conversation text, but it must never start speaking after the user cancels/mutes the mic or moves the phone app to the background.
- Keep explicit user mic permission, no auto-recording on boot, no new UI buttons, no unsafe device commands, no changes to Gemini Live/WebAudio owner's state machine. Single-speaker desktop priority is preserved.


## 2026-10-10 — Natural chat intelligence first: context relevance + smarter local reasoning
- Owner instructed to focus ONLY on natural dialogue and intelligence until further notice; do not divert into 3D/UI/tools/smart-home. "JARVIS 100%" is a fictional target, not a measurable percentage; prioritize verified conversation quality, reduced contradictions and latency over invented progress points.
- New personal_context_focus.py selects bounded, question-relevant **already saved** memories by topic and preserves style preferences and near-dated unfinished plans before unrelated facts. This fixes old memory ordering where 100 recent entries could exhaust the Gemini/Qwen prompt before any plans. Never retrieve private plan notes or unrelated user conversations; no new automatic learning or provider.
- Both Cloud Gemini and local Qwen queue now pass their current question to the owner-only memory selector; output bounded 3400 cloud characters, existing 2400 Qwen cap. Stored values are single-line, untrusted model data.
- Local FastBrain policy now routes explicit complex analysis/comparisons and reasoning requests to the most suitable already-installed Qwen reasoning model (8B when available), while short greetings use faster 4B. No extra model downloads, judge calls, device permissions or background work. 8B may be slower on CPU/GPU offload.
- Existing safety, consent and Approval Gate unchanged. Real human-level JARVIS abilities cannot be asserted from static tests; physical Windows and iPhone natural-language benchmarks are required. User expressly deferred Windows installation until final handoff.


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


Release verification: merge commit `bd09410034d369093b87430e61737cd6e9fbff1e` contains the self-development routing and PR flow. Cloud/PostgreSQL Actions `38430065807`, Scene/UI `38430065886`, and WORLD smoke `38430065957` all **SUCCESS**; workflow logs inspected. Render deployment `dep-db75lruq1p3s73f2eorg` is **LIVE** and `/health` confirms exact SHA `bd09410`. This verifies the Cloud routing and repository checks. The Windows app has not been installed, and GÖLGE's own laptop `gh auth status`, actual branch push, and draft PR have not been tested.
## 2026-10-13 — Upload-aware Gemini image creation and editing

Cloud chat now keeps uploaded-image analysis and reference follow-ups in the same owner-scoped conversation. In the active browser session, explicit “resim oluştur/çiz”, “attığım resmi düzenle” and short “daha iyi yap” requests call Gemini's configurable image model (`GEMINI_IMAGE_MODEL`, default `gemini-2.5-flash-image`) and show only returned image bytes. Image files stay in browser memory and are uploaded only for analysis/edit requests; they are not stored in conversation rows. Provider access is not live-tested in this workspace.
## 2026-10-13 — Image output usability and bounds

Generated and edited images now have an explicit download/save action, with temporary object URLs revoked when the page closes. Image uploads for editing stream through an 8 MB bound; provider image outputs are limited to PNG/JPEG/WebP and 8 MB. Originals remain transient in the browser and are not persisted server-side.

## Self-development reliability

Require explicit standalone owner commands for chat-based patch approval. When several proposals are pending, bind approval/rejection to the displayed proposal ID, and preserve the remaining pending proposal in the UI after each decision. Continue to require local approval, tests, and draft-only GitHub PR publication; merge and Render deployment remain separate owner-controlled actions.

## Image and desktop self-development correctness

Before image generation, validate ownership of any existing conversation without exposing foreign threads to the provider. Only create/update a conversation after successful provider output so failed attempts do not leave empty records. For desktop self-development, enforce resolved filesystem ancestry at proposal time as well as application time; keep exact owner approval, sandbox checks, rollback, test execution and draft-only GitHub PR behavior.

## Release evidence and real-device validation

Keep synthetic provider tests separate from actual Gemini image quality and accessibility. A healthy `/health` response confirms service configuration and commit only; phone image generation/download and owner laptop GÖLGE GitHub draft-PR workflow still need hands-on verification.

## GÖLGE self-development reviewable patch limits

Before a generated code proposal reaches owner approval, validate resolved project ancestry, reject security-core paths and duplicate normalized targets, and bound review size to 12 files / 128 KiB per file / 512 KiB total. Keep approval, sandbox, tests, rollback and draft-only PR publication in force.

Latest GÖLGE proposal-boundary release: Scene Action `38437781712` passed for `4112b3c`; the Cloud service remains at Render `54f91bb`, which contains the separate image ownership fix. No Windows installation or live-provider claim.

## 2026-10-14 — Memory + verified research V3 scope

Implemented in code commit `d95b64640381ae4a519024f767560892e20270a4` on a feature branch from production SHA `0b2315a77d657361821ae728814ba3506a79b309`; not merged or deployed.

- **Memory delivered:** versioned owner memory corrections, additive history storage, idempotent writes, transaction-scoped owner/key serialization, explicit historical retrieval, delete-both-current-and-history, legacy-secret filtering, and shared write path for live voice. Current ordinary context remains current-value-only. Existing production rows are preserved; pre-V3 history is not inferable.
- **Research delivered:** bounded public HTML/plain-text fetch after search discovery; pinned public IP connection, DNS checks on every redirect, blocked private/non-global targets, restricted ports/types, time/size/redirect bounds, no cookies/auth forwarding/script execution, source excerpts and actual read times. Explicit research intent is wired through Cloud and desktop's existing model call; normal chat avoids the reader.
- **Evidence boundary:** search title/snippet is not evidence. Only read page excerpts can be cited. Sentence checks use lexical overlap and exact numbers and are plainly labelled; no semantic entailment, independent source corroboration, contradiction resolution, or PDF reading is claimed.
- **Episodic Memory V4 now implemented in PR #34 (with Evidence V4 from PR #35 stacked into its branch):** explicit owner-confirmed episodes, correction/version history, deletion, time-bounded owner-scoped recall, and bounded lexical search. It does not claim semantic/vector recall. The exact current branch head must pass Actions before merge.
- **Still open:** semantic/vector recall; robust claim-level semantic verifier and independent-source clustering; PDF; live internet/provider/device testing; production deploy verification. Retrieval is lexical/temporal and web evidence checks are not semantic entailment.

The continuation path also passed a test-first 500 “Devam et” regression: it preserves the original goal, a later correction, and the newest status after the prior 320-message scan failed. The read is limited to 1,200 rows in the same owner/thread and leaves model context size unchanged.

Exact-head GitHub Actions on `698190a94ac8f8a471cc91dc481cac59d0f71ea5` passed: [Cloud/PostgreSQL #38555225630](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225630), [Scene #38555225647](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225647), and [Local Qwen Listening #38555225690](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225690). Draft [PR #33](https://github.com/fatmakahraman304-hash/ULTRON/pull/33) remains unmerged. Render remains LIVE at production SHA `0b2315a77d657361821ae728814ba3506a79b309`; no deployment was started.

Next dependency order: finish exact-head CI for PR #34/#35 → merge and verify the Render deploy SHA → integrate PR #36 interruption with current production → continue evidence claim/contradiction improvements and live provider/device validation when services are available.
## Windows desktop update reliability — 2026-10-15

- Keep `START.bat` self-healing after code pulls: compare the installed frontend dependency fingerprint with `ultron/frontend/package-lock.json`, install from the lockfile when stale, and rebuild only after dependency synchronization succeeds.
- Acceptance: the dependency sync contract test passes, frontend `npm ci` + production build passes, Scene Build CI passes on the exact commit, and the owner's Windows `START.bat` no longer reports missing frontend packages.
- Current limitation: Windows hardware verification depends on the owner's laptop and remains pending until the fix is pulled and started there.
## Native desktop backend startup — 2026-10-15

- Ensure the launcher-provided Python environment makes the repository package `ultron.cloud_service` importable when the backend process uses `ultron/backend` as its working directory.
- Acceptance: a real subprocess import from the backend cwd passes while preserving caller `PYTHONPATH`; Scene Build CI and the Windows PowerShell validation pass; the owner reruns `START.bat` on Windows.
- The local Qwen model, Piper TTS and Render health already passed the owner's doctor check, so the observed startup failure is an import-path issue, separate from provider readiness.
- Follow-up Windows startup issue: once the Cloud backend becomes healthy, the desktop launcher must prioritize the root `memory/` package and import it before UI initialization, avoiding collision with `ultron/backend/memory.py`. Acceptance is the safe-path subprocess regression plus physical `START.bat` confirmation.
## 2026-10-16 — Verification follow-up

- Fix the PR #4 CI environment by installing its declared `aiohttp` dependency before the local Qwen and cancellation contract tests. Keep provider tests offline and cost-free.


## PR #34/#35 release reconciliation — 2026-10-16

- Memory V4 and Evidence V4 remain stacked as a single reviewable feature chain. The feature branch needs a merge commit from current production because its tracking documents and Scene workflow diverged since the original checks.
- Acceptance: preserve existing production changes, run Memory/PostgreSQL and Evidence fixtures on the synchronized exact head, and confirm production Render deploy SHA after merge.
## 2026-10-16 — User-visible GÖLGE naming cleanup

- [x] Replace retired MARK/ULTRON product labels in visible desktop video feedback, mobile conversation-note guidance, and desktop-only API error/title copy.
- [x] Set the legacy-compatible `ultron_name` setting value to `GÖLGE`.
- [x] Remove the retired assistant name from active local-model prompts and generated task-report headings; keep old persisted conversation roles readable.
- [ ] Keep protocol/module/storage keys and the installed custom wake-word identity unchanged until an explicit migration can preserve existing installations and saved browser data.
## Follow-up — owner-reported runtime defects

- Completed in development code: deterministic stop command handling, honest licensed-satellite failure, provider-backed weather chat result, and native desktop file-byte transfer into existing vision/document handlers.
- Remaining acceptance work: pull the fix onto Windows and repeat the four manual interactions on the actual Qt/native audio path. Confirm local vision model availability separately. No new map provider is configured, so satellite imagery remains unavailable; ordinary street map and the separate Globe remain intact.
- Release gate: review CI and manual Windows evidence before merging. Do not deploy to Render for this desktop bridge change unless separately required and explicitly authorized.
