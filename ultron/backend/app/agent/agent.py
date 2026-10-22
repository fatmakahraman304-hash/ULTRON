import json,re
from urllib.parse import quote_plus
from app.agent.persona_guard import PersonaGuard, ANCHOR as _PERSONA_ANCHOR  # noqa: F401
import app.agent.persona_guard as persona_guard
from app.emotion.emotion_engine import analyze as emotion_analyze
from app.core.intent import classify, research_pattern, vision_pattern, VISION_PROMPT

class Agent:
    def __init__(self,brain,executor,memory,registry,settings,audit,tts,max_steps=8,semantic_memory=None,planner=None,vision_llm=None,adaptive=None,router=None,world_fn=None,redact_fn=None,research_engine=None):
        self.brain=brain; self.executor=executor; self.memory=memory; self.registry=registry; self.settings=settings; self.audit=audit; self.tts=tts; self.max_steps=max_steps
        self.semantic_memory=semantic_memory; self.planner=planner; self.vision_llm=vision_llm
        self.adaptive=adaptive
        self.router=router  # PHASE 2: model router (GENERAL chat + fallback)
        self.world_fn=world_fn  # PHASE 4: live world-state context (WorldModel)
        self.redact_fn=redact_fn  # PHASE 10: vault-backed redaction (prompts/tool output)
        self.research_engine=research_engine
        self.persona=PersonaGuard(mode=settings.get('persona_guard_mode','reframe'))
    def _persona_finalize(self, answer):
        chk=self.persona.check(answer)
        bad = chk["violations"] or chk["score"] < self.persona.threshold
        if not bad:
            return answer
        mode=self.persona.mode
        if mode in ("regenerate","hybrid") and chk["violation_score"] > 0.8:
            try:
                rw=self.brain.ask(
                    "Aşağıdaki metni anlamı koruyarak GÖLGE'nin sakin ve saygılı "
                    "kişisel asistan üslubuyla yeniden yaz. Doğrudan yardımcı ol; "
                    "gereksiz resmi kalıpları ve kullanıcıyla alayı kaldır:\n"+answer,
                    system=persona_guard.ANCHOR)
                if rw:
                    return rw
            except Exception:
                pass
            return PersonaGuard.reframe(answer)
        if mode in ("reframe","hybrid"):
            return PersonaGuard.reframe(answer)
        return answer
    def _boss_hitap(self, answer):
        # Retain the method for older integrations, but do not force a title
        # or greeting onto every concise local-assistant reply.
        return answer
    def _save(self,role,text): self.memory.add("conversation",f"{role}: {text}")
    def _history(self,limit=20):
        rows=list(reversed(self.memory.recent(limit))); out=[]
        for kind,c,_ in rows:
            if kind=="conversation" and (c.startswith("USER: ") or c.startswith("GÖLGE: ") or c.startswith("ULTRON: ")):
                role="user" if c.startswith("USER: ") else "assistant"; out.append({"role":role,"content":c.split(": ",1)[1]})
        return out
    def _vision_pipeline(self,text):
        """capture → verify PNG → llava vision → response. Never touches the
        text-only chat path; on any failure returns the exact error."""
        import os
        from app.tools.ollama_tools import ollama_status
        m=re.search(r"(\S+\.(?:png|jpe?g))", text, re.I)
        path=m.group(1) if m else None
        if not path:
            self.audit.write("VISION","stage=screenshot start")
            try:
                path=self.executor.execute([('capture_screen',{})],approved=True)[0]
            except Exception as e:
                return f"SCREENSHOT ERROR: {e}"
        if not (os.path.exists(path) and os.path.getsize(path)>0):
            return f"SCREENSHOT ERROR: PNG doğrulanamadı: {path}"
        self.audit.write("VISION",f"detected intent=screen_analyze screenshot={path} size={os.path.getsize(path)}")
        if self.vision_llm is None:
            return "VISION ERROR: VisionLLM runtime'a bağlı değil."
        try:
            models=ollama_status(self.brain.base_url,self.brain.model).get('models') or []
        except Exception:
            models=[]
        model=self.vision_llm.resolve_model(models)
        self.audit.write("VISION",f"selected_model={model} endpoint={self.brain.base_url}/api/chat")
        if model is None:
            return "VISION UNAVAILABLE: kurulu llava/vision modeli yok (Ollama /api/tags kontrol edildi)."
        try:
            analysis=self.vision_llm.analyze(path, VISION_PROMPT, available_models=models)
        except Exception:
            return "Görsel analizi tamamlanamadı."
        if not analysis:
            return "VISION ERROR: model boş yanıt verdi."
        final=f"EKRAN ANALİZİ ({model}): {analysis}"
        self.audit.write("VISION",f"final_head={final[:160]}")
        return final

    def _direct(self,text):
        # vision requests must NEVER reach the text-only Qwen chat path
        if vision_pattern(text):
            return self._vision_pipeline(text)
        if self.adaptive and "sarkazm" in text.lower() and ("aç" in text.lower() or "kapat" in text.lower()):
            mode=self.adaptive.override
            return f"Kaydedildi, Boss. Sarkazm modu: {'AÇIK' if mode=='sarkazm-on' else 'KAPALI' if mode=='sarkazm-off' else 'OTOMATİK'}."
        intent=classify(text); t=text.lower()
        # Deterministic conversation memory for common identity/context requests.
        m=re.search(r"(?:benim adım|benim ismim|adım|ismim)\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)", text, re.I)
        if m and not any(x in t for x in ["ne", "nedir"]):
            name=m.group(1).strip().capitalize()
            self.memory.add("profile", f"name: {name}")
            return f"Tamam. Adınızı {name} olarak hatırlayacağım."
        if any(x in t for x in ["benim adım ne", "ismim ne"]):
            rows=[x for x in self.memory.recent(100) if x[0]=="profile" and x[1].startswith("name:")]
            if rows: return f"Adınız {rows[0][1].split(':',1)[1].strip()}."
        # ---- long-term memory categories (never store sensitive data)
        sensitive = re.search(r"(şifre|password|parola|token|api[_-]?key|secret|kredi kart)", t)
        mnote = re.search(r"(?:not al|kaydet|unutma)\s*[:\"]*(.+)", text, re.I)
        if mnote and "görev" not in t:
            if sensitive: return "Hassas bilgileri (şifre/token/anahtar) kaydetmiyorum."
            kind = "PREFERENCE" if any(x in t for x in ["tercih", "sever", "hoşlan", "sevmem"]) else "FACT"
            self.memory.add(kind, mnote.group(1).strip()[:300])
            return f"Kaydettim ({kind})."
        mtask = re.search(r"(?:görev ekle|task ekle|todo ekle)\s*[:\"]*(.+)", text, re.I)
        if mtask:
            if sensitive: return "Hassas bilgileri kaydetmiyorum."
            self.memory.add("TASK", mtask.group(1).strip()[:300])
            return "Görevi TASK listesine ekledim."
        if any(x in t for x in ["hatırlat", "görevlerim", "todo listem", "ne yapmam gerektiğini", "bugün ne yapmam"]):
            rows = [x for x in self.memory.recent(100) if x[0] == "TASK"]
            if not rows: return "Kayıtlı görev yok. 'görev ekle: ...' diyerek ekleyebilirsin."
            return "Görevlerin:\n" + "\n".join(f"- {c[1]}" for c in rows[:8])
        if "cihaz bilgisi" in t and "kaydet" in t:
            from app.telemetry.system_stats import get_system_stats
            s = get_system_stats()
            self.memory.add("DEVICE", f"{s['platform']} · RAM {s['ram_total_gb']}GB")
            return "Cihaz bilgisi kaydedildi (DEVICE)."
        if any(x in t for x in ["az önce ne sordum", "son isteğim ne", "son isteğimi hatırla"]):
            rows=self._history(20); users=[x["content"] for x in rows if x["role"]=="user"]
            if len(users)>=2: return f"Son isteğiniz şuydu: {users[-2]}"
            if users: return f"Bu konuşmadaki isteğiniz: {users[-1]}"
        if "kısa ve sonra ayrıntılı" in t or "kısa sonra ayrıntılı" in t:
            return "Kısa: GÖLGE, görevleri anlayıp gerçekleştiren bir Windows AI asistanıdır.\nAyrıntılı: GÖLGE; sistem telemetrisi, uygulama kontrolü, web, dosya işlemleri, ekran görüntüsü, hafıza ve çok adımlı görev yürütme gibi yetenekleri tek bir agent çekirdeğinde birleştirmeyi amaçlar."
        if intent=="calculate":
            try: return f"Sonuç: {self.executor.execute([('calculate',{'text':text})],approved=True)[0]}"
            except Exception as e: return f"Hesaplama yapılamadı: {e}"
        if intent=="system_status":
            r=self.executor.execute([('system_status',{})],approved=True)[0]; g=(r.get('gpus') or [{}])[0]
            return f"CPU {r.get('cpu_percent')}%, RAM {r.get('ram_percent')}%, Disk {r.get('disk_percent')}%, GPU {g.get('util_percent',0)}%."
        if intent=="self_diagnostic":
            try:
                r=self.executor.execute([("self_diagnostic",{})],approved=True)[0]
                return r.get("report") if isinstance(r,dict) else str(r)
            except Exception as e:
                return f"Öz-teşhis çalıştırılamadı: {e}"
        if intent=="ollama_status":
            r=self.executor.execute([('ollama_status',{})],approved=True)[0]
            if r.get('connected'): return f"Ollama bağlı. Model: {self.brain.model}. Kurulu modeller: {', '.join(r.get('models') or []) or 'yok'}. Seçili model {'kurulu' if r.get('model_installed') else 'kurulu değil'}."
            return f"Ollama bağlantısı başarısız: {r.get('error','bilinmeyen hata')}"
        if intent=="audit":
            rows=self.audit.recent(10); return "\n".join(rows) if rows else "Henüz işlem kaydı yok."
        if intent=="capabilities":
            if "modelle" in t: return f"Aktif model: {self.brain.model}. Provider: {self.brain.provider}."
            return "Aktif araçlar: " + ", ".join(self.registry.names())
        if intent=="screen":
            try:
                p=self.executor.execute([('capture_screen',{})],approved=True)[0]
                if any(x in t for x in ["ne var","ekranımda","ekrandaki","ekranı gör"]):
                    o=self.executor.execute([('screen_ocr',{'path':p})],approved=True)[0]
                    if o.get('text'): return f"Ekran görüntüsü alındı: {p}\nOCR: {o['text'][:3000]}"
                return f"Ekran görüntüsü alındı: {p}"
            except Exception as e: return f"Ekran görüntüsü alınamadı: {e}"
        if intent=="open_app" and "chrome" in t and "google" not in t:
            try: return self.executor.execute([('open_application',{'name':'chrome'})],approved=True)[0]
            except Exception as e: return f"Chrome açılamadı: {e}"
        if intent=="file_task":
            if "indirilenler" in t: root=str(__import__('pathlib').Path.home()/"Downloads")
            elif "masaüst" in t: root=str(__import__('pathlib').Path.home()/"Desktop")
            else: root=None
            if "ultron projesi" in t:
                p=self.executor.execute([('find_project',{'start':root,'name_hint':'Ultron'})],approved=True)[0]
                return f"Ultron projesi: {p}" if p else "Ultron projesi bulunamadı."
            if root:
                items=self.executor.execute([('list_directory',{'root':root})],approved=True)[0]
                return "\n".join(f"{'[Klasör]' if x['type']=='folder' else '[Dosya]'} {x['name']}" for x in items[:80]) or "Klasör boş."
        if intent=="run_tests":
            return self._run_project_tests()
        if intent=="web_search" and "chrome" not in t:
            q=self._extract_search_query(text); return self.executor.execute([('open_url',{'url':'https://www.google.com/search?q='+quote_plus(q)})],approved=True)[0]
        if intent=="speak":
            answer="Elbette. Sesli yanıt sistemi hazır."; self.tts.speak(answer); return answer
        return None
    def _extract_search_query(self,text):
        t=text.strip(); low=t.lower()
        for marker in ["google'da","google da","google'de","google de"]:
            if marker in low:
                q=t[low.find(marker)+len(marker):].strip(" :.")
                return re.sub(r"^(ara|arama yap|araştır)\s*","",q,flags=re.I).strip(" .")
        q=re.sub(r".*?(?:internette|web'de)\s*", "", t, flags=re.I)
        return re.sub(r"\s*(ara|arama yap)$","",q,flags=re.I).strip(" .")
    def _browser(self,text):
        low=text.lower()
        if "chrome" not in low or "google" not in low: return None
        q=self._extract_search_query(text)
        # Remove trailing command phrases that are not part of the query.
        q=re.sub(r"\s+ve\s+(?:ilk sonucu|sonucu bana bildir|araştır|ara)$","",q,flags=re.I).strip()
        if not q: return None
        url='https://www.google.com/search?q='+quote_plus(q)
        result=self.executor.execute([('open_url',{'url':url})],approved=True)[0]
        return f"{result} Google'da '{q}' araması başlatıldı."
    def _run_project_tests(self):
        import subprocess, pathlib
        p=self.executor.execute([('find_project',{'start':str(pathlib.Path.home()/"Downloads"),'name_hint':'Ultron'})],approved=True)[0]
        if not p: return "Ultron projesi bulunamadı; test çalıştırılamadı."
        try:
            r=subprocess.run([__import__('sys').executable,'-m','pytest','-q'],cwd=p,capture_output=True,text=True,timeout=180)
            return f"Test sonucu: {r.stdout.strip() or r.stderr.strip()}"
        except Exception as e: return f"Test çalıştırılamadı: {e}"
    def _deterministic_browser_task(self,text):
        return self._browser(text)

    def _extract_tool_calls(self,message):
        native=message.get("tool_calls") or []
        if native: return native
        c=(message.get("content") or "").strip(); candidates=[c]
        a,b=c.find("{"),c.rfind("}")
        if a>=0 and b>a: candidates.append(c[a:b+1])
        for x in candidates:
            try:o=json.loads(x)
            except Exception:continue
            if isinstance(o,dict) and o.get("name"):
                args=o.get("arguments",{}); args=json.loads(args) if isinstance(args,str) else args
                return [{"function":{"name":o["name"],"arguments":args or {}}}]
        return []
    def _redact(self,text):
        if self.redact_fn is None: return text
        try: return self.redact_fn(str(text))
        except Exception: return text

    def handle(self,text,approved=False):
        text=self._redact(text)  # secrets never reach prompts/logs
        self._save("USER",text); self.audit.write("USER",text)
        # V7: emotion-aware persona (override commands + hint injection)
        if self.adaptive:
            self.adaptive.handle_command(text)
            emo=emotion_analyze(text=text)
            hint=self.adaptive.adapt(emo["state"], emo["confidence"])
            self.persona.set_emotion_hint(hint, emo["state"])
        research_result=None
        if self.research_engine is not None:
            try:
                if research_pattern(text):
                    from app.cognitive.research_context import extract_research_query, safe_public_query
                    if safe_public_query(text):
                        research_result=self.research_engine.research(
                            extract_research_query(text),max_sources=3,store=False)
                    else:
                        research_result={"ok":False,"status":"research_blocked_sensitive_input",
                                         "evidence_level":"none","citations":[],
                                         "synthesis":{"findings":[]}}
            except Exception:
                research_result={"ok":False,"status":"research_unavailable",
                                 "evidence_level":"none","citations":[],
                                 "synthesis":{"findings":[]}}
        if research_result is not None and not (research_result.get("synthesis") or {}).get("findings"):
            answer=("Bu sorgu özel bilgi içeriyor. Özel bilgileri kaldırıp yeniden sorabilirsin."
                    if research_result.get("status")=="research_blocked_sensitive_input" else
                    "Güncel kaynaklara erişemedim; bu bilgiyi doğrulayamıyorum.")
            self._save("GÖLGE",answer); self.audit.write("ASSISTANT",answer)
            return answer
        direct=None if research_result is not None else self._direct(text)
        if direct:
            direct=self._boss_hitap(direct)
            self._save("GÖLGE",direct); self.audit.write("ASSISTANT",direct); return direct
        browser=None if research_result is not None else self._browser(text)
        if browser:
            self._save("GÖLGE",browser); return browser
        history=self._history(24)
        semantic=(self.semantic_memory.context(text,5) if self.semantic_memory else "")
        base=("Sen GÖLGE'sin, Windows masaüstünde çalışan kişisel asistansın. Türkçe konuş. "
                "Gerçek bir aracı çalıştırmadan bir işlemi yaptığını asla iddia etme. "
                "Araç başarısızsa açıkça başarısız olduğunu söyle. Bağlamdaki önceki mesajları kullan. "
                "Kısa cevap isteğinde kısa, ayrıntılı isteğinde ayrıntılı cevap ver. "
                "İlgili uzun dönem hafıza varsa onu bağlam olarak kullan.")
        system=self.persona.compose(base, len(history)) + ("İlgili hafıza:\n"+semantic if semantic else "")
        if callable(self.world_fn):
            try:
                world_block=self.world_fn()
                if world_block: system=system+"\n"+world_block
            except Exception: pass
        if research_result is not None:
            from app.cognitive.research_context import build_research_prompt_block
            system=system+build_research_prompt_block(research_result)
        messages=[{"role":"system","content":system}]+history[-20:]+[{"role":"user","content":text}]
        last_error=None
        for _ in range(self.max_steps):
            try:
                if self.router is not None:
                    from app.core.model_router import TaskType as _TT
                    from app.core.fast_brain import simple_chitchat
                    greeting = bool(
                        self.router.fast_policy.enabled and simple_chitchat(text)
                    )
                    tools = None if greeting or research_result is not None else self.registry.ollama_tools(include_dangerous=True)
                    response=self.router.chat(_TT.GENERAL,messages,tools=tools)
                else:
                    tools = None if research_result is not None else self.registry.ollama_tools(include_dangerous=True)
                    response=self.brain.chat(messages,tools=tools)
            except Exception as e:
                from app.core.model_router import safe_provider_error
                last_error=("model", safe_provider_error(e)); break
            msg=response.get("message",{}); calls=self._extract_tool_calls(msg)
            if not calls:
                answer=self._persona_finalize((msg.get("content") or "").strip() or "Bunu tamamlayamadım.")
                if research_result is not None:
                    from app.cognitive.research_context import append_research_sources
                    answer=append_research_sources(answer,research_result)
                self._save("GÖLGE",answer); return answer
            messages.append(msg)
            for call in calls:
                fn=call.get("function",{}); name=fn.get("name",""); args=fn.get("arguments") or {}
                try:
                    raw=self.executor.execute([(name,args)],approved=approved)[0]
                    messages.append({"role":"tool","content":self._redact(json.dumps({"success":True,"result":raw},ensure_ascii=False,default=str))})
                except Exception as e:
                    detail=self._redact(str(e))
                    last_error=("tool", detail); messages.append({"role":"tool","content":json.dumps({"success":False,"error":detail},ensure_ascii=False)})
        if last_error and last_error[0] == "model":
            answer = ("Şu anda model hizmetine erişemiyorum. İsteğini tamamlayamadım; "
                      "biraz sonra yeniden deneyebilirsin."
                      if last_error[1] == "provider_temporarily_unavailable"
                      else "Model yanıtı üretilemedi. İsteğini tamamlayamadım.")
        elif last_error: answer=f"İşlemi tamamlayamadım: {last_error[1]}"
        else: answer="Görevi güvenli adım sınırında tamamlayamadım."
        answer=self._persona_finalize(answer)
        self._save("GÖLGE",answer); return answer
