import {test} from 'node:test';
import assert from 'node:assert/strict';
import {earthToCartesian,cartesianToEarth,normalizeLongitude,clampLatitude} from '../src/dashboard/earthMath.ts';

const near=(actual,expected,tolerance=1e-6)=>assert.ok(Math.abs(actual-expected)<tolerance,`expected ${actual} ≈ ${expected}`);

test('Earth geographic axes match the Earth Watch texture convention',()=>{
 const greenwich=earthToCartesian(0,0,2.25);
 near(greenwich.x,2.25);near(greenwich.y,0);near(greenwich.z,0);
 const east=earthToCartesian(0,90);
 near(east.x,0);near(east.y,0);near(east.z,-1);
 const north=earthToCartesian(90,0);
 near(north.y,1);
});
test('Round-trip multiple real Earth locations',()=>{
 for(const [lat,lon] of [
  [0,0],[35.13,33.43],[39,35],[41.01,28.98],
  [40.7128,-74.006],[35.6762,139.6503],[-33.8688,151.2093],
  [70.5,-179.4],[-69.25,179.99],[0,-180]
 ]){
  const xyz=earthToCartesian(lat,lon,2.25);
  const result=cartesianToEarth(xyz.x,xyz.y,xyz.z);
  near(result.lat,lat,1e-5);
  near(result.lon,normalizeLongitude(lon),1e-5);
 }
});
test('Longitude wrap and invalid input are deterministic',()=>{
 near(normalizeLongitude(190),-170);
 near(normalizeLongitude(-540),-180);
 near(normalizeLongitude(540),-180);
 near(clampLatitude(100),90);near(clampLatitude(-101),-90);
 assert.deepEqual(cartesianToEarth(0,0,0),{lat:0,lon:0});
 assert.deepEqual(cartesianToEarth(NaN,0,0),{lat:0,lon:0});
 const xyz=earthToCartesian(Infinity,NaN,-5);
 near(xyz.x,0);near(xyz.y,0);near(xyz.z,0);
});
test('Radius does not affect reported GPS coordinates',()=>{
 const tiny=earthToCartesian(23.5,-42.7,1);
 const large=earthToCartesian(23.5,-42.7,300);
 near(cartesianToEarth(tiny.x,tiny.y,tiny.z).lat,cartesianToEarth(large.x,large.y,large.z).lat);
 near(cartesianToEarth(tiny.x,tiny.y,tiny.z).lon,cartesianToEarth(large.x,large.y,large.z).lon);
});
