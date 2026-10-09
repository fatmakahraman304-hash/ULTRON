/* ULTRON Mobile: user-invoked, read-only owner briefing and capability display.
 * No automatic polling, microphone, permissions, storage writes or device actions.
 * All cloud-sourced text is displayed with textContent (never innerHTML).
 */
(function(global, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (global) global.ULTRONPersonalPanel = api;
})(typeof window !== "undefined" ? window : null, function() {
  "use strict";
  const STATUS = Object.freeze({
    available_in_code: "Kod mevcut",
    partial: "Kısmen mevcut",
    blocked_hardware: "Donanım gerekiyor",
    requires_native_setup: "iOS kurulumu gerekiyor",
    requires_device_test: "Cihaz testi gerekli",
    requires_approval: "Kullanıcı onayı gerekli",
    requires_provider: "Hesap entegrasyonu gerekli",
    requires_devices: "Bağlı cihaz gerekiyor",
  });
  function clean(value, limit) {
    return String(value == null ? "" : value).trim().slice(0, limit);
  }
  function briefingEntries(payload) {
    const manual = (Array.isArray(payload && payload.plans) ? payload.plans : [])
      .slice(0, 8)
      .filter(p => p && p.source === "owner_created_plan")
      .map(p => ({
        title: clean(p.title, 140),
        category: "PLAN",
        detail: clean(p.date, 10) + (p.time ? " " + clean(p.time, 5) : ""),
        source: "ULTRON kişisel planı",
      }))
      .filter(p => p.title);
    const stored = (Array.isArray(payload && payload.items) ? payload.items : [])
      .slice(0, 12)
      .map(x => ({
        title: clean(x && x.key, 100),
        category: clean(x && x.category, 50),
        detail: clean(x && x.value, 300),
        source: x && x.source === "owner_saved_memory" ? "ULTRON hafızası" : "Kaynak doğrulanmadı",
      }))
      .filter(x => x.title && x.detail);
    return [...manual, ...stored].slice(0, 12);
  }
  function capabilityEntries(payload) {
    return (Array.isArray(payload && payload.capabilities) ? payload.capabilities : [])
      .slice(0, 15)
      .map(x => ({
        title: clean(x && x.name, 100),
        status: STATUS[x && x.status] || "Durum doğrulanmadı",
        detail: clean(x && x.detail, 500),
      }))
      .filter(x => x.title);
  }
  function renderEntries(doc, holder, entries) {
    holder.replaceChildren();
    entries.forEach(item => {
      const card = doc.createElement("div");
      card.className = "memory";
      const title = doc.createElement("b");
      title.textContent = item.title;
      const body = doc.createElement("div");
      body.textContent = item.detail;
      const note = doc.createElement("small");
      note.textContent = item.status || ((item.category ? "[" + item.category + "] • " : "") + item.source);
      card.append(title, body, note);
      holder.appendChild(card);
    });
  }
  function create(options) {
    const opt = options || {};
    const doc = opt.document || (typeof document !== "undefined" ? document : null);
    const fetchJson = opt.fetchJson;
    if (!doc || typeof fetchJson !== "function") throw Error("document_and_fetchJson_required");
    const find = id => doc.getElementById(id);
    let briefingPending = false, readinessPending = false;
    async function loadBriefing() {
      if (briefingPending) return;
      briefingPending = true;
      const button = find("refreshBriefing"), status = find("briefingStatus");
      button.disabled = true;
      status.textContent = "Kayıtlı hafıza okunuyor…";
      try {
        const payload = await fetchJson("/api/personal-briefing");
        const entries = briefingEntries(payload);
        renderEntries(doc, find("briefingItems"), entries);
        status.textContent = entries.length
          ? entries.length + " kayıtlı bilgi • yalnızca ULTRON hafızası"
          : "Henüz kayıtlı bilgi yok. Aşağıdaki hafıza alanına bir hedef ekleyebilirsin.";
      } catch (err) {
        status.textContent = "Özet getirilemedi: " + clean(err && err.message, 160);
      } finally { briefingPending = false; button.disabled = false; }
    }
    async function loadReadiness() {
      if (readinessPending) return;
      readinessPending = true;
      const button = find("refreshReadiness"), status = find("readinessStatus");
      button.disabled = true;
      status.textContent = "Bağlı cihaz ve yetenek durumu kontrol ediliyor…";
      try {
        const payload = await fetchJson("/api/capability-readiness");
        const entries = capabilityEntries(payload);
        renderEntries(doc, find("readinessItems"), entries);
        status.textContent = (payload.desktop_online ? "Windows bağlı" : "Windows çevrimdışı") +
          " • cihaz yetenekleri ve dağıtım ayrı doğrulama gerektirir";
      } catch (err) {
        status.textContent = "Yetenek durumu getirilemedi: " + clean(err && err.message, 160);
      } finally { readinessPending = false; button.disabled = false; }
    }
    function init() {
      const briefButton = find("refreshBriefing"), readyButton = find("refreshReadiness");
      if (!briefButton || !readyButton) return false;
      briefButton.addEventListener("click", loadBriefing);
      readyButton.addEventListener("click", loadReadiness);
      return true;
    }
    return {init, loadBriefing, loadReadiness};
  }
  return {create, briefingEntries, capabilityEntries};
});
