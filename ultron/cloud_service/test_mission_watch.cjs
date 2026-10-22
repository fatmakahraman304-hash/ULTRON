"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const mw = require("./static/mission-watch.js");

test("progress is toasted, final report delivered once and spoken", async () => {
  const toasts = [], messages = [], spoken = [];
  const seq = [
    {status: "running", steps: [{id: 1, status: "running"}, {id: 2, status: "pending"}]},
    {status: "running", steps: [{id: 1, status: "done"}, {id: 2, status: "running"}]},
    {status: "done", steps: [{id: 1, status: "done"}, {id: 2, status: "done"}], report: "<b>Rapor</b>", delivered: true, assistant_message_id: 9},
  ];
  let i = 0;
  const w = mw.create({sleep: async () => {}, toast: t => toasts.push(t), addMessage: (...a) => messages.push(a), speak: s => spoken.push(s),
    fetchJson: async url => { assert.match(url, /^\/api\/mission\/m1\?conversation_id=c1$/); return seq[i++]; }});
  assert.equal(await w.watch("m1", "c1"), "done");
  assert.deepEqual(toasts, ["Görev: …1 ·2", "Görev: ✓1 …2"]);
  assert.deepEqual(messages, [["assistant", "<b>Rapor</b>", {id: 9}]]);
  assert.deepEqual(spoken, ["<b>Rapor</b>"]);
});

test("already delivered or cancelled missions add nothing; network errors are retried", async () => {
  const messages = [];
  let n = 0;
  const w = mw.create({sleep: async () => {}, addMessage: (...a) => messages.push(a),
    fetchJson: async () => { if (n++ === 0) throw Error("offline"); return {status: "done", steps: [], report: "x", delivered: false}; }});
  assert.equal(await w.watch("m", "c"), "done");
  assert.deepEqual(messages, []);
  const c = mw.create({sleep: async () => {}, toast: () => {}, fetchJson: async () => ({status: "cancelled", steps: []})});
  assert.equal(await c.watch("m", "c"), "cancelled");
});
