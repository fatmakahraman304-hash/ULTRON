/* One deterministic router for PWA and React. No provider calls or permissions. */
(function(root,factory){const api=factory();if(typeof module!=='undefined')module.exports=api;root.GolgeImages=api;})(globalThis,function(){
 function resolve(text){
  const t=String(text||'').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i');
  if(!t||t.length>4000)return null;
  if(/\b(?:bul|ara|indir|analiz|incele|hakkinda|nedir|nasil|find|search|download|analyze|explain)\b/.test(t))return null;
  const noun=/fotograf|gorsel|res(?:im|mi)|duvar kagidi|image|picture|wallpaper|photo|digital sanat/.test(t);
  if(noun&&/sinematik yap|duzenle|iyilestir|degistir|edit|enhance/.test(t)&&/\b(?:bu|bunu|this|it)\b/.test(t))return 'edit';
  if((noun&&/olustur|uret|ciz|yarat|\byap\b|generate|create|draw|paint/.test(t))||/\bciz\b|\bdraw\b/.test(t)||/^(?:bana )?(?:bir )?.{1,60}\bdaire olustur/.test(t))return 'generate';
  return null;
 }
 function options(text){const t=String(text).toLocaleLowerCase('tr-TR');return {aspect_ratio:/dikey|telefon.*duvar|portrait/.test(t)?'9:16':/yatay|masaüstü.*duvar|landscape/.test(t)?'16:9':'1:1',style:/sinematik|cinematic/.test(t)?'cinematic':/anime|çizim/.test(t)?'anime':/3d|3 boyut/.test(t)?'3d':/dijital sanat/.test(t)?'digital-art':/fotoğraf|gerçekçi|photo/.test(t)?'photo':'natural'};}
 return {resolve,options};
});
