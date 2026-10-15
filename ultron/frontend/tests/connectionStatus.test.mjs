import test from 'node:test';
import assert from 'node:assert/strict';
import {cloudConnection,chatChannel} from '../src/dashboard/connectionStatus.ts';
test('local backend health alone never proves a Cloud connection',()=>{
 assert.equal(cloudConnection({ok:true}).online,false);
 assert.equal(cloudConnection({ok:true,cloud:{enabled:false}}).text,'Yapılandırılmadı');
});
test('configuration alone and stale successful responses remain unverified',()=>{
 assert.equal(cloudConnection({cloud:{enabled:true,last_ok_ts:0}}).online,false);
 assert.equal(cloudConnection({cloud:{enabled:true,last_ok_ts:100}},500000).online,false);
 assert.equal(cloudConnection({cloud:{enabled:true,last_ok_ts:600}},500000).online,false);
});
test('only a fresh real Cloud success is shown as verified',()=>{
 assert.equal(cloudConnection({cloud:{enabled:true,last_ok_ts:400}},500000).online,true);
 assert.equal(cloudConnection({cloud:{enabled:true,last_ok_ts:400,last_error:'cloud_request_failed'}},500000).online,false);
});

test('an authenticated native bridge remains usable when the local HTTP/WebSocket service is offline',()=>{
 assert.equal(chatChannel(false,true),'native');
 assert.equal(chatChannel(true,true),'server');
 assert.equal(chatChannel(true,false),'server');
 assert.equal(chatChannel(false,false),'unavailable');
});
