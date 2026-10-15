/** A local WebSocket or an enabled connector is not proof of a Cloud response. */
export function cloudConnection(health:any,now=Date.now()){
 const cloud=health?.cloud;
 if(!cloud)return {text:'Durum doğrulanamadı',online:false,detail:'Servis sağlık kaydı bekleniyor'};
 if(!cloud.enabled)return {text:'Yapılandırılmadı',online:false,detail:'Bulut cihaz bağlantısı yok'};
 const last=Number(cloud.last_ok_ts)||0;
 if(cloud.last_error)return {text:'Bağlantı sorunu',online:false,detail:'Son bulut isteği tamamlanamadı'};
 if(last>0&&now/1000-last>=0&&now/1000-last<300)return {text:'Doğrulandı',online:true,detail:'Son başarılı bulut yanıtı 5 dk içinde'};
 return {text:'Yapılandırıldı',online:false,detail:last?'Önceki doğrulama güncel değil':'İlk başarılı yanıt bekleniyor'};
}

/** Reuse the original Qt engine when its local HTTP service is not reachable. */
export function chatChannel(serverConnected:boolean,nativeAvailable:boolean):'server'|'native'|'unavailable'{
 return serverConnected?'server':nativeAvailable?'native':'unavailable';
}
