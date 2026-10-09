/**
 * ULTRON Earth Watch geographic math.
 *
 * Coordinate convention matches the existing Earth sphere UV map:
 * +X is the prime meridian, +Y is north, and -Z is 90°E.
 * Pure functions for deterministic tests without a WebGL context.
 */
export type EarthCoordinates={lat:number;lon:number};
export type CartesianPosition={x:number;y:number;z:number};

export function clampLatitude(latitude:number):number {
 if(!Number.isFinite(latitude))return 0;
 return Math.min(90,Math.max(-90,latitude));
}
export function normalizeLongitude(longitude:number):number {
 if(!Number.isFinite(longitude))return 0;
 return ((longitude+180)%360+360)%360-180;
}
export function earthToCartesian(latitude:number,longitude:number,radius=1):CartesianPosition {
 const lat=clampLatitude(latitude)*Math.PI/180;
 const lon=normalizeLongitude(longitude)*Math.PI/180;
 const r=Number.isFinite(radius)?Math.max(0,radius):1;
 const cos=Math.cos(lat);
 return {x:r*cos*Math.cos(lon),y:r*Math.sin(lat),z:-r*cos*Math.sin(lon)};
}
export function cartesianToEarth(x:number,y:number,z:number):EarthCoordinates {
 if(!Number.isFinite(x)||!Number.isFinite(y)||!Number.isFinite(z))return {lat:0,lon:0};
 const radius=Math.hypot(x,y,z);
 if(radius<1e-10)return {lat:0,lon:0};
 const lat=Math.atan2(y,Math.hypot(x,z))*180/Math.PI;
 const lon=Math.abs(x)+Math.abs(z)<1e-10?0:Math.atan2(-z,x)*180/Math.PI;
 return {lat:clampLatitude(lat),lon:normalizeLongitude(lon)};
}
