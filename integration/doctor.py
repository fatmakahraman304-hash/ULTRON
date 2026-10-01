"""Real checks, isolated processes for the two applications' import namespaces."""
import argparse
import asyncio
import importlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from .paths import ROOT, BACKEND, LOGS
from .launcher import Services

class Unavailable(RuntimeError):
    pass


def probe(name):
    if name == 'MARK imports':
        for mod in ('mark_app','ui','core.gemini','core.audio_devices','core.viseme','core.wake_word','core.echo','actions.browser_control','actions.screen_processor','actions.system_monitor','dashboard.server'):
            importlib.import_module(mod)
    elif name == 'Core dependencies':
        for mod in ('google.genai','PyQt6.QtWidgets','numpy','sounddevice','aiohttp','fastapi','uvicorn','psutil','cryptography','PIL','pyautogui','pygetwindow','playwright','cv2','pytesseract'):
            importlib.import_module(mod)
    elif name in ('MARK config','Gemini config'):
        from memory.config_manager import load_api_keys
        cfg = load_api_keys()
        if name=='Gemini config' and not cfg.get('gemini_api_key'):
            raise Unavailable('NOT_CONFIGURED')
    elif name in ('Audio input','Audio output'):
        import sounddevice as sd
        field='max_input_channels' if name=='Audio input' else 'max_output_channels'
        if not any(d[field]>0 for d in sd.query_devices()):
            raise Unavailable('No device enumerated')
    elif name=='Wake word':
        import numpy as np
        from openwakeword.model import Model
        model=Model(wakeword_models=['hey_jarvis'],inference_framework='onnx')
        model.predict(np.zeros(1280,dtype=np.int16))
    elif name=='STT':
        sys.path.insert(0,str(BACKEND))
        from app.voice.local_whisper import load_whisper
        import numpy as np
        model, info=load_whisper('models/whisper-tiny')
        segments, _=model.transcribe(np.zeros(16000,dtype=np.float32),language='tr',vad_filter=False)
        list(segments)  # actually executes the inference pipeline
    elif name=='TTS':
        sys.path.insert(0,str(BACKEND))
        from app.voice.tts import TextToSpeech
        tts=TextToSpeech()
        if not tts.backend():
            raise Unavailable('No local TTS engine/model')
        audio, mime=asyncio.run(tts.synthesize('Merhaba. Sistem testi.'))
        assert len(audio)>44 and audio[:4]==b'RIFF', 'No WAV audio synthesized'
    elif name=='SQLite':
        with tempfile.TemporaryDirectory() as folder:
            from contextlib import closing
            with closing(sqlite3.connect(str(Path(folder)/'test.db'))) as db:
                db.execute('create table test(value text)')
                db.execute('insert into test values (?)',('roundtrip',))
                assert db.execute('select value from test').fetchone()[0]=='roundtrip'
    elif name=='Memory':
        sys.path.insert(0,str(BACKEND))
        from app.memory.sqlite_memory import Memory
        with tempfile.TemporaryDirectory() as folder:
            m=Memory(Path(folder)/'memory.db')
            row=m.add('TEST','doctor memory roundtrip')
            assert m.recent_full()[0]['content']=='doctor memory roundtrip'
            assert m.delete(row)
    elif name=='Vault':
        sys.path.insert(0,str(BACKEND))
        from app.security.vault import CredentialVault
        with tempfile.TemporaryDirectory() as folder:
            v=CredentialVault(folder)
            v.set('doctor','test-value')
            assert v.get('doctor')=='test-value'
            assert 'test-value' not in v.store_path.read_text()
            assert v.delete('doctor')
    elif name=='Playwright':
        from playwright.sync_api import sync_playwright
        from http.server import HTTPServer,BaseHTTPRequestHandler
        import threading
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'<title>MARK doctor</title>')
            def log_message(self,*args):
                return
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                page=browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}',timeout=15000)
                assert page.title()=='MARK doctor'
                browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
    elif name=='Screen capture':
        import pyautogui
        shot=pyautogui.screenshot()
        assert shot.width>0 and shot.height>0
    elif name=='OCR':
        import pytesseract
        from PIL import Image,ImageDraw,ImageFont
        if not shutil.which('tesseract'):
            candidate=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tesseract-OCR/tesseract.exe'
            if candidate.is_file(): pytesseract.pytesseract.tesseract_cmd=str(candidate)
        image=Image.new('RGB',(600,150),'white')
        font=ImageFont.truetype('arial.ttf',50)
        ImageDraw.Draw(image).text((15,30),'MARK 123',font=font,fill='black')
        text=pytesseract.image_to_string(image)
        assert '123' in text, 'OCR failed known image'
    elif name=='Plugin registry':
        from core.plugin_loader import discover_plugins
        registry=discover_plugins(ROOT/'plugins',set())
        assert registry.has('ultron_capability')
        assert all(row['valid'] for row in registry.list_for_ui())
    elif name=='Action registry':
        from core.action_loader import discover_actions
        registry=discover_actions(ROOT/'actions')
        assert registry.get_tool_declarations()
    elif name=='ULTRON imports':
        sys.path.insert(0,str(BACKEND))
        os.chdir(BACKEND)
        for mod in ('server','app.core.runtime','app.agent.supervisor','app.tasks.engine','app.voice.wake','app.security.vault'):
            importlib.import_module(mod)
    elif name=='Log write':
        target=LOGS/'doctor-write.tmp'
        target.write_text('roundtrip',encoding='utf-8')
        assert target.read_text()=='roundtrip'
        target.unlink()
    else:
        raise ValueError(name)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--probe')
    parser.add_argument('--quick',action='store_true')
    args=parser.parse_args()
    LOGS.mkdir(exist_ok=True)
    if args.probe:
        try:
            probe(args.probe)
            return 0
        except (Unavailable,FileNotFoundError,ModuleNotFoundError) as exc:
            print(type(exc).__name__+': '+str(exc)); return 2
        except Exception as exc:
            if (args.probe == 'Playwright' and ('spawn EPERM' in str(exc) or 'Executable doesn\'t exist' in str(exc))) or (args.probe == 'Screen capture' and isinstance(exc, OSError) and 'screen grab failed' in str(exc)):
                print('UNAVAILABLE: OS session/access restriction: '+str(exc)); return 2
            import traceback
            traceback.print_exc(); return 1
    rows=[]
    def record(name,status,detail=''):
        rows.append({'name':name,'status':status,'detail':str(detail)[-1500:]})
        print(f'{name:.<28} {status} {str(detail)[:120]}',flush=True)
    record('Python','PASS',sys.version.split()[0])
    record('Venv','PASS' if sys.prefix!=sys.base_prefix else 'FAIL')
    result=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True,timeout=60)
    record('pip check','PASS' if result.returncode==0 else 'FAIL',result.stdout+result.stderr)
    optional={'Gemini config','Audio input','Audio output','Wake word','STT','TTS','Playwright','Screen capture','OCR'}
    for name in ('Core dependencies','MARK imports','ULTRON imports','MARK config','Gemini config','Audio input','Audio output','Wake word','STT','TTS','SQLite','Memory','Vault','Playwright','Screen capture','OCR','Plugin registry','Action registry','Log write'):
        try:
            result=subprocess.run([sys.executable,'-m','integration.doctor','--probe',name],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            status='PASS' if result.returncode==0 else ('WARN' if result.returncode==2 and name in optional else 'FAIL')
            record(name,status,(result.stdout+result.stderr) if result.returncode else '')
        except subprocess.TimeoutExpired:
            record(name,'FAIL','timeout')
    custom=[p for p in (BACKEND/'data/voice/wake/ultron.onnx',BACKEND/'data/voice/wake/ultron.tflite') if p.is_file()]
    record('Custom ULTRON wake','WARN','Custom model present; acoustic validation required' if custom else 'CUSTOM_MODEL_NOT_INSTALLED')
    try:
        with Services() as service:
            health=service.start()
            record('Backend HTTP','PASS' if health['ok'] else 'FAIL')
            async def websocket():
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(service.bridge.url+'/ws',headers={'X-MARK-Token':service.bridge.token},timeout=10) as ws:
                        await ws.receive(timeout=10)
            asyncio.run(websocket());record('Backend WebSocket','PASS')
            record('Tool registry','PASS' if service.bridge.request('/api/tools') else 'FAIL')
            mem=service.bridge.request('/api/memory/v16/add',{'kind':'TEST','text':'MARK doctor temporary'})
            assert mem.get('ok'), mem
            found=service.bridge.request('/api/memory/v16')
            record('MARK-ULTRON bridge','PASS' if found else 'FAIL')
            if mem.get('id'):
                service.bridge.request('/api/memory/v16/delete',{'id':mem['id']})
            with tempfile.TemporaryDirectory() as folder:
                target=Path(folder)/'forbidden.txt'
                denied=service.bridge.request('/api/merged/tool',{'name':'write_text','arguments':{'path':str(target),'content':'forbidden'},'approved':True})
                record('Security approval','PASS' if not denied.get('ok') and not target.exists() else 'FAIL','Caller self-approval rejected')
            calculated=service.bridge.request('/api/merged/tool',{'name':'calculate','arguments':{'text':'2+3'}})
            record('Tool invocation','PASS' if calculated.get('result')==['5'] else 'FAIL')
            for folder,label in [('frontend','Desktop frontend'),('frontend-mobile','Mobile frontend')]:
                from urllib.request import Request,urlopen
                with urlopen(Request(service.bridge.url+'/'+folder+'/index.html',headers={'X-MARK-Token':service.bridge.token}),timeout=10) as response:
                    assert b'<html' in response.read()
                record(label,'PASS','Built HTML served over HTTP')
            record('Ollama','PASS' if health['ollama']['connected'] else 'WARN')
            if not args.quick and health['ollama']['connected']:
                reply=service.bridge.ask('Sadece TAMAM yaz.','fast')
                record('Ollama inference','PASS' if reply.get('ok') and reply.get('text') else 'FAIL',reply.get('error',''))
            else:
                record('Ollama inference','WARN','Not run in quick mode' if args.quick else 'UNAVAILABLE')
            models=health['ollama'].get('models',[])
            models=[m if isinstance(m,str) else m.get('name','') for m in models]
            vision=next((m for m in models if 'llava' in m),None)
            if args.quick or not vision:
                record('Vision model','WARN','Not run in quick mode' if args.quick else 'NOT_INSTALLED')
            else:
                from urllib.request import Request,urlopen
                from PIL import Image
                import base64,io
                buffer=io.BytesIO();Image.new('RGB',(64,64),'red').save(buffer,format='PNG')
                body={'model':vision,'prompt':'Name the main color. One word.', 'images':[base64.b64encode(buffer.getvalue()).decode()], 'stream':False,'options':{'num_predict':20}}
                try:
                    with urlopen(Request('http://127.0.0.1:11434/api/generate',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=180) as response:
                        answer=json.load(response)
                    record('Vision model','PASS' if answer.get('response','').strip() else 'FAIL','Actual image inference: '+answer.get('response',''))
                except (OSError,ValueError) as exc:
                    record('Vision model','WARN','Inference unavailable: '+str(exc))
    except Exception as exc:
        record('Backend/bridge','FAIL',exc)
    (LOGS/'doctor.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    return int(any(row['status']=='FAIL' for row in rows))

if __name__=='__main__':
    raise SystemExit(main())
