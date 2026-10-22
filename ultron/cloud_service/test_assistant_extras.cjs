"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const extras = require("./static/assistant-extras.js");

function fakeDOM(ids) {
  class Node {
    constructor() { this.children = []; this.listeners = {}; this.textContent = ""; this.value = ""; this.style = {}; this.className = "";
      this.classList = {add: () => {}, remove: () => {}, toggle: () => {}}; this.attrs = {}; }
    append(...n) { this.children.push(...n); }
    prepend(n) { this.children.unshift(n); }
    remove() { this.removed = true; }
    setAttribute(k, v) { this.attrs[k] = v; }
    addEventListener(e, f) { this.listeners[e] = f; }
  }
  const elements = Object.fromEntries(ids.map(id => [id, new Node()]));
  return {document: {hidden: false, getElementById: id => elements[id] || null, createElement: () => new Node(),
                     addEventListener() {}}, elements};
}

test("due reminders are shown with textContent, spoken and notified once", async () => {
  const {document, elements} = fakeDOM(["reminderBanners"]);
  const spoken = [], notes = [];
  class N { constructor(t, o) { notes.push([t, o.body]); } static get permission() { return "granted"; } }
  const x = extras.create({document, window: {Notification: N}, speak: (t, f) => spoken.push([t, f]),
    fetchJson: async url => { assert.equal(url, "/api/reminders/due");
      return {due: [{id: 4, text: "<img src=x onerror=evil()>", late: false}]}; }});
  assert.equal(await x.poll(), 1);
  const banner = elements.reminderBanners.children[0];
  assert.equal(banner.children[1].textContent, "<img src=x onerror=evil()>");
  assert.deepEqual(spoken, [["Hatırlatıcı: <img src=x onerror=evil()>", true]]);
  assert.equal(notes.length, 1);
});

test("offline polling failure is silent and returns 0", async () => {
  const {document} = fakeDOM(["reminderBanners"]);
  const x = extras.create({document, fetchJson: async () => { throw Error("offline"); }});
  assert.equal(await x.poll(), 0);
});

test("calendar link is sent once, input cleared, URL never echoed back", async () => {
  const {document, elements} = fakeDOM(["calendarFeedUrl", "calendarFeedStatus", "calendarFeedDisconnect"]);
  const secret = "https://calendar.google.com/calendar/ical/a/private-SECRET/basic.ics";
  elements.calendarFeedUrl.value = secret;
  const calls = [];
  const x = extras.create({document, fetchJson: async (url, o) => { calls.push([url, o.method]);
    return {connected: true, host: "calendar.google.com", upcoming_30_days: 5}; }});
  await x.connectFeed();
  assert.deepEqual(calls, [["/api/calendar-feed", "PUT"]]);
  assert.equal(elements.calendarFeedUrl.value, "");
  assert.ok(!elements.calendarFeedStatus.textContent.includes("SECRET"));
  assert.match(elements.calendarFeedStatus.textContent, /5 etkinlik/);
});

test("calendar errors become friendly Turkish messages", async () => {
  const {document, elements} = fakeDOM(["calendarFeedUrl", "calendarFeedStatus"]);
  elements.calendarFeedUrl.value = "https://evil.com/x";
  const x = extras.create({document, fetchJson: async () => { const e = Error("x"); e.data = {error: "host_not_allowed"}; throw e; }});
  await x.connectFeed();
  assert.match(elements.calendarFeedStatus.textContent, /desteklenmiyor/);
});

test("enablePush asks permission, subscribes with the server key and registers the device", async () => {
  const {document} = fakeDOM(["reminderBanners"]);
  const calls = [], toasts = [];
  const sub = {toJSON: () => ({endpoint: "https://web.push.apple.com/x", keys: {p256dh: "a", auth: "b"}})};
  let subscribeOpts;
  const win = {
    atob: s => Buffer.from(s, "base64").toString("binary"),
    Notification: {requestPermission: async () => "granted", permission: "granted"},
    PushManager: {},
    navigator: {serviceWorker: {ready: Promise.resolve({pushManager: {subscribe: async o => { subscribeOpts = o; return sub; }}})}},
  };
  const x = extras.create({document, window: win, toast: t => toasts.push(t), fetchJson: async (url, o) => {
    calls.push([url, o && o.method]);
    return url === "/api/push/key" ? {public_key: "BAUG"} : {};
  }});
  assert.equal(await x.enablePush(), "subscribed");
  assert.deepEqual(calls.map(c => c[0]), ["/api/push/key", "/api/push/subscribe", "/api/push/test"]);
  assert.equal(subscribeOpts.userVisibleOnly, true);
  assert.ok(subscribeOpts.applicationServerKey instanceof Uint8Array);
});

