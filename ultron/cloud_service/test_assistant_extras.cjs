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
