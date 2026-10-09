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

/**
 * Approximate geodetic point directly facing the Sun at a UTC instant.
 * NOAA low-cost solar declination + equation-of-time approximation.
 * Suitable for Earth Watch visuals, NOT navigation or astronomical research.
 * No network, telemetry, timezone dependency or geolocation permissions.
 */
export function solarPositionUTC(date:Date):EarthCoordinates {
 const timestamp=date.getTime();
 if(!Number.isFinite(timestamp))return {lat:0,lon:0};
 const year=date.getUTCFullYear();
 const utcDay=(timestamp-Date.UTC(year,0,1))/86_400_000;
 const yearDays=(Date.UTC(year+1,0,1)-Date.UTC(year,0,1))/86_400_000;
 const gamma=2*Math.PI/yearDays*(utcDay-.5);
 const declination=.006918-.399912*Math.cos(gamma)+.070257*Math.sin(gamma)
                  -.006758*Math.cos(2*gamma)+.000907*Math.sin(2*gamma)
                  -.002697*Math.cos(3*gamma)+.00148*Math.sin(3*gamma);
 const equationOfTime=229.18*(.000075+.001868*Math.cos(gamma)-.032077*Math.sin(gamma)
                          -.014615*Math.cos(2*gamma)-.040849*Math.sin(2*gamma));
 const utcMinutes=(timestamp%86_400_000+86_400_000)%86_400_000/60_000;
 // Solar noon = 720 UTC minutes at 0° longitude when equation-of-time is zero.
 const subsolarLon=normalizeLongitude((720-utcMinutes-equationOfTime)/4);
 return {lat:clampLatitude(declination*180/Math.PI),lon:subsolarLon};
}
