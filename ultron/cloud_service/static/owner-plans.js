/* ULTRON manual planning UI: all writes follow user interaction.
 * This is NOT Google/Apple Calendar sync or a scheduled push notification.
 */
(function(global, factory) {
  "use strict";
  const value = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = value;
  if (global) global.ULTRONOwnerPlans = value;
})(typeof window !== "undefined" ? window : null, function() {
  "use strict";
  function create(options) {
    const opt = options || {};
    const doc = opt.document || (typeof document !== "undefined" ? document : null);
    const api = opt.fetchJson;
    const ask = opt.confirmDelete || (typeof window !== "undefined" ? text => window.confirm(text) : () => false);
    if (!doc || typeof api !== "function") throw Error("document_and_fetchJson_required");
    const el = id => doc.getElementById(id);
    let busy = false, editingId = null;
    function resetEditor() {
      editingId = null;
      for (const id of ["planTitle","planDate","planTime","planNote"]) el(id).value = "";
      el("saveOwnerPlan").textContent = "PLANI KAYDET";
      el("cancelPlanEdit").classList.add("hidden");
    }
    function beginEdit(plan) {
      const id = Number(plan.id);
      if (busy || !Number.isSafeInteger(id) || id <= 0) return;
      editingId = id;
      el("planTitle").value = String(plan.title || "").slice(0, 140);
      el("planDate").value = String(plan.scheduled_date || "").slice(0, 10);
      el("planTime").value = String(plan.scheduled_time || "").slice(0, 5);
      el("planNote").value = String(plan.note || "").slice(0, 500);
      el("saveOwnerPlan").textContent = "DEĞİŞİKLİKLERİ KAYDET";
      el("cancelPlanEdit").classList.remove("hidden");
      el("ownerPlansStatus").textContent = "Plan düzenleniyor. Değişiklikler yalnızca kaydettiğinde uygulanır.";
      el("planTitle").focus();
    }

    function itemElement(p) {
      const row = doc.createElement("div");
      row.className = "memory";
      const title = doc.createElement("b");
      title.textContent = String(p.title || "").slice(0, 140);
      const detail = doc.createElement("div");
      const date = String(p.scheduled_date || "").slice(0, 10);
      const time = p.scheduled_time ? " " + String(p.scheduled_time).slice(0, 5) : "";
      detail.textContent = date + time + (p.note ? " • " + String(p.note).slice(0, 500) : "");
      const state = doc.createElement("small");
      state.textContent = p.is_done ? "Tamamlandı • ULTRON planı" : "Planlandı • bildirim kurulmadı";
      const controls = doc.createElement("div");
      controls.className = "row";
      const edit = doc.createElement("button");
      edit.type = "button";
      edit.className = "secondary";
      edit.textContent = "DÜZENLE";
      edit.addEventListener("click", () => beginEdit(p));
      const done = doc.createElement("button");
      done.type = "button";
      done.className = "secondary";
      done.textContent = p.is_done ? "GERİ AL" : "TAMAMLANDI";
      done.addEventListener("click", () => mutate(p.id, "PATCH", {is_done: !p.is_done}));
      const remove = doc.createElement("button");
      remove.type = "button";
      remove.className = "secondary";
      remove.textContent = "SİL";
      remove.addEventListener("click", () => {
        if (ask("Bu ULTRON planını kalıcı olarak silmek istiyor musun?")) return mutate(p.id, "DELETE");
      });
      controls.append(edit, done, remove);
      row.append(title, detail, state, controls);
      return row;
    }

    async function refresh() {
      const button = el("refreshOwnerPlans"), status = el("ownerPlansStatus");
      if (busy) return;
      busy = true; button.disabled = true; status.textContent = "Planların yükleniyor…";
      try {
        const result = await api("/api/owner-plans");
        const plans = Array.isArray(result.plans) ? result.plans.slice(0, 100) : [];
        const list = el("ownerPlansList"); list.replaceChildren();
        plans.forEach(p => list.appendChild(itemElement(p)));
        status.textContent = plans.length
          ? plans.length + " kişisel plan • takvim senkronizasyonu veya bildirim aktif değil"
          : "Henüz kişisel planın yok. Tarih ve başlık seçip kaydedebilirsin.";
      } catch (e) {
        status.textContent = "Planlar alınamadı: " + String(e.message || e).slice(0, 120);
      } finally { busy = false; button.disabled = false; }
    }

    async function mutate(id, method, body) {
      if (busy) return;
      const valid = Number.isSafeInteger(Number(id)) && Number(id) > 0;
      if (!valid) return;
      busy = true;
      let changed = false;
      try {
        await api("/api/owner-plans/" + encodeURIComponent(String(id)), {
          method,
          ...(body ? {body: JSON.stringify(body)} : {})
        });
        changed = true;
        if (method === "DELETE" && editingId === Number(id)) resetEditor();
      } catch (e) {
        el("ownerPlansStatus").textContent = "Plan güncellenemedi: " + String(e.message || e).slice(0, 120);
      } finally { busy = false; }
      if (changed) await refresh();
    }

    async function save() {
      if (busy) return;
      const title = el("planTitle").value.trim();
      const date = el("planDate").value;
      const time = el("planTime").value;
      const note = el("planNote").value.trim();
      if (!title || !date) {
        el("ownerPlansStatus").textContent = "Plan başlığı ve tarihi gerekli.";
        return;
      }
      busy = true;
      const button = el("saveOwnerPlan");
      button.disabled = true;
      let saved = false;
      try {
        const update = editingId !== null;
        const path = update ? "/api/owner-plans/" + encodeURIComponent(String(editingId)) : "/api/owner-plans";
        await api(path, {
          method: update ? "PUT" : "POST",
          body: JSON.stringify({title, date, time, note})
        });
        resetEditor();
        saved = true;
      } catch (e) {
        el("ownerPlansStatus").textContent = "Plan kaydedilemedi: " + String(e.message || e).slice(0, 120);
      } finally {
        busy = false;
        button.disabled = false;
      }
      if (saved) await refresh();
    }

    function init() {
      if (!el("refreshOwnerPlans") || !el("saveOwnerPlan")) return false;
      el("refreshOwnerPlans").addEventListener("click", refresh);
      el("saveOwnerPlan").addEventListener("click", save);
      el("cancelPlanEdit").addEventListener("click", () => {
        if (busy) return;
        resetEditor();
        el("ownerPlansStatus").textContent = "Düzenleme iptal edildi. Kayıt değiştirilmedi.";
      });
      return true;
    }
    return {init, refresh, save};
  }
  return {create};
});
