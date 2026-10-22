/* GÖLGE phone → laptop chat bridge (client side).
 * mayRoute() is only a cheap prefilter; the server decides and may answer
 * {routed:false}. Results come from the laptop itself and are rendered with
 * textContent through the host page's addMessage.
 */
(function(global, factory) {
  "use strict";
  const value = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = value;
  if (global) global.ULTRONLaptopBridge = value;
})(typeof window !== "undefined" ? window : null, function() {
  "use strict";
  const HINT = /(laptop|bilgisayar|\bpc\b|masa[uü]st[uü]|ekran)/i;
  const POLL_MS = 3000, POLL_LIMIT = 100; // ≈ 5 minutes
  function mayRoute(text) { return HINT.test(String(text || "")) && String(text).length <= 4000; }

  function create(options) {
    const opt = options || {};
    const api = opt.fetchJson;
    if (typeof api !== "function") throw Error("fetchJson_required");
    const addMessage = opt.addMessage || (() => ({}));
    const speak = opt.speak || (() => {});
    const toast = opt.toast || (() => {});
    const sleep = opt.sleep || (ms => new Promise(r => setTimeout(r, ms)));

    async function watch(taskId, conversationId) {
      for (let i = 0; i < POLL_LIMIT; i++) {
        await sleep(POLL_MS);
        let result;
        try { result = await api("/api/laptop-task/" + encodeURIComponent(taskId) +
                                 "?conversation_id=" + encodeURIComponent(conversationId)); }
        catch (_) { continue; }
        if (result.status === "pending") continue;
        if (result.delivered) {
          addMessage("assistant", result.reply, {id: result.assistant_message_id});
          toast(result.status === "completed" ? "Laptop görevi tamamlandı." : "Laptop görevi başarısız.");
          speak(result.reply);
        }
        return result.status;
      }
      toast("Laptop görevi hâlâ sürüyor; UZAKTAN sekmesinden izleyebilirsin.");
      return "timeout";
    }

    /** Returns null when the message is normal chat, else the routed result. */
    async function route(text, state) {
      if (!mayRoute(text)) return null;
      const result = await api("/api/laptop-task", {method: "POST", timeoutMs: 60000,
        body: JSON.stringify({message: text, conversation_id: state?.conversationId || undefined})});
      if (!result || !result.routed) return null;
      if (opt.onConversation) opt.onConversation(result.conversation_id);
      addMessage("assistant", result.reply, {id: result.assistant_message_id});
      if (result.status === "completed") speak(result.reply);
      if (result.status === "pending" && result.task_id) watch(result.task_id, result.conversation_id);
      return result;
    }
    return {route, watch};
  }
  return {create, mayRoute};
});
