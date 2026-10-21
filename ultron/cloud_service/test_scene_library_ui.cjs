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
