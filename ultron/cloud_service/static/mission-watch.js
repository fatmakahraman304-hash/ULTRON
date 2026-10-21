/* GÖLGE missions (client): follow a "görev: …" run and show the final report once. */
(function(global, factory) {
  "use strict";
  const value = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = value;
  if (global) global.ULTRONMissionWatch = value;
})(typeof window !== "undefined" ? window : null, function() {
  "use strict";
  const POLL_MS = 3000, POLL_LIMIT = 120; // ≈ 6 minutes
  const ICON = {pending: "·", running: "…", done: "✓", failed: "✗", skipped: "↷"};

  function create(options) {
    const opt = options || {};
    const api = opt.fetchJson;
    if (typeof api !== "function") throw Error("fetchJson_required");
    const addMessage = opt.addMessage || (() => ({}));
    const toast = opt.toast || (() => {});
    const speak = opt.speak || (() => {});
    const sleep = opt.sleep || (ms => new Promise(r => setTimeout(r, ms)));

    async function watch(missionId, conversationId) {
      let lastLine = "";
      for (let i = 0; i < POLL_LIMIT; i++) {
        await sleep(POLL_MS);
        let m;
        try { m = await api("/api/mission/" + encodeURIComponent(missionId) +
                            "?conversation_id=" + encodeURIComponent(conversationId || "")); }
        catch (_) { continue; }
        const steps = Array.isArray(m.steps) ? m.steps : [];
        const line = steps.map(s => (ICON[s.status] || "·") + s.id).join(" ");
        if (line && line !== lastLine && m.status === "running") { lastLine = line; toast("Görev: " + line); }
        if (m.status === "done" || m.status === "failed") {
          if (m.delivered) {
            addMessage("assistant", m.report, {id: m.assistant_message_id});
            speak(m.report);
          }
          return m.status;
        }
        if (m.status === "cancelled") { toast("Görev iptal edildi."); return "cancelled"; }
      }
      toast("Görev hâlâ sürüyor; birazdan sohbeti yenile.");
      return "timeout";
    }
    return {watch};
  }
  return {create};
});
