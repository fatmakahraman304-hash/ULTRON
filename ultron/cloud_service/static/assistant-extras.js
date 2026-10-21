/* GÖLGE assistant extras: in-app reminder delivery + read-only iCal calendar link.
 * Reminders fire only while this page/app is open (no server-side OS push).
 * The secret calendar address is sent once to the server and never shown again.
 */
(function(global, factory) {
  "use strict";
  const value = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = value;
  if (global) global.ULTRONAssistantExtras = value;
})(typeof window !== "undefined" ? window : null, function() {
  "use strict";
  const POLL_MS = 20000;
  const FEED_ERRORS = {
    invalid_url: "Adres geçersiz görünüyor.",
    https_only: "Yalnızca https:// (veya webcal://) adresleri kabul edilir.",
    host_not_allowed: "Bu site desteklenmiyor. Google, iCloud, Outlook, Fastmail veya Proton takvim adresi gir.",
    feed_unavailable: "Takvim adresine ulaşılamadı. Adresi kontrol et.",
    not_ical: "Bu adres bir iCal (.ics) takvimi değil.",
    feed_too_large: "Takvim dosyası çok büyük.",
  };

  function create(options) {
    const opt = options || {};
    const doc = opt.document || (typeof document !== "undefined" ? document : null);
    const api = opt.fetchJson;
    if (!doc || typeof api !== "function") throw Error("document_and_fetchJson_required");
    const toast = opt.toast || (() => {});
    const speak = opt.speak || (() => {});
    const win = opt.window || (typeof window !== "undefined" ? window : {});
    let timer = null, polling = false;

    function notify(title, body) {
      try {
        if (win.Notification && win.Notification.permission === "granted") new win.Notification(title, {body, tag: "golge-reminder"});
      } catch (_) { /* notifications are best effort */ }
      try { win.navigator?.vibrate?.([200, 100, 200]); } catch (_) {}
    }

    function banner(item) {
      const host = doc.getElementById("reminderBanners");
      if (!host) return;
      const box = doc.createElement("div");
      box.className = "panel";
      box.setAttribute("role", "alert");
      box.style.cssText = "margin:8px 0;border:1px solid var(--neon,#ff2447)";
      const title = doc.createElement("b");
      title.textContent = item.late ? "⏰ Kaçırdığın hatırlatıcı" : "⏰ Hatırlatıcı";
      const text = doc.createElement("div");
      text.textContent = String(item.text || "").slice(0, 200);
      const row = doc.createElement("div");
      row.className = "row";
      row.style.marginTop = "8px";
      const ok = doc.createElement("button");
      ok.type = "button"; ok.textContent = "TAMAM";
      ok.addEventListener("click", () => box.remove());
      const snooze = doc.createElement("button");
      snooze.type = "button"; snooze.className = "secondary"; snooze.textContent = "10 DK ERTELE";
      snooze.addEventListener("click", async () => {
        snooze.disabled = true;
        try {
          await api("/api/reminders/" + encodeURIComponent(item.id) + "/snooze",
            {method: "POST", body: JSON.stringify({minutes: 10})});
          toast("10 dakika sonra tekrar hatırlatacağım.");
          box.remove();
        } catch (_) { snooze.disabled = false; toast("Erteleme başarısız."); }
      });
      row.append(ok, snooze);
      box.append(title, text, row);
      host.prepend(box);
    }

    async function poll() {
      if (polling) return 0;
      polling = true;
      try {
        const result = await api("/api/reminders/due");
        const due = Array.isArray(result?.due) ? result.due : [];
        for (const item of due) {
          banner(item);
          notify("GÖLGE hatırlatıcı", String(item.text || ""));
          speak("Hatırlatıcı: " + String(item.text || ""), true);
        }
        return due.length;
      } catch (_) {
        return 0; // offline or signed out: try again next tick
      } finally { polling = false; }
    }

    function startPolling() {
      if (timer) return;
      timer = setInterval(() => { if (!doc.hidden) poll(); }, POLL_MS);
      doc.addEventListener?.("visibilitychange", () => { if (!doc.hidden) poll(); });
      poll();
    }

    // ── calendar feed panel ──
    const el = id => doc.getElementById(id);
    function setStatus(text) { const s = el("calendarFeedStatus"); if (s) s.textContent = text; }

    async function refreshFeed() {
      try {
        const st = await api("/api/calendar-feed");
        setStatus(st.connected ? "Bağlı takvim: " + String(st.host || "").slice(0, 80) + " (salt okunur)"
                               : "Takvim bağlı değil.");
        const rm = el("calendarFeedDisconnect");
        if (rm) rm.classList.toggle("hidden", !st.connected);
      } catch (_) { setStatus("Takvim durumu okunamadı."); }
    }

    async function connectFeed() {
      const input = el("calendarFeedUrl");
      const url = String(input?.value || "").trim();
      if (!url) return setStatus("Önce gizli iCal adresini yapıştır.");
      setStatus("Takvim doğrulanıyor…");
      try {
        const result = await api("/api/calendar-feed", {method: "PUT", body: JSON.stringify({url})});
        input.value = "";
        setStatus("Takvim bağlandı (" + String(result.host || "").slice(0, 80) + "). Önümüzdeki 30 günde " +
                  Number(result.upcoming_30_days || 0) + " etkinlik var. Artık “bugün programım ne” diye sorabilirsin.");
        el("calendarFeedDisconnect")?.classList.remove("hidden");
      } catch (err) {
        const code = String(err?.data?.error || err?.message || "");
        setStatus(FEED_ERRORS[code] || "Takvim bağlanamadı.");
      }
    }

    async function disconnectFeed() {
      try { await api("/api/calendar-feed", {method: "DELETE"}); } catch (_) { return setStatus("Bağlantı kaldırılamadı."); }
      setStatus("Takvim bağlantısı kaldırıldı.");
      el("calendarFeedDisconnect")?.classList.add("hidden");
    }

    function requestNotifications() {
      const N = win.Notification;
      if (!N) return toast("Bu tarayıcı bildirimleri desteklemiyor.");
      N.requestPermission().then(p => toast(p === "granted" ? "Bildirimler açıldı." : "Bildirim izni verilmedi."));
    }

    function init() {
      el("calendarFeedConnect")?.addEventListener("click", connectFeed);
      el("calendarFeedDisconnect")?.addEventListener("click", disconnectFeed);
      el("reminderNotifyPermission")?.addEventListener("click", requestNotifications);
      refreshFeed();
      startPolling();
    }

    return {init, poll, refreshFeed, connectFeed, disconnectFeed, banner};
  }
  return {create, FEED_ERRORS};
});
