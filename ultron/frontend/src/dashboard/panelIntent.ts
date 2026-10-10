/** UI-only speech/text routing. Never runs a native OS tool. */
export type Workspace = 'chat'|'world'|'hologram'|'memory'|'remote'|'develop'|'tools'|'settings';
export function resolvePanelIntent(input:string):Workspace|null {
 const t=String(input||'').toLocaleLowerCase('tr-TR').replace(/[’']/g,"'").replace(/\s+/g,' ').trim();
 if(!t||t.length>400)return null;
 if(/^(?:ana ekrana dön|ana ekrana don|sohbete dön|sohbete don|paneli kapat|ekranı kapat|ekrani kapat|close panel|back to chat|ultron ana ekran)$/.test(t))return 'chat';
 if(!/(?:^|\s)(?:aç|ac|göster|goster|getir|çıkart|cikart|geç|gec|bak|izle|başlat|baslat|open|show|bring)(?=$|\s|[.!?])/.test(t))return null;
 if(/(?:hologram\s*(?:lab|laboratuvar|çalışma alanı|calisma alani)|hologram laboratuvarı|hologram laboratuvari|hologram tasarım|hologram tasarim)/.test(t))return 'hologram';
 if(/(?:dünya|dunya|world|harita|earth watch|uçak|ucak|deprem|hava durumu|weather)/.test(t))return 'world';
 if(/(?:hafıza|hafiza|hatıra|hatira|öğrenme|ogrenme|takvim|planlarım|planlarim)/.test(t))return 'memory';
 if(/(?:uzaktan|laptop kontrol|bilgisayar kontrol|remote)/.test(t))return 'remote';
 if(/(?:geliştir|gelistir|geliştirme panel|kod panel|development)/.test(t))return 'develop';
 if(/(?:araçlar|araclar|çalışma alanları|calisma alanlari|workspace|toolbox)/.test(t))return 'tools';
 if(/(?:ayarlar|settings)/.test(t))return 'settings';
 if(/(?:sohbet|konuşma|konusma|chat)/.test(t))return 'chat';
 return null;
}
