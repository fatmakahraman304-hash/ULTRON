import test from "node:test";
import assert from "node:assert/strict";
import { buildCoreNetwork } from "../src/dashboard/coreNetwork.ts";

test("CORE network is deterministic, bounded, spherical, and connected",()=>{
  const a=buildCoreNetwork(1400), b=buildCoreNetwork(1400);
  assert.equal(a.nodePositions.length,1400*3);
  assert.equal(a.nodeColors.length,1400*3);
  assert.ok(a.links.length>1400*6&&a.links.length<1400*3*6);
  assert.equal(a.flowSeeds.length,a.links.length/6);
  assert.deepEqual(a.nodePositions,b.nodePositions);
  assert.deepEqual(a.links,b.links);
  for(let i=0;i<a.nodePositions.length;i+=3){
    const r=Math.hypot(a.nodePositions[i],a.nodePositions[i+1],a.nodePositions[i+2]);
    assert.ok(r>1.45&&r<1.8,`unexpected radius ${r}`);
  }
  assert.ok(a.orangeNodeCount>0&&a.orangeNodeCount<40);
});

test("invalid CORE sizes clamp to the documented safe range",()=>{
  assert.equal(buildCoreNetwork(0).nodeCount,128);
  assert.equal(buildCoreNetwork(10000).nodeCount,2400);
});

test("network edges connect nearby surface nodes rather than long horizontal chords",()=>{
  const net=buildCoreNetwork(1400);
  for(let i=0;i<net.links.length;i+=6){
    const distance=Math.hypot(net.links[i]-net.links[i+3],net.links[i+1]-net.links[i+4],net.links[i+2]-net.links[i+5]);
    assert.ok(distance<.65,`nonlocal chord ${distance}`);
  }
});

test("CORE network includes sparse amber nodes and bounded signal phases",()=>{
  const net=buildCoreNetwork(700);
  assert.ok(net.orangeNodeCount>0&&net.orangeNodeCount<20);
  assert.equal(net.nodeSeeds.length,net.nodeCount);
  assert.ok([...net.flowSeeds].every(seed=>seed>=0&&seed<1));
  assert.ok([...net.links].every(Number.isFinite));
});

test("desktop CORE uses live Three.js buffers and the real audio amplitude input",async()=>{
  const fs=await import('node:fs');
  const source=fs.readFileSync(new URL('../src/dashboard/GolgeOrb.tsx',import.meta.url),'utf8');
  assert.match(source,/new THREE\.WebGLRenderer/);
  assert.match(source,/buildCoreNetwork\(1400\)/);
  assert.match(source,/new THREE\.LineSegments/);
  assert.match(source,/flowMaterial/);
  assert.match(source,/Number\(d\.amplitude\)/);
  assert.match(source,/attribute float seed;uniform float time;uniform float energy;uniform float alert;/);
  assert.doesNotMatch(source,/Math\.random\(/);
});
