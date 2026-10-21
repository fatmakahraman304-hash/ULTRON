"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const bridge = require("./static/laptop-bridge.js");

test("prefilter is loose but ordinary chat never calls the API", async () => {
  assert.equal(bridge.mayRoute("merhaba"), false);
  assert.equal(bridge.mayRoute("ekranıma bak"), true);
  assert.equal(bridge.mayRoute("laptop: chrome aç"), true);
  const calls = [];
  const b = bridge.create({fetchJson: async u => { calls.push(u); return {}; }});
  assert.equal(await b.route("bugün hava nasıl", {}), null);
  assert.deepEqual(calls, []);
});

test("server decline falls back to normal chat; routed result is rendered", async () => {
  const messages = [], convs = [];
  const declined = bridge.create({fetchJson: async () => ({routed: false}), addMessage: (...a) => messages.push(a)});
  assert.equal(await declined.route("bilgisayar fiyatları", {}), null);
  assert.deepEqual(messages, []);
  const ok = bridge.create({
    fetchJson: async (u, o) => { assert.equal(u, "/api/laptop-task"); assert.equal(JSON.parse(o.body).message, "ekran analizi yap");
      return {routed: true, status: "completed", reply: "<b>VS Code</b> açık", assistant_message_id: 5, conversation_id: "c1"}; },
    addMessage: (...a) => messages.push(a), speak: () => {}, onConversation: id => convs.push(id)});
  const r = await ok.route("ekran analizi yap", {conversationId: ""});
  assert.equal(r.status, "completed");
  assert.deepEqual(messages, [["assistant", "<b>VS Code</b> açık", {id: 5}]]);
  assert.deepEqual(convs, ["c1"]);
});

test("pending tasks are watched until the laptop result arrives, once", async () => {
  const messages = [];
  let polls = 0;
  const b = bridge.create({sleep: async () => {}, addMessage: (...a) => messages.push(a), toast: () => {},
    fetchJson: async u => { polls++; return polls < 3 ? {status: "pending"}
      : {status: "completed", reply: "Rapor hazır.", delivered: true, assistant_message_id: 8}; }});
  assert.equal(await b.watch(4, "c1"), "completed");
  assert.equal(polls, 3);
  assert.deepEqual(messages, [["assistant", "Rapor hazır.", {id: 8}]]);
});
