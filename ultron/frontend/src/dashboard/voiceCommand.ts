/** Exact, low-risk voice commands that must bypass the chat/model path. */
const normalize=(input:string)=>input.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/[’']/g,'').replace(/[.!?,;:]+/g,' ').replace(/\s+/g,' ').trim().replace(/^(?:golge|gölge)\s+/,'');
const STOP_COMMANDS=new Set(['dur','sus','kes','konusmayi durdur','konusmayi kes','konusmayi sustur','yaniti durdur','cevabi durdur','tts durdur','stop','stop speaking','be quiet']);
export function isStopCommand(input:string){return STOP_COMMANDS.has(normalize(input));}
