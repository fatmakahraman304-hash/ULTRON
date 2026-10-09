"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const guard = require("./static/mobile-action-guard.js");
const command = { version: 1, source: "ultron", action: "set_brightness", target: "", value: "35" };

test("allowed iOS action points only to ULTRON Bridge", () => {
  const event = guard.fromLiveEvent({ type: "ios_action", command });
  assert.equal(event.label, "Ekran parlaklığını değiştir");
  assert.deepEqual(event.command, command);
  const url = new URL(guard.shortcutURL(event.command));
  assert.equal(url.protocol, "shortcuts:");
  assert.equal(url.hostname, "run-shortcut");
  assert.equal(url.searchParams.get("name"), "ULTRON Bridge");
  assert.deepEqual(JSON.parse(url.searchParams.get("text")), command);
});

test("named shortcut accepts only validated ULTRON Bridge JSON", () => {
  const valid = { type: "ios_shortcut", shortcut_name: "ULTRON Bridge", input: JSON.stringify(command) };
  assert.deepEqual(guard.fromLiveEvent(valid).command, command);
  assert.equal(guard.fromLiveEvent({ ...valid, shortcut_name: "Erase Phone" }), null);
  assert.equal(guard.fromLiveEvent({ ...valid, input: "not json" }), null);
  assert.equal(guard.fromLiveEvent({ ...valid, input: JSON.stringify({action:"erase_phone"}) }), null);
});

test("invalid settings and injected fields are rejected", () => {
  for (const candidate of [
    null, [], {}, { ...command, source:"other" }, { ...command, version:2 },
    { ...command, action:"erase_device" }, { ...command, url:"shortcuts://other" },
    { ...command, value:"101" }, { ...command, value:"-2" },
    { ...command, value:"1;run" }, { ...command, value:35 },
    { ...command, target:"x".repeat(301) }, { ...command, value:"x".repeat(1201) }
  ]) assert.equal(guard.validateCommand(candidate), null);
});

test("wifi and bluetooth must include an explicit toggle value", () => {
  assert.equal(guard.validateCommand({ ...command, action:"wifi",value:"on" }).action,"wifi");
  assert.equal(guard.validateCommand({ ...command, action:"bluetooth",target:"off",value:"" }).action,"bluetooth");
  assert.equal(guard.validateCommand({ ...command, action:"wifi",value:"toggle" }),null);
});

test("cannot make unsafe shortcut URL", () => {
  assert.equal(guard.shortcutURL({ ...command, action:"erase_device" }),null);
  assert.equal(guard.fromLiveEvent({type:"phone_action",action:"set_brightness"}),null);
});

test("PWA must show user approval rather than auto-run live shortcuts", () => {
  const html=fs.readFileSync(path.join(__dirname,"static","index.html"),"utf8");
  const sw=fs.readFileSync(path.join(__dirname,"static","sw.js"),"utf8");
  assert.match(html,/<script src="\/static\/mobile-action-guard\.js"><\/script>/);
  assert.match(html,/if\(d\.type==='ios_action'\|\|d\.type==='ios_shortcut'\)/);
  assert.match(html,/queueIOSApproval\(d\)/);
  assert.match(html,/\$\('#approvePhoneAction'\)\.onclick=\(\)=>/);
  assert.match(html,/\$\('#denyPhoneAction'\)\.onclick=\(\)=>/);
  assert.match(html,/if\(pendingIOSAction\)\{toast\('Önce bekleyen iPhone işlemini/);
  assert.match(sw,/\/static\/mobile-action-guard\.js/);
});

test("remote tab includes queue status badge and task summary", () => {
  const html=fs.readFileSync(path.join(__dirname,"static","index.html"),"utf8");
  assert.match(html,/function updateRemoteTaskIndicator\(rows\)/);
  assert.match(html,/x\.status==='queued'/);
  assert.match(html,/x\.status==='delivered'/);
  assert.match(html,/id="remoteTaskSummary"/);
  assert.match(html,/id="remoteBadge"/);
});
