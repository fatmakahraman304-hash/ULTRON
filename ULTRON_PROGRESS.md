## 2026-10-21 — Tek beyin entegrasyon turu: sızıntı, çakışma ve Türkçe yazı düzeltmeleri

Gerçek hatalar bulundu ve düzeltildi, hepsi mock testlerle doğrulandı (fiziksel cihaz testi NOT RUN, aşağıda işaretli):
- `ultron/backend/cloud_dispatch_journal.py`: `with sqlite3.connect(...)` bağlantıyı kapatmıyordu (Python'da context manager sadece commit/rollback yapar); her telefon→masaüstü dispatch'inde bağlantı/kilit sızıyordu. `db.close()` eklendi.
- `integration/launcher.py` + `integration/doctor.py`: degraded-mode'da `os.environ.copy()` PYTHONPATH'i siliyor, `mark_app.py` `ModuleNotFoundError: No module named 'cloud_client'` ile çöküyordu; "MARK imports" probu da aynı eksikle hatalıydı. İkisi de düzeltildi (BACKEND path `append`, `memory/` paketini ezmeyecek şekilde).
- `integration/web_panel.py`: **Kritik çift-claim çakışması.** `NativeBridge.cloud_commands` (Qt timer, 2.2s) ve `mark_app.py`'nin `_cloud_remote_loop` (asyncio) ikisi de `/api/device-commands/claim`'den `agent_task` çekiyordu — biri journal/lease/180s timeout ile korumalı, diğeri korumasız (log-satırı sniffing ile "tamamlandı" sanıyordu, redeliver edilen satırları journal'dan geçirmeden çalıştırabiliyordu). `agent_task` artık sadece asyncio döngüsünde claim ediliyor; Qt tarafındaki ölü kod (`_remote_task_ids` ve ilişkili log-sniffing) kaldırıldı.
- Türkçe karakter yazma hatası (**doğrulandı**: pyautogui'nin KEYBOARD_KEYS tablosunda ğ ü ş ı ö ç İ Ğ Ü Ş Ö Ç'nin HİÇBİRİ yok): `core/clipboard_safe.py` eklendi — pano tabanlı giriş + kullanıcının önceki pano içeriğini otomatik geri yükleme. `actions/computer_control.py` (`_type`, `_smart_type`), `actions/send_message.py` (`_paste_text`), `actions/computer_settings.py` (`type_text`) bunu kullanacak şekilde güncellendi.
- `plugins/_whatsapp_core.py`: Önceki oturumda eksik olan doğrulanmış WhatsApp Desktop sürücüsü yazıldı (gerçek pencere bulma, sohbet listesi filtre doğrulaması, WhatsApp'ın kendi "`<Kişi>` sohbetine bir mesaj yazın" etiketiyle doğru kişi teyidi, yazılan metnin geri okunması, Enter sonrası kutunun boşaldığının doğrulanması). Mesaj kutusu paste'inden sonra kullanıcının panosu geri yükleniyor.
- `actions/open_app.py`: "about"/"sistem hakkında" → `ms-settings:about` eklendi; açılış artık yeni bir pencere başlığı belirip belirmediğini kontrol ediyor ve dürüst raporluyor ("doğrulanamadı" yerine kör "Opened X." iddiası yok). **Gerçek cihazda test edildi**: Hesap Makinesi açıldı ve "Hesap Makinesi" penceresi tespit edildi (PASS); Ayarlar→Hakkında açıldı ama pencere zaten açık olduğu için "yeni pencere" tespit edilemedi (bilinen sınır, dürüst mesaj verdi, yanlış başarı iddiası yok).
- `ultron/cloud_service/app.py`: Render 23-30 dk başlangıç gecikmesi için geçici zamanlama logları eklendi (`startup_timing stage=...`); kod incelemesinde engelleyici bir ağ/DB çağrısı bulunamadı, gerçek kök neden bir sonraki deploy'un loglarından ölçülecek.

Test özeti: `./.venv/Scripts/python.exe -m pytest -q` → **1381 passed, 4 skipped** (çevre bağımlı, dürüst skip). Önceki oturumların Türkçe prompt/ComfyUI/WhatsApp-onay testleri de bu sette korunuyor.

## 2026-10-20 — Turkish prompt translation and recipient gate

Added `integration/turkish_prompt.py` and wired it before ComfyUI workflow construction. Turkish prompts use the configured local Ollama fast model; English skips inference, the known sunset template stays local, and invalid/incomplete output keeps the user's source. Requests use JSON schema, no tools, a 25-second timeout, and `num_gpu: 0` so translation does not reserve the 4 GB GPU needed by ComfyUI. Text negations populate the SD negative prompt. Manual model testing exposed a dropped lighting sentence and `loş` translated as `dusty`; sentence-count rejection and a disambiguation instruction now cover those cases. Combined translator/ComfyUI tests **16 passed**. A real integrated Qwen3:4b run preserved every sentence and `ollama ps` confirmed **100% CPU**; it took about 20 seconds. WhatsApp recipient-confirmation tests **2 passed**. GPU render and native confirmation UI remain untested. Existing `integration/comfyui_image.py` coastal and `integration/web_panel.py` heartbeat edits are preserved. No PR/commit/deployment.

## PR #61 — Ücretsiz yerel görsel / CI düzeltmesi

[Taslak PR #61](https://github.com/fatmakahraman304-hash/ULTRON/pull/61), ilk uygulama `1dc4041`. Scene CI yeni Comfy transport testini aiohttp/Pillow kurulmadan önce çalıştırdığı için ModuleNotFoundError ile durdu. Test bağımlılıkların kurulduğu mevcut adımın arkasına taşındı; test/assertion kaldırılmadı. Son commit'in bütün Actions sonuçları PR üzerinde ayrıca doğrulanır. GPU/model/cihaz testleri NOT RUN; paid image çağrısı, PR #59/#60 değişikliği veya merge/deploy yok.

## 2026-10-18 — Ücretsiz yerel Image Studio / ComfyUI

PR #60 `d690c74` tabanından ayrı `feat/golge-free-comfyui-20261018` dalı. Free-by-default SD 1.5, stock ComfyUI workflow, loopback-only transport, mevcut telefon→laptop queue/lease/fencing, aynı özel görsel/geçmiş deposu ve GPU düşük VRAM başlatma profili uygulandı. Ücretsiz modda Gemini helper SDK kurmadan reddeder; çevrimdışı/bozuk yapılandırma ücretli fallback yapmaz. Windows/PWA aynı kuyruğu bekler; maliyet penceresi açılmaz. PR #59/#60/üretim korunur; indirme, gerçek GPU testi, paid çağrı, merge/deploy yok. Ayrıntılar: docs/GOLGE_FREE_IMAGE_STUDIO.md.

## 2026-10-18 — Image Studio PR #60 final consent verification

Draft [PR #60](https://github.com/fatmakahraman304-hash/ULTRON/pull/60), branch `feat/golge-image-studio-20261017`, is stacked on unchanged PR #59 `b0b4dbf`. Initial implementation `dbd00a45e7ebdfd6cda7bbfb04bb42e11af5996e` passed all seven GitHub Actions jobs across five workflows. Cost approval now uses a non-blocking accessible dialog shared by Windows React and iPhone PWA. A test first reproduced dispatch after switching conversations while consent was pending; a second owner/thread/active-request check now prevents it. Seven Image Studio Chromium tests and two research-renderer tests pass; the event-loop check is not physical microphone validation. Corrected screenshots use Chromium SwiftShader with CPU compositing and a clearly marked synthetic PNG. No paid call, merge or Render deploy. Follow-up exact-commit CI is recorded on PR #60.

## 2026-10-17 — Image Studio (review build, separate from PR #59)

Implemented owner-scoped Google image generation through the existing Cloud image endpoint, with explicit enablement/budget/per-request cost consent, PostgreSQL at-most-once ledger, quota and late-output suppression. Windows React and iPhone PWA now share intent/options and private generated-image history. Qt uses a restricted save-dialog download route. No paid provider call, production merge or deploy. See `docs/GOLGE_IMAGE_STUDIO.md`.

## PR #59 — CI düzeltmesi (17 Ekim 2026)

[Taslak PR #59](https://github.com/fatmakahraman304-hash/ULTRON/pull/59). İlk HEAD `e286772` için 6/7 Actions işi geçti; responsive-ui eski `ultron-shell-v74` assertion'ında durdu. Hata yerelde yeniden üretildi; v75 ve yeni kaynak renderer'ının HTML/cache bağımlılığı birlikte test ediliyor. Test kaldırılmadı veya genel sürüm regex'iyle gevşetilmedi. Yeni exact-head CI sonuçları PR'da kontrol edilecek; üretim/Render değişmedi. Actions log artefaktı erişimi 403 verdi; job/step durumları GitHub API'den, hata nedeni aynı komutun yerel çalıştırmasından doğrulandı.

## 2026-10-17 — Kaynaklı Google araştırması ve bounded model fallback (güncel)

Geliştirme dalı: `feat/golge-grounded-research-20261017`; başlangıç üretim `b486f13`, uygulama `a42b6bf`, PR #56 düzeltmelerini **yalnızca geliştirme dalına** alma `48a688a`. Üretim veya Render'a merge/deploy yok. Önceki kayıtlar tarihseldir. Ayrıntılar: [docs/GOLGE_GROUNDED_RESEARCH.md](docs/GOLGE_GROUNDED_RESEARCH.md).

Mevcut ResearchEngine'e resmî SDK Google Search adaptörü eklendi; kapalı varsayılan, ayrı model/bütçe/anahtar kapıları, en fazla iki model denemesi. Güncel soru yönlendirme, hassas sorguyu kısaltmadan önce denetleme, owner/thread kapsamlı ardışık araştırma devamı, güvenli kaynak yedeği ve kanıt yoksa dürüst yanıt çalışır. Grounding URL/UTF-8 support denetimi, tıklanabilir React/PWA kaynakları, sandbox öneri widget'ı, mesajla atomik PostgreSQL metadata kaydı ve iptal sonrası geç yanıtı kaydetmeme uygulandı. Eski ses/harita düzeltmeleri PR #56'dan korundu; Calculator UIA/approval sınırları değiştirilmedi.

443 Cloud/gerçek geçici PostgreSQL, 376 ilgili backend/güvenlik/kanıt/Calculator sözleşmesi, 43 frontend, 169 PWA JS, 4 gerçek Chromium ve 3 manuel komut regresyonu PASS. Build/compile PASS. 100 mevcut yönlendirme senaryosu 100/100; yeni 16 vaka üretim başlangıcında 8/16, şimdi 16/16. Bunlar model zekâsı ölçümü değildir. SDK 1.75.0 ve 2.31.0 fixture sözleşmeleri geçti. Gerçek Gemini/Qwen BLOCKED; cihaz/mikrofon/TTS NOT_RUN. Render health timeout; canlı sürüm doğrulanmadı. Exact-head CI sonucu PR üzerinde ayrıca izlenecek.

## 2026-10-16 — Üç legacy preset kaldırıldı

Kullanıcının açık kapsam yanıtıyla yalnızca GÖLGE intro render, Dünya hologramı ve enerji hologramı kaldırıldı; ana CORE, EarthWatch/harita ve kontrol merkezi korunur. Dashboard Araçlar düğmeleri, CenterStage presetleri/çizimleri, ilgili sahne kısayolları ve agent araç açıklamaları temizlendi. Backend artık kaldırılan türleri create/update/add, batch ve JSON import yollarında HTTP 400 ile reddeder; intro/energy video şablonları kabul edilmez. Eski snapshot'lar yalnızca desteklenen nesneleri canlı sahneye getirir; kullanıcı proje dosyaları ve hafıza silinmez.

Test-first regresyon eski sürümün kaldırılan özellikleri hâlâ kabul ettiğini gösterdi. Düzeltme sonrası 47 odaklı test geçti (7 kaldırma, 11 backend Earth, 24 frontend, 3 PWA sözleşmesi, 1 bundle, 1 gerçek Chromium). npm ci, TypeScript/Vite build, Python compile, YAML ve eklenen satırlarda credential-pattern taraması başarılı. Chromium testi üç düğmenin yokluğunu ve ana CORE/kontrol merkezi Dünya dönüşünü birlikte sınar. Browser backend'i kontrollü fixture'dır; gerçek model/Windows/iPhone/ses doğrulaması değildir. Bu kayıt yerel doğrulamadır; yeni commit'in Actions sonucu PR üzerinden ayrıca kontrol edilir. Merge/deploy yapılmaz.

## 2026-10-16 — PR #44 ortak CORE / Dünya ve gerçek kaynaklar

- Aynı PR dalında CORE ↔ EarthWatch GPU geçişi, ortak stage.earth/kamera, gerçek Photon/OSM araması, belirsiz konum seçimi, lazy Leaflet sokak haritası ve opsiyonel lisanslı XYZ sözleşmesi uygulandı. Night/day terminatörü, katmanlar, gerçek hava/uçuş ve ISS kaynakları mevcut adaptörlerle bütünleşti.
- Kıbrıs sorgusunun yanlış mahallelere gitmesi, düşük FPS kamera süresi, aynı konuma tekrar odaklanma ve pikselleşen aşırı küre zoom'u düzeltildi. Şehir ayrıntısı gerçek harita döşemesinde; uydu/terrain yapılandırılmadan başarı denmez.
- 54 odaklı test + 10 gerçek izole backend/WebGL kabul kontrolü PASS; ayrı 4 sentetik ses/transkript sözleşmesi PASS. Qwen/Gemini BLOCKED, fiziksel Windows/iPhone/mikrofon/TTS NOT RUN. Görsel kabul REVIEW_REQUIRED; SwiftShader'da 60 FPS elde edilmedi.
- Kanıt/rapor: docs/GOLGE_EARTH_V7.md ve docs/ui-v7/. Open-Meteo, adsb.lol, Photon ve OSM tile gerçek HTTP yanıtları alındı. PR taslak; merge/deploy yok.

## 2026-10-15 — PR #44 tasarım reddi sonrası gerçek düzeltmeler

- Aynı `feat/golge-v5-interface-control-center-20261015` dalı kullanılıyor; üretim tabanı 6ef3f5d korunuyor. Eski görünüm tamamlanmış tasarım sayılmadı.
- CORE'daki uzun yatay bağlantı hatası önce testle yeniden üretildi; gerçek yüzey komşuları, değişken ışık noktaları, cyan/amber parıltıları, dönen enerji halkaları, shader arka plan ve daha güçlü projeksiyon oluşturuldu. 1.400 düğüm / sınırlandırılmış geometri bütçesi korundu.
- Normal masaüstü düzeni ve kontrol merkezi yeniden tasarlandı. Telefonun geometrik SVG'si kaldırıldı; üretilen fotoğraf görünümündeki dağ/göl WebP'si hem React hem Cloud PWA'da sabit katman oldu (shell v74). Dünya doku/bulut/gece görüntüleri yerelden yükleniyor; canlı uydu sağlayıcısı yoksa açıkça belirtiliyor.
- Yerel servis bağlantısının Cloud başarısı sayılması düzeltildi. HTTP bağlantısı yokken Qt köprüsü mevcutsa otomatik native sohbet yolu korunuyor; gerçek fiziksel Qt davranışı henüz NOT RUN.
- Gerçek izole backend, mevcut session/Origin güvenliği, tek WebSocket ve gerçek Linux telemetrisi doğrulandı. `/api/merged/invoke` gerçek istek aldı ancak model yok: UNAVAILABLE. Sağlayıcı başarı sonucu uydurulmadı.
- Headless SwiftShader'ın varsayılan kompozitöründe dolu sohbeti küçültme sırasında bozuk PNG yakalandı; QA, gerçek WebGL'i CPU kompozitörüyle kaydediyor ve kayıp başlık piksellerini reddediyor. Bu fiziksel RTX doğrulaması değildir. Görsel kabul REVIEW_REQUIRED; Windows/iPhone/mikrofon/TTS NOT RUN.

## 2026-10-15 — GÖLGE V5 interface and interactive CORE

- Work is isolated on `feat/golge-v5-interface-control-center-20261015`, from GitHub/Render production base `6ef3f5d207fc9430cbbd552988935995529e87f5`; no upstream branch files were overwritten. Draft [PR #44](https://github.com/fatmakahraman304-hash/ULTRON/pull/44) is open and unmerged. Validated code/test commit `41c907056130536b6ec7abb482a4a02bf33e1437` passed exact-head Actions: Responsive Interface #38772280381, Scene Build #38772280054, Cloud/PostgreSQL #38772280060, and Local Qwen Listening #38772280179. An older Scene run failed because a stale test inspected `body`'s removed gradient; the test now verifies the fixed night-lake pseudo-element before and after message scrolling, and its updated Chromium run passes. No merge/deploy was performed.
- React desktop has NORMAL CHAT and a user/voice-command-opened CONTROL CENTER view. The latter reuses existing telemetry, device presence, task notifications, tool modal, native camera bridge and `EarthWatch`; unavailable values stay explicit, event text is redacted, and no unrestricted shell or fake sensor feed was added. Returning home retains chat/runtime state. Mobile rendering omits the CORE and control center.
- Three.js GÖLGE CORE is an actual bounded procedural network of 1,400 points with link/signal buffers, animated torus rings and projection base; state/amplitude arrive from the existing native bridge. A genuine Chromium shader error was found and fixed. The browser regression checks shader compilation and WebGL `NO_ERROR`, not hardware FPS/audio quality.
- Mobile React and Cloud PWA use a fixed, authored SVG mountain/lake wallpaper behind the independent chat scroller; composer/safe-area CSS and service-worker pre-cache were updated. The scene's visible product labels now say GÖLGE. `EarthWatch` was extracted/reused instead of creating another globe implementation.
- Generated visual evidence: `/workspace/golge-v5-ui-evidence/desktop-chat.png`, `desktop-control-center.png`, `mobile-chat.png`. Local Chromium checks: 1366×768 and 1920×1080 desktop chat/control view; 390×844 mobile scroll isolation, fixed background, composer within viewport, zero React page errors; one CORE canvas and one globe canvas; zero Three shader compile errors and WebGL error 0. These are browser emulation/SwiftShader checks.
- Real authenticated chat, backend telemetry, local Qwen/Gemini, physical microphone/TTS, Windows GPU, iPhone Safari and live Render health were not verified. Render MCP confirms service `srv-db20lmei0phs73crgujg` is LIVE at production SHA `6ef3f5d207fc9430cbbd552988935995529e87f5` (deploy `dep-db7mfuss728c73db4k10`). A direct public `/health` request timed out from this executor; no deployment was started. Vite emits an informational 575.89 kB OrbitControls chunk warning; the production build succeeds.

## 2026-10-14 — Shared cognitive intent router v2

- Started clean from production `b6b563d0521a874c46bd0cbe2d1a1ab5e4d8efc0` on isolated branch `feat/golge-cognitive-router-v2-20261014`; previous local branch and user files were preserved.
- Test-first regressions covered mixed Turkish/English corrections, continuation, previous-topic return, recent history vs personal memory, research and tool/scene honesty. Previous-topic context is owner/thread-scoped and bounded to at most 320 source turns; recent “what did I just say?” no longer creates a misleading old-keyword search.
- Unified intent and model-task recognition now feeds Cloud/local dialogue guidance and the existing Qwen FastBrain model router. Research can select the configured installed reasoning model; basic conversation stays on FAST. Existing specific UI tool handlers, read-only chat and Approval Gate remain unchanged.
- Frozen route suite: **100/100** deterministic label/context/tool matches (10 categories, 50 TR/50 EN). Production legacy dialogue-act label coverage on that corpus was **32/100**. Router-only p50/p95 moved from **0.003164/0.004637 ms** to **0.038924/0.080290 ms** across repeated local samples; it adds **zero model calls**. This does not measure model response quality or answer latency.
- Verification: Cloud **345 passed, 60 skipped**; backend model/tool regressions **56 passed + 4 subtests**; local-cloud bridge **6 passed**; Earth backend **5 passed**; frontend `npm ci` + production build passed (existing large GLTF chunk advisory); Earth frontend **6 passed**; chat transport UI **8 passed**, panel routing UI **4 passed**; frozen real-model suite structurally valid.
- Draft [PR #32](https://github.com/fatmakahraman304-hash/ULTRON/pull/32) is open on isolated branch `feat/golge-cognitive-router-v2-20261014`, with functional code head `74c932ae5002e9dae4285ffdc5552972ca50514c`, against base/production `b6b563d0521a874c46bd0cbe2d1a1ab5e4d8efc0`. Exact-head Actions all **SUCCESS**: Cloud/PostgreSQL #38548733163, Scene #38548733148, and Local Qwen Listening #38548733003. The PR remains unmerged and no Render deploy was triggered.
- Provider/device check: no Gemini key or reachable Ollama in this environment. Real Gemini/Qwen transcript quality, first-token and total response time, laptop inference and iPhone behavior are **NOT_RUN**. Render `/health` still reports production commit `b6b563d...`.
- Desktop `merged_api.invoke` routes classified explicit computer actions from default/general modes to the existing local approval-gated agent without a model preflight. It returns the actual agent state/message; waiting approval, partial plans and no-matching-intent outcomes cannot report `completed=true`. Test-first HTTP contracts cover dispatch, normal-chat preservation, ignoring client-supplied approval, and unsupported-action failure. A follow-up research honesty fix marks current result discovery as search-results-only, leaves answer confidence at zero without page evidence, demotes the research capability to adapter, and rejects lookalike reliability domains. Full backend suite at code head `74c932a`: **1,029 passed, 3 skipped, 6 subtests passed**. Focused research/process tests: **28 passed**. No actual Windows task, source page fetch, or live model ran. Exact-head Cloud/PostgreSQL #38548733163, Scene #38548733148, and Local Qwen Listening #38548733003 all passed.

## 2026-10-14 — Conversation policy survives context compression

- Followed PR #30 by inspecting `build_system_instruction`: under a small Qwen context cap, a long optional `ULTRON_SYSTEM_PROMPT` consumed the budget before persona and read-only policy. The previous implementation then cut the complete instruction at an arbitrary character boundary. The phone-to-Qwen path also failed to pass the shared configured prompt that Gemini receives.
- Test-first: three regressions failed before the fixes. Local Qwen now receives the shared configured prompt through the same bounded composer; oversized optional guidance is dropped whole, and a 64-character cap keeps required policy whole while omitting context.
- Targeted conversation, local-bridge and PR #30 continuity tests: **67 passed, 86 subtests passed**. Full Cloud Python: **275 passed, 60 skipped** because disposable PostgreSQL/integration prerequisites are absent. Long-listening Node contracts **22/22**, listening browser tests **7/7**, dataset validation **100 scenarios / 50 TR / 50 EN**.
- No live Gemini/Qwen call was made. The frozen 100-case set was structurally validated only; model quality and p50/p95 latency remain NOT MEASURED. Physical iPhone Safari/microphone validation remains NOT_RUN.
- Draft [PR #31](https://github.com/fatmakahraman304-hash/ULTRON/pull/31) has runtime code SHA `db1fd50b63b1abd1097e0ec5082e833b2e81f15e` and doc head `971673e1c55b16a4f0389610e8cb7c16b7c61f27`. Exact-head Cloud/PostgreSQL `38541558443`, Local Qwen Listening `38541558445`, and Scene `38541558508` Actions **passed**. Production GÖLGE `/health` is `ok` at merge SHA `9c7817f`; Render deploy `dep-db7jjdm7bikc73d3h5og` is LIVE. This feature branch has not been deployed.

## 2026-10-14 — First-run setup accepts typing and persists once

The native Qt setup overlay was shown before the main window, leaving keyboard focus in the chat field behind it. The setup key field now claims focus after the parent window is shown, supports Enter-to-submit, and has an explicit SHOW/HIDE control. Saving setup merges the Gemini key and OS choice into the existing ignored `config/api_keys.json`, preserving local model preferences, so a completed setup is not requested again at launch. Regression tests first reproduced focus remaining in the underlying input; both setup regressions now pass. Scene Build Actions `38469167141` passed for exact code SHA `1dda1d4f5833a3e52564711c29aa10f7274e1741`. Render `/health` remains HTTP 200 at the independent Cloud SHA `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c`; this desktop-only change does not deploy to Render. The real Windows screenshot flow remains to be retested after pull.

## Windows installation passed — 2026-10-14

Owner confirmed `INSTALL.bat` completed on Windows 11 at commit `4648d70` (Python 3.12.14, Node 24.19.0, npm 11.17.0), including frontend build, pip checks, Playwright install, `pytest tests`, and `integration.doctor --quick`; the installer printed `Kurulum tamamlandi.` The console did not show pytest's summary count. Ollama already had the configured four models, so setup did not need to pull Qwen weights. `START.bat` and real chat, voice, vision, Gemini fallback and scene controls are the next hands-on checks.

The frontend audit warning was traced to transitive `source-map-js` 1.2.1 (GHSA-68fv-2mgg-jv7q). Updated the lock to 1.2.2; clean `npm ci`, `npm audit` (0 findings), and Vite production build now pass. The Vite large-chunk warning is informational and did not block the Windows build. Scene Build `38467187863` and Frontend Build `38467187789` both passed on fix commit `4d9b8a7`. The Render cloud service was unaffected and remains LIVE at `1ad5f28`.

## Laptop handoff — 2026-10-13

The source archive was originally prepared from functional code SHA `13b3147eb01a0cdcd1352b5bbf136fda7ab1d56c`; the owner cloned handoff commit `3a6f489`. After the install exposed a stale title assertion and npm advisory, the correction was pushed as `4d9b8a7`, and the owner fast-forwarded to `4648d70`. Archive integrity checks confirmed installer and source files were present without generated dependency folders. Windows installation now passes; live model/device acceptance remains unverified.

## Completed checkpoint — end-to-end desktop provider error privacy

Code commits `b327c3de1b8bf4269ddbfb0ea2d2b0715bbf5c16` and `675ea678ec41bd7b88fac645f218a9d1493dcb3f` now protect model-router health, local chat/vision HTTP responses, the desktop agent's final error message, CloudClient health/fallback status, and vision debug logs. Chat failures return safe Turkish text and status codes; malformed image input keeps its specific validation response. Vision debug output records response length, not user-image-derived text.

Full backend tests: **1,025 passed, 3 skipped, 6 subtests passed**; focused provider suites: 41 passed plus 4 subtests. Scene Actions [#38460977820](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38460977820) and [#38462071665](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38462071665) passed; the latest new desktop privacy step passed 22/22. Cloud/PostgreSQL Actions [#38460977851](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38460977851) and [#38462071649](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38462071649) passed.

In authorized My Workspace, the Render service remains LIVE at Cloud SHA `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c`; `/health` returned HTTP 200 and the exact commit, and the error-log query was empty. This desktop-only change does not trigger a Cloud deployment. Real Gemini/Qwen inference, phone/laptop acceptance and Windows installation remain NOT RUN; no 100/100 model score is claimed.

## 2026-10-13 — Provider errors no longer echo sensitive exception text

Replaced raw Gemini failure text in chat, vision, PDF, camera and live-voice event rows with two fixed diagnostic categories. The Live websocket now receives the same safe category; desktop task watcher failures use a fixed Turkish status message. Transient provider errors still take the existing 503 path. A fake-key vision failure exercised the real HTTP handler and proved neither the response nor event record contains the raw error. Focused privacy tests: 3/3; full Cloud Python: 323 passed, 60 skipped. GitHub Cloud run #38458215679 passed the new privacy step; Scene #38457949652 and WORLD #38457949491 passed. Render deploy `dep-db78mn5bedkc738a0fu0` is LIVE at `1ad5f288d1f4084d0561c8027dbee51f5ad75b6c`, confirmed by `/health` HTTP 200. The test double does not establish live Gemini behavior.

## 2026-10-13 — Bilingual evaluation checks now match the stated 100-case split

Fixed a frozen-suite validation gap: non-English labels and missing English cases were not rejected. The validator now requires exactly `tr` and `en`, with five of each in every one of ten categories. A regression first failed against the old validator and passes after the fix. Evaluation tests pass 11/11; Cloud Python passes 320 with 60 environment-dependent skips; the dataset command confirms 100 cases / 50 per language. Commit `5677dca638909d23d96aab2dedab2597dbd196c1` passed Cloud/PostgreSQL #38456643001 and Scene #38456642956. Render `dep-db78i45bedkc7389oi50` is LIVE, and `/health` reports the exact SHA. No real Gemini/Qwen score was produced.

## 2026-10-13 — Typed Live turns share consent and history handling

Closed a gap in the websocket's typed-message branch: text sent to Gemini now also enters that turn's consent evidence and persisted user history. Oversize typed input is rejected at 16,000 characters. The actual nested websocket/tool/history functions are exercised by a test-first integration regression; focused live-voice tests pass 8/8. Full local Cloud Python tests: 319 passed, 60 skipped; browser tests: 153/153. Commit `f932b184eda215585a01d8d5d933b9f682611de1` passed GitHub Cloud/PostgreSQL #38455888395, Scene #38455888286 and WORLD smoke #38455888333. Render deploy `dep-db78feajnfac73d01fo0` is LIVE, with public `/health` returning 200 and the exact SHA. Real Gemini Live and phone use remain unverified.

## 2026-10-13 — Natural Turkish memory requests in live voice

Expanded the explicit-consent recognizer to understand “aklında bulunsun”, “bunu aklında bulundur”, “bunu hafızana yaz”, and “bunu notlarına ekle”; negative instructions and questions do not authorize writes. Four missing-phrase regressions failed before the implementation and passed after it. Cloud Python: 318 passed, 60 skipped. Commit `86ad3922f2ae04fe630c0ea08a4d53275a6f32f2` passed Scene #38452607673 and Cloud/PostgreSQL #38452607354. Render deploy `dep-db783rnavr4c73euva8g` is LIVE; `/health` reports the exact SHA with HTTP 200. Actual phone/Gemini transcription was not tested.

## 2026-10-13 — Explicit live-voice memory consent

Refactored the oversized phone voice instruction into a concise policy tied to actual tool results. Persistent memory requires a clear “hatırla/kaydet” request in the current transcribed turn; a personal disclosure alone cannot write. The server blocks password/API-token-like values and maps unsupported memory categories to the valid FACT category. Transcript parsing now runs before same-packet tool calls so consent checks see what the owner said. Removed unverified desktop feature claims; delegation reports task status and retains the code-approval gate. Policy size fell 6,789 → 1,913 characters (72%). Focused handler tests 7/7; full Cloud Python suite 318 passed, 60 skipped. Exact-SHA Scene #38449688028 and Cloud/PostgreSQL #38449688070 passed at `166ae52e4f47421329e60d1d5c474d47e8ef2a9b`. Render deploy `dep-db77pougekts73dhtjpg` is LIVE at the same SHA; `/health` returned HTTP 200 and Render error logs were empty. Real Gemini Live and physical phone behavior are untested; no model-quality score is claimed.

## 2026-10-13 — Dashboard chat starts before WebGL

Made `CenterStage` lazy and delayed its import 250 ms so the default orb no longer competes with the initial chat UI. Main entry: 294.21 kB raw / 84.34 kB gzip before; 105.07 kB / 30.92 kB after. Actual WebGL stays in the production build and renders after the delay; bundle contract and Chromium-with-held-renderer test prove both parts. Production build, bundle contract, Earth 6/6, frontend Node 10/10, scene intent/design checks, real Chromium stage-load test 1/1, and WebGL scene suite 9/9 pass. Exact commit `a4f31c66bfb31c1d733ea5ab9d475bf4a8af9f24` passed Frontend Build Check `38445096269` and Scene Build Check `38445096168`. Render `/health` is HTTP 200 at backend SHA `c805e1e`; the frontend-only commit is outside the service root `ultron/cloud_service/`. The chunk-size warning remains for the deferred GLTF/WebGL chunk.

## 2026-10-13 — Whole-system verification

Checked the current release across local suites, GitHub Actions, Render, and the served runtime files. Local results: Cloud Python 311 run / 60 environment-dependent skips; Cloud JavaScript 153/153; backend Python 58/58; scripts 62 run / 6 environment-dependent skips (including actual offscreen Qt widget tests 5/5); frontend `npm ci`, production build, and Earth 6/6; Python compilation and 3D intent/design validation pass. Real Chromium/SwiftShader 3D scene interactions passed 9/9, GÖLGE mobile composition passed in Chromium, and a real 154,988-byte Poly Haven CC0 ArmChair_01 was downloaded and manipulated successfully. Exact c805e1e Actions Cloud/PostgreSQL #38440168681 and Scene #38440168682 succeeded. Render deployment `dep-db76oo6q1p3s73f48g6g` is LIVE at c805e1e; `/health` is HTTP 200 and five checked runtime JavaScript assets match local files byte for byte. Gemini credentials and local Ollama are absent from this workspace, so no real inference or model score was produced. No phone/laptop hardware test or Windows install was performed. Frontend emits an advisory for an 821.74 kB raw (222.42 kB gzip) chunk; the initial 3D orb uses Three.js at startup, while the separate Hologram Lab is lazy. Measure the startup cost before changing the display.

Expanded the system-wide Python matrix with `PYTHONPATH=ultron/backend:ultron/cloud_service python -m pytest -q ultron/backend/tests scripts/tests`: **1,074 passed, 9 skipped, 6 subtests passed**. Skips require a user Picovoice key, physical Windows/microphone/screen, a disposable PostgreSQL service, or a deterministic parser path not recognized in this runtime. No failures.

## 2026-10-13 — Turkish without diacritics

Added a shared Unicode normalization helper for matching only. The response-length/tone/persona rules and thread topic-switch, correction, continuation, recap and reminder detectors now recognize common unaccented Turkish input. Two regressions failed before the change and pass after it. Original messages are not rewritten; ownership, history scopes, safety roles and provider routing are unchanged. CI initially exposed the desktop-package import path; package-relative imports now cover both desktop and service launches. The fixed release passed exact-SHA Scene and Cloud/PostgreSQL Actions and is LIVE on Render.

## 2026-10-13 — Qwen readiness probe recovery

Fixed the typed-chat path where a failing `/api/device-presence` probe threw after the composer cleared the text and before either provider received it. Unknown readiness now resolves to Gemini; a confirmed fresh `local_chat_ready` response continues to prefer laptop Qwen. Added a mobile routing regression for a network-failed presence probe. No device task or duplicate local submission is created by that fallback. Commit `52b776a` is pushed; exact-SHA Scene and Cloud/PostgreSQL Actions passed, and Render health confirms the release SHA.

## 2026-10-13 — GitHub PR path for GÖLGE code changes

Added local intent routing to the approval-gated CodeGen proposal flow, strict vague-request clarification, clean/current checkout and repository verification, GitHub CLI login check, path-limited staging, separate draft branch/PR, and no auto-merge. Expanded approved CodeGen verification to include backend tests and the production frontend build. Phone transcript interception now lets the conversation tool queue work to the paired laptop. Added [GOLGE_KENDI_KODUNU_GELISTIRME.md](GOLGE_KENDI_KODUNU_GELISTIRME.md) with the Windows-side prerequisites; no Windows installation or user token entry was performed.

## 2026-10-13 — Suggestions grounded in saved goals

Replaced the same generic briefing suggestion with one contextual option sourced from the nearest listed owner plan or saved GOAL/PROJECT; other saved data and empty memory receive a transparent fallback. Added a dedicated mobile panel region. Existing auth and owner scoping remain. The plan, tool, and memory systems are already implemented and were not replaced.

## 2026-10-13 — Owner corrections retained during topic recall

Reproduced a dropped Turkish correction in `select_contextual_turns` before changing code. Old question/answer and adjacent owner correction are now selected atomically; insufficient turn budget omits the superseded exchange. Added Turkish/English and tight-budget regressions. Windows installation remains deferred.

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

## 2026-10-10 — Explicit historic user correction and real reminder-intent separation

- Verified code commits `dc97a58cf327e4d9c77880d934b845aef5bed9c0` (topic-nameless historical owner correction preserved after retrieved Q&A) and `800a54d07e0159cec063c67f7555a94abe2ced48` (future reminders no longer falsely handled as historical recall, no invented notification state).
- Query safety: correction row is accepted only when it immediately follows matched historical assistant answer and begins with explicit corrective language. One capped owner/thread/previous-message SQL lookup; within unchanged total chars and max model turns. New disposable PostgreSQL tests with >115 intervening turns, other account and other conversation records.
- History-like `ne demiştik?` / `konuşmamızı hatırlat` remains historical. `Yarın saat 9'da hatırlat`, `in 20 minutes remind me` are future scheduling requests and use recent-thread context only. No device permission bypass or actual scheduling performed. Deterministic and real PostgreSQL tests pass.
- CI at exact latest code SHA: [Cloud/PostgreSQL #38079636700](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079636700) **SUCCESS**; [Scene/Frontend #38079636678](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079636678) **SUCCESS**. Previous code Cloud [#38079471594](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079471594) and Scene [#38079471493](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38079471493) also SUCCESS.
- Outstanding: real Gemini/Qwen human-reviewed acceptance and 20-case pilot, accurate model latency, latest deployed Render SHA, iPhone/Windows physical runtime. No Windows update run.

## 2026-10-10 — Final user correction + explicit topic switching

- Code commits: `a08b3afadaed0f17ec67bfdbab6a3ebe5375b8bf` (current messages keep head/end under original Qwen/Gemini limits) and `ec566816ef4eeaa162b579f05f86bb0828ff4237` (explicit new-topic commands avoid old lexical history matches and add TOPIC SWITCH persona hint).
- Added no-provider mock Ollama wire and Gemini prompt tests for late user instructions; new deterministic and real disposable PostgreSQL tests for topic switch, owner/thread isolation, before-current cutoff and maximum context size.
- Verified GitHub exact-SHA CI: [Cloud Queue PostgreSQL Integration 38078914038](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078914038) **SUCCESS**; [ULTRON Scene Build Check 38078914033](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078914033) **SUCCESS**. Older code commit CI also both successful.
- Still NOT TESTED: real Gemini/Qwen 20/100 case inference and independent human quality review, accurate live model latency, exact deployed Render commit, iOS/Windows hardware. No local Windows update or download was performed.

## 2026-10-10 — Current long-message final correction preserved in Gemini and Qwen

- Production code commit `a08b3afadaed0f17ec67bfdbab6a3ebe5375b8bf`. A new shared `bounded_user_request` helper retains the beginning and ending of overlong current turns. Qwen `local_chat` and `ollama_messages` preserve final instructions under their existing 3,000-character cap; `gemini_turns` does the same under its existing 16,000-character cap. Regular short turns remain unchanged. No model training, download, prompt-size increase, implicit memory write, external account access or Windows changes.
- Tests verify last-request correction after long unrelated text in Gemini and Ollama message payloads and local loopback mocked chat call. GitHub CI **SUCCESS** for Cloud/PostgreSQL [38078688366](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688366) and Scene/frontend [38078688244](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38078688244).
- Outstanding: real Gemini/Qwen human-reviewed pilot and 100-case conversational quality, provider latency, exact live Render SHA and real iOS/Windows hardware testing. Do not use synthetic infrastructure tests to claim a model quality percentile.

## 2026-10-10 — 20-case bilingual pilot and honest provider labeling

- Functional SHAs: `bf9ddc28b112266228a606e4c2fd817a7625f558`, followed by verified `ceef1f499ccb5690de3bdcd8289873a5d6f8c52f`.
- Pilot selector draws 10 TR + 10 EN from all 10 existing categories (20 out of frozen 100), zero changed criteria, and reports 80 unselected cases as NOT_RUN. Allows an authorized small real-model pass before spending time/API quota on a full evaluation.
- Read-only Qwen evaluator now checks that locally installed and actually selected Ollama model belongs to Qwen; another-family output is never scored under Qwen. Production model routing is unchanged.
- Gemini preflight safe failure emits explicit `GEMINI_API_KEY_not_configured` without revealing any actual credential. New offline CLI regression verifies 0 captured, 100 NOT_RUN with 20 unavailable and 80 pilot exclusions; model score remains null. This is **not** a live Gemini run.
- **GitHub exact-code checks SUCCESS:** [Cloud/PostgreSQL #38076948096](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38076948096), [Scene/Frontend #38076948157](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38076948157). Still NOT MEASURED: actual Gemini/Qwen model quality, p50/p95 on real hardware, production Render SHA, physical iPhone/Windows voice and local inference. No Windows change.

## 2026-10-10 — Dense older named-topic mentions: oldest + newest scoped recall

- Functional code SHA `f73d43358715358dc21b48f4b34c510307627f3f` on `feat/ultron-cloud-shared-memory`.
- Fixed the old-history query taking only the 24 most recent lexical matches. In long same-topic discussions, this could hide the original question and first decision even though the user explicitly asked to recall it. Two bounded SQL queries now sample the oldest and newest historical matches (16 each), with explicit owner/conversation/previous-message constraints on both. Best-scoring old/new evidence and adjacent Q&A are included within unchanged character/turn budgets; ordinary chat still avoids extra searches. This is lexical recall, not semantic truth or general contradiction resolution.
- Deterministic regression simulates dense later references; real disposable PostgreSQL regression inserts 42 historical keyword mentions, >100 newer turns, and unrelated user/thread records. The original discussion, assistant answer and latest context survive without crossing owners.
- Exact CI **SUCCESS**: [Cloud/PostgreSQL 38073658327](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073658327) and [Scene/Frontend 38073658416](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073658416).
- Live Gemini/Qwen natural quality NOT MEASURED; 100/100 unproven. New Render deployment and Windows/iPhone hardware tests not verified. No Windows update was run.

## 2026-10-10 — Conversation acceptance integrity and provider metadata

- Verified functional code `043a5386e510bc81a1bc163d9887cef8f75a4071` after evaluation-runner changes in `0ad17db51fb60b50ceab42abf5e22d3cb7f4baa9`.
- Versioned 100-case (50 Turkish + 50 English) scenario suite is unchanged. Completed transcripts gain reproducible SHA256 digests, blank independent-review templates, digest verification before accepting reviews, per-turn model identity and presentation flags, plus measured p50/p95 latency reporting. None of this substitutes for real model inference and human judgement. SHA256 binds transcript content to reviewed content but does not prove that an external provider generated it.
- The production Gemini retry/fallback wrapper now supports a keyword-only `include_model=True` exclusively for evaluation; the default remains the original text string for normal Cloud conversations. A no-network test exercises fallback and primary-only behavior with the actual function AST. This allows honest per-call Gemini model labeling, and keeps Qwen labels already returned by the local adapter.
- GitHub exact-code workflows all **SUCCESS**: [Cloud/PostgreSQL 38073193493](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193493), [Scene/Frontend 38073193481](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193481), [WORLD read-only smoke 38073193495](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38073193495).
- Actual Gemini and Ollama/Qwen 100-case transcripts: **NOT RUN** in this continuation (no authorized reachable provider demonstrated). Model quality 100/100: **NOT MEASURED**. New Render live commit, Windows installation and physical phone voice not verified.

## 2026-10-10 — Historical Q&A conclusions preserved under context caps

- Functional code commit: `4a196658820aa38f747cb6cd1e74a12714c59eaf`, following named-recall improvements at `064a9f6efbea16f5a71bb474f35e27300584d26c`.
- The generic old-topic selector previously sliced matched historic messages from the beginning only, which could discard a final decision, user correction or important response conclusion. It now uses the same bounded beginning/ending excerpting applied elsewhere, preserving both portions without extra inference calls, new memory writes, or bigger context budgets.
- Tests: deterministic old long-question/long-answer finale recovery, plus real disposable PostgreSQL 110+ unrelated intervening-message named recall and cross-user/cross-conversation isolation. Exact-commit Cloud/PostgreSQL [38072623731](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38072623731) **SUCCESS**; Scene/Frontend [38072623801](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38072623801) **SUCCESS**.
- Not verified: real Gemini/Qwen 100-case quality, real model inference latency, deployment on Render of this SHA, Windows/iPhone hardware. No 100/100 conversational claim; keep the final Windows update on hold.

## 2026-10-10 — Conversational intelligence: historical topic retrieval and corrected long messages

- Code SHAs: `d9d1f9ac33d75fd558671a2f3fafc7ab376dd5af` (context and targeted retrieval), then `1e5e11002a471d041023e5c8efd95047b733442b` (grounded named-recall system guidance).
- Explicit named old-topic questions can now find messages older than the last 80 turns. The additional keyword search is parameterized, capped, same-owner / same-conversation / prior-message only and runs only on explicit historical requests with no recent match. The matched user/assistant exchange is paired so the model sees what was said, not a detached keyword.
- `prepare_turns` now retains the opening and ending excerpt of a long previous message, protecting late corrections from silent head-only truncation within the same character budget. Short topic acronyms and end-of-message entities are recognized, with bounded token scanning.
- The system prompt distinguishes confirmed earlier Q&A from speculation and forbids invented recall. The new deterministic tests and real disposable PostgreSQL >120-turn cross-owner/cross-conversation regression passed on GitHub.
- **CI PASS on exact `1e5e11002a471d041023e5c8efd95047b733442b`:** [Cloud Queue PostgreSQL Integration #38071243972](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071243972); [ULTRON Scene Build Check #38071243961](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071243961). Prior context code `d9d1f9a` also passed both [38071107141](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071107141) and [38071107135](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38071107135).
- Quality limits: older search is lexical, not general semantic truth retrieval; long texts are still excerpted; 100 live Gemini/Qwen scenario quality remains NOT MEASURED. Render promotion of this new SHA, iPhone voice and Windows updates were not verified.

## 2026-10-10 — Long conversation recap true-midpoint follow-up

- Functional SHA: `066b7b982a19c97297a2d74ee4cf68a4a9c4d336` on `feat/ultron-cloud-shared-memory`.
- Old limitation: a recap request used at most the last 80 thread messages. For 100+ messages, the sampled 'beginning' and 'middle' were actually inside that recent window. This did not reflect the full conversation.
- New behavior: an explicit recap with >80 prior turns now fetches the real start and midpoint and keeps recent dialogue under the existing 7,200-character / 20-turn hard ceilings. Scoped SQL filters on user_id, conversation_id and before_id apply to every slice and count. Short conversations retain the previous one-query path. No extra LLM calls, memory writes, cross-thread reads or approval-policy changes.
- New deterministic long-thread test and real disposable PostgreSQL 120+ message tenant-isolation test were added. CI: [Cloud 38070614904](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614904) SUCCESS; [Scene 38070614899](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614899) SUCCESS.
- Gemini/Qwen real-answer acceptance remains NOT_RUN / NOT MEASURED. Render deployment of this newer SHA and Windows/iPhone physical tests have not been verified in this continuation.

# ULTRON — Kalıcı Geliştirme Günlüğü

Bu belge geçmişteki gerçek kod değişikliklerini ve doğrulamayı kaydeder. Kendiliğinden arka plan çalışan bir süreç değildir.

## 2026-10-09 — Otonom geliştirme oturumu

**Repo:** `fatmakahraman304-hash/ULTRON`  
**Branch:** `feat/ultron-cloud-shared-memory`  
**Başlangıç HEAD:** `0638b116c30d221f4167a4df35381a5697237668`

### Döngü 1 — Earth Watch etkileşim
- `CenterStage.tsx` içinde kamera position/target ve Dünya orientation durumunu layer değişikliklerinde koruma.
- Focus hedefine yumuşak geçiş; drag hareketini gerçek nokta tıklamasından ayırma.
- `earthMath.ts` ile deterministik coğrafi koordinat matematiği.
- `earthMath.test.mjs` ve `npm run test:earth` ile regresyonlar.

### Döngü 2 — Backend state doğrulama
- Yeni `ultron/backend/earth_watch.py`: JSON veri normalizasyonu, doğru bool yorumlama, nonfinite koruması, longitude wrapping, renk/label/id/marker sınırları.
- `server.py` Earth Watch komutları ve diskten yükleme bu katmanı kullanıyor.
- Focus durumunda otomatik dönüş durur; GLOBAL seçimi dönüşü yeniden açar.
- Yeni `test_earth_watch_config.py`, CI'da bağımsız stdlib testleri.

### Döngü 3 — Gerçek dünya aydınlatma + ISS güvenilirliği
- Yaklaşık UTC Güneş pozisyonu ve dinamik ışıklandırma; manuel `UTC SUN` düğmesi ve sesli kontrol.
- Ekinoks/gündönümü/UTC farkı için testler.
- ISS kaynağı doğrulanmadan konum pini gösterilmiyor; request timeout, tek aktif request ve cleanup uygulanıyor.
- Bu, ISS kaynağının her ortamda erişilebilir olduğu anlamına gelmez.

### Döngü 4 — Geliştirme oturumları arası devam
- Root `AGENTS.md` Codex çalışma kuralları; riskli işlemlerde onayı korur.
- `scripts/ultron_dev_resume.py`: dört devam belgesini, branch/HEAD/git durumunu ve sıradaki işleri read-only raporlar.
- `scripts/tests/test_ultron_dev_resume.py` ve CI doğrulaması.
- Dört devam belgesi oluşturuldu, bu oturum sonunda gerçek kayıtlarla güncellendi.

### Doğrulama
- Son tam kod/CI referansı: `a010726149f7a1352933a2e45af51f9b1a985662`.
- `ULTRON Scene Build Check` run `37893780863`: PASS. Python syntax, backend Earth tests, resume tests/command, TypeScript/Vite ve Earth math tests geçti.
- Tam Python test suite, Windows `START.bat`, gerçek RTX 2050 FPS, mikrofon ve gerçek ISS bağlantısı: **bu oturumda çalıştırılmadı**.
- Cloud/Render otomatik deploy edildiği iddia edilmemiştir.

## Sonraki kesin iş
`ULTRON_NEXT_TASKS.md` içindeki Windows smoke doğrulaması ve Cloud queue idempotence regresyonları.

### Döngü 5 — Cloud queue atomik task teslimi ve completion koruması
- `ultron/cloud_service/app.py`: aynı `user_id:target` için `pg_advisory_xact_lock` ile eşzamanlı claim sorgularını seri hale getirme; yalnızca `status='delivered'` halinde retry/completion yapılması; eski/tekrarlanan completion için 409.
- `ultron/cloud_service/test_device_queue_contract.py`: gerçek handler AST ile çalıştırılan izole stub/mock veritabanında duplicate completion, inactive task, retry limiti, direction guard, iki paralel claim ve SQL state guard testleri.
- `.github/workflows/scene-check.yml` queue testlerini çalıştırıyor.
- İlk CI test denemeleri `37894708692` ve `37894774521` test harness hatalarıyla FAILED; source path ve HTTP stub düzeltildikten sonra `37894840971` SUCCESS.
- **Doğrulanmış son kod SHA:** `34b80e43abe023e58a8f65c87688aa104d6d55e7`.
- Başarılı CI adımları: Python compile, Earth backend test, 6 Cloud queue test, resume test/command, frontend TypeScript/Vite build, Earth math test.
- **Henüz doğrulanmayan:** gerçek PostgreSQL paralel transaction, Render deploy SHA, eski worker'ın yeniden teslim edilmiş task'a karşı attempt fencing'i, gerçek Windows/Gemini/Cloud uçtan uca test.


### Döngü 6 — Cloud delivery generation ve gerçek PostgreSQL doğrulaması
- `ultron/cloud_service/schema.sql`: teslim nesli `delivery_attempt` eklendi.
- `ultron/cloud_service/app.py`: claim nesli artırır; completion/retry, heartbeat/progress ve checkpoint kayıtlarında teslim nesli atomic SQL guard ile kontrol edilir. Tamamlanma/checkpoint JSONB yanıtları normalize edilir. PostgreSQL'in `jsonb_build_object` parametre belirsizliği `$3::integer` ile giderildi.
- `ultron/backend/cloud_client.py`, `mark_app.py`: masaüstü komutunun claim nesli tüm ilgili çağrılara eklenir; `agent_task` dışındaki legacy kontroller korunur.
- `ultron/cloud_service/test_device_queue_contract.py`: eksik/eski attempt, yarışan completion ve gerçek progress/lease/checkpoint handler testleri.
- `ultron/cloud_service/test_device_queue_postgres.py`: disposable PostgreSQL üzerinde paralel claim, retry/reclaim, stale completion, stale progress/lease/checkpoint ve legacy wake kontrolü testleri.
- `.github/workflows/cloud-queue-postgres.yml`: GitHub Actions PostgreSQL 16 disposable DB entegrasyonu. `scene-check.yml` masaüstü istemci/worker py_compile kontrolü de yapar.
- İlk PostgreSQL denemeleri `37897241297` ve `37897368506` FAIL oldu. Tespit edilen gerçek SQL tipi ve test JSONB dönüş sorunları giderildi.
- **Kod SHA:** `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`.
- **CI PASS:** `37897505788` (Python compile, 5 Earth, 14 Cloud contract, 3 resume, TypeScript/Vite, 6 Earth math); `37897505793` (4 gerçek PostgreSQL 16 testi).
- **NOT RUN:** Render üretim deploy, gerçek Windows masaüstü/Gemini/telefon uçtan uca testleri, yerel eylemlerde exact-once garanti analizi.


### Döngü 7 — Masaüstü Cloud lease fencing ve görev serileştirme
- `ultron/backend/cloud_client.py` yanıtı 404/409 olan `/api/device-commands/*` işlemlerini `CloudDeliveryRejected` olarak sınıflandırıyor. 503/diğer URL yanıtları stale fence sayılmıyor.
- Yeni `ultron/backend/cloud_delivery.py` yenilemeyi kısa timeout'la yapıyor; belirgin lease reddi ve 15 sn boyunca doğrulanamama durumunda `lost` sinyali veriyor.
- `mark_app.py` görev çalıştırmadan önce ve Gemini bekleme döngüsünde lease'i kontrol ediyor; kayıp tespitinde best-effort `interrupt()` çağırıyor, eski teslimi completed olarak göndermiyor. Aynı process'teki agent görevleri artık ortak oturumda üst üste binmiyor.
- Yeni `ultron/backend/tests/test_cloud_delivery_guard.py`: 6 lease guard + 4 HTTP hata senaryosu, **10 PASS**.
- `.github/workflows/scene-check.yml` yeni regresyonları zorunlu kılıyor.
- **Kod SHA**: `d96638e1ecaad7d0b800e20fb22580ade555e777`; **CI** `37914696238` — PASS (5 Earth backend, 10 lease/client, 14 Cloud contract, 3 devam aracı testi; TypeScript/Vite PASS).
- **Sınır:** Cihaz üzerinde sesli/Gemini gerçek workflow ve Render ortamı doğrulanmadı; geriye dönük yan etkiler iptal edilemez.


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

## 2026-10-10 — Warm ULTRON persona across devices
- Created ultron/cloud_service/conversation_persona.py plus eight stdlib regression tests.
- Integrated policy into local_brain_bridge.py and Cloud app.py for Gemini text, image, PDF, camera and Live audio. Local Qwen still requires Windows and cannot execute device tools.
- Added standalone CI persona-policy job independent of Postgres. Prior Cloud queue runs failed during GitHub runner Postgres container initialization, before checkout or Python tests; not a code failure.
- No real device or Render deployment validation completed at authoring time.

## 2026-10-10 — Shared persona verification
- GitHub Actions Cloud Queue PostgreSQL Integration run #37992572797 SUCCESS at commit 015ed652a03fd67caaf1118ff6707cc55e3b6f30. The separate persona-policy job passed all eight tests; the postgres-fencing job also passed its persona test and real PostgreSQL queue, local-brain memory/reply and dev-request integration steps.
- Docker Hub rate limit was the cause of earlier CI setup failures; replaced postgres:16 with public.ecr.aws/docker/library/postgres:16 to restore integration tests.
- ULTRON Scene Build Check run #37992487672 SUCCESS for persona fix commit 2e424e9c6da7eb2efecff50b8737f18532e36a67. No runtime files changed since that run, only workflow/docs.
- Real iPhone/Windows/Gemini sessions and Render deployment remain NOT VERIFIED.

## 2026-10-10 — Windows assistant persona refinement / verified
- Desktop Agent persona_guard.py now uses respectful ULTRON guidance rather than mocking the owner; no longer penalizes ordinary replies for lacking 'Boss'. agent.py no longer forces 'Boss' after reframing and removes the harsh rewrite cue.
- Added ultron/backend/tests/test_persona_warmth.py: 4 stdlib tests covering kind anchor, ordinary direct response, genuine apology and desktop postprocessor.
- GitHub Actions Cloud Queue PostgreSQL Integration #37992833637 on SHA 433617f77b669fbe30526705faccbe6532ccd545 SUCCESS: persona-policy (Cloud 8 + Windows 4 tests), real PostgreSQL queue/memory/development-request integrations all passed.
- ULTRON Scene Build Check #37992774370 SUCCESS at Windows agent postprocessor SHA 93f921f266a37bf01f565b9c8c32880854f3f372.
- No Windows local checkout, microphone/audio, physical phone or current Render deploy verified.


## 2026-10-10 — Personal owner briefing API
- Previous capability-readiness implementation and five tests passed CI (Cloud Queue PostgreSQL Integration #37995713894 success; scene build #37995706268 success on adjacent code commit).
- New pure Python personal_briefing.py reads only user-saved memory rows, deduplicates entries, bounds all outputs, and labels every item owner_saved_memory; it never invents deadlines, reminders, appointments, email access or executed actions.
- app.py now offers authenticated GET /api/personal-briefing with user-scoped memory query; no automatic polling or data gathering.
- Four new tests in test_personal_briefing.py wired into the standalone persona-policy CI job. CI / physical iPhone / Windows / Render current deployment should be checked separately; do not claim they are verified without passing results.


## 2026-10-10 — iPhone personal overview implementation
- Confirmed previous briefing API CI #37995893863 SUCCESS and Render successfully deployed briefing test SHA ba3c46df.
- Added /static/personal-panel.js with on-demand personal-memory and ten-capability panels, linked into mobile HAFIZA tab; loaded scripts via PWA cache v44.
- Node test contracts added: test_personal_panel.cjs (6), wired to scene-check.yml. CI initially red because test_local_voice.cjs pinned cache v43; patched version regex and new asset assertion in c1c641f67cf7a8627609b02df2996072a88489d6.
- This is code + automated contract validation, not yet physical iPhone Safari screenshot testing or confirmation of latest Render HEAD.


## 2026-10-10 — Personal dated plans and Cloud API
- Added personal_plans.py owner-browser-authenticated GET/POST/PATCH/DELETE /api/owner-plans with validation, owner-scoped parameterized queries and cross-site request checks.
- Added owner_plans table and index. Every write needs a direct user action; no automatic alerts or external account changes.
- /api/personal-briefing shows pending owner plans; _memory_context includes only plan titles, dates and times, deliberately omitting private notes.
- iPhone HAFIZA create/list/done/undo/delete UI, confirmation-gated delete, separate refresh; PWA static asset cache v45.
- Added offline, real PostgreSQL tenant-isolation and Node UI regressions, wired into both GitHub Actions workflows; final CI and Render must be verified separately before announcing success.


## 2026-10-10 — Life planner reschedule/edit increment
- Implemented plan PUT endpoint with shared strict field validation and user_id-bound SQL. Existing done/delete paths unchanged; missing or other-owner plan returns 404.
- iPhone owner's existing plan now offers DÜZENLE, DEĞİŞİKLİKLERİ KAYDET and DÜZENLEMEYİ İPTAL ET, preserving entries on failed network save. PWA cache v46.
- Extended Python offline and disposable PostgreSQL lifecycle tests and Node UI regression contracts. CI / Render current commit confirmation required; actual devices not tested.


## 2026-10-10 — Delivered opt-in .ics export
- Added ultron/cloud_service/personal_calendar_ics.py with bounded RFC5545 UTF-8 folding, reserved-char escaping, opaque stable UID, calendar timestamps and explicit DST-safe UTC conversion. Private owner notes excluded.
- Registered authenticated, no-store GET /api/owner-plans/calendar.ics in personal_plans.py with user_id-scoped SQL and a strict IANA timezone allowlist, only outstanding plans.
- HAFIZA owner-plans.js and index.html now expose timezone selector (Europe/Istanbul / Asia/Nicosia / UTC) plus explicit download button. No background export and no third-party calendar authorization. No push notifications.
- Automated Python offline test_personal_calendar_ics.py, extended disposable PostgreSQL test_personal_plans_postgres.py, and Node test_owner_plans_ui.cjs. Cloud Queue PostgreSQL Integration #38034057983 SUCCESS, Scene Build Check #38034046409 SUCCESS (code/test SHA 74162f6). Render confirmed export UI SHA 74162f6 live. Current docs-only or workflow-only HEAD can be ahead; distinguish deployment proof of working code from HEAD deployment proof.
- This session had no access to the user's real iPhone/Windows hardware, so Safari file-download/import and native Apple Calendar appearance are not verified.

## 2026-10-10 — Reviewable ULTRON learning / memory deletion
- Added approved_learning.py, learning_proposals PostgreSQL table with pending-only unique index, and web-session-only owner-scoped APIs for create/list/review/delete. Explicit approval uses an atomic PostgreSQL transaction and INSERT memories ON CONFLICT DO NOTHING (existing memories are not silently overwritten). Rejection never saves memory.
- iPhone HAFIZA now shows İZİNLİ ÖĞRENME panel for user-proposed preference/goal/project/fact/device records. No automatic extraction, polling or hidden memory writes; only the owner tapping ONAYLA can approve.
- Added a separate confirmation-gated HAFIZADAN SİL control to shared memory entries to revoke learned information; deleting the proposal itself does not delete a previously approved memory.
- Tests: offline validators, disposable PostgreSQL cross-owner consent/privacy/duplicate/conflict scenarios, and mobile Node safe DOM/explicit-click tests wired to Cloud and Scene CI. No native device or LLM quality claims.
- The ten-capability readiness API now reports available reviewed learning but honestly marks general autonomous learning only partial.

## 2026-10-10 — Opt-in auto-learning implementation
- Implemented auto_learning.py with default-off owner_auto_learning PostgreSQL table and authenticated GET/PUT /api/auto-learning (JSON + same-origin write). An atomic FOR UPDATE check guards writes against switch-off races.
- Supports deterministic high-confidence owner-declared preference/goal/project chat statements, normalizes and hashes per-value key, and INSERT ... ON CONFLICT DO NOTHING so existing memories are never silently overwritten. Excludes common secrets, sensitive phrases, emails, long numbers, URLs, control chars and multiline requests.
- Attached to accepted /api/chat (Gemini) and /api/local-chat (Windows Qwen bridge). No network model extractor, background observer, assistant-message learning or unrestricted continuous retraining.
- Added HAFIZA one-click status fetch followed by explicit confirmation to enable, reversible OFF and honest scope/exclusions text; PWA shell v48.
- Added offline Python extraction/owner-scope tests, disposable PostgreSQL on/off/cross-owner/no-overwrite tests and Node manual-toggle tests. Wired GitHub CI; statuses verified separately. iPhone/Windows real hardware not tested.


## 2026-10-10 — Command-first mobile + laptop UX
- Added pure mobile static/panel-intents.js and React panelIntent.ts with Turkish/English recognized requests and strict standalone command verbs; normal questions like "Dünya kaç yaşında?" must stay in chat.
- PWA index.html: original WORLD map remains in iframe but never prominently exposed. All five/six tab buttons only appear via tiny ⋯ menu; natural speech transcripts and typed messages routed through handlePanelIntent. New optional Hologram Lab screen-only CSS 3D ring energy preview; no third-party assets.
- Desktop Dashboard: voice-first class hides large nav/footer/system rail/redundant right panels by default, retains chat+CenterStage+mic+Menu. React HologramLab and Earth accessible by exact command; handles new native voice-log commands.
- CI tests added for iOS typed/Live words and no accidental question interception, desktop command parser and minimalist CSS; existing WORLD legacy test updated for new handlePanelIntent chain. Focus on low-cost GPU.
- Old scene CI failing because tests assumed direct worldVoiceIntent(heard) and naive "aç" substring matched "kaç"; patched actual intent routing/whole-word grammar. Need confirm exact final CI SHA and Render deployed code before reporting verified.


## 2026-10-10 — Implemented fully automatic brain route in minimal mobile UI
- Added static/auto-brain.js (select devices, safeToFallback verified 409 desktop_offline only) and PWA service worker cache v50.
- index.html removes the entire brain-picker row, unused CSS and old saved manual model preference; reads authenticated device presence on login, before chat submission, on voice tap, via existing 5s laptop heartbeat and on reactivation. Keeps a short re-check cache / deduplicated in-flight check; no extra microphone permission prompts on load.
- A connected, heartbeat-online Windows ULTRON gets first chance at local Ollama/Qwen. Otherwise Gemini Cloud chat. Local /api/local-chat rechecks heartbeat before creating queue task; only pre-queue desktop_offline permits resending to Gemini. If queued local later times out, the error is shown rather than risking double answer. Current live voice session is not automatically interrupted to switch providers.
- Kept microphone, attachment, message send controls; replaced provider text with generic speech status. If browser STT unsupported, Gemini Live can be offered after a direct microphone tap (existing permission requirements still apply). No silent mic start.
- Updated old local voice and bridge tests to new auto selection contract. Added test_auto_brain.cjs in Scene CI for owner-scoped heartbeat, safe fallback, no picker, JS syntax, privacy conditions. Must still verify final exact HEAD GitHub CI/Render; real device test not possible here.


## 2026-10-10 — More natural ULTRON personality and real turn history
- Added conversation_turns.py: strict user_id + conversation_id query, prior-only id exclusion, latest-first bounded turns (14–20 max) and explicit Ollama/Gemini role mapping that never promotes saved history to the system role.
- app.py /api/chat: current message id returned and excluded from history; Gemini gets structured Content user/model turns; read-only status prevents false tool claims. Shared /api/live-voice request initializes history only for the relevant voice session.
- local_brain_bridge.py: user-scoped thread history in queued, read-only local_brain payload; conversation owner-bound INSERT ON CONFLICT ... WHERE ..., preventing malicious reused UUID. mark_app.py passes only the text turns to local_cloud_brain.local_chat; no desktop dangerous tools or extra network providers.
- integration/local_cloud_brain.py uses conversation_turns.ollama_messages and moderate bounded sampling for less robotic Qwen replies while retaining configured provider and installed-model selection.
- conversation_persona.py now specifically instructs pronoun resolution, short casual tone and fewer formulaic honorifics, no repetitive follow-up questions, transparent limitations and respectful correction.
- Regression suite test_conversation_turns.py, test_conversation_turns_postgres.py and test_local_dialogue_runtime.py added to Cloud CI. Latest code SHA dddbb7338c0689aa20fc0d708abfd5433d6646c6 is awaiting final Scene/Render verification. Native hardware and live model sample dialogues still NOT tested here.


## 2026-10-10 — Natural dialogue continued, Windows deferred
- Added classify_reply_mode, classify_dialogue_act and dialogue_guidance to conversation_persona.py. Dynamic response hints now match explicit request for short vs detailed explanations, same-topic followups, or corrected misunderstanding.
- Changed Cloud Gemini /api/chat and local Qwen bridge to set has_prior_turns=bool(real_thread_turns), not truthy placeholder strings; Gemini Live uses existing session-scoped recent context presence. No new data source or cross-session tracking.
- Hardening in conversation_turns.py ignores malformed/non-text history records instead of permitting invalid roles/content to derail conversation generation. Maintains bounded newest-first user/assistant turn history.
- Added offline test_conversation_style.py with realistic Turkish/English user utterances, history/no-history followups, seriousness/corrections and malicious history structure checks. Wired into Cloud Queue PostgreSQL Integration persona-policy job. Native Windows installation deliberately deferred.
- Cloud CI/Render must be confirmed on exact functional code SHA. Real Qwen/Gemini model subjective quality tests and Windows local updates remain outstanding.


## 2026-10-10 — Delivered topic-aware contextual recall
- Added _topic_terms, select_contextual_turns, load_contextual_thread_turns in conversation_turns.py. Directly stated salient topics can retrieve a small set of older messages within the exact same owner/conversation; pronoun-only turns use normal latest history.
- Updated app.py /api/chat and local_brain_bridge.py /api/local-chat to use this bounded selection. More natural continuity for very long threads without introducing another model call, autonomous memory writes or new platform dependencies.
- Changed old thread-contract checks to assert the new helper. Added test_contextual_recall.py and expanded disposable PostgreSQL test_conversation_turns_postgres.py for earlier same-thread recall, no current-turn duplication and cross-owner/cross-conversation denial. Cloud CI workflow runs the new tests.
- After code/test commit 8c25b3db4186d7e62bac465b6bbe8693af55a298: Cloud Queue PostgreSQL Integration 38057407803 SUCCESS, ULTRON Scene Build Check 38057407812 SUCCESS, Render deployment dep-db546815efls73a9o7cg LIVE. Real Gemini/Qwen spoken quality and iPhone/Windows device acceptance NOT independently verified.
- Requested persistent hourly development automation now enabled with explicit instructions not to install/download Windows files until the user chooses a final release; each hourly execution must still independently verify permissions and CI.


## 2026-10-10 — Read-only conversation recap for natural dialogues
- Added is_thread_recap_request() and select_recap_turns() in conversation_turns.py. Exact owner request only; samples from start / midpoint / latest messages in order with capped char and role budgets. load_contextual_thread_turns() detects recap commands and fetches at most 80 scoped prior user/assistant messages, honoring before_id, instead of only recent history.
- conversation_persona.py adds THREAD RECAP guidance to avoid hallucinating omitted discussion, and to state when thread has no prior messages.
- Both Gemini Cloud and queued Windows Qwen already use load_contextual_thread_turns; no new dispatch, model provider, microphone behavior, API endpoint, file write, database table, or visible UI change.
- Added test_thread_recap.py: exact command detection vs incidental summarization, chronological beginning-middle-end, caps, invalid/system-role rejection, no missing-context invention, scoped SQL and current-message exclusion.
- Expanded real PostgreSQL test_conversation_turns_postgres.py with cross-owner/cross-thread privacy and older-summary detection. CI wired in cloud-queue-postgres.yml.
- Code da9f6e76049953e88ae91b17104018bb9bdc6613 verified Render live; tests 8ffd9983cc1fc077745f3c5ed257b9f224553b8f verified Scene+PostgreSQL CI successes; workflow-only commit ef474b66ad9009871aa4dae7126223ee363ebe6c Cloud CI success. Actual mobile Safari / Gemini and local Qwen live answers not tested in this session.


## 2026-10-10 — Conversation-notes implementation and verification
- Added ultron/cloud_service/conversation_notes.py with explicit owner-only preview/list/create/edit/delete REST endpoints. Preview uses bounded same-thread excerpts, avoids common secrets and never saves; actual persistence requires direct Save from owner.
- Added conversation_notes table in schema.sql (conversation FK ON DELETE CASCADE, owner indexes). Registered routes in app.py. The notes table is intentionally NOT read by _memory_context or sent to Gemini/Qwen prompts.
- New static/conversation-notes.js creates a safe textContent-based editor/list under HAFIZA. Typed or voice "Sohbet notu hazırla" opens editable preview on demand; "Notlarımı göster" opens current conversation's notes. No extra home controls. sw.js v51 precaches the module.
- Added Python validators and preview safety tests (test_conversation_notes.py), disposable PostgreSQL consent/ACL/edit/delete/no-memory tests (test_conversation_notes_postgres.py), Node mobile preview/save/edit/safe-DOM tests (test_conversation_notes_ui.cjs). Wired GitHub Cloud Queue and Scene workflows.
- Fixed stale test_auto_brain.cjs PWA-version assertion after v51 cache bump (pinning v50 previously caused Scene CI failure).
- Final functional/test SHA a1afc4befbdfbd84fc52e3b0511aebdba675bed8: Cloud Queue PostgreSQL Integration #38061837383 SUCCESS, Scene Build Check #38061837381 SUCCESS, Render deploy dep-db555toae00c739bvqn0 LIVE. No real iPhone Safari, microphone or Windows hardware tests completed.


## 2026-10-10 — Fixed mobile Gemini Live end-of-answer clipping
- Created static/live-playback.js with generation-scoped pending audio counters, turnComplete() (drain rather than cut), enqueue()/idempotent finish() and cancel() invalidating stale completion events.
- index.html player registers every AudioBufferSourceNode with queue; audio onended removes and retires its entry, while normal turn_complete keeps already scheduled buffers running. Listening status returns after the last chunk. stopPlayback for real barge-in, server-interrupted, microphone stop, socket close and single-speaker desktop handoff still cancels immediately.
- service worker moved to v52 to precache Live playback helper. No additional home UI button or audible double TTS, no new account/provider/storage.
- New test_live_playback.cjs verifies normal end -> full drain, interruption -> invalidation, empty response -> no audio lock, late duplicate ended event safety, server/UI hook correctness, and microphone owner protection. Added to ULTRON Scene Build Check.
- Intermediate Scene workflow #38065262849 failed because UMD helper used a module variable shadowing Node's module.exports; fixed in final code commit b431b82314c4b27fee7c1cf7b2d96e5b27a51acf. Final Cloud Queue PostgreSQL Integration #38065354266 SUCCESS, Scene Build Check #38065354265 SUCCESS, Render dep-db55ubl9mjac73899sl0 LIVE at same SHA.
- No real iPhone Safari microphone, real-time Gemini audio API or paired Windows physical tests have been conducted. Laptop installation remains deferred.


## 2026-10-10 — One speaker per ULTRON voice turn
- Added static/speaker-policy.js pure decision functions for desktop eligibility and phone Live/local Qwen mic priority; only genuine boolean heartbeat fields grant desktop output.
- PWA index.html now blocks speakRemoteResult browser TTS while desktop is speaker leader; setDesktopVoiceLeader cancels WebAudio/browser TTS and clears remoteResultSpeaking after output handoff. watchDesktopPresence uses monotonic sequence to ignore stale out-of-order async responses and includes localVoiceController.active() as phone priority. Local voice onState takes phone priority immediately on explicit tap.
- PWA service worker cache advanced to v53 to precache speaker-policy.js; main minimal UI untouched.
- Added test_speaker_policy.cjs with no provider: online/unmuted actual speaker, invalid/stale statuses, phone Live or local microphone priority, no duplicate TTS, handoff cancellation, out-of-order presence safety and inline JS/PWA registration.
- Updated old test_live_playback.cjs to accept versioned PWA service-worker names and wired new Node speaker tests to Scene Build Check. Latest code/test SHA 4952ea5a6a44c041aebf5d87e21ce2184ad3e48d; Cloud CI and Scene CI SUCCESS (see tests doc).
- Windows laptop installation deferred at user request. Latest Render deployment must be checked for live separately. Real physical iPhone/Windows sound ownership NOT verified by browser/static CI.


## 2026-10-10 — Tap-to-interrupt stale phone Qwen voice reply
- Added static/voice-turn-guard.js, a tiny generation-token gate for browser local speech recognition completions and later model replies. A second explicit mic tap, typed new turn, voice mute, pagehide or app background invalidates the prior token.
- Mobile index.html now cancels browser SpeechSynthesis BEFORE starting/restarting a local mic; onTranscript associates a distinct token with send(true,voiceToken). The local/cloud response is still appended to chat, but audio is only played when the original voice turn remains current and the app is visible. No automatic cancellation or unsafe replay of an accepted desktop queue task.
- sw.js advanced v53 -> v54 to precache voice-turn-guard.js; no new visible panels, model picker, or automatic mic startup.
- test_voice_turn_guard.cjs checks cancellation and new-generation fencing, invalid tokens, pending text-vs-audio separation, mute/background cleanup, and PWA JavaScript syntax. Scene Build Check runs this module. A stale old test_local_voice.cjs assertion expected await send(true) without the new voice token; fixed to assert await send(true,voiceToken).
- Final code/test commit 70991ff6610e2cac631a2c1ec91d856588aa0cab: Cloud Queue PostgreSQL Integration #38066919827 SUCCESS and Scene Build Check #38066919837 SUCCESS. Render deploy dep-db5697jhu5js73djph4g was update_in_progress when checked; confirm live before saying deployed. No physical iPhone or Windows voice tests performed; Windows install remains deferred.


## 2026-10-10 — Relevant owner memory and higher-quality text routing
- Added ultron/cloud_service/personal_context_focus.py with select_personal_context and async load_focused_owner_context; owner-scoped PostgreSQL query fetches only saved memories and unfinished plans (never private plan notes or separate conversation-notes table). Plan and preference information survives long unrelated fact histories, with topical overlap ranking and 3400-character cap.
- app.py _memory_context delegates to helper, Gemini /api/chat passes current user text, and local_brain_bridge.py passes current Qwen prompt to the same helper. No manual brain picker or visible new UI; both models retain the established role-separated turns.
- Extended ultron/backend/app/core/fast_brain.py complexity recognition for explicitly detailed comparisons, logical reasoning and in-depth analyses; chooses already-installed 8B reasoning over 4B conversation model when requested, preserving low-cost FAST on ordinary chat and existing installed-model validation.
- Offline test_personal_context_focus.py covers 96 irrelevant facts plus one old C180 project, persistent Turkish reply preference, dated plan priority, owner note exclusion and strict 64–3400 char caps; routing tests verify deep request selects 8B and greetings 4B when available.
- Disposable PostgreSQL test_personal_context_focus_postgres.py verifies actual owner-scoped memory + event retrieval; foreign user memories, private notes and other-account plans stay excluded.
- Updated refactor-aware test_personal_plans.py and test_approved_learning.py to verify actual standalone helper, not obsolete SQL source positions. Latest functional/test commit a6ce694ff35423f93a386140c7e1938a374ad162 passed Cloud Queue PostgreSQL Integration #38068020642 and Scene Build Check #38068020631. Exact Render promotion still needs checking; no actual live Gemini model conversational rating or Windows 8B speed measured.


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

The suggestion panel is live in Render at `a0352a5`; Cloud/PostgreSQL and Scene/UI workflows passed for that exact merge SHA.


Release verification: merge commit `bd09410034d369093b87430e61737cd6e9fbff1e` contains the self-development routing and PR flow. Cloud/PostgreSQL Actions `38430065807`, Scene/UI `38430065886`, and WORLD smoke `38430065957` all **SUCCESS**; workflow logs inspected. Render deployment `dep-db75lruq1p3s73f2eorg` is **LIVE** and `/health` confirms exact SHA `bd09410`. This verifies the Cloud routing and repository checks. The Windows app has not been installed, and GÖLGE's own laptop `gh auth status`, actual branch push, and draft PR have not been tested.
## 2026-10-13 — Cloud image creation and upload continuity

Fixed uploaded photo analysis creating an unrelated conversation: `/api/vision` accepts the active conversation ID, includes its bounded prior turns, validates ownership, and returns message IDs so the UI does not duplicate server-saved messages. Follow-ups that refer to visible image content resend the in-memory image to Gemini. Added authenticated `/api/image/generate` for real Gemini image creation/editing and inline display; the client does not retain uploaded images beyond the current page session or persist image bytes. Actual Gemini image-model availability has not been tested.
## 2026-10-13 — Image output improvements

Added mobile-friendly download/save for generated and edited results, page-close cleanup for object URLs, incremental upload size checks, and output MIME/size validation. The Gemini SDK response extraction has a provider-free fake response test, including rejection of unsupported SVG output. No live Gemini call or uploaded-photo persistence was added.

## 2026-10-13 — GÖLGE self-development approval safety

- Chat approvals now require a standalone explicit command; ordinary sentences containing “uygula” or “approve” cannot run a code patch. Turkish dotless-i normalization is covered. If several proposals are waiting, the owner must include the exact proposal ID; wrong IDs leave code untouched. Reject/apply responses keep the next pending proposal visible.
- Added approval-routing regression tests and wired them into Scene CI, with bridge/publisher Python compilation. Local tests: 2 approval-routing tests PASS; existing publisher tests are also checked with pytest.
- This keeps code changes behind the existing local approval gate and continues to open draft PRs only; it does not merge or deploy from GÖLGE. Laptop `gh` authentication and physical draft-PR operation remain unverified.

## 2026-10-13 — Image request isolation and self-development path fencing

- Gemini image generation now checks an existing conversation's owner before invoking the provider and creates/touches conversation history only after successful image generation. This prevents cross-owner provider calls and empty ghost conversations after provider failures. Added tests for both cases.
- GÖLGE's code proposal path check now uses resolved path ancestry rather than a string prefix; a sibling directory named `ULTRON-private` can no longer appear to be inside the project. Regression was confirmed failing before the fix and passing after it. Approval routing remains exact-command/ID bound.
- Cloud and Scene Actions now include the relevant image and desktop path-boundary tests. Full Cloud discovery: **306 passed, 58 skipped**. Pytest codegen/publisher: **11 passed**; approval-routing unittest **2 passed**; path-boundary unittest **1 passed**; image UI intent and mobile chat tests passed.
- Code changes are local and awaiting commit/push and exact-SHA CI/Render verification. Live Gemini generation and physical phone/laptop interactions remain unverified.

- CI follow-up: the first Cloud run exposed a missing `asyncpg` dependency in the lightweight persona-policy job. Added `asyncpg` and `google-genai`; corrected Cloud run #38437032742 passed for workflow/docs SHA `7f959972a2ab581aec464b8695ebaa16b5737f64`, including the new image test. Scene #38436800737 and WORLD smoke #38436800759 passed for code SHA `54f91bbb5e061c2eb79a5ae53daca653fc55bdef`.
- Render deployment `dep-db76d1bm8hqs73fe8spg` is LIVE at code SHA `54f91bb`; `/health` returned HTTP 200 with the same commit and configured database/Gemini/auth fields. This config check does not prove an actual image-model request succeeds. Windows and phone provider-backed tests remain pending.

## 2026-10-13 — Bounded GÖLGE code proposals

- Expanded the self-development gate: patches above 12 files, 128 KiB per file or 512 KiB total are rejected before approval; duplicate normalized paths and protected security-core files are rejected; project scope uses resolved path ancestry. Four regressions were first shown failing, then passed after the validator was added.
- This is a limit on generated proposals, not a change to owner approval, sandboxing, test-before-apply, rollback or draft-only PR behavior.
- Local validation: path-boundary suite **4 passed**, codegen pipeline and PR publisher **11 passed**, approval router **2 passed**, Python compilation and diff whitespace check passed. Scene Action [38437781712](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38437781712) passed for code SHA `4112b3ca99c850c8e286dc087002a968788c5cd7`. Render remains correctly on Cloud SHA `54f91bb`; this desktop-only change is not part of the Render service.

## 2026-10-14 — Memory Engine V3 and Verified Research V3 (draft work)

- Started from production SHA `0b2315a77d657361821ae728814ba3506a79b309` on isolated branch `feat/golge-memory-research-v3-20261014`; PR #30–#32 code remains the base. Render was verified LIVE at that exact SHA before work began. No production merge or deploy was performed.
- Cloud personal-memory corrections now use an additive PostgreSQL `memory_history` table. Owner/key-scoped transaction locks serialize writes; identical values are idempotent; superseded values are timestamped and appear only on explicit history requests; delete purges current and historical rows. The voice `save_memory` tool now uses the same writer. Legacy credential-like current/history values are filtered from model context, and proposal writes reject them.
- Added owner-scoped `GET /api/memories/{key}/history`. The migration creates a new table/indexes without rewriting existing memories. Historical versions begin accumulating from V3 updates; older overwritten values cannot be reconstructed.
- The existing research engine now reads a bounded number of public HTML/plain-text pages using pinned public DNS addresses, per-redirect validation, strict protocol/port/content/size/time limits, no forwarded credentials, no page scripts, and bounded text extraction. Search snippets remain discovery metadata only. Cloud and desktop explicit research intents share this reader; ordinary chat does not search and no second model call was added. Web text is passed as labelled untrusted data and never saved as user memory.
- A conservative lexical/number overlap audit labels possible sentence-to-excerpt matches. It is not semantic entailment, independent corroboration, or a factual truth oracle; output says so. PDF and semantic verification are not implemented.
- Full local tests: backend **1,141 passed, 3 skipped**; Cloud **354 passed, 7 skipped**, including the new correction/history/privacy tests against disposable PostgreSQL 16. Skips: real Windows audio/screen, missing wake-word key, parser fixture, and seven unrelated listening tests needing their own isolated DB. No real device or provider calls were made.
- Extended PR #30 continuation paging: new 500-continuation target/correction regression failed before the fix (old code stopped before the original goal), then passed with a bounded 1,200-message same-owner/thread scan. Existing 100-continuation behavior remains covered; ordinary prompts and model context budgets are unchanged. Targeted continuity/context/PostgreSQL suite: **51 passed, 16 subtests passed**.
- Deterministic 100-scenario TR/EN memory/research harness: **101 passed** (100 cases plus suite validation). Provider-backed Gemini/Qwen quality and live web research: **NOT_RUN**. Benchmark fixture: existing 98-record memory selection p50/p95 **0.3708/0.5109 ms** before vs **0.7471/0.9088 ms** after; fake three-page research core **0.0683/0.1036 ms**. Normal-chat provider latency and live network latency were not measured.
- Functional code commit: `d95b64640381ae4a519024f767560892e20270a4`; Actions wiring commit: `698190a94ac8f8a471cc91dc481cac59d0f71ea5`; project tracking docs are committed separately.
- Exact final feature/workflow commit `698190a94ac8f8a471cc91dc481cac59d0f71ea5` passed all three GitHub checks: [Cloud/PostgreSQL #38555225630](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225630), [Scene #38555225647](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225647), and [Local Qwen Listening #38555225690](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38555225690). The hosted checks include the new 500-continuation test, research/evaluation contracts (112 passed), and real PostgreSQL owner-memory versioning/isolation/purge (8 passed). Draft [PR #33](https://github.com/fatmakahraman304-hash/ULTRON/pull/33) remains unmerged.
- After pushing the feature branch, Render deployment `dep-db7lkuavcj2c73e8hb70` remained **LIVE** at production SHA `0b2315a77d657361821ae728814ba3506a79b309`; `https://ultron-yubh.onrender.com/health` returned HTTP 200 with that exact SHA and production branch. No deploy or merge was started.
## 2026-10-15 — Windows START syncs frontend lockfile dependencies

- Startup failure was reproduced from the owner's report: TypeScript could not resolve `leaflet` after the production pull. The production lockfile contains Leaflet, but `START.bat`'s bootstrap only ran `npm ci` when `node_modules` was absent, leaving an older dependency tree in place.
- `scripts/bootstrap.ps1` now hashes `package-lock.json`, compares the hash with a local marker under ignored `node_modules`, and runs `npm ci --no-audit --no-fund` before rebuilding if dependencies are missing or stale. The marker is written only after successful installation; source-only rebuilds avoid reinstalling packages.
- Added a startup dependency-sync contract regression test and wired it to Scene Build CI. Linux code-level test does not execute PowerShell or the Windows desktop; exact Windows validation still requires running `START.bat` on the laptop after pulling this fix.
- Immediate recovery on the current laptop is `cd /d "%USERPROFILE%\ULTRON-3a6f489\ultron\frontend" && npm ci`, then return to the repo root and rerun `START.bat`.
## 2026-10-15 — Windows backend startup import path

- The owner's backend log identified a real startup failure: `merged_api.py` raised `ModuleNotFoundError: No module named 'ultron'` because the launcher started `server.py` from `ultron/backend` while `PYTHONPATH` only contained that backend folder.
- `integration/launcher.py` now prepends both repository root and backend to the child runtime's `PYTHONPATH`, preserving and deduplicating existing entries. Added a regression that imports the exact `ultron.cloud_service.conversation_persona` module from the backend working directory.
- Baseline reproduction failed with `ModuleNotFoundError`; post-fix subprocess regressions **2 passed**, prior startup-import regressions **4 passed**, Python compile and diff checks passed. Owner's Qwen/Render doctor passed 3/3; physical desktop startup must still be repeated after pulling the fix.
- Follow-up Windows log after the temporary root `PYTHONPATH` confirms backend health succeeds, then `mark_app.py:52` fails with `No module named 'memory.memory_manager'; 'memory' is not a package`. Root cause is desktop Python resolving backend `memory.py` before the desktop `memory/` package. The memory package import is now moved before UI imports; safe-path subprocess and source-order regressions bring the focused suite to **8 passed**.

## 2026-10-15 — PR #34/#35 rebase on current production candidate

- User authorized merging outstanding PRs. PR #35's Evidence V4 changes were first merged into its dependency branch; Memory V4 + Evidence V4 are now being synchronized against current production to resolve tracking-workflow conflicts before production merge.
- Reconciliation keeps the current production UI/startup workflow and adds its Earth, removed-preset, frontend-lock, and Python-launcher CI checks alongside Evidence V4 tests. User-facing app/API code conflicts are not being discarded.
- Hosted tests must rerun on the synchronized head before production merge. Real iPhone/Windows usage and live provider research remain separate device/provider verification.

## 2026-10-15 — PR #34 review findings addressed

- Added bounded, explicit 1–365 day recall windows so accepted retrospective phrases always apply their requested time bounds; unsupported ranges remain ordinary chat.
- Excluded English `for` and Turkish `hakkında` from mandatory lexical groups; added regression tests for both languages and date limits.
- Real disposable-PostgreSQL episodic API/security suite: **13 passed**. Evidence engine and 100-case evaluation: **109 passed**. Python compilation passed.
- All four resume documents now record V4 implementation, exact test evidence, limits, and the next merge step. The GitHub review's stale V4 next-task note is addressed in the branch tracking files.

## 2026-10-15 — PR #36 dependency synchronization

- Current production UI, Earth view, launcher fixes, and CI checks are preserved while the request-scoped interruption state from PR #36/#37 is retained.
- PR #37 true interruption changes merged into this dependency branch at 61f3e02; synchronize and validate before production merge.

## 2026-10-15 — PR #4 synchronized with current production

- Retained local-Qwen thinking-only fallback while merging the latest production interruption changes. Regression tests: recovery 5 passed; local brain 7 passed; Python compilation passed. Actual model inference remains device-dependent.
## 2026-10-16 — Cloud Qwen CI dependency correction

- PR #4's exact-head `local-qwen-safety` workflow failed before tests because it imported the Cloud bridge without installing `aiohttp`. Added the declared runtime dependency to that focused workflow; other jobs remain unchanged.
- Live desktop import-path correction PR #51 is already merged into production at `c66b5dae`; current production has advanced through PR #36 and PR #34.

## 2026-10-15 — PR #5 synchronized with current production

- The current bounded owner/thread paging implementation preserves the original goal and latest correction across bare continuations. Disposable-PostgreSQL conversation suites passed **27/27** on the preceding synchronized base; rerun exact-head CI after this production merge.

## 2026-10-15 — PR #36 production merge and PR #34 resync

- PR #36/#37 merged to production at squash SHA `378e3b3e6c36b81306e0a9383a18aa84ae4d00a4`; all seven exact-head GitHub Actions checks passed. Render deploy SHA remains subject to a separate health/deploy check.
- PR #34/#35 was rebased by a merge commit onto the new production SHA. Cloud API test discovery against disposable PostgreSQL: **387 passed, 7 skipped**. The latest GitHub Actions must validate the synchronized exact head before PR #34 can merge.
## 2026-10-16 — GÖLGE görünür ad temizliği

- Masaüstü video oynatma bildirimleri, mobil sohbet notu uyarısı, eski masaüstü API hata/panel metinleri ve masaüstü/bulut health yanıtlarındaki ürün etiketi GÖLGE olarak düzenlendi. Ses sahipliği durumu eski `mark` ayarından gelirse dış yanıtta nötr `desktop` olarak verilir.
- `ultron_name` ayarının değeri GÖLGE yapıldı; anahtar geriye dönük ayar uyumluluğu için korundu.
- Yerel Qwen sistem yönergesi, persona düzeltme yönergesi ve otomatik görev raporu kimliği GÖLGE olarak değişti. Zorunlu “Boss” hitabı kaldırıldı. Yeni yerel konuşma mesajları GÖLGE rolüyle kaydediliyor; eski ULTRON etiketli satırlar geçmiş bağlamında okunmaya devam ediyor.
- Yerel TTS hazır mesajı, bağlantı/izin hata metinleri ve süreç sağlık/başlangıç etiketleri GÖLGE adını kullanıyor.
- Sohbet/hafıza kayıtları, kullanıcı dosyaları ve depolama anahtarları silinmedi. `X-MARK-Token`, `X-ULTRON-DEVICE`, localStorage adları ve özel ULTRON wake-model dosyası değiştirilmedi; bunlar protokol veya kurulu kullanıcı verisi uyumluluğu taşıyor.
- Bu dal: `codex/golge-brand-cleanup`, başlangıç üretim SHA `f88eec1`. Üretime merge/deploy yapılmadı.
## 2026-10-16 — Manual GÖLGE checks: interruption, weather, satellite and file picker

- Owner-run Windows session exposed four product failures: spoken “Dur” did not stop TTS (ESC did); an unavailable licensed satellite layer was followed by contradictory success wording; live weather values appeared in the Earth panel but were not reported in chat; native file selection did not send selected file contents into the vision/document routes.
- Added exact Turkish stop-command routing in the React chat/native Qt bridge and fixed the Cloud Live final-transcript path so it stops queued audio regardless of whether a typed-chat request is active. Local Qwen/provider generation is cancelled only through existing cancellation path; Cloud Live output suppression does not claim to stop remote Gemini generation.
- The satellite command variants route to the existing licensed-layer availability gate. Weather chat replies are now composed from the returned provider temperature, wind, source and timestamp and explicitly label forecast data.
- Native Qt file picker now allows only supported image/document suffixes, enforces the existing 8 MiB cap and sends bytes to the existing authenticated image/document API. The selected filename/preview and real analysis/extraction result or error are shown; no file is silently called “loaded”.
- Local verification: frontend build PASS; frontend Node tests 40/40 PASS; Cloud JavaScript tests 167/167 PASS; focused desktop voice/file Python tests 3/3 PASS; Earth layer/geocoding tests 5/5 PASS; Python compile PASS. Exact-head Actions for the first fix commit passed all seven checks; a follow-up made typed “Dur” bypass the busy composer lock and is awaiting its own CI run. No real Windows retest was possible from this runner. Image vision may still report unavailable if the local vision model is not installed; selection and this limitation are surfaced honestly.
- Work is isolated on `fix/golge-manual-test-failures`, based on production `b4086aa`; no PR merge or Render deployment was performed. Exact Windows verification after pulling this branch remains required.


## 2026-10-21 — Phone assistant stack: what changed in the repo

New modules in `ultron/cloud_service/`: instant_skills, phone_skills, knowledge_skills, reminders (repeat rules), plan_skills, memory_skills, calendar_feed, proactive, web_push, alert_skills, smart_home, missions, laptop_bridge, infra, http_client, ops. New static scripts: assistant-extras.js, laptop-bridge.js, mission-watch.js; service worker cache `ultron-shell-v81` with push + notificationclick handlers. Schema additions are idempotent (`owner_reminders`, `push_*`, `owner_notifications`, `owner_prefs`, `owner_alerts`, `missions`, `owner_calendar_feeds`).
Existing code touched: `app.py` (chat intercepts, middlewares, startup tasks, routes), `world_api.py` and `local_brain_bridge.py` (shared client; cloud-skill hand-back), `capability_readiness.py` (details only), brand strings in laptop/desktop Python files.
Dependency added: `cryptography` (cloud_service/requirements.txt).

## 2026-10-21 — Context-aware follow-ups (`followups.py`)
Skill replies are stored with `device_id = 'golge-skill:<skill>'`. A very short, explicitly marked follow-up ("peki yarın?", "ya Londra?", "ya euro?", "peki spor?") right after such a reply is rewritten into the full request and re-routed; the local-Qwen endpoint hands such follow-ups to `/api/chat`. Tests: `test_followups.py` (4 passed); suite 492 passed, 9 skipped (non-PG). Not run against a real phone.

## 2026-10-21 — Lists and timers
`list_skills.py` ("alışveriş listesine süt, ekmek ve yumurta ekle", "alışveriş listem", "ekmek … listesinden çıkar", "… listesini temizle", "listelerim"; table `owner_list_items`, key folded + original label) and timer phrases in `reminders.py` ("10 dakika zamanlayıcı kur"). Router corpus now 307 utterances (0 chat hijacked). Real-PostgreSQL stack test: 7 passed. Suite: 497 passed, 9 skipped (non-PG).

## 2026-10-21 — Expense log
`expense_skills.py` ("150 lira market harcaması ekle", "bugün kahveye 80 tl harcadım", "bu ay/hafta/bugün/dün/geçen ay ne kadar harcadım", "son harcamayı sil"; table `owner_expenses`, TRY only; included in `/api/export`). Router corpus 320 utterances, 0 chat hijacked; real-PostgreSQL stack test 8 passed; suite 501 passed, 9 skipped (non-PG).

## 2026-10-21 — Birthdays/yearly reminders and habit log
`birthday_skills.py` ("Murat'ın doğum günü 3 Mart" → two yearly reminders: eve 19:00 + day 09:00; Turkish vowel-harmony genitive; `reminders.py` gained `yearly:MM-DD`, 29 Feb handled; DB CHECK migrated). `habit_skills.py` (water/sleep/exercise/steps/weight/mood log, daily/weekly summaries with targets; table `owner_habits`; also in `/api/export`). Router corpus 353 utterances (0/144 chat hijacked); real-PostgreSQL stack test 9 passed (incl. constraint migration); suite 516 passed, 9 skipped (non-PG).

## 2026-10-21 — Navigation, focus, schedule intelligence, severe weather
`nav_skills.py` (directions / "yakınımda eczane" / traffic as prefilled Apple+Google Maps links; only real place categories; phone location optional), `focus_skills.py` (pomodoro = two reminders, cancellable), `plan_skills.py` (+ clash warning when adding a plan, "yarın ne zaman boşum" free-slot finder, plans assumed 1 h, calendar events included), `proactive.weather_alerts` (rain + thunderstorm + gusts ≥60 km/h + heat ≥37 °C + cold ≤-3 °C within 3 h, once per day per kind). Router corpus 383 utterances (0/158 chat hijacked); real-PostgreSQL stack test 10 passed; suite 530 passed, 9 skipped (non-PG). CI lint list extended; `followups.py` unused import fixed.

## 2026-10-21 — Style, recall, voice skill gateway, feedback loop
New modules `style_skills.py`, `recall_skills.py`, `voice_skills.py`, `feedback_skills.py`, `feedback_to_corpus.py`; schema tables `skill_usage`, `skill_feedback`; `instant_reply` gained `allow` (restrict writing skills) and `history` (previous exchange); `/api/chat` records usage, passes feedback history and appends the owner's style to the system instruction; live voice declares `golge_skill` and appends style; `/api/feedback` (thumbs, owner-scoped message lookup). `proactive.set_pref` merges unknown keys (style/suggested survive); new `get_extra/set_extra`. Live-voice prompt budget test raised 2600→3000 chars for the SKILLS/SPEAKING block. Fixed a test-pollution bug: `test_reminders_calendar.MemorySkills` monkeypatched `memory_skills.upsert_owner_memory` for the rest of the process (now restored via addCleanup). No UI for thumbs buttons yet (chat commands + endpoint only).

## 2026-10-21 — Utilities and feedback buttons
`utility_skills.py` (no model/network): yazı-tura, zar (≤10 zar, 2–1000 yüzlü), rastgele sayı, "seç: a, b, c", "N gün/hafta/ay/yıl sonra/önce hangi gün", iki tarih arası gün, "X hangi gün", yaş hesabı, VKİ (tıbbi değil uyarısıyla), bahşiş ve hesap bölüşme. `static/assistant-extras.js`: 👍/👎 under assistant messages that exist in the cloud → `POST /api/feedback`; service-worker cache `ultron-shell-v82` (tests updated). Corpus +18 cases incl. ordinary-chat negatives.

## 2026-10-21 — Richer morning briefing
`answer_briefing` greets with the owner's chosen name (style) instead of "efendim", and adds a "🔁 Dün" recap (habits logged yesterday + yesterday's spending). Today's reminders were already in the agenda block, so no duplicate section. Real-PostgreSQL test added; 566 passed in `ultron/cloud_service`.

## 2026-10-21 — Journal
`journal_skills.py` + table `owner_journal`: "günlüğe yaz: …" / "günlük: …", "günlüğüm", "bugünkü/dünkü/bu haftaki/geçen haftaki günlüğüm", "günlüğümde X geçenler", "son günlük kaydını sil"; secrets refused; allowed through the voice gateway; included in `/api/export`. Real-PostgreSQL test added; corpus +10.

## 2026-10-21 — Double-click desktop launcher
`GOLGE.vbs` (hidden-console launcher: checks `.venv`, offers a one-time visible `INSTALL.bat`, runs `scripts\bootstrap.ps1 -Mode start` with output appended to `logs\golge-baslat.log`, offers to open the log on a non-zero exit) and `GOLGE_KISAYOL_KUR.vbs` (creates Desktop + Start Menu "GÖLGE" shortcuts with `config\ultron.ico`; Startup shortcut only if the owner answers Yes). ASCII-only VBScript (Turkish letters via `ChrW`), `.gitattributes` keeps CRLF. START.bat/INSTALL.bat unchanged. Static contract test `tests/test_desktop_launcher.py`. Documented in `QUICK_START_TR.md`.

## 2026-10-21 — Hologram: any shape on request (phone + laptop)
`shape_library.py`: 45 deterministic generators (kalp, yıldız, DNA, ev, ağaç, kardan adam, robot, roket, araba, masa, sandalye, merdiven, atom, güneş sistemi, satürn, dünya, uçak, çiçek, kale, köprü, kule, Eyfel, gemi, dişli, saat, piyon, laptop, telefon, kitap, mum, lamba, fincan, mantar, elmas, kum saati, spiral/galaksi, …) producing the existing validated primitive schema (≤24 parts, no colour field). Counts parameterise shapes ("8 köşeli yıldız", "12 basamaklı merdiven"); two or three nouns are combined side by side ("bir ev ve ağaç"). `POST /api/scene-design` now tries the library first (`source:"library"`, no model call, works offline), then Gemini (`source:"model"`). `ultron/frontend/src/spatial/intents.ts` (shared by the phone bundle and the laptop HologramLab): "bana bir kalp çiz", "masa oluştur" (no "model" word needed for library shapes) and "hologramda <anything> göster" (any description, goes to library/model); `static/scene-control.js` + `scene-intents.js` rebuilt with `scripts/build_scene_browser.mjs`. Python test keeps the TS noun list in sync with the catalogue. Rendered 30 shapes with real three.js/Chromium (software GL) and fixed the unrecognisable ones (heart, atom, solar system, earth). Changed existing expectations: `masa oluştur` is now a design intent without an active scene; the scene-design API test uses an unknown noun for the model path.

## 2026-10-21 — Memory: correct, history, recent
`memory_skills.py`: "düzelt: <kelime> => <yeni değer>" (unique match only, secrets refused, old value archived in `memory_history`), "hafızada X notumun geçmişi / X kaydımın eski hali / hafızada X eskiden neydi" (previous versions). `recall_skills.py`: "son notlarım", "son 3 kayıt", "bugün/dün/bu hafta ne kaydettim". Generic "X'in geçmişi" is deliberately NOT intercepted. Real-PostgreSQL test added; routing corpus now 446/446, hijacked chat 0/178.

## 2026-10-21 — Weekly review
`weekly_skills.py`: "haftalık özet / geçen hafta nasıldı / bu haftanın özeti" → plans done/total, habit totals/averages, spending with top category, journal entries, fired reminders, most-used skills; sections with no data are omitted and an empty week says so. Read-only (also available through the voice gateway). Real-PostgreSQL test; corpus 453/453, hijacked chat 0/180.

## 2026-10-21 — Weekly review notification
New pref `weekly_review` (default off): "haftalık özet bildirimi aç/kapat"; proactive rule `weekly_review` sends the weekly review on Sunday 19:00–22:00 (Istanbul), once per date key, only when the week has recorded data; listed in "bildirim ayarlarım". Real-PostgreSQL test covers default-off, Sunday window, empty-week skip, Saturday skip and toggling.

## 2026-10-21 — Budget, streaks, birthday countdown, "nerede kalmıştık"
`expense_skills.py`: "aylık bütçem 15000 tl" (stored in `owner_prefs.budget`, survives other pref changes), every expense reply shows month total / budget / %/ remaining with warnings at ≥80 % and over budget, "bütçe durumu", "bütçeyi kaldır". `habit_skills.py`: "su/spor/uyku/adım serim", "serilerim" (consecutive days; yesterday counts while today is empty). `birthday_skills.py`: "Ahmet'in doğum gününe kaç gün var". `recall_skills.py`: "nerede kalmıştık / en son ne konuştuk" (last three of the owner's messages). Real-PostgreSQL tests added; corpus 470/470, hijacked chat 0/184.

## 2026-10-21 — Shape library reaches every hologram path
Found while reading `static/index.html`: with local Qwen preferred, the phone used `/api/local-scene-design` and would have bypassed the library; the laptop proxy (`ultron/backend/scene_design_api.py`) also went straight to the model. Now: `POST /api/scene-library` (library-only lookup, `design:null` when unknown) is asked first by `generateSceneDesign()`; `scene_design_api.design_request` answers known shapes locally (works offline, no cloud/model). SW cache `ultron-shell-v84`. Tests: `test_scene_library_ui.cjs`, API tests, `ultron/backend/tests/test_scene_design_library.py` (run it separately from the cloud suite — both define a module called `app`).

## 2026-10-21 — Independent review of the new skills: findings fixed
A read-only reviewer agent reproduced 20 issues; fixed (each with a regression test in `test_style_recall_feedback.py::test_review_regressions` or `test_shape_library.py`):
- **Voice**: smart home was reachable through `golge_skill` (now gated by `allow`); spoken delete/cancel/forget requests are refused ("yazarak söylersen yaparım"); over-long utterances are refused instead of silently truncated.
- **Birthdays**: removal/countdown no longer build a `LIKE` from user text (`%`/`_` wildcards and "Ali" matching "Alişan" are gone; exact label match in Python); 1 March's eve reminder uses 28 Feb.
- **False positives**: journal and memory writes need an explicit command (`günlüğe yaz:` / `hatırla:`; "Unutma, yarın…" and "Günlük, haftalık…" are ordinary chat); style name/address/tone patterns are anchored ("Annem bana … diye seslendi", "Sen de", "Ciddi konuşuyorum" no longer change the persona).
- **Data**: weekly review uses Turkish number format and Istanbul-date bucketing; the weekly push body no longer shows amounts on the lock screen; `set_pref` is now a jsonb merge of only the changed keys (no lost update of style/budget); feedback stores no secrets, de-duplicates, and rejects out-of-range ids; "son su kaydını sil" removes only water; a question about the weekly notification reports instead of toggling.
- **Misc**: absurd birth years no longer raise; "kum saati"/"sarmal merdiven"/"uzay aracı" build one shape; dead non-folded regex branches fixed; history dates in Istanbul time.
Not changed: older `_CORRECT` quadratic whitespace backtracking (bounded by the 220/1,200 input caps).

## 2026-10-21 — Spoken hologram requests; feature level list
Live voice can now show a shape: `control_phone_ui` accepts `action=hologram` (query ≤100 chars, required), the PWA turns it into `hologramda <shape> göster` → shape library / model; one line added to the voice policy (still < 3000 chars); SW cache v85. New `GOLGE_OZELLIK_SEVIYELERI.md`: every phone and laptop feature with an evidence-based level (S0–S4) and an explicit list of what was never run on a real device.

## 2026-10-21 — Capability-gap backlog and thinking guide
`gap_skills.py` + `capability_gaps`: GÖLGE records what it could not do (model inability phrases → `auto` gaps with a one-line hint; "eksik: …" by the owner), lists them, and "eksik N'i geliştir" creates a `dev_requests` row (AGENTS.md rules embedded) and, with an online laptop, a laptop task that asks only for a patch PROPOSAL (no writes without the owner's approval). Voice can list/add but never build. Chat system instruction gained `THINKING_GUIDE` (step-by-step reasoning, assumptions, runnable code, honest limits, never claim self-modification). Approval gate, audit, SelfCodeBoundary and PR-only flow untouched. Export includes gaps. Real-PostgreSQL test covers the whole flow; corpus 488/488, hijacked chat 0/190.

## 2026-10-21 — Calculator toolbox and personal ledgers
`calc_skills.py` (pure, offline, 30 commands): loan instalment, compound interest, VAT add/split, discount, % change, fuel cost; list sum/average/median/min/max, primes, prime factors, factorial, EBOB/EKOK, Fibonacci, number words, Roman numerals both ways, binary/hex/octal; text tools (Turkish upper/lower, reverse, counts, palindrome), Base64, Morse, hex↔rgb; bedtime from wake time, week/day of year, business days, next fixed public holiday, zodiac and Chinese zodiac, running pace, calorie estimate (not advice), recipe scaling, kitchen conversions, time zones. `ledger_skills.py` + 5 tables: contacts, debts, goals, stopwatch time log, fuel log (20 commands). Voice may use both (deleting stays typed). Real-PostgreSQL ledger test, 30-command unit test, routing corpus 535/535 with 0/200 hijacked chat messages.
