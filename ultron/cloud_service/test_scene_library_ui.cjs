"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const html = fs.readFileSync(path.join(__dirname, "static", "index.html"), "utf8");

test("phone hologram asks the shape library before the local or cloud model", () => {
  const body = html.slice(html.indexOf("async function generateSceneDesign"), html.indexOf("async function handleSceneIntent"));
  const library = body.indexOf("/api/scene-library");
  assert.ok(library > 0, "library lookup missing");
  assert.ok(library < body.indexOf("refreshAutoBrain"), "library must run before brain selection");
  assert.ok(library < body.indexOf("/api/local-scene-design"), "library must run before the local model");
  assert.ok(library < body.indexOf("'/api/scene-design'"), "library must run before the cloud model");
  assert.match(body, /known&&known\.design\)return known\.design/);
});

test("spoken 'show a heart' reaches the hologram through control_phone_ui", () => {
  assert.match(html, /if\(action==='hologram'&&query\)handleSceneIntent\('hologramda '\+query\.slice\(0,100\)\+' goster'\)/);
  const app = fs.readFileSync(path.join(__dirname, "app.py"), "utf8");
  assert.match(app, /"whatsapp_message", "hologram"\}/);
  assert.match(app, /shape_description_required/);
});

test("a voice-started agent mission is followed on the phone like a typed one", () => {
  assert.match(html, /d\.type==='mission_started'&&d\.mission_id&&window\.ULTRONMissionWatch/);
  const app = fs.readFileSync(path.join(__dirname, "app.py"), "utf8");
  assert.match(app, /"name": "start_agent"/);
  assert.match(app, /missions\.start_core\(request\.app, user_id, goal, str\(conv_uuid\), "agent"\)/);
  assert.match(app, /"type": "mission_started"/);
});
