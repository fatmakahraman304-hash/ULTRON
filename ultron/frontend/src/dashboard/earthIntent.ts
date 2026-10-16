/** Deterministic extension of the existing stage router; no model or OS tools. */
export type EarthIntent={operation:string;args:Record<string,unknown>};
const normalize=(s:string)=>s.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i');
export function cleanPlaceQuery(place:string){return place.trim().replace(/[’']/g,"'").replace(/'(?:ya|ye|yi|yı|yu|yü|a|e|i|ı|u|ü)$/i,'').trim().slice(0,100);}
export function resolveEarthIntent(input:string,active=false):EarthIntent|null{
 const raw=input.trim().replace(/^(?:gölge|golge|ultron)[,\s:]+/i,'').replace(/[.!?]+$/,'').trim();
 if(!raw||raw.length>300)return null;
 const t=normalize(raw).replace(/[’']/g,'');
 const action=(operation:string,args:Record<string,unknown>={}):EarthIntent=>({operation,args});
 if(/^(?:(?:normal )?(?:holograma|corea|cekirdege) don|dunyadan cik)$/.test(t))return action('reset');
 if(/^(?:3d )?(?:dunya(?:yi)?|earth)(?: goruntusunu)? (?:ac|goster|open|show)$/.test(t)||/^(?:show|open) (?:the )?earth$/.test(t))return action('earth_open');
 if(/^(?:uydu(?: mod(?:una|unu|u)| gorunumunu| haritasi(?:ni|na)?)?|satellite(?: mode| map)?) (?:ac|gec|goster|open|switch)$/.test(t))return action('earth_layer',{layer:'SATELLITE'});
 if(/^(?:2d )?harita(?:yi| modu(?:nu|na))? (?:ac|goster|gec)$/.test(t))return action('earth_layer',{layer:'MAP'});
 if(/^(?:3d gorunum(?:u)?|global(?: mod)?|kuresel gorunum) (?:ac|goster|gec)$/.test(t))return action('earth_layer',{layer:'GLOBAL'});
 if(/^(?:3d terrain|arazi(?: gorunumu)?) (?:ac|goster)$/.test(t))return action('earth_layer',{layer:'TERRAIN'});
 if(/^(?:ucaklari|ucuslari|flights) (?:goster|ac|show)$/.test(t))return action('earth_layer',{layer:'FLIGHTS'});
 if(/^(?:hava durumunu|weather) (?:goster|ac|show)$/.test(t))return action('earth_layer',{layer:'WEATHER'});
 if(/^(?:kayitli )?konumlari goster$/.test(t))return action('earth_layer',{layer:'LOCATIONS'});
 if(!active)return null;
 const coords=raw.match(/^(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)(?:\s*(?:koordinat(?:ına|ina)?|enlem|boylam|lat|lon))?\s+(?:git|odaklan|göster|goster|focus)$/i);
 if(coords){const lat=Number(coords[1]),lon=Number(coords[2]);return Math.abs(lat)<=90&&Math.abs(lon)<=180?action('earth_focus',{lat,lon,place:'KOORDİNAT'}):action('earth_invalid');}
 if(/^(?:bulut|cloud).*(?:kapat|gizle)$/.test(t))return action('earth_control',{clouds:false});
 if(/^(?:bulut|cloud).*(?:ac|goster)$/.test(t))return action('earth_control',{clouds:true});
 if(/^(?:enlem|boylam|grid|izgara).*(?:kapat|gizle)$/.test(t))return action('earth_control',{grid:false});
 if(/^(?:enlem|boylam|grid|izgara).*(?:ac|goster)$/.test(t))return action('earth_control',{grid:true});
 if(/^(?:gunes|utc gunes|sun).*(?:kapat|sabit|durdur)$/.test(t))return action('earth_control',{sun_sync:false});
 if(/^(?:gunes|utc gunes|sun).*(?:ac|senkron|aktif et)$/.test(t))return action('earth_control',{sun_sync:true});
 if(/^(?:pin|isaret|marker).*(?:temizle|sil|kaldir)$/.test(t))return action('earth_marker_clear');
 if(/^(?:iss|uzay istasyonu).*(?:goster|ac|izle|takip)$/.test(t))return action('earth_control',{live_iss:true});
 if(/^(?:iss|uzay istasyonu).*(?:kapat|gizle|durdur)$/.test(t))return action('earth_control',{live_iss:false});
 if(/^(?:(?:dunyanin )?gece tarafini goster|gece (?:modunu|gorunumunu) ac)$/.test(t))return action('earth_control',{night:true});
 if(/^(?:gece modu|night mode)$/.test(t))return action('earth_control',{night:true});
 if(/^(?:gunduz (?:modunu|gorunumunu) ac|gunduz modu|day mode)$/.test(t))return action('earth_control',{night:false});
 if(/^(?:dunya(?:yi)? )?(?:dondur|donsun|donusu baslat)$/.test(t))return action('earth_control',{auto_rotate:true});
 if(/^(?:dunya(?:nin)? )?(?:donusu durdur|donmeyi durdur)$/.test(t))return action('earth_control',{auto_rotate:false});
 if(/^(?:biraz |biraz daha |daha )?yakinlas$/.test(t))return action('earth_zoom',{factor:.77});
 if(/^(?:biraz |biraz daha |daha )?uzaklas$/.test(t))return action('earth_zoom',{factor:1.3});
 const match=raw.match(/^(.+?)\s+(?:konumunu göster|haritada göster|yaklaş|yaklas|odaklan|git|göster|goster|focus|show)$/i);
 if(match&&!/dosya|kod|rapor|kamera|sistem|sohbet|hafıza|hafiza|panel|model|görev|gorev|resim|fotograf/i.test(match[1])){
  const query=cleanPlaceQuery(match[1]);
  if(query.length>=3)return action('earth_search',{query});
 }
 return null;
}