test("enablePush explains how to install the PWA when push is unsupported or denied", async () => {
  const {document} = fakeDOM(["reminderBanners"]);
  const toasts = [];
  const none = extras.create({document, window: {}, toast: t => toasts.push(t), fetchJson: async () => ({})});
  assert.equal(await none.enablePush(), "unsupported");
  assert.match(toasts[0], /Ana Ekrana Ekle/);
  const denied = extras.create({document, toast: t => toasts.push(t), fetchJson: async () => { throw Error("no calls"); },
    window: {Notification: {requestPermission: async () => "denied"}, PushManager: {}, navigator: {serviceWorker: {}}}});
  assert.equal(await denied.enablePush(), "denied");
});

test("proactive notifications from the poll are shown as plain banners without snooze", async () => {
  const {document, elements} = fakeDOM(["reminderBanners"]);
  const x = extras.create({document, window: {}, fetchJson: async () => ({due: [], notifications: [{title: "Yağmur bekleniyor", body: "Şemsiye al"}]})});
  assert.equal(await x.poll(), 1);
  const banner = elements.reminderBanners.children[0];
  assert.equal(banner.children[0].textContent, "🔔 GÖLGE");
  assert.equal(banner.children[1].textContent, "Yağmur bekleniyor — Şemsiye al");
  assert.equal(banner.children[2].children.length, 1);
});

test("quick command buttons send their fixed text through the host callback", () => {
  const {document} = fakeDOM(["reminderBanners"]);
  const clicks = [], sent = [];
  document.querySelectorAll = sel => {
    assert.equal(sel, "[data-quick]");
    return ["hava nasıl", "haberler"].map(q => ({dataset: {quick: q}, addEventListener: (e, f) => clicks.push([q, f])}));
  };
  const x = extras.create({document, window: {}, fetchJson: async () => ({}), sendQuick: t => sent.push(t)});
  assert.equal(x.bindQuickCommands(), 2);
  clicks[1][1]();
  clicks[0][1]();
  assert.deepEqual(sent, ["haberler", "hava nasıl"]);
});

test("without querySelectorAll or callback nothing breaks", () => {
  const {document} = fakeDOM(["reminderBanners"]);
  assert.equal(extras.create({document, window: {}, fetchJson: async () => ({})}).bindQuickCommands(), 0);
});

test("feedback buttons post a rating once per assistant message", async () => {
  const {document} = fakeDOM([]);
  const calls = [];
  const x = extras.create({document, fetchJson: async (u, o) => { calls.push([u, JSON.parse(o.body)]); return {ok: true}; }});
  const node = document.createElement(); node.className = "msg assistant"; node.dataset = {cloudId: "42"};
  assert.equal(x.attachFeedback(node), true);
  assert.equal(x.attachFeedback(node), false);
  const row = node.children[0];
  assert.equal(row.children.length, 2);
  await row.children[1].listeners.click();
  assert.deepEqual(calls, [["/api/feedback", {rating: "bad", message_id: 42}]]);
  assert.match(row.textContent, /kaydettim/);
  const user = document.createElement(); user.className = "msg user"; user.dataset = {cloudId: "7"};
  assert.equal(x.attachFeedback(user), false);
});

test("approval cards post approve/reject once and disappear", async () => {
  const {document, elements} = fakeDOM(["reminderBanners"]);
  const calls = [], toasts = [];
  const x = extras.create({document, toast: m => toasts.push(m), fetchJson: async (u, o) => {
    calls.push([u, o && o.method]);
    if (u === "/api/actions/pending") return {actions: [{id: 7, text: "alışveriş listesine süt ekle", source: "agent"}]};
    return {reply: "Listeye eklendi."};
  }});
  assert.equal(await x.pollActions(), 1);
  assert.equal(await x.pollActions(), 1);                                  // the same card is not shown twice
  const card = elements.reminderBanners.children[0];
  assert.equal(elements.reminderBanners.children.length, 1);
  assert.equal(card.children[1].textContent, "alışveriş listesine süt ekle");
  const [approve, reject] = card.children[2].children;
  assert.equal(approve.textContent, "ONAYLA");
  await approve.listeners.click();
  assert.deepEqual(calls.filter(c => c[1] === "POST"), [["/api/actions/7/approve", "POST"]]);
  assert.equal(card.removed, true);
  assert.deepEqual(toasts, ["Listeye eklendi."]);
  assert.equal(reject.textContent, "REDDET");
});
