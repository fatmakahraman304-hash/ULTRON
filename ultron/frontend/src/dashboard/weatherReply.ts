type WeatherPayload={source?:unknown;updated?:unknown;forecast_not_observation?:unknown;current?:Record<string,unknown>;current_units?:Record<string,unknown>};
const number=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?new Intl.NumberFormat('tr-TR',{maximumFractionDigits:1}).format(value):null;
/** Compose a user-facing report only from the provider response returned by the weather API. */
export function formatWeatherReply(payload:WeatherPayload,place:string){
 const current=payload?.current||{},temperature=number(current.temperature_2m),wind=number(current.wind_speed_10m);
 if(!temperature)return 'Hava durumu sağlayıcısı kullanılabilir bir sıcaklık verisi döndürmedi; doğrulanmış sonuç gösteremiyorum.';
 const tempUnit=String(payload.current_units?.temperature_2m||'°C');
 const windUnit=String(payload.current_units?.wind_speed_10m||'km/h');
 const windText=wind?` Rüzgâr ${wind} ${/km\/h/i.test(windUnit)?'km/sa':windUnit}.`:'';
 const source=typeof payload.source==='string'&&payload.source.trim()?payload.source.trim():'Kaynağı bildirilmedi';
 const updated=typeof payload.updated==='string'&&payload.updated.trim()?` Veri zamanı: ${payload.updated.trim()}.`:'';
 const forecast=payload.forecast_not_observation===true||payload.forecast_not_observation===undefined?' Bu, sağlayıcının tahmin verisidir; yerel ölçüm değildir.':'';
 const location=place&&place!=='GLOBAL'?place:`${current.latitude??''} ${current.longitude??''}`.trim()||'seçili konum';
 return `${location} için hava durumu: ${temperature} ${tempUnit}.${windText} Kaynak: ${source}.${updated}${forecast}`;
}
