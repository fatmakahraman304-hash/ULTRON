/* ULTRON FREE VOICE (PWA).
 * Explicit user tap -> browser speech recognizer (if supported) ->
 * owner's authenticated /api/local-chat -> paired Windows Ollama ->
 * existing browser speechSynthesis. No Gemini Live connection or paid API.
 *
 * SpeechRecognition engine availability and whether the browser sends audio
 * to its provider depend on Safari/OS. It is NOT guaranteed offline/private
 * STT. For fully local transcription use the Windows Whisper pipeline.
 */
(function(global, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (global) global.ULTRONLocalVoice = api;
})(typeof window !== "undefined" ? window : null, function() {
  "use strict";

  function create(options) {
    const opt = options || {};
    const host = opt.host || (typeof window !== "undefined" ? window : {});
    const Constructor = host.SpeechRecognition || host.webkitSpeechRecognition;
    const report = typeof opt.onState === "function" ? opt.onState : function() {};
    const onError = typeof opt.onError === "function" ? opt.onError : function() {};
    const onTranscript = typeof opt.onTranscript === "function" ? opt.onTranscript : function() {};
    let recognition = null, state = "idle", generation = 0, processed = false;

    function update(next) {
      if (next !== state) {
        state = next;
        report(next);
      }
    }
    function supported() { return typeof Constructor === "function"; }
    function active() { return state !== "idle"; }
    function stop() {
      generation++;
      const prev = recognition;
      recognition = null;
      if (prev) {
        prev.onresult = null;
        prev.onerror = null;
        prev.onend = null;
        prev.onstart = null;
        try { prev.abort(); } catch (_) {}
      }
      processed = false;
      update("idle");
    }
    function start() {
      if (state !== "idle") return false;
      if (!supported()) {
        onError("Bu tarayıcıda konuşmayı yazıya çevirme desteği yok. Metinle ücretsiz Qwen'i kullanabilirsin; Gemini'ye otomatik geçilmeyecek.");
        return false;
      }
      const token = ++generation;
      processed = false;
      const instance = new Constructor();
      recognition = instance;
      instance.lang = "tr-TR";
      instance.continuous = false;  // one tap/one utterance; no always-on mic
      instance.interimResults = false;
      instance.maxAlternatives = 1;
      instance.onstart = function() {
        if (token === generation) update("listening");
      };
      instance.onresult = function(event) {
        if (token !== generation || processed) return;
        const results = event && event.results;
        let text = "";
        if (results) {
          for (let i = 0; i < results.length; i++) {
            const item = results[i];
            if (item && item[0] && item.isFinal !== false) {
              text += String(item[0].transcript || "") + " ";
            }
          }
        }
        text = text.trim().slice(0, 3000);
        if (!text) return;
        processed = true;
        update("processing");
        Promise.resolve().then(function() {
          if (token === generation) return onTranscript(text);
        }).catch(function(error) {
          if (token === generation) onError(
            "Yerel sesli soru tamamlanamadı: " + String(error && error.message || error).slice(0, 180)
          );
        }).finally(function() {
          if (token === generation) {
            recognition = null;
            update("idle");
          }
        });
        try { instance.stop(); } catch (_) {}
      };
      instance.onerror = function(event) {
        if (token !== generation || processed) return;
        const kind = String(event && event.error || "");
        const message = kind === "not-allowed" || kind === "service-not-allowed"
          ? "Mikrofon veya konuşma tanıma izni reddedildi."
          : kind === "no-speech"
          ? "Ses algılanmadı, mikrofona yeniden dokun."
          : "Tarayıcı konuşmayı tanıyamadı (" + (kind || "hata") + "). Metinle devam edebilirsin.";
        stop();
        onError(message);
      };
      instance.onend = function() {
        if (token === generation && !processed) {
          recognition = null;
          update("idle");
        }
      };
      update("starting");
      try { instance.start(); return true; }
      catch (error) {
        stop();
        onError("Tarayıcı mikrofonu başlatamadı: " + String(error && error.message || error).slice(0, 160));
        return false;
      }
    }
    function toggle() { return active() ? (stop(), false) : start(); }
    return { supported, active, start, stop, toggle, get state() { return state; } };
  }
  return { create };
});
